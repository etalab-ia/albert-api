import logging
from urllib.parse import urlparse
import base64
import json
import time

from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, Depends, HTTPException, Request, Security
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.helpers._accesscontroller import AccessController
from app.utils.context import global_context, request_context
from app.schemas.auth import OAuth2LogoutRequest, User
from app.sql.session import get_db_session
from app.utils.configuration import configuration
from app.utils.variables import ROUTER__OAUTH2

from .encryption import encrypt_redirect_data
from .token import perform_proconnect_logout
from .user import retrieve_user_info, create_user

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


def generate_redirect_url(request, app_token, token_id, proconnect_token, original_url=None):
    """
    Generate redirect URL with domain validation and token encryption
    """
    parsed_url = urlparse(original_url)
    request_domain = parsed_url.netloc.split(":")[0]  # Extract domain without port

    # Get allowed domains from configuration and parse them if it's a string
    allowed_domains_config = configuration.dependencies.proconnect.allowed_domains
    # Split the comma-separated string and strip whitespace
    allowed_domains = [domain.strip() for domain in allowed_domains_config.split(",")]

    # Check if the request domain or its parent domain is allowed
    if not any(request_domain == allowed_domain or request_domain.endswith(f".{allowed_domain}") for allowed_domain in allowed_domains):
        raise HTTPException(status_code=400, detail=f"Invalid domain: {request_domain} not in allowed domains or their subdomains")

    # Encrypt the tokens into a single parameter
    encrypted_data = encrypt_redirect_data(app_token, token_id, proconnect_token)

    # Generate a redirect URL to the origin with the encrypted data
    origin = f"{parsed_url.scheme}://{parsed_url.netloc}"
    redirect_url = f"{origin}?encrypted_token={encrypted_data}"
    return redirect_url


@router.get(f"/{ROUTER__OAUTH2}/login")
async def oauth2_login(request: Request, oauth2_client=Depends(get_oauth2_client)):
    """
    Initiate the OAuth2 login flow with ProConnect with time-stamped state to invalidate old requests
    """
    try:
        redirect_uri = configuration.dependencies.proconnect.redirect_uri
        original_url = request.headers.get("referer") or request.query_params.get("origin")
        state_data = {"original_url": original_url, "timestamp": int(time.time())}
        state = base64.urlsafe_b64encode(json.dumps(state_data).encode()).decode()
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
    """
    Handle OAuth2 callback from ProConnect
    """
    # Try to decode the state parameter to get the original URL and validate timestamp
    try:
        state = request.query_params.get("state")
        decoded_state = base64.urlsafe_b64decode(state.encode()).decode()
        state_data = json.loads(decoded_state)
        original_url = state_data.get("original_url")
        timestamp = state_data.get("timestamp")
        if timestamp is None:
            raise HTTPException(status_code=400, detail="Missing timestamp in state parameter")
        current_time = int(time.time())
        # Allow a 10-minute window for the OAuth2 flow to complete
        timestamp_expiry = 600  # 10 minutes in seconds
        if current_time - timestamp > timestamp_expiry:
            raise HTTPException(status_code=400, detail="OAuth2 request has expired. Please try again.")

    except HTTPException:
        raise  # Re-raise HTTPException as-is
    except Exception as e:
        logger.error(f"Could not decode state parameter: {e}")
        raise HTTPException(status_code=400, detail="No original URL found in state or request")

    try:
        # Exchange the authorization code for a token
        token = await oauth2_client.authorize_access_token(request)
        user_info = await retrieve_user_info(token, oauth2_client)

        # Extract user information
        sub, email, given_name, usual_name = (user_info.get(key) for key in ("sub", "email", "given_name", "usual_name"))

        # Verify required information
        if not sub:
            raise HTTPException(status_code=400, detail="Missing subject (sub) in user info")

        # Search for an existing user
        iam = global_context.identity_access_manager
        user = await iam.get_user(session=session, sub=sub)
        if user and user.email != email:
            logger.info(f"User {user.id} email mismatch: {user.email} != {email}. Updating email.")
            user.email = email
            session.add(user)
            await session.commit()
        elif user := await iam.get_user(session=session, email=email):
            logger.info(f"Found user {user.id} by email: {email}, setting sub to {sub}")
            user.sub = sub
            session.add(user)
            await session.commit()
        else:
            user = await create_user(session, iam, given_name, usual_name, email, sub)

        token_id, app_token = await iam.refresh_token(session=session, user_id=user.id, name="playground")

        # Extract ProConnect token (id_token for logout functionality)
        proconnect_token = token.get("id_token", "")

        # Validate the origin of the request with state information
        redirect_url = generate_redirect_url(request, app_token, token_id, proconnect_token, original_url)
        return RedirectResponse(url=redirect_url)
    except Exception as e:
        logger.exception(f"General error: {e}")
        raise HTTPException(status_code=400, detail=f"OAuth2 callback failed: {str(e)}")


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
