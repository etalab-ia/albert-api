import re
from fastapi import APIRouter, Request, Security

from app.schemas.rerank import RerankRequest
from app.schemas.security import User
from app.utils.settings import settings
from app.utils.lifespan import clients, limiter
from app.utils.security import check_api_key, check_rate_limit

router = APIRouter()


@router.post("/rerank")
@limiter.limit(settings.default_rate_limit, key_func=lambda request: check_rate_limit(request=request))
async def rerank(request: Request, body: RerankRequest, user: User = Security(check_api_key)):
    """LLM based reranker."""
    client = clients.models[body.model]
    # TODO: Add rerank model based reranker
    url = f"{client.base_url}rerank"
    headers = {"Authorization": f"Bearer {client.api_key}"}

    prompts = []
    for doc in body.inputs:
        prompt_ = f"""Voila un texte : {doc}\n 
        En se basant uniquement sur ce texte, réponds 1 si ce texte peut donner des éléments de réponse à la question suivante ou 0 si aucun élément de réponse n'est présent dans le texte. Voila la question: {body.prompt}
        Le texte n'a pas besoin de répondre parfaitement à la question, juste d'apporter des éléments de réponses et/ou de parler du même thème. Réponds uniquement 0 ou 1."""
        prompts.append(prompt_)

    results = []
    for prompt in prompts:
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}], model=body.model, temperature=0.1, max_tokens=3, stream=False
        )
        result = response.choices[0].message.content
        match = re.search(r"[0-1]", result)
        result = int(match.group(0)) if match else 0
        results.append(result)

    return results
