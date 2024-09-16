from app.schemas.config import EMBEDDINGS_MODEL_TYPE
from app.utils.lifespan import clients
from fastapi import HTTPException
from pydantic import BaseModel, RootModel, validator


class EmbeddingsModel(BaseModel):
    root: str

    @validator("root")
    def check_model(cls, v, values, **kwargs):
        if clients["models"][v].type != EMBEDDINGS_MODEL_TYPE:

            raise HTTPException(
                status_code=400, detail=f"Model type must be {EMBEDDINGS_MODEL_TYPE}"
            )
        return v
