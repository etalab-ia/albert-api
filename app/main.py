from fastapi import FastAPI, Security, Response

from utils.lifespan import lifespan
from utils.security import check_api_key
from endpoints import (
    ChatRouter,
    CollectionsRouter,
    CompletionsRouter,
    EmbeddingsRouter,
    FilesRouter,
    ModelsRouter,
    ToolsRouter,
)

# @TODO: add metadata: https://fastapi.tiangolo.com/tutorial/metadata/
app = FastAPI(title="Albert API", version="1.0.0", lifespan=lifespan)


@app.get("/health")
def health(api_key: str = Security(check_api_key)):
    """
    Health check.
    """

    return Response(status_code=200)


app.include_router(ModelsRouter, tags=["Models"], prefix="/v1")
app.include_router(ChatRouter, tags=["Chat"], prefix="/v1")
app.include_router(CompletionsRouter, tags=["Completions"], prefix="/v1")
app.include_router(CollectionsRouter, tags=["Collections"], prefix="/v1")
app.include_router(EmbeddingsRouter, tags=["Embeddings"], prefix="/v1")
app.include_router(FilesRouter, tags=["Files"], prefix="/v1")
app.include_router(ToolsRouter, tags=["Tools"], prefix="/v1")
