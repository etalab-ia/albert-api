from typing import Union

from fastapi import APIRouter, Path, Request, Security

from app.helpers import Authorization
from app.schemas.models import Model, Models
from app.utils.lifespan import context
from app.utils.variables import ENDPOINT__MODELS

router = APIRouter()


@router.get(path=ENDPOINT__MODELS + "/{model:path}", dependencies=[Security(dependency=Authorization())])
async def get_model(request: Request, model: str = Path(description="The name of the model to get.")) -> Model:
    """
    Get a model by name and provide basic informations.
    """

    model = context.models.list(model=model)[0]

    return model


@router.get(path=ENDPOINT__MODELS, dependencies=[Security(dependency=Authorization())])
async def get_models(request: Request) -> Union[Models, Model]:
    """
    Lists the currently available models and provides basic informations.
    """

    data = context.models.list()

    return Models(data=data)
