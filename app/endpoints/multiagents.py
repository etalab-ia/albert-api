from fastapi import APIRouter, Request, Security
import asyncio

from app.schemas.multiagents import MultiAgentsRequest
from app.schemas.security import User
from app.utils.settings import settings
from app.utils.lifespan import clients, limiter
from app.utils.security import check_api_key, check_rate_limit


router = APIRouter()

explain_choice = {
    0: "Je ne comprends pas la demande.",
    1: "Des informations pertinentes ont été trouvées dans la base de données cherchée.",
    2: "Je n'ai pas trouvé d'informations pertinentes en base de données, mais il me semblait juste de répondre avec mes connaissances générales.",
    3: "Je n'ai pas trouvé d'informations pertinentes en base de données, et je ne veux pas me mouiller en répondant quelque chose de faux.",
    4: "La décision d'aller sur internet a été prise pour chercher des informations pertinentes.",
}


def prep_net(body, user):
    body.collections = []
    internet_chunks = []
    internet_chunks = clients.internet.get_chunks(prompt=body.prompt)
    internet_collection = clients.internet.create_temporary_internet_collection(internet_chunks, body.collections, user)
    body.collections.append(internet_collection.id)


def get_prompt_teller_multi(question, docs_tmp, choice):
    """
    Create a batch of prompts based on docs for the writers maker LLMs.
    If there is no docs (no context needed), only create one prompt.
    """
    prompts = []
    if choice == 1 or choice == 4:
        for doc in docs_tmp:
            prompt_teller = f"""
Tu es un assistant administratif qui réponds a des questions sur le droit et l'administratif en Français. Tes réponses doit être succinctes et claires. Ne détailles pas inutilement.
Voilà un contexte : \n{doc}\n
Voilà une question : {question}
En ne te basant uniquement sur le contexte donné, réponds à la question avec une réponse de la meilleure qualité possible. 
- Si le contexte ne te permets pas de répondre à la question, réponds juste "Rien ici", ne dis jamais "le texte ne mentionne pas".
- Si le contexte donne des éléments de réponse, réponds uniquement a la question et n'inventes rien, donnes même juste quelques éléments de réponse si tu n'arrives pas à répondre totalement avec le contexte. Donnes le nom du texte du contexte dans ta réponse.
- Si la question n'est pas explicite et renvoie à la conversation en cours, et que tu trouve que le contexte est en lien avec la conversation, réponds juste "Ces informations sont interessantes pour la conversation".
question : {question}
réponse ("Rien ici" ou ta réponse): 
            """
            prompts.append(prompt_teller)
    elif choice == 2:
        for i in range(1):
            prompt_teller = f"""
Tu es un assistant administratif qui réponds a des questions sur le droit et l'administratif en Français. Nous sommes en 2024. Tes réponses doit être succinctes et claires. Ne détailles pas inutilement.
Voilà une demande utilisateur : {question}
Réponds à cette question comme tu peux. 
Règles à respecter :
N'inventes pas de référence.
Si tu as besoin de plus d'information ou que la question n'est pas claire, dis le a l'utilisateur.
La réponse doit être la plus courte possible.  Mets en forme ta réponse avec des sauts de lignes. Réponds en Français et part du principe que l'interlocuteur est Français et que ses questions concerne la France.
Réponse : 
            """
            prompts.append(prompt_teller)
    return prompts


def get_completion(model, prompt, user, temperature=0.2, max_tokens=200):
    response = clients.models[model].chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model=model,  # self.model_clients[model],
        temperature=temperature,
        max_tokens=max_tokens,
        stream=False,
        user=user,
    )
    result = response.choices[0].message.content
    return result


async def get_completion_async(model, prompt, user, temperature, max_tokens):
    return get_completion(model, prompt, user, temperature, max_tokens)


async def ask_in_parallel(model, prompts, user):
    tasks = []
    for prompt in prompts:
        print("-" * 32)
        print(prompt)
        print("-" * 32)
        task = asyncio.create_task(get_completion_async(model, prompt, user, temperature=0.2, max_tokens=200))
        tasks.append(task)
    answers = await asyncio.gather(*tasks)
    return answers


PROMPT_CONCAT = """
    Tu es un expert pour rédiger les bonnes réponses et expliquer les choses. 
    Voila plusieurs réponses générées par des agents : {answers}
    En te basant sur ces réponses, ne gardes que ce qui est utile pour répondre à la question : {prompt}
    Cites les sources utilisées s'il y en a, mais ne parle jamais des "réponses des agents".
    Réponds avec une réponse à cette question de la meilleure qualité possible.
    Si des éléments de réponses sont contradictoire, donnes les quand même à l'utilisateur en expliquant les informations que tu as.
    Réponds juste à la question, ne dis rien d'autre. Tu dois faire un mélange de ces informations pour ne sortir que l'utile de la meilleure manière possible. Termines ta réponse avec un emoji.
    Réponse : 
    """


def remove_duplicates(lst):
    seen = set()
    return [x for x in lst if not (x in seen or seen.add(x))]


@router.post("/multiagents")
@limiter.limit(settings.default_rate_limit, key_func=lambda request: check_rate_limit(request=request))
async def multiagents(request: Request, body: MultiAgentsRequest, user: User = Security(check_api_key)):
    """Multi Agents researcher."""
    client = clients.models[body.supervisor_model]
    print("YOOOOO")
    print(body)
    url = f"{client.base_url}multiagents"
    headers = {"Authorization": f"Bearer {client.api_key}"}

    # body.collections.remove(INTERNET_COLLECTION_DISPLAY_ID)
    searches = clients.search.query(
        prompt=body.prompt,
        collection_ids=body.collections,
        method=body.method,
        k=25,  # body.k,
        rff_k=25,  # body.rff_k,
        score_threshold=body.score_threshold,
        user=user,
    )
    # docs_json = Searches(data=searches)
    initial_docs = [doc.chunk.content for doc in searches]
    # print(initial_docs)
    # print(len(initial_docs))
    print(searches)
    initial_refs = [doc.chunk.metadata.document_name for doc in searches]

    async def go_multiagents(body, initial_docs, initial_refs, n_retry, max_retry=5, window=5):
        rerank_type = "choicer"
        docs_tmp = initial_docs[n_retry * window : (n_retry + 1) * window]
        refs_tmp = initial_refs[n_retry * window : (n_retry + 1) * window]
        context = "\n-------\n".join(["(Extrait : " + ref + ") " + doc[:250] + "..." for doc, ref in zip(docs_tmp, refs_tmp)])

        choice = clients.rerank.get_rank(body.prompt, context, body.supervisor_model, rerank_type)

        if choice in [0, 3] and n_retry <= max_retry:
            print(f"retry ! {n_retry}")
            return await go_multiagents(body, initial_docs, initial_refs, n_retry=n_retry + 1, max_retry=5, window=5)
        elif choice in [1, 2]:
            print("yay 1 or 2")
            prompts = get_prompt_teller_multi(body.prompt, docs_tmp, choice)
            answers = await ask_in_parallel(body.writers_model, prompts, body.user)
            print(answers)
            prompt = PROMPT_CONCAT.format(prompt=body.prompt, answers=answers)
            answer = get_completion(body.supervisor_model, prompt, body.user, temperature=0.2, max_tokens=600)
            return answer, docs_tmp, refs_tmp, choice, n_retry
        elif choice == 4 or n_retry > max_retry:  # else ?
            print("Internet time")
            prep_net(body, user)
            print("should be internet:", body.collections)
            searches = clients.search.query(
                prompt=body.prompt,
                collection_ids=body.collections,
                method=body.method,
                k=5,  # body.k,
                rff_k=5,  # body.rff_k,
                score_threshold=body.score_threshold,
                user=user,
            )
            docs_tmp = [doc.chunk.content for doc in searches]
            refs_tmp = [doc.chunk.metadata.document_name for doc in searches]
            prompts = get_prompt_teller_multi(body.prompt, docs_tmp, choice)
            answers = await ask_in_parallel(body.writers_model, prompts, body.user)
            prompt = PROMPT_CONCAT.format(prompt=body.prompt, answers=answers)
            answer = get_completion(body.supervisor_model, prompt, body.user, temperature=0.2, max_tokens=600)
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
