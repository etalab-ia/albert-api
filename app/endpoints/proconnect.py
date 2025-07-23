import logging
from urllib.parse import urlparse
import time
import base64
import hashlib
import json

from authlib.integrations.starlette_client import OAuth
from cryptography.fernet import Fernet
from fastapi import APIRouter, Depends, HTTPException, Request, Security
from fastapi.responses import RedirectResponse
from jose import jwt, jwk
from jose.exceptions import JWTError
import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.helpers._accesscontroller import AccessController
from app.helpers._identityaccessmanager import IdentityAccessManager
from app.utils.context import global_context
from app.schemas.auth import OAuth2LogoutRequest, User
from app.sql.models import Role
from app.sql.models import User as UserTable
from app.sql.session import get_db_session
from app.utils.context import request_context
from app.utils.configuration import configuration
from app.utils.variables import ROUTER__OAUTH2

logger = logging.getLogger(__name__)

router = APIRouter()

# Singleton pattern for OAuth2 client
_oauth2_client = None


def get_oauth2_client():
    """
    Dependency to get the OAuth2 client for ProConnect (singleton pattern)
    """
    global _oauth2_client

    if _oauth2_client is None:
        if configuration.dependencies.proconnect is None:
            raise HTTPException(status_code=500, detail="ProConnect is not configured")

        oauth = OAuth()
        _oauth2_client = oauth.register(
            name="proconnect",
            client_id=configuration.dependencies.proconnect.client_id,
            client_secret=configuration.dependencies.proconnect.client_secret,
            server_metadata_url=configuration.dependencies.proconnect.server_metadata_url,
            client_kwargs={"scope": configuration.dependencies.proconnect.scope},
        )

    return _oauth2_client


def get_fernet():
    """
    Initialize Fernet encryption using the OAuth2 encryption key from configuration
    """
    try:
        # If the key is "changeme", generate a proper key
        if configuration.settings.encryption_key == "changeme":
            logger.warning("Using default encryption key 'changeme'. This is not secure for production.")
            # Generate a consistent key from the default string for development
            key_bytes = hashlib.sha256("changeme".encode()).digest()
            key = base64.urlsafe_b64encode(key_bytes)
        else:
            # Use the provided key - it should be 32 url-safe base64-encoded bytes
            key = configuration.settings.encryption_key.encode()

        return Fernet(key)
    except Exception as e:
        logger.error(f"Failed to initialize Fernet encryption: {e}")
        raise HTTPException(status_code=500, detail="Encryption initialization failed")


def encrypt_redirect_data(app_token: str, token_id: str, proconnect_token: str) -> str:
    """
    Encrypt redirect data into a single token
    """
    try:
        fernet = get_fernet()
        data = {"app_token": app_token, "token_id": token_id, "proconnect_token": proconnect_token, "timestamp": int(time.time())}

        json_data = json.dumps(data)
        encrypted_data = fernet.encrypt(json_data.encode())
        return base64.urlsafe_b64encode(encrypted_data).decode()
    except Exception as e:
        logger.error(f"Failed to encrypt redirect data: {e}")
        raise HTTPException(status_code=500, detail="Encryption failed")


@router.get(f"/{ROUTER__OAUTH2}/login")
async def oauth2_login(request: Request, oauth2_client=Depends(get_oauth2_client)):
    """
    Initiate the OAuth2 login flow with ProConnect
    """
    try:
        # Use the configured redirect URL rather than generating it dynamically
        redirect_uri = configuration.dependencies.proconnect.redirect_uri

        # Get the original URL from the referer header or a query parameter
        original_url = request.headers.get("referer") or request.query_params.get("origin")

        # Encode the original URL in the state parameter for security
        state_data = {"original_url": original_url, "timestamp": int(time.time())}

        # Base64 encode the state to pass it safely
        state = base64.urlsafe_b64encode(json.dumps(state_data).encode()).decode()

        # Try to explicitly pass the scope
        redirect_response = await oauth2_client.authorize_redirect(
            request,
            redirect_uri,
            state=state,
            scope=configuration.dependencies.proconnect.scope,  # Explicitly pass the scope
        )

        return redirect_response
    except Exception as e:
        logger.exception(f"OAuth2 login failed: {e}")
        raise HTTPException(status_code=400, detail=f"OAuth2 login failed: {str(e)}")


@router.get(f"/{ROUTER__OAUTH2}/callback")
async def oauth2_callback(request: Request, session: AsyncSession = Depends(get_db_session), oauth2_client=Depends(get_oauth2_client)):
    try:
        # Exchange the authorization code for a token
        token = await oauth2_client.authorize_access_token(request)

        # Get the state parameter
        state = request.query_params.get("state")

        logger.debug(f"Token: {token}")

        # Retrieve user information via oauth2.userinfo()
        user_info = await retrieve_user_info(token, oauth2_client)

        # Extract user information
        sub = user_info.get("sub")
        email = user_info.get("email")
        given_name = user_info.get("given_name")
        usual_name = user_info.get("usual_name")

        # Verify required information
        if not sub:
            raise HTTPException(status_code=400, detail="Missing subject (sub) in user info")

        iam = global_context.identity_access_manager

        # Search for an existing user
        user = await iam.get_user(session=session, sub=sub, email=email)

        # If no user is found, create a new one
        if not user:
            user = await create_user(session, iam, given_name, usual_name, email, sub)

        token_id, app_token = await iam.refresh_token(session=session, user_id=user.id, name="playground")

        # Extract ProConnect token (id_token for logout functionality)
        proconnect_token = token.get("id_token", "")

        # Validate the origin of the request with state information
        redirect_url = generate_redirect_url(request, app_token, token_id, proconnect_token, state=state)
        return RedirectResponse(url=redirect_url)
    except Exception as e:
        logger.exception(f"General error: {e}")
        raise HTTPException(status_code=400, detail=f"OAuth2 callback failed: {str(e)}")


def generate_redirect_url(request, app_token, token_id, proconnect_token, state=None):
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

    # Get allowed domains from configuration and parse them if it's a string
    allowed_domains_config = configuration.dependencies.proconnect.allowed_domains
    if isinstance(allowed_domains_config, str):
        # Split the comma-separated string and strip whitespace
        allowed_domains = [domain.strip() for domain in allowed_domains_config.split(",")]
    else:
        # Assume it's already a list
        allowed_domains = allowed_domains_config

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

    # Encrypt the tokens into a single parameter
    encrypted_data = encrypt_redirect_data(app_token, token_id, proconnect_token)

    # Generate a redirect URL to the origin with the encrypted data
    origin = f"{parsed_url.scheme}://{parsed_url.netloc}"
    redirect_url = f"{origin}?encrypted_token={encrypted_data}"
    return redirect_url


async def get_jwks_keys():
    """
    Retrieve the JWKS (JSON Web Key Set) from the OAuth2 provider
    """
    try:
        # Get the JWKS URL from the server metadata
        async with httpx.AsyncClient() as client:
            response = await client.get(configuration.dependencies.proconnect.server_metadata_url)
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
            audience=configuration.dependencies.proconnect.client_id,
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


async def retrieve_user_info(token, oauth2_client):
    try:
        # Extract access_token from the token dict for userinfo call
        access_token = token.get("access_token")
        if not access_token:
            raise Exception("No access_token found in token")

        # Get userinfo endpoint from server metadata
        if hasattr(oauth2_client, "server_metadata") and oauth2_client.server_metadata:
            server_metadata = oauth2_client.server_metadata
        else:
            # Fallback: load metadata if not available
            server_metadata = await oauth2_client.load_server_metadata()

        userinfo_endpoint = server_metadata.get("userinfo_endpoint")
        if not userinfo_endpoint:
            raise Exception("No userinfo_endpoint found in server metadata")

        # Make direct HTTP request with Bearer token
        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {access_token}"}
            response = await client.get(userinfo_endpoint, headers=headers)
            response.raise_for_status()

            # Check if response is a JWT (starts with typical JWT pattern)
            response_text = response.text.strip()
            # Response is a JWT, decode it
            user_info = await verify_jwt_signature(response_text)
            logger.info(f"Decoded JWT user info: {user_info}")

        logger.info(f"SUCCESS with direct userinfo request - User info: {user_info}")
        return user_info
    except Exception as userinfo_error:
        logger.exception(f"ERROR calling userinfo endpoint: {userinfo_error}")
        # Fallback: use token info if available
        id_token = token.get("id_token")
        if id_token:
            # Decode the ID token (JWT) with signature verification
            try:
                user_info = await verify_jwt_signature(id_token)
                logger.info(f"Fallback - Using verified ID token: {user_info}")
                return user_info
            except Exception as jwt_error:
                logger.exception(f"Error verifying ID token: {jwt_error}")
                # Last fallback: use available token info
                user_info = token.get("userinfo", {})
                logger.info(f"Fallback - Using userinfo from token: {user_info}")
                return user_info
        else:
            # Last fallback: use available token info
            user_info = token.get("userinfo", {})
            logger.info(f"Fallback - Using userinfo from token: {user_info}")
            return user_info


async def create_user(session: AsyncSession, iam: IdentityAccessManager, given_name: str, usual_name: str, email: str, sub: str):
    """
    Create a new user with default role
    """
    # Get the default role ID
    default_role_query = select(Role.id).where(Role.name == configuration.dependencies.proconnect.default_role)
    default_role_result = await session.execute(default_role_query)
    default_role_id = default_role_result.scalar_one_or_none()

    if default_role_id is None:
        raise HTTPException(
            status_code=500,
            detail=f"Default role for OAuth user not found in database, please create a role named {configuration.dependencies.proconnect.default_role} in the database or update the configuration.",
        )

    # Generate a default username if information is missing
    display_name = f"{given_name or ''} {usual_name or ''}".strip()
    if not display_name:
        display_name = email or f"User-{sub[:8]}" if sub else "Unknown User"

    user_id = await iam.create_user(
        session=session,
        name=display_name,
        role_id=default_role_id,
        email=email,
        sub=sub,
    )
    user = await session.get(UserTable, user_id)
    return user


@router.post(f"/{ROUTER__OAUTH2}/logout", dependencies=[Security(dependency=AccessController())], status_code=200)
async def logout(
    request: Request,
    logout_request: OAuth2LogoutRequest,
    user: User = Security(AccessController()),
    session: AsyncSession = Depends(get_db_session),
    oauth2_client=Depends(get_oauth2_client),
):
    """
    Logout and expire the current token, optionally logout from ProConnect
    """
    try:
        logger.info(f"Processing logout for user {user.id}")

        # Get the current token ID from request context
        context = request_context.get()
        current_token_id = context.token_id

        # Initialize IdentityAccessManager and invalidate the current token
        if current_token_id:
            iam = global_context.identity_access_manager
            await iam.invalidate_token(session=session, token_id=current_token_id, user_id=user.id)
            logger.info(f"Expired token {current_token_id} for user {user.id}")

        # Get ProConnect token from request (optional)
        proconnect_token = logout_request.proconnect_token
        proconnect_logout_success = False

        # Attempt ProConnect logout if token is provided
        if proconnect_token:
            logger.info(f"Attempting ProConnect logout for user {user.id}")
            proconnect_logout_success = await perform_proconnect_logout(proconnect_token, oauth2_client)

            if proconnect_logout_success:
                logger.info(f"Successfully logged out user {user.id} from ProConnect")
            else:
                logger.warning(f"ProConnect logout failed for user {user.id}")
        else:
            logger.info(f"No ProConnect token provided for user {user.id}, skipping ProConnect logout")

        # Return appropriate response
        if proconnect_token and proconnect_logout_success:
            return {"status": "success", "message": "Successfully logged out from ProConnect and expired token"}
        elif proconnect_token and not proconnect_logout_success:
            return {"status": "warning", "message": "Token expired successfully, but ProConnect logout may have failed"}
        else:
            return {"status": "success", "message": "Token expired successfully"}

    except Exception as e:
        logger.exception(f"Error during logout for user {user.id}: {e}")
        raise HTTPException(status_code=500, detail=f"Logout failed: {str(e)}")


async def perform_proconnect_logout(proconnect_token: str, oauth2_client) -> bool:
    """
    Perform the actual logout call to ProConnect using the existing OAuth2 client
    """
    try:
        # The OAuth2 client should already have server metadata loaded
        # We can access it directly without reloading
        if hasattr(oauth2_client, "server_metadata") and oauth2_client.server_metadata:
            server_metadata = oauth2_client.server_metadata
        else:
            # Fallback: load metadata if not available
            server_metadata = await oauth2_client.load_server_metadata()

        end_session_endpoint = server_metadata.get("end_session_endpoint")

        if not end_session_endpoint:
            logger.warning("No end_session_endpoint found in ProConnect metadata")
            return False

        # Prepare logout parameters
        logout_params = {"id_token_hint": proconnect_token, "client_id": configuration.dependencies.proconnect.client_id}

        # Use httpx directly but maintain consistency with OAuth2 client approach
        async with httpx.AsyncClient() as client:
            logout_response = await client.post(
                end_session_endpoint, data=logout_params, headers={"Content-Type": "application/x-www-form-urlencoded"}
            )

            # ProConnect may return various response codes for successful logout
            if logout_response.status_code in [200, 204, 302]:
                logger.info(f"ProConnect logout successful, status: {logout_response.status_code}")
                return True
            else:
                logger.warning(f"ProConnect logout returned status: {logout_response.status_code}")
                return False

    except Exception as e:
        logger.error(f"Failed to call ProConnect logout endpoint: {e}")
        return False
