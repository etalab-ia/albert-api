from io import BytesIO
from typing import List

from fastapi import UploadFile
import requests

from app.clients.internet import BaseInternetClient as InternetClient
from app.clients.model import BaseModelClient as ModelClient
from app.helpers.data.chunkers import LangchainRecursiveCharacterTextSplitter
from app.helpers.data.parsers import HTMLParser
from app.schemas.chunks import Chunk


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

    USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"
    PAGE_LOAD_TIMEOUT = 60
    CHUNK_SIZE = 1000  # @TODO: make chunk size dynamic based on the model
    CHUNK_OVERLAP = 0
    CHUNK_MIN_SIZE = 20
    BATCH_SIZE = 32

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

    def __init__(self, internet: InternetClient) -> None:
        self.internet = internet

    async def get_chunks(self, prompt: str, model_client: ModelClient, n: int = 3) -> List[Chunk]:
        query = await self._get_web_query(prompt=prompt, model_client=model_client)
        urls = await self.internet.get_result_urls(query=query, n=n)
        chunks = self._build_chunks(urls=urls, query=query)

        return chunks

    async def _get_web_query(self, prompt: str, model_client: ModelClient) -> str:
        prompt = self.GET_WEB_QUERY_PROMPT.format(prompt=prompt)
        response = await model_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}], model=model_client.model, temperature=0.2, stream=False
        )
        query = response.choices[0].message.content

        return query

    def _build_chunks(self, urls: List[str], query: str, model_client: ModelClient) -> List[Chunk]:
        chunker = LangchainRecursiveCharacterTextSplitter(
            chunk_size=self.CHUNK_SIZE, chunk_overlap=self.CHUNK_OVERLAP, chunk_min_size=self.CHUNK_MIN_SIZE
        )
        chunks = []
        parser = HTMLParser()
        for url in urls:
            try:
                assert not self.LIMITED_DOMAINS or any([domain in url for domain in self.LIMITED_DOMAINS])
                response = requests.get(url=url, headers={"User-Agent": self.USER_AGENT})
                assert response.status_code == 200
            except Exception:
                continue

            file = BytesIO(response.text.encode("utf-8"))
            file = UploadFile(filename=url, file=file)

            # @TODO: parse pdf if url is a pdf or json if url is a json
            output = parser.parse(file=file)
            chunks.extend(chunker.split(input=output))

        if len(chunks) == 0:
            return []
        else:
            # Add internet query to the metadata of each chunk
            for chunk in chunks:
                chunk.metadata["web_search_query"] = query
            return chunks
