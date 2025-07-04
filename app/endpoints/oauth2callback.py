from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import RedirectResponse
from authlib.integrations.starlette_client import OAuth
from app.utils.settings import settings
from app.helpers._identityaccessmanager import IdentityAccessManager
from sqlalchemy.ext.asyncio import AsyncSession
from app.sql.models import User as UserTable
from app.utils.variables import ROUTER__OAUTH2
from urllib.parse import urlparse
from app.sql.session import get_db_session

router = APIRouter()

oauth = OAuth()
oauth2 = oauth.register(
    name="proconnect",
    client_id=settings.oauth2.client_id,
    client_secret=settings.oauth2.client_secret,
    access_token_url=settings.oauth2.token_url,
    authorize_url=settings.oauth2.authorization_url,
    client_kwargs={"scope": settings.oauth2.scope},
)


@router.get(f"/{ROUTER__OAUTH2}/callback")
async def oauth2_callback(request: Request, session: AsyncSession = Depends(get_db_session)):
    try:
        # Exchange the authorization code for a token
        token = await oauth2.authorize_access_token(request)
        user_info = await oauth2.parse_id_token(request, token)

        # Extract user information
        sub = user_info.get("sub")
        email = user_info.get("email")
        given_name = user_info.get("given_name")
        usual_name = user_info.get("usual_name")
        expires_at = user_info.get("exp")

        # Initialize IdentityAccessManager
        iam = IdentityAccessManager()

        # Search for an existing user
        user = await iam.get_user(session=session, sub=sub, email=email)

        # If no user is found, create a new one
        if not user:
            user_id = await iam.create_user(
                session=session,
                name=f"{given_name} {usual_name}",
                role_id=1,  # TODO : create a default role for ProConnect users
                email=email,
                sub=sub,
                expires_at=expires_at,
            )
            user = await session.get(UserTable, user_id)

        # Create a token for the user
        _, app_token = await iam.create_token(session=session, user_id=user.id, name="ProConnect Token", expires_at=expires_at)

        # Validate the origin of the request
        parsed_url = urlparse(str(request.url))
        origin = f"{parsed_url.scheme}://{parsed_url.netloc}"
        allowed_origins = settings.oauth2.allowed_origins  # Retrieve allowed origins from settings
        if origin not in allowed_origins:
            raise HTTPException(status_code=400, detail="Invalid origin")

        # Generate a redirect URL to the origin with the app token
        redirect_url = f"{origin}?api_key={app_token}"
        return RedirectResponse(url=redirect_url)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"OAuth2 callback failed: {str(e)}")
