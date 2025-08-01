import logging
import httpx

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.helpers._identityaccessmanager import IdentityAccessManager
from app.sql.models import Role, User as UserTable
from app.utils.configuration import configuration
from .token import verify_jwt_signature

logger = logging.getLogger(__name__)


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
