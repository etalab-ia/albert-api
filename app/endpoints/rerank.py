from fastapi import APIRouter, Request, Security

from app.helpers import LanguageModelReranker
from app.schemas.rerank import RerankRequest, Reranks
from app.schemas.security import User
from app.utils.lifespan import clients, limiter
from app.utils.security import check_api_key, check_rate_limit
from app.utils.settings import settings
from app.utils.variables import LANGUAGE_MODEL_TYPE, RERANK_MODEL_TYPE

from app.utils.exceptions import WrongModelTypeException

router = APIRouter()


@router.post("/rerank")
@limiter.limit(settings.rate_limit.by_key, key_func=lambda request: check_rate_limit(request=request))
async def rerank(request: Request, body: RerankRequest, user: User = Security(check_api_key)):
    """
    Rerank a list of inputs with a language model or reranker model.
    """
    model = clients.models[body.model]

    if model.type == LANGUAGE_MODEL_TYPE:
        reranker = LanguageModelReranker(model=model)
        data = reranker.create(prompt=body.prompt, input=body.input)
    elif model.type == RERANK_MODEL_TYPE:
        data = model.rerank.create(prompt=body.prompt, input=body.input, model=model.id)
    else:
        raise WrongModelTypeException()

    return Reranks(data=data)
