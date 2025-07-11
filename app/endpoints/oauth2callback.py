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
        # Utiliser l'URL de redirection configurée plutôt que de la générer dynamiquement
        redirect_uri = settings.oauth2.redirect_uri

        # Redirect the user to the authorization URL
        return await oauth2.authorize_redirect(request, redirect_uri)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"OAuth2 login failed: {str(e)}")


@router.get(f"/{ROUTER__OAUTH2}/callback")
async def oauth2_callback(request: Request, session: AsyncSession = Depends(get_db_session)):
    try:
        # Exchange the authorization code for a token
        token = await oauth2.authorize_access_token(request)

        # DEBUG: Voir ce qui est retourné
        print(f"Token reçu: {token}")
        print(f"Access token: {token.get('access_token')}")
        print(f"Scope: {token.get('scope')}")

        # Récupérer les informations utilisateur via l'endpoint userinfo
        try:
            print("Tentative d'appel à userinfo...")
            user_info = await oauth2.userinfo(token=token)
            print(f"SUCCESS - User info from userinfo endpoint: {user_info}")
        except Exception as userinfo_error:
            print(f"ERREUR lors de l'appel userinfo: {userinfo_error}")
            print(f"Type d'erreur: {type(userinfo_error)}")
            # Réessayer avec juste l'access token
            try:
                print("Tentative avec access_token uniquement...")
                user_info = await oauth2.userinfo(token=token["access_token"])
                print(f"SUCCESS avec access_token - User info: {user_info}")
            except Exception as second_error:
                print(f"Échec aussi avec access_token: {second_error}")
                # Fallback: utiliser les infos déjà dans le token
                user_info = token.get("userinfo", {})
                print(f"Fallback - Using userinfo from token: {user_info}")

        # Extract user information
        sub = user_info.get("sub")
        email = user_info.get("email")
        given_name = user_info.get("given_name")
        usual_name = user_info.get("usual_name")
        expires_at = user_info.get("exp")

        print(f"Informations extraites - sub: {sub}, email: {email}, given_name: {given_name}, usual_name: {usual_name}")

        # Vérifier les informations obligatoires
        if not sub:
            raise HTTPException(status_code=400, detail="Missing subject (sub) in user info")

        # Initialize IdentityAccessManager
        iam = IdentityAccessManager()

        # Search for an existing user
        user = await iam.get_user(session=session, sub=sub, email=email)

        # If no user is found, create a new one
        if not user:
            user_id = await iam.create_user(
                session=session,
                name=f"{given_name or ''} {usual_name or ''}".strip() or "Unknown User",
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
        print(f"Erreur générale: {e}")
        raise HTTPException(status_code=400, detail=f"OAuth2 callback failed: {str(e)}")
