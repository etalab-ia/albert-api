from fastapi import FastAPI, Response, Security

from app.endpoints import chat, chunks, collections, completions, embeddings, files, models, search, tools
from app.utils.config import APP_CONTACT_EMAIL, APP_CONTACT_URL, APP_DESCRIPTION, APP_VERSION
from app.utils.lifespan import lifespan
from app.utils.security import check_api_key

app = FastAPI(
    title="Albert API",
    version=APP_VERSION,
    description=APP_DESCRIPTION,
    contact={"url": APP_CONTACT_URL, "email": APP_CONTACT_EMAIL},
    licence_info={"name": "MIT License", "identifier": "MIT"},
    lifespan=lifespan,
)


@app.get("/health")
def health(user: str = Security(check_api_key)):
    """
    Health check.
    """

    return Response(status_code=200)


app.include_router(models.router, tags=["Models"], prefix="/v1")
app.include_router(chat.router, tags=["Chat"], prefix="/v1")
app.include_router(completions.router, tags=["Completions"], prefix="/v1")
app.include_router(embeddings.router, tags=["Embeddings"], prefix="/v1")
app.include_router(collections.router, tags=["Collections"], prefix="/v1")
app.include_router(chunks.router, tags=["Chunks"], prefix="/v1")
app.include_router(files.router, tags=["Files"], prefix="/v1")
app.include_router(search.router, tags=["Search"], prefix="/v1")
app.include_router(tools.router, tags=["Tools"], prefix="/v1")
