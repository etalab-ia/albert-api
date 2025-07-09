from io import BytesIO
import logging
from typing import List, Optional
from urllib.parse import urlparse

from fastapi import UploadFile
import requests
from starlette.datastructures import Headers

from app.clients.web_search import BaseWebSearchClient as WebSearchClient
from app.helpers.models.routers import ModelRouter
from app.utils.variables import ENDPOINT__CHAT_COMPLETIONS

logger = logging.getLogger(__name__)


class WebSearchManager:
    GET_WEB_QUERY_PROMPT = """Tu es un spécialiste pour transformer des demandes en requête google. Tu sais écrire les meilleurs types de recherche pour arriver aux meilleurs résultats.
Voici la demande : {prompt}
Réponds en donnant uniquement une requête Google qui permettrait de trouver des informations pour répondre à la question.

Exemples :
- Question: Peut-on avoir des jours de congé pour un mariage ?
  Réponse: jour de congé mariage conditions

- Question: Donne-moi des informations sur Jules Verne.
  Réponse: Jules Verne

- Question: Comment refaire une pièce d'identité ?
  Réponse: renouvellement pièce identité France

Ne donne pas d'explications, ne mets pas de guillemets, réponds uniquement avec la requête Google qui renverra les meilleurs résultats pour la demande. Ne mets pas de mots qui ne servent à rien dans la requête Google.
"""

    def __init__(
        self, web_search: WebSearchClient, model: ModelRouter, limited_domains: Optional[List[str]] = None, user_agent: Optional[str] = None
    ) -> None:
        self.web_search = web_search
        self.model = model
        self.limited_domains = [] if limited_domains is None else limited_domains
        self.user_agent = user_agent

    async def get_web_query(self, prompt: str) -> str:
        prompt = self.GET_WEB_QUERY_PROMPT.format(prompt=prompt)
        client = self.model.get_client(endpoint=ENDPOINT__CHAT_COMPLETIONS)
        response = await client.forward_request(
            method="POST",
            json={"messages": [{"role": "user", "content": prompt}], "model": self.model.id, "temperature": 0.2, "stream": False},
        )
        query = response.json()["choices"][0]["message"]["content"]

        return query

    async def get_results(self, query: str, k: int) -> List[UploadFile]:
        urls = await self.web_search.search(query=query, k=k)
        results = []
        for url in urls:
            # Parse the URL and extract the hostname
            parsed = urlparse(url)
            domain = parsed.hostname
            if not domain:
                # Skip invalid URLs
                continue

            # Check if the domain is authorized
            if self.limited_domains:
                # Allow exact match or subdomains of allowed domains
                if not any(domain == allowed or domain.endswith(f".{allowed}") for allowed in self.limited_domains):
                    # Skip unauthorized domains
                    continue

            # Fetch the content, skipping on network errors
            try:
                response = requests.get(url=url, headers={"User-Agent": self.user_agent}, timeout=5)
            except requests.RequestException:
                logger.exception("Error fetching URL: %s", url)
                continue

            if response.status_code != 200:
                continue

            file = BytesIO(response.text.encode("utf-8"))
            file = UploadFile(filename=f"{url}.html", file=file, headers=Headers({"content-type": "text/html"}))
            results.append(file)
        return results
