from io import BytesIO
from typing import List

from fastapi import UploadFile
import requests

from app.clients.web_search import BaseWebSearchClient as WebSearchClient
from app.clients.model import BaseModelClient as ModelClient


class WebSearchManager:
    LIMITED_DOMAINS = [
        "service-public.fr",
        ".gouv.fr",
        "france-identite.gouv.fr",
        "caf.fr",
        "info-retraite.fr",
        "ameli.fr",
        "education.gouv.fr",
        "elysee.fr",
        "vie-publique.fr",
        "wikipedia.org",
        "autoritedelaconcurrence.fr",
        "assemblee-nationale.fr",
        "amf.asso.fr",
        "elysee.fr",
        "conseil-etat.fr",
        "departements.fr",
        "courdecassation.fr",
        "lcp.fr",
        "archives.assemblee-nationale.fr",
        "senat.fr",
        "gouvernement.fr",
        "vie-publique.fr",
        "carrefourlocal.senat.fr",
        "elections-legislatives.fr",
        "ccomptes.fr",
        "conseil-constitutionnel.fr",
        "ladocumentationfrancaise.fr",
        "franceinfo.fr",
        "lefigaro.fr",
        "ouest-france.fr",
        "lemonde.fr",
        "leparisien.fr",
        "refugies.info",
    ]

    GET_WEB_QUERY_PROMPT = """Tu es un spécialiste pour transformer des demandes en requête google. Tu sais écrire les meilleurs types de recherches pour arriver aux meilleurs résultats.
Voici la demande : {prompt}
Réponds en donnant uniquement une requête google qui permettrait de trouver des informations pour répondre à la question.
Exemples :
question: Peut-on avoir des jours de congé pour un mariage ?
reponse : jour congé mariage conditions
question : Donnes-moi des informations sur toto et titi
reponse : toto titi
Comment refaire une pièce d'identité ?
reponse : Renouvellement pièce identité France
Ne donnes pas d'explication, ne mets pas de guillemets, réponds uniquement avec la requête google qui renverra les meilleurs résultats pour la demande. Ne mets pas de mots qui ne servent à rien dans la requête Google.
"""

    def __init__(self, web_search: WebSearchClient) -> None:
        self.web_search = web_search

    async def get_web_query(self, prompt: str, model_client: ModelClient) -> str:
        prompt = self.GET_WEB_QUERY_PROMPT.format(prompt=prompt)
        response = await model_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=model_client.model,
            temperature=0.2,
            stream=False,
        )
        query = response.choices[0].message.content

        return query

    async def get_results(self, query: str, n: int = 3) -> List[UploadFile]:
        urls = await self.web_search.search(query=query, n=n)
        results = []
        for url in urls:
            try:
                assert not self.LIMITED_DOMAINS or any([domain in url for domain in self.LIMITED_DOMAINS])
                response = requests.get(url=url, headers={"User-Agent": self.web_search.USER_AGENT}, timeout=5)
                assert response.status_code == 200
            except Exception:
                continue

            file = BytesIO(response.text.encode("utf-8"))
            file = UploadFile(filename=f"{url}.html", file=file)
            results.append(file)

        return results
