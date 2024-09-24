from typing import List
import uuid

from bs4 import BeautifulSoup
from duckduckgo_search import DDGS
import numpy as np
import requests

from app.helpers import UniversalParser
from app.schemas.chunks import Chunk
from app.schemas.search import Search


class UseInternet:
    LIMITED_DOMAINS = []
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
        self.parser = UniversalParser()

    def search(self, prompt: str, language_model: str, embeddings_model: str, n: int = 3) -> List:
        query = self._get_web_query(prompt=prompt, language_model=language_model)

        with DDGS() as ddgs:
            results = list(ddgs.text(query, region="fr-fr", safesearch="On", max_results=n))

        documents = []
        for result in results:
            url = result["href"].lower()

            try:
                assert not self.LIMITED_DOMAINS or any([domain in url for domain in self.LIMITED_DOMAINS])
                response = requests.get(url, headers={"User-Agent": self.USER_AGENT})
                assert response.status_code == 200
            except Exception:
                continue

            file = BeautifulSoup(response.text, "html.parser")
            chunks = self.parser._html_to_chunks(
                file=file, file_name=url, chunk_size=self.CHUNK_SIZE, chunk_overlap=self.CHUNK_OVERLAP, chunk_min_size=self.CHUNK_MIN_SIZE
            )

            documents.extend(chunks)

        data = []
        if len(documents) == 0:
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
            search = Search(score=score, chunk=Chunk(id=str(uuid.uuid4()), content=chunk.page_content, metadata=chunk.metadata))
            data.append(search)

        return data

    def _get_web_query(self, prompt: str, language_model: str) -> str:
        prompt = self.GET_WEB_QUERY_PROMPT.format(prompt=prompt)
        response = self.clients["models"][language_model].chat.completions.create(
            messages=[{"role": "user", "content": prompt}], model=language_model, temperature=0.2, stream=False
        )
        query = response.choices[0].message.content

        return query
