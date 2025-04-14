import asyncio
import re

from fastapi import APIRouter, Depends, Request, Security
from sqlalchemy.ext.asyncio import AsyncSession

from app.helpers import Authorization
from app.schemas.auth import User
from app.schemas.multiagents import MultiAgentsRequest
from app.sql.session import get_db as get_session
from app.utils.lifespan import context
from app.utils.variables import ENDPOINT__CHAT_COMPLETIONS, ENDPOINT__MULTIAGENTS

from .prompts import PROMPT_LLM_BASED, PROMPT_CHOICER, PROMPT_CONCAT, PROMPT_TELLER_1_4, PROMPT_TELLER_2

router = APIRouter()

explain_choice = {
    0: "Je ne comprends pas la demande.",
    1: "Des informations pertinentes ont été trouvées dans la base de données cherchée.",
    2: "Je n'ai pas trouvé d'informations pertinentes en base de données, mais il me semblait juste de répondre avec mes connaissances générales.",
    3: "Je n'ai pas trouvé d'informations pertinentes en base de données, et je ne veux pas me mouiller en répondant quelque chose de faux.",
    4: "La décision d'aller sur internet a été prise pour chercher des informations pertinentes.",
}


def get_prompt_teller_multi(question, docs_tmp, choice):
    """
    Create a batch of prompts based on docs for the writers maker LLMs.
    If there is no docs (no context needed), only create one prompt.
    """
    prompts = []
    if choice == 1 or choice == 4:
        for doc in docs_tmp:
            prompts.append(
                PROMPT_TELLER_1_4.format(
                    doc=doc,
                    question=question,
                )
            )
    elif choice == 2:
        prompts.append(PROMPT_TELLER_2.format(question=question))
    return prompts


async def get_completion(model, prompt, user, temperature=0.2, max_tokens=200):
    client = model.get_client(endpoint=ENDPOINT__CHAT_COMPLETIONS)
    response = await client.forward_request(
        method="POST",
        json=dict(
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
            model="albert-small",
        ),
    )
    result = response.json()["choices"][0]["message"]["content"]
    return result


async def get_completion_async(model, prompt, user, temperature, max_tokens):
    return get_completion(model, prompt, user, temperature, max_tokens)


async def ask_in_parallel(model, prompts, user, max_tokens):
    tasks = []
    for prompt in prompts:
        task = asyncio.create_task(get_completion_async(model, prompt, user, temperature=0.2, max_tokens=max_tokens))
        tasks.append(task)
    answers = await asyncio.gather(*tasks)
    return answers


def remove_duplicates(lst):
    seen = set()
    return [x for x in lst if not (x in seen or seen.add(x))]


async def get_rank(prompt: str, inputs: list, model: str, rerank_type: str) -> str:
    async def request_model(prompt, max_choice):
        client = model.get_client(endpoint=ENDPOINT__CHAT_COMPLETIONS)
        response = await client.forward_request(
            method="POST",
            json={"messages": [{"role": "user", "content": prompt}], "temperature": 0.1, "max_tokens": 3, "stream": False, "model": model},
        )
        result = response.json()["choices"][0]["message"]["content"]
        match = re.search(f"[0-{max_choice}]", result)
        result = int(match.group(0)) if match else 0
        return result

    if rerank_type == "classic_rerank":
        # TODO: Add classic reranker
        return []

    elif rerank_type == "llm_rerank":
        prompts = []
        for doc in inputs:
            prompt_ = PROMPT_LLM_BASED.format(prompt=prompt, doc=doc)
            prompts.append(prompt_)

        results = []
        for prompt in prompts:
            result = await request_model(prompt, 1)
            results.append(result)
        return results
    elif rerank_type == "choicer":
        prompt = PROMPT_CHOICER.format(prompt=prompt, docs=inputs)
        result = await request_model(prompt, 4)
        return result


@router.post(ENDPOINT__MULTIAGENTS, dependencies=[Security(dependency=Authorization())])
async def multiagents(
    request: Request, body: MultiAgentsRequest, user: User = Security(dependency=Authorization()), session: AsyncSession = Depends(get_session)
):
    """Multi Agents researcher."""

    searches = await context.documents.search(
        session=session,
        collection_ids=body.collections,
        prompt=body.prompt,
        method=body.method,
        k=body.k,
        rff_k=body.rff_k,
        score_threshold=body.score_threshold,
        user_id=request.app.state.user.id,
    )
    initial_docs = [doc.chunk.content for doc in searches]
    initial_refs = [doc.chunk.metadata.document_name for doc in searches]

    async def go_multiagents(body, initial_docs, initial_refs, n_retry, max_retry=5, window=5):
        docs_tmp = initial_docs[n_retry * window : (n_retry + 1) * window]
        refs_tmp = initial_refs[n_retry * window : (n_retry + 1) * window]

        inputs = ["(Extrait : " + ref + ") " + doc[:250] + "..." for doc, ref in zip(docs_tmp, refs_tmp)]
        model = context.models(model=body.model)
        choice = await get_rank(prompt=body.prompt, inputs=inputs, model=model, rerank_type="choicer")

        if choice in [0, 3] and n_retry < max_retry:
            return await go_multiagents(body, initial_docs, initial_refs, n_retry=n_retry + 1, max_retry=5, window=5)
        elif choice in [1, 2]:
            pass
        elif choice == 4 or n_retry >= max_retry:  # else ?
            searches = await context.documents.search(
                session=session,
                collection_ids=body.collections,
                prompt=body.prompt,
                method=body.method,
                k=5,
                rff_k=5,
                web_search=True,
                user_id=request.app.state.user.id,
            )
            docs_tmp = [doc.chunk.content for doc in searches]
            refs_tmp = [doc.chunk.metadata.document_name for doc in searches]
        prompts = get_prompt_teller_multi(body.prompt, docs_tmp, choice)
        answers = await ask_in_parallel(model, prompts, user, body.max_tokens_intermediate)
        prompt = PROMPT_CONCAT.format(prompt=body.prompt, answers=answers)
        answer = await get_completion(model, prompt, user, temperature=0.2, max_tokens=body.max_tokens)
        return answer, docs_tmp, refs_tmp, choice, n_retry

    answer, docs_tmp, refs, choice, n_retry = await go_multiagents(body, initial_docs, initial_refs, n_retry=0, max_retry=5, window=5)

    response = {}
    response["answer"] = answer
    response["choice"] = choice
    response["choice_desc"] = explain_choice[choice]
    response["n_retry"] = n_retry
    response["sources_refs"] = remove_duplicates(refs)
    response["sources_content"] = remove_duplicates(docs_tmp)
    if choice == 2:
        response["sources_refs"] = ["Trust me bro."]
        response["sources_content"] = []
    return response
