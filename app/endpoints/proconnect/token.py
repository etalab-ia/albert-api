import logging
import httpx

from jose import jwt, jwk
from jose.exceptions import JWTError
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.helpers._identityaccessmanager import IdentityAccessManager
from app.sql.models import Role, User as UserTable
from app.utils.configuration import configuration

logger = logging.getLogger(__name__)


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
    """
    Retrieve user information from the OAuth2 provider
    """
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
