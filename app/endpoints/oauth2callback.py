from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse
from authlib.integrations.starlette_client import OAuth
from app.utils.settings import settings

router = APIRouter()

oauth = OAuth()
proconnect = oauth.register(
    name="proconnect",
    client_id=settings.proconnect.client_id,
    client_secret=settings.proconnect.client_secret,
    access_token_url=settings.proconnect.token_url,
    authorize_url=settings.proconnect.authorization_url,
    client_kwargs={"scope": settings.proconnect.scope},
)


@router.get("/proconnect/callback")
async def proconnect_callback(request: Request):
    try:
        # Exchange the authorization code for a token
        token = await proconnect.authorize_access_token(request)
        user_info = await proconnect.parse_id_token(request, token)

        # Generate a redirect URL to Streamlit with the token
        redirect_url = f"{settings.playground.home_url}?api_key={token['access_token']}"
        return RedirectResponse(url=redirect_url)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"ProConnect callback failed: {str(e)}")
