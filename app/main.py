from fastapi import FastAPI

from utils.lifespan import lifespan
from endpoints import AlbertRouter, StandardRouter

# @TODO: add metadata: https://fastapi.tiangolo.com/tutorial/metadata/
app = FastAPI(title="Albert API", version="1.0.0", lifespan=lifespan)

app.include_router(StandardRouter, tags=["Standard"], prefix="/v1")
app.include_router(AlbertRouter, tags=["Albert"], prefix="/v1")
