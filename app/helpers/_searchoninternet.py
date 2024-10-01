from io import BytesIO
from typing import List, Optional
import uuid

from duckduckgo_search import DDGS
import numpy as np
import requests

from app.helpers.chunkers import LangchainRecursiveCharacterTextSplitter
from app.helpers.parsers import HTMLParser
from app.schemas.chunks import Chunk
from app.schemas.search import Search


class SearchOnInternet:
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
    ]

    USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X x.y; rv:10.0) Gecko/20100101 Firefox/10.0"
    PAGE_LOAD_TIMEOUT = 60
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

    def __init__(self, clients: dict):
        self.clients = clients
        self.parser = HTMLParser()
        # TODO: change this after create client manager class
        self.language_model = [model for model in self.clients["models"].keys() if self.clients["models"][model].search_internet][0]

    def search(self, prompt: str, embeddings_model: str, n: int = 3, score_threshold: Optional[float] = None) -> List:
        parser = HTMLParser()
        chunker = LangchainRecursiveCharacterTextSplitter(
            chunk_size=self.CHUNK_SIZE, chunk_overlap=self.CHUNK_OVERLAP, chunk_min_size=self.CHUNK_MIN_SIZE
        )
        query = self._get_web_query(prompt=prompt)

        with DDGS() as ddgs:
            results = list(ddgs.text(query, region="fr-fr", safesearch="On", max_results=n))

        chunks = []
        for result in results:
            url = result["href"].lower()

            try:
                assert not self.LIMITED_DOMAINS or any([domain in url for domain in self.LIMITED_DOMAINS])
                response = requests.get(url, headers={"User-Agent": self.USER_AGENT})
                assert response.status_code == 200
            except Exception:
                continue

            file = BytesIO(response.text.encode("utf-8"))
            documents = parser.parse(file=file)
            for document in documents:
                document.metadata["file_name"] = url

            document_chunks = chunker.split(documents)
            chunks.extend(document_chunks)

        data = []
        if len(chunks) == 0:
            return data

        response = self.clients["models"][embeddings_model].embeddings.create(input=[prompt], model=embeddings_model)
        vector = response.data[0].embedding
        vectors = []
        for i in range(0, len(documents), self.BATCH_SIZE):
            batch = documents[i : i + self.BATCH_SIZE]

            texts = [document.page_content for document in batch]
            response = self.clients["models"][embeddings_model].embeddings.create(input=texts, model=embeddings_model)
            vectors.extend([vector.embedding for vector in response.data])

        cosine = np.dot(vectors, vector) / (np.linalg.norm(vectors, axis=1) * np.linalg.norm(vector))

        for chunk, score in zip(documents, cosine):
            if score_threshold and score < score_threshold:
                continue
            search = Search(score=score, chunk=Chunk(id=str(uuid.uuid4()), content=chunk.page_content, metadata=chunk.metadata))
            data.append(search)

        return data

    def _get_web_query(self, prompt: str, language_model: str) -> str:
        prompt = self.GET_WEB_QUERY_PROMPT.format(prompt=prompt)
        response = self.clients["models"][self.language_model].chat.completions.create(
            messages=[{"role": "user", "content": prompt}], model=self.language_model, temperature=0.2, stream=False
        )
        query = response.choices[0].message.content

        return query
