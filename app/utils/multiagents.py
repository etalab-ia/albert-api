import asyncio
import logging
import re
from typing import List

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.search import Search, SearchMethod
from app.utils.variables import ENDPOINT__CHAT_COMPLETIONS


logger = logging.getLogger(__name__)

explain_choice = {
    0: "Je ne comprends pas la demande.",
    1: "Des informations pertinentes ont été trouvées dans la base de données cherchée.",
    2: "Je n'ai pas trouvé d'informations pertinentes en base de données, mais il me semblait juste de répondre avec mes connaissances générales.",
    3: "Je n'ai pas trouvé d'informations pertinentes en base de données, et je ne veux pas me mouiller en répondant quelque chose de faux.",
    4: "La décision d'aller sur internet a été prise pour chercher des informations pertinentes.",
}

PROMPT_TELLER_1_4 = """
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

PROMPT_TELLER_2 = """
Tu es un assistant administratif qui réponds a des questions sur le droit et l'administratif en Français. Nous sommes en 2024. Tes réponses doit être succinctes et claires. Ne détailles pas inutilement.
Voilà une demande utilisateur : {question}
Réponds à cette question comme tu peux. 
Règles à respecter :
N'inventes pas de référence.
Si tu as besoin de plus d'information ou que la question n'est pas claire, dis le a l'utilisateur.
La réponse doit être la plus courte possible.  Mets en forme ta réponse avec des sauts de lignes. Réponds en Français et part du principe que l'interlocuteur est Français et que ses questions concerne la France.
Réponse : 
"""

PROMPT_CHOICER = """
Tu es un expert en compréhension et en évaluation des besoins en information pour répondre à un message utilisateur. Ton travail est de juger la possibilité de répondre à un message utilisateur en fonction d'un contexte donné.
Nous sommes en 2024 et ton savoir s'arrete en 2023.

Le contexte est composé d'une liste d'extrait d'article qui sert d'aide pour répondre au message utilisateur, mais n'est pas forcément en lien avec lui. Tu dois évaluer s'il y a besoin du contexte ou non.

Ne réponds pas au message utilisateur.
Voilà le message utilisateur : {prompt}
 
Voilà tes choix :

- Si le message utilisateur n'est vraiment pas claire ou ne veut vraiment rien dire en français réponds 0 OU
- Si le message utilisateur est compréhensible et que le contexte donné est en lien avec le message utilisateur (même de loin, même un seul article du contexte) / Si le message utilisateur aborde un sujet qui est également abordé dans le contexte réponds 1 OU
- Si le contexte contient certains éléments qui peuvent aider à répondre au message utilisateur réponds 1 OU
- Si le message utilisateur demande explicitement des sources ou des références réponds 1 (si le contexte associé est bon) ou 3 (si le contexte associé est mauvais) OU
- Si le message utilisateur n'a pas besoin de contexte car ce n'est pas une question adminitrative / c'est de la culture générale simple réponds 2 OU
- Si le message utilisateur est un message simple ou personnel / Le reste de la conversation permets d'y répondre réponds 2 OU
- Si le message utilisateur a besoin de contexte car elle est spécifique, sur de l'administratif, ou complexe, mais qu'aucun des articles du contexte n'est en lien avec elle réponds 3
- Si on te demande de chercher sur internet / qu'on te demande des informations sur quelqu'un ou une personnalité / qu'on te demande des informations actuelles / si le message utilisateur commence par "internet" réponds 4

Pour chaque choix, assure-toi de bien évaluer le message utilisateur selon ces critères avant de donner ta réponse. 
Regardes bien le contexte, s'il peut t'aider à répondre au message utilisateur c'est important.
Même si le contexte ne contient que quelques informations ou mots commun avec le message utilisateur, considère qu'il est en lien avec la question.

Ne fais pas de phrase, réponds uniquement 0, 1, 2, 3 ou 4.

Exemples
----------
Exemple 1 - "Le contexte permet de répondre à la question"
context : Pour la retraite anticipée [...]
question : Comment bien préparer sa retraite ?
reponse : 1
Exemple 2 - "toto voiture n'est pas une question et ne veut rien dire"
context : les assurances de véhicules [...]
question : toto voiture
reponse : 0
Exemple 3 : "Pas besoin de contexte, la question est de la culture générale / facile"
context : En cas de vol ou de perte [...]
question : Quelle est la capitale de la France ?
reponse : 2
Exemple 4 : "Question necessitant du contexte pertinent mais pas dans le rag"
context : Vous pouvez faire une demarche [...]
question : Qui est le président des usa actuellement ?
reponse : 4
----------

Ne réponds pas à la question, réponds uniquement 0, 1, 2, 3 ou 4. Ne donnes jamais d'explication ou de phrase dans ta réponse, renvoies juste un chiffre. Ta réponse doit être sous ce format:<CHIFFRE>
Bases toi également sur le reste des messages de la conversation pour répondre avec ton choix.
context : {docs}
question : {prompt}
reponse :
"""

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


async def get_completion(model, prompt, temperature=0.2, max_tokens=200):
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


async def get_completion_async(model, prompt, temperature, max_tokens):
    return get_completion(model, prompt, temperature, max_tokens)


async def ask_in_parallel(model, prompts, max_tokens):
    tasks = []
    for prompt in prompts:
        task = asyncio.create_task(get_completion_async(model, prompt, temperature=0.2, max_tokens=max_tokens))
        tasks.append(task)
    answers = await asyncio.gather(*tasks)
    return answers


def remove_duplicates(lst):
    seen = set()
    return [x for x in lst if not (x in seen or seen.add(x))]


async def get_rank(prompt: str, inputs: list, model: str) -> list[int]:
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

    prompt_str = PROMPT_CHOICER.format(prompt=prompt, docs=inputs)
    result = await request_model(prompt_str, 4)
    return [
        result,
    ]


async def search(
    doc_search: callable,
    searches: List[Search],
    prompt: str,
    method: str,
    collection_ids: List[int],
    session: AsyncSession,
    model,
    max_tokens=50,
    max_tokens_intermediate=20,
):
    """Multi Agents researcher."""

    initial_docs = [doc.chunk.content for doc in searches]
    initial_refs = [doc.chunk.metadata.get("document_name") for doc in searches]

    async def go_multiagents(prompt, model, method, initial_docs, initial_refs, n_retry, max_retry=5, window=5):
        docs_tmp = initial_docs[n_retry * window : (n_retry + 1) * window]
        refs_tmp = initial_refs[n_retry * window : (n_retry + 1) * window]

        inputs = ["(Extrait : " + ref + ") " + doc[:250] + "..." for doc, ref in zip(docs_tmp, refs_tmp)]
        choices = await get_rank(prompt=prompt, inputs=inputs, model=model)
        if not choices:
            logger.warning("No choices returned from get_rank.")
            choices = [0]
        choice = choices[0]

        if choice in [0, 3] and n_retry < max_retry:
            return await go_multiagents(prompt, initial_docs, initial_refs, n_retry=n_retry + 1, max_retry=5, window=5)
        elif choice in [1, 2]:
            pass
        elif choice == 4 or n_retry >= max_retry:
            searches = doc_search(
                session=session,
                collection_ids=collection_ids,
                prompt=prompt,
                method=SearchMethod.SEMANTIC,
                k=5,
                rff_k=5,
                web_search=True,
            )
            docs_tmp = [doc.chunk.content for doc in searches]
            refs_tmp = [doc.chunk.metadata.get("document_name") for doc in searches]
        else:
            raise ValueError(f"Unknown choice: {choice}")
        prompts = get_prompt_teller_multi(prompt, docs_tmp, choice)
        answers = await ask_in_parallel(model, prompts, max_tokens_intermediate)
        prompt = PROMPT_CONCAT.format(prompt=prompt, answers=answers)
        answer = await get_completion(model, prompt, temperature=0.2, max_tokens=max_tokens)
        return answer, docs_tmp, refs_tmp, choice, n_retry

    answer, docs_tmp, refs, choice, n_retry = await go_multiagents(
        prompt, model, method, initial_docs, initial_refs, n_retry=0, max_retry=5, window=5
    )

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
