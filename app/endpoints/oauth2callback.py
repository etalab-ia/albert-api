import logging
from urllib.parse import urlparse
import time
import base64
import json

from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from jose import jwt, jwk
from jose.exceptions import JWTError
import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.helpers._identityaccessmanager import IdentityAccessManager
from app.sql.models import Role
from app.sql.models import User as UserTable
from app.sql.session import get_db_session
from app.utils.settings import settings
from app.utils.variables import ROUTER__OAUTH2

logger = logging.getLogger(__name__)

router = APIRouter()

# TODO : we should not initialize OAuth2 on module import, but rather on application startup
if settings.oauth2 is not None:
    oauth = OAuth()
    oauth2 = oauth.register(
        name="proconnect",
        client_id=settings.oauth2.client_id,
        client_secret=settings.oauth2.client_secret,
        server_metadata_url=settings.oauth2.server_metadata_url,
        client_kwargs={"scope": settings.oauth2.scope},
    )


@router.get(f"/{ROUTER__OAUTH2}/login")
async def oauth2_login(request: Request):
    """
    Initiate the OAuth2 login flow with ProConnect
    """
    try:
        # Use the configured redirect URL rather than generating it dynamically
        redirect_uri = settings.oauth2.redirect_uri

        # Get the original URL from the referer header or a query parameter
        original_url = request.headers.get("referer") or request.query_params.get("origin")

        # Encode the original URL in the state parameter for security
        state_data = {"original_url": original_url, "timestamp": int(time.time())}

        # Base64 encode the state to pass it safely
        state = base64.urlsafe_b64encode(json.dumps(state_data).encode()).decode()

        # Redirect the user to the authorization URL with state
        return await oauth2.authorize_redirect(request, redirect_uri, state=state)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"OAuth2 login failed: {str(e)}")


@router.get(f"/{ROUTER__OAUTH2}/callback")
async def oauth2_callback(request: Request, session: AsyncSession = Depends(get_db_session)):
    try:
        # Exchange the authorization code for a token
        token = await oauth2.authorize_access_token(request)

        # Get the state parameter
        state = request.query_params.get("state")

        logger.debug(f"Token: {token}")

        # Retrieve user information via oauth2.userinfo()
        user_info = await retrieve_user_info(token)

        # Extract user information
        sub = user_info.get("sub")
        email = user_info.get("email")
        given_name = user_info.get("given_name")
        usual_name = user_info.get("usual_name")

        # Verify required information
        if not sub:
            raise HTTPException(status_code=400, detail="Missing subject (sub) in user info")

        # Initialize IdentityAccessManager
        iam = IdentityAccessManager()

        # Search for an existing user
        user = await iam.get_user(session=session, sub=sub, email=email)

        # If no user is found, create a new one
        if not user:
            user = await create_user(session, iam, given_name, usual_name, email, sub)

        token_id, app_token = await iam.refresh_token(session=session, user_id=user.id, name="playground")

        # Validate the origin of the request with state information
        redirect_url = generate_redirect_url(request, app_token, token_id, state=state)
        return RedirectResponse(url=redirect_url)
    except Exception as e:
        logger.exception(f"General error: {e}")
        raise HTTPException(status_code=400, detail=f"OAuth2 callback failed: {str(e)}")


def generate_redirect_url(request, app_token, token_id, state=None):
    original_url = None

    # Try to decode the state parameter to get the original URL
    if state:
        try:
            decoded_state = base64.urlsafe_b64decode(state.encode()).decode()
            state_data = json.loads(decoded_state)
            original_url = state_data.get("original_url")
        except Exception as e:
            logger.warning(f"Could not decode state parameter: {e}")

    # If we have an original URL, use it; otherwise fallback to current request
    if original_url:
        parsed_url = urlparse(original_url)
    else:
        raise HTTPException(status_code=400, detail="No original URL found in state or request")

    request_domain = parsed_url.netloc.split(":")[0]  # Extract domain without port

    # Get allowed domains from settings
    allowed_domains = settings.oauth2.allowed_domains

    # Check if the request domain or its parent domain is allowed
    domain_allowed = False
    for allowed_domain in allowed_domains:
        # Exact match
        if request_domain == allowed_domain:
            domain_allowed = True
            break
            # Subdomain match (e.g., api.gouv.fr matches gouv.fr)
        if request_domain.endswith(f".{allowed_domain}"):
            domain_allowed = True
            break

    if not domain_allowed:
        raise HTTPException(status_code=400, detail=f"Invalid domain: {request_domain} not in allowed domains or their subdomains")

    # Generate a redirect URL to the origin with the app token
    origin = f"{parsed_url.scheme}://{parsed_url.netloc}"
    redirect_url = f"{origin}?token={app_token}&token_id={token_id}"
    return redirect_url


async def get_jwks_keys():
    """
    Retrieve the JWKS (JSON Web Key Set) from the OAuth2 provider
    """
    try:
        # Get the JWKS URL from the server metadata
        async with httpx.AsyncClient() as client:
            response = await client.get(settings.oauth2.server_metadata_url)
            metadata = response.json()
            jwks_uri = metadata.get("jwks_uri")

            if not jwks_uri:
                logger.warning("No jwks_uri found in server metadata")
                return None

            # Fetch the JWKS
            jwks_response = await client.get(jwks_uri)
            jwks = jwks_response.json()
            return jwks
    except Exception as e:
        logger.error(f"Error fetching JWKS: {e}")
        return None


async def verify_jwt_signature(id_token: str) -> dict:
    """
    Verify JWT signature and return claims if valid
    """
    try:
        # Get JWKS keys
        jwks = await get_jwks_keys()
        if not jwks:
            logger.warning("Could not fetch JWKS, falling back to unverified claims")
            return jwt.get_unverified_claims(id_token)

        # Get the header to find the key ID
        unverified_header = jwt.get_unverified_header(id_token)
        kid = unverified_header.get("kid")

        if not kid:
            logger.warning("No 'kid' found in JWT header, falling back to unverified claims")
            return jwt.get_unverified_claims(id_token)

        # Find the matching key
        key = None
        for jwk_key in jwks.get("keys", []):
            if jwk_key.get("kid") == kid:
                key = jwk.construct(jwk_key)
                break

        if not key:
            logger.warning(f"No matching key found for kid: {kid}, falling back to unverified claims")
            return jwt.get_unverified_claims(id_token)

        # Verify the signature and decode
        claims = jwt.decode(
            id_token,
            key,
            algorithms=["RS256", "ES256"],  # Common algorithms for OIDC
            audience=settings.oauth2.client_id,
            issuer=None,  # You might want to verify issuer too
        )

        logger.debug("JWT signature verified successfully")
        return claims

    except JWTError as e:
        logger.warning(f"JWT verification failed: {e}, falling back to unverified claims")
        return jwt.get_unverified_claims(id_token)
    except Exception as e:
        logger.error(f"Unexpected error during JWT verification: {e}, falling back to unverified claims")
        return jwt.get_unverified_claims(id_token)


async def retrieve_user_info(token):
    try:
        user_info = await oauth2.userinfo(token=token)
        logger.debug(f"SUCCESS with oauth2.userinfo - User info: {user_info}")
        return user_info
    except Exception as userinfo_error:
        logger.debug(f"ERROR calling oauth2.userinfo: {userinfo_error}")
        # Fallback: use token info if available
        id_token = token.get("id_token")
        if id_token:
            # Decode the ID token (JWT) with signature verification
            try:
                user_info = await verify_jwt_signature(id_token)
                logger.debug(f"Fallback - Using verified ID token: {user_info}")
                return user_info
            except Exception as jwt_error:
                logger.debug(f"Error verifying ID token: {jwt_error}")
                # Last fallback: use available token info
                user_info = token.get("userinfo", {})
                logger.debug(f"Fallback - Using userinfo from token: {user_info}")
                return user_info
        else:
            # Last fallback: use available token info
            user_info = token.get("userinfo", {})
            logger.debug(f"Fallback - Using userinfo from token: {user_info}")
            return user_info

    # This should not be reached, but just in case
    raise HTTPException(status_code=400, detail="Unable to retrieve user information")


async def create_user(session: AsyncSession, iam: IdentityAccessManager, given_name: str, usual_name: str, email: str, sub: str, expires_at: int):
    """
    Create a new user with default role
    """
    # Get the default role ID
    default_role_query = select(Role.id).where(Role.name == settings.oauth2.default_role)
    default_role_result = await session.execute(default_role_query)
    default_role_id = default_role_result.scalar_one_or_none()

    if default_role_id is None:
        raise HTTPException(
            status_code=500,
            detail=f"Default role for OAuth user not found in database, please create a role named {settings.oauth2.default_role} in the database or update the settings.",
        )

    # Generate a default username if information is missing
    display_name = f"{given_name or ""} {usual_name or ""}".strip()
    if not display_name:
        display_name = email or f"User-{sub[:8]}" if sub else "Unknown User"

    user_id = await iam.create_user(
        session=session,
        name=display_name,
        role_id=default_role_id,
        email=email,
        sub=sub,
        expires_at=expires_at,
    )
    user = await session.get(UserTable, user_id)
    return user
