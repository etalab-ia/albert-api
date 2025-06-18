import asyncio
import logging
import re
from typing import List

from sqlalchemy.ext.asyncio import AsyncSession

from app.helpers.models.routers._modelrouter import ModelRouter
from app.schemas.search import Search
from app.utils.settings import settings
from app.utils.variables import ENDPOINT__CHAT_COMPLETIONS

logger = logging.getLogger(__name__)


CHOICES = {
    0: "Je ne comprends pas la demande.",
    1: "Des informations pertinentes ont été trouvées dans la base de données cherchée.",
    2: "Je n'ai pas trouvé d'informations pertinentes en base de données, mais il me semblait juste de répondre avec mes connaissances générales.",
    3: "Je n'ai pas trouvé d'informations pertinentes en base de données, et je ne veux pas me mouiller en répondant quelque chose de faux.",
}


_PROMPT_TELLER_1 = """
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

_PROMPT_TELLER_2 = """
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
Voilà le message utilisateur : {{prompt}}
 
Voilà tes choix :

- Si le message utilisateur n'est vraiment pas claire ou ne veut vraiment rien dire en français réponds 0 OU
- Si le message utilisateur est compréhensible et que le contexte donné est en lien avec le message utilisateur (même de loin, même un seul article du contexte) / Si le message utilisateur aborde un sujet qui est également abordé dans le contexte réponds 1 OU
- Si le contexte contient certains éléments qui peuvent aider à répondre au message utilisateur réponds 1 OU
- Si le message utilisateur demande explicitement des sources ou des références réponds 1 (si le contexte associé est bon) ou 3 (si le contexte associé est mauvais) OU
- Si le message utilisateur n'a pas besoin de contexte car ce n'est pas une question adminitrative / c'est de la culture générale simple réponds 2 OU
- Si le message utilisateur est un message simple ou personnel / Le reste de la conversation permets d'y répondre réponds 2 OU
- Si le message utilisateur a besoin de contexte car elle est spécifique, sur de l'administratif, ou complexe, mais qu'aucun des articles du contexte n'est en lien avec elle réponds 3

Pour chaque choix, assure-toi de bien évaluer le message utilisateur selon ces critères avant de donner ta réponse. 
Regardes bien le contexte, s'il peut t'aider à répondre au message utilisateur c'est important.
Même si le contexte ne contient que quelques informations ou mots commun avec le message utilisateur, considère qu'il est en lien avec la question.

Ne fais pas de phrase, réponds uniquement 0, 1, 2 ou 3.

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
reponse : 3
----------

Ne réponds pas à la question, réponds uniquement 0, 1, 2, 3. Ne donnes jamais d'explication ou de phrase dans ta réponse, renvoies juste un chiffre. Ta réponse doit être sous ce format:<CHIFFRE>
Bases toi également sur le reste des messages de la conversation pour répondre avec ton choix.
context : {{docs}}
question : {{prompt}}
reponse :
"""


_PROMPT_CONCAT = """
Tu es un expert pour rédiger les bonnes réponses et expliquer les choses. 
Voila plusieurs réponses générées par des agents : {answers}
En te basant sur ces réponses, ne gardes que ce qui est utile pour répondre à la question : {prompt}
Cites les sources utilisées s'il y en a, mais ne parle jamais des "réponses des agents".
Réponds avec une réponse à cette question de la meilleure qualité possible.
Si des éléments de réponses sont contradictoire, donnes les quand même à l'utilisateur en expliquant les informations que tu as.
Réponds juste à la question, ne dis rien d'autre. Tu dois faire un mélange de ces informations pour ne sortir que l'utile de la meilleure manière possible.
Réponse : 
"""


class MultiAgents:
    """Multi Agents researcher for handling complex search queries with multiple models."""

    def __init__(self, model: ModelRouter, ranker_model: ModelRouter):
        """Initialize MultiAgents with the given models."""
        self.model = model
        self.ranker_model = ranker_model

    async def search(
        self,
        searches: List[Search],
        prompt: str,
        session: AsyncSession,
        k: int,
    ) -> List[Search]:
        """Multi Agents researcher."""

        async def _go_agents(prompt_text, docs, refs, n_retry=0, max_retry=5, window=5):
            chunk_batch = docs[n_retry * window : (n_retry + 1) * window]
            inputs = [f"(Extrait : {refs[i]}) {chunk[: settings.multi_agents_search.extract_length]}..." for i, chunk in enumerate(chunk_batch)]
            choice = (await self._get_rank(prompt_text, inputs))[0]
            if choice in (0, 3) and n_retry < max_retry:
                return await _go_agents(prompt_text, docs, refs, n_retry + 1)
            if choice in (1, 2):
                return searches, choice, n_retry
            # fallback when max retries reached
            if n_retry >= max_retry:
                return searches, 3, n_retry
            raise ValueError(f"Unknown choice: {choice}")

        initial_docs = [s.chunk.content for s in searches]
        initial_refs = [s.chunk.metadata.get("document_name") for s in searches]
        searches_out, choice, n_retry = await _go_agents(prompt, initial_docs, initial_refs)

        for s in searches_out:
            s.chunk.metadata["choice"] = choice
            s.chunk.metadata["choice_desc"] = CHOICES[choice]
            s.chunk.metadata["n_retry"] = n_retry

        return searches_out

    async def full_multiagents(self, searches: List[Search], prompt: str) -> str:
        prompts = self._get_prompts(prompt, searches)
        answers = await self._ask_in_parallel(prompts)
        return _PROMPT_CONCAT.format(prompt=prompt, answers=answers)

    # --- private helpers ---

    def _get_prompts(self, question: str, searches: List[Search]) -> List[str]:
        choice = searches[0].chunk.metadata["choice"]
        if choice == 1:
            return [_PROMPT_TELLER_1.format(doc=s.chunk.content, question=question) for s in searches]
        if choice == 2:
            return [_PROMPT_TELLER_2.format(question=question)]
        return []

    async def _get_completion(self, prompt: str, temperature=0.2) -> str:
        client = self.model.get_client(endpoint=ENDPOINT__CHAT_COMPLETIONS)
        resp = await client.forward_request(
            method="POST",
            json={
                "messages": [{"role": "user", "content": prompt}],
                "temperature": temperature,
                "max_tokens": settings.multi_agents_search.max_tokens,
                "model": self.model,
            },
        )
        return resp.json()["choices"][0]["message"]["content"]

    async def _ask_in_parallel(self, prompts: List[str]) -> List[str]:
        tasks = [asyncio.create_task(self._get_completion(prm, temperature=0.2)) for prm in prompts]
        return await asyncio.gather(*tasks)

    async def _get_rank(self, prompt: str, inputs: List[str]) -> List[int]:
        client = self.ranker_model.get_client(endpoint=ENDPOINT__CHAT_COMPLETIONS)
        query = PROMPT_CHOICER.format(prompt=prompt, docs=inputs)
        resp = await client.forward_request(
            method="POST",
            json={
                "messages": [{"role": "user", "content": query}],
                "temperature": 0.1,
                "max_tokens": 3,
                "stream": False,
                "model": self.ranker_model,
            },
        )
        text = resp.json()["choices"][0]["message"]["content"]
        m = re.search("[0-3]", text)
        return [int(m.group())] if m else [0]
