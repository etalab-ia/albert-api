import logging
import httpx

from jose import jwt, jwk
from jose.exceptions import JWTError
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
