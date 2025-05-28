from fastapi import APIRouter, Path, Request, Security
from fastapi.responses import JSONResponse

from app.helpers.core import AccessController
from app.schemas.models import Model, Models
from app.utils.context import global_context
from app.utils.variables import ENDPOINT__MODELS

router = APIRouter()


@router.get(path=ENDPOINT__MODELS + "/{model:path}", dependencies=[Security(dependency=AccessController())], status_code=200, response_model=Model)
async def get_model(request: Request, model: str = Path(description="The name of the model to get.")) -> JSONResponse:
    """
    Get a model by name and provide basic informations.
    """

    model = global_context.models.list(model=model)[0]

    return JSONResponse(content=model.model_dump(), status_code=200)


@router.get(path=ENDPOINT__MODELS, dependencies=[Security(dependency=AccessController())], status_code=200, response_model=Models)
async def get_models(request: Request) -> JSONResponse:
    """
    Lists the currently available models and provides basic informations.
    """

    data = global_context.models.list()

    return JSONResponse(content=Models(data=data).model_dump(), status_code=200)
