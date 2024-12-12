from io import BytesIO
from typing import List, Optional

from fastapi import UploadFile
import requests

from app.clients import ModelClients
from app.clients import InternetClient
from app.helpers.data.chunkers import LangchainRecursiveCharacterTextSplitter
from app.helpers.data.parsers import HTMLParser
from app.schemas.chunks import Chunk
from app.utils.variables import EMBEDDINGS_MODEL_TYPE, LANGUAGE_MODEL_TYPE


class InternetManager:
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
        "refugies.info"
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
        internet_client: InternetClient,
        default_language_model_id: str,
        default_embeddings_model_id: str,
        api_key: Optional[str] = None,
    ) -> None:
        self.type = type
        self.api_key = api_key
        self.model_clients = model_clients
        self.internet_client = internet_client
        self.default_language_model_id = default_language_model_id
        self.default_embeddings_model_id = default_embeddings_model_id

        assert self.default_language_model_id in self.model_clients, "Default internet language model is unavailable."
        assert (
            self.model_clients[self.default_language_model_id].type == LANGUAGE_MODEL_TYPE
        ), "Default internet language model is not a language model."
        assert self.default_embeddings_model_id in self.model_clients, "Default internet embeddings model is unavailable."
        assert (
            self.model_clients[self.default_embeddings_model_id].type == EMBEDDINGS_MODEL_TYPE
        ), "Default internet embeddings model is not an embeddings model."

    def get_chunks(self, prompt: str, collection_id: str, n: int = 3) -> List[Chunk]:
        query = self._get_web_query(prompt=prompt)
        urls = self.internet_client.get_result_urls(query=query, n=n)
        chunks = self._build_chunks(urls=urls, query=query, collection_id=collection_id)

        return chunks

    def _get_web_query(self, prompt: str) -> str:
        prompt = self.GET_WEB_QUERY_PROMPT.format(prompt=prompt)
        response = self.model_clients[self.default_language_model_id].chat.completions.create(
            messages=[{"role": "user", "content": prompt}], model=self.default_language_model_id, temperature=0.2, stream=False
        )
        query = response.choices[0].message.content

        return query

    def _build_chunks(self, urls: List[str], query: str, collection_id: str) -> List[Chunk]:
        chunker = LangchainRecursiveCharacterTextSplitter(
            chunk_size=self.CHUNK_SIZE, chunk_overlap=self.CHUNK_OVERLAP, chunk_min_size=self.CHUNK_MIN_SIZE
        )
        chunks = []
        parser = HTMLParser(collection_id=collection_id)
        for url in urls:
            try:
                assert not self.LIMITED_DOMAINS or any([domain in url for domain in self.LIMITED_DOMAINS])
                response = requests.get(url=url, headers={"User-Agent": self.USER_AGENT})
                assert response.status_code == 200
            except Exception:
                continue

            file = BytesIO(response.text.encode("utf-8"))
            file = UploadFile(filename=url, file=file)

            # TODO: parse pdf if url is a pdf or json if url is a json
            output = parser.parse(file=file)
            chunks.extend(chunker.split(input=output))

        if len(chunks) == 0:
            return []
        else:
            # Add internet query to the metadata of each chunk
            for chunk in chunks:
                chunk.metadata.internet_query = query
            return chunks
