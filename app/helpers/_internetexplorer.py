from io import BytesIO
from typing import List, Literal, Optional
import uuid

from duckduckgo_search import DDGS
from duckduckgo_search.exceptions import RatelimitException
from fastapi import UploadFile
import requests

from app.helpers.chunkers import LangchainRecursiveCharacterTextSplitter
from app.helpers.parsers import HTMLParser
from app.helpers.searchclients import SearchClient
from app.helpers._modelclients import ModelClients
from app.schemas.collections import Collection
from app.schemas.chunks import Chunk
from app.schemas.security import User
from app.utils.config import logger
from app.utils.variables import INTERNET_COLLECTION_DISPLAY_ID, INTERNET_BRAVE_TYPE, INTERNET_DUCKDUCKGO_TYPE


class InternetExplorer:
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
    ]

    USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"
    PAGE_LOAD_TIMEOUT = 60
    # TODO: make chunk size dynamic based on the model
    CHUNK_SIZE = 1000
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

    def __init__(
        self,
        model_clients: ModelClients,
        search_client: SearchClient,
        method: Literal[INTERNET_DUCKDUCKGO_TYPE, INTERNET_BRAVE_TYPE] = INTERNET_BRAVE_TYPE,
        api_key: Optional[str] = None,
    ):
        self.model_clients = model_clients
        self.search_client = search_client
        self.parser = HTMLParser(collection_id=INTERNET_COLLECTION_DISPLAY_ID)
        self.method = method
        self.api_key = api_key

    def _get_web_query(self, prompt: str) -> str:
        prompt = self.GET_WEB_QUERY_PROMPT.format(prompt=prompt)
        response = self.model_clients[self.model_clients.DEFAULT_INTERNET_LANGUAGE_MODEL_ID].chat.completions.create(
            messages=[{"role": "user", "content": prompt}], model=self.model_clients.DEFAULT_INTERNET_LANGUAGE_MODEL_ID, temperature=0.2, stream=False
        )
        query = response.choices[0].message.content

        return query

    def _get_result_urls(self, query: str, n: int = 3) -> List[str]:
        if self.method == INTERNET_DUCKDUCKGO_TYPE:
            try:
                with DDGS() as ddgs:
                    results = list(ddgs.text(query, region="fr-fr", safesearch="On", max_results=n))
            except RatelimitException:
                logger.warning("DuckDuckGo rate limit exceeded.")
                results = []
            return [result["href"].lower() for result in results]

        if self.method == INTERNET_BRAVE_TYPE:
            headers = {"Accept": "application/json", "X-Subscription-Token": self.api_key}
            params = {"q": query, "count": n, "country": "fr", "safesearch": "strict"}

            try:
                response = requests.get("https://api.search.brave.com/res/v1/web/search", headers=headers, params=params)
                results = response.json().get("web", {}).get("results", [])
            except Exception as e:
                logger.warning(f"Brave Search API error: {str(e)}")
                results = []
            return [result["url"].lower() for result in results]

    def _build_chunks(self, urls: List[str], query: str) -> List[Chunk]:
        chunker = LangchainRecursiveCharacterTextSplitter(
            chunk_size=self.CHUNK_SIZE, chunk_overlap=self.CHUNK_OVERLAP, chunk_min_size=self.CHUNK_MIN_SIZE
        )
        chunks = []
        for url in urls:
            try:
                assert not self.LIMITED_DOMAINS or any([domain in url for domain in self.LIMITED_DOMAINS])
                response = requests.get(url, headers={"User-Agent": self.USER_AGENT})
                assert response.status_code == 200
            except Exception:
                continue
            file = BytesIO(response.text.encode("utf-8"))
            file = UploadFile(filename=url, file=file)
            # TODO: parse pdf if url is a pdf or json if url is a json
            output = self.parser.parse(file=file)
            chunks.extend(chunker.split(input=output))

        if len(chunks) == 0:
            return []
        else:
            # Add internet query to the metadata of each chunk
            for chunk in chunks:
                chunk.metadata.internet_query = query
            return chunks

    def get_chunks(self, prompt: str, n: int = 3) -> List[Chunk]:
        query = self._get_web_query(prompt=prompt)
        urls = self._get_result_urls(query=query, n=n)
        return self._build_chunks(urls=urls, query=query)

    def _get_internet_embeddings_model_id(self, collection_ids: List[str], user: User) -> str:
        all_collections_with_internet_are_queried = not collection_ids
        if all_collections_with_internet_are_queried:
            any_first_collection = self.search_client.get_collections([], user=user)[0]
            return any_first_collection.model

        collection_ids_without_internet = [collection_id for collection_id in collection_ids if collection_id != INTERNET_COLLECTION_DISPLAY_ID]
        only_internet_collection_queried = len(collection_ids_without_internet) == 0
        if only_internet_collection_queried:
            return self.model_clients.DEFAULT_INTERNET_EMBEDDINGS_MODEL_ID

        any_first_collection_queried = self.search_client.get_collections(collection_ids_without_internet, user=user)[0]
        return any_first_collection_queried.model

    def create_temporary_internet_collection(
        self, chunks: List[Chunk], collection_ids: List[str], user: User, limit: int = 3
    ) -> Optional[Collection]:
        stored_internet_collection_id = str(uuid.uuid4())
        internet_embeddings_model_id = self._get_internet_embeddings_model_id(collection_ids, user)
        internet_collection = self.search_client.create_collection(
            collection_id=stored_internet_collection_id,
            collection_name=stored_internet_collection_id,
            collection_model=internet_embeddings_model_id,
            user=user,
        )
        self.search_client.upsert(chunks, collection_id=stored_internet_collection_id, user=user)

        return internet_collection
