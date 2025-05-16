from io import BytesIO
from typing import List
from urllib.parse import urlparse

from fastapi import UploadFile
import requests

from app.clients.web_search import BaseWebSearchClient as WebSearchClient
from app.helpers.models.routers import ModelRouter
from app.utils.variables import ENDPOINT__CHAT_COMPLETIONS

import logging

logger = logging.getLogger(__name__)


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
- Question: Peut-on avoir des jours de congé pour un mariage ?
  Réponse: jour de congé mariage conditions

- Question: Donnes-moi des informations sur Jules Verne.
  Réponse: Jules Verne

- Question: Comment refaire une pièce d'identité ?
  Réponse: renouvellement pièce identité France

Ne donnes pas d'explication, ne mets pas de guillemets, réponds uniquement avec la requête google qui renverra les meilleurs résultats pour la demande. Ne mets pas de mots qui ne servent à rien dans la requête Google.
"""

    def __init__(self, web_search: WebSearchClient, model: ModelRouter) -> None:
        self.web_search = web_search
        self.model = model

    async def get_web_query(self, prompt: str) -> str:
        prompt = self.GET_WEB_QUERY_PROMPT.format(prompt=prompt)
        client = self.model.get_client(endpoint=ENDPOINT__CHAT_COMPLETIONS)
        response = await client.forward_request(
            method="POST",
            json={"messages": [{"role": "user", "content": prompt}], "model": self.model.id, "temperature": 0.2, "stream": False},
        )
        query = response.json()["choices"][0]["message"]["content"]

        return query

    async def get_results(self, query: str, n: int = 3) -> List[UploadFile]:
        urls = await self.web_search.search(query=query, n=n)
        results = []
        for url in urls:
            # Parse the URL and extract the hostname
            parsed = urlparse(url)
            domain = parsed.hostname
            if not domain:
                # Skip invalid URLs
                continue

            # Check if the domain is authorized
            if self.LIMITED_DOMAINS:
                # Allow exact match or subdomains of allowed domains
                if not any(domain == allowed or domain.endswith(f".{allowed}") for allowed in self.LIMITED_DOMAINS):
                    # Skip unauthorized domains
                    continue

            # Fetch the content, skipping on network errors
            try:
                response = requests.get(url=url, headers={"User-Agent": self.web_search.USER_AGENT}, timeout=5)
            except requests.RequestException:
                logger.exception("Error fetching URL: %s", url)
                continue

            if response.status_code != 200:
                continue

            file = BytesIO(response.text.encode("utf-8"))
            file = UploadFile(filename=f"{url}.html", file=file)
            results.append(file)

        return results
