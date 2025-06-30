from typing import List, Optional

from elasticsearch import AsyncElasticsearch, helpers

from app.schemas.chunks import Chunk
from app.schemas.search import Search, SearchMethod

from app.clients.vector_store._basevectorstoreclient import BaseVectorStoreClient


class ElasticsearchVectorStoreClient(BaseVectorStoreClient, AsyncElasticsearch):
    default_method = SearchMethod.HYBRID

    def __init__(self, *args, model=None, **kwargs):
        BaseVectorStoreClient.__init__(self, *args, model=model, **kwargs)
        AsyncElasticsearch.__init__(self, *args, **kwargs)
        self.url = kwargs.get("url")

    async def check(self) -> bool:
        try:
            await self.ping()
            return True
        except Exception:
            return False

    async def close(self) -> None:
        await super(AsyncElasticsearch, self).transport.close()

    async def create_collection(self, collection_id: int, vector_size: int) -> None:
        settings = {
            "similarity": {"default": {"type": "BM25"}},
            "analysis": {
                # TODO: support other languages
                "filter": {
                    "french_stop": {"type": "stop", "stopwords": "_french_"},
                    "french_stemmer": {"type": "stemmer", "language": "light_french"},
                },
                "analyzer": {
                    "french_analyzer": {
                        "tokenizer": "standard",
                        "filter": ["lowercase", "french_stop", "french_stemmer"],
                    }
                },
            },
        }
        mappings = {
            "properties": {
                "id": {"type": "integer"},
                "embedding": {"type": "dense_vector", "dims": vector_size},
                "content": {"type": "text", "analyzer": "french_analyzer"},
                "metadata": {"type": "object", "dynamic": True},
            },
        }

        await self.indices.create(index=str(collection_id), mappings=mappings, settings=settings)

    async def delete_collection(self, collection_id: int) -> None:
        await self.indices.delete(index=str(collection_id))

    async def get_collections(self) -> list[int]:
        collections = await self.indices.get_alias()
        return [int(collection) for collection in collections]

    async def get_chunk_count(self, collection_id: int, document_id: int) -> Optional[int]:
        try:
            body = {"query": {"match": {"metadata.document_id": document_id}}}
            result = await AsyncElasticsearch.count(self, index=str(collection_id), body=body)
            return result["count"]
        except Exception:
            return None

    async def delete_document(self, collection_id: int, document_id: int) -> None:
        body = {"query": {"match": {"metadata.document_id": document_id}}}
        await AsyncElasticsearch.delete_by_query(self, index=str(collection_id), body=body)
        await self.indices.refresh(index=str(collection_id))

    async def get_chunks(self, collection_id: int, document_id: int, offset: int = 0, limit: int = 10, chunk_id: Optional[int] = None) -> List[Chunk]:
        body = {"query": {"bool": {"must": [{"match": {"metadata.document_id": document_id}}]}}, "_source": ["id", "content", "metadata"]}
        if chunk_id is not None:
            body["query"]["bool"]["must"].append({"term": {"id": chunk_id}})

        results = await AsyncElasticsearch.search(self, index=str(collection_id), body=body, from_=offset, size=limit)

        chunks = []
        for hit in results["hits"]["hits"]:
            chunks.append(Chunk(id=hit["_source"]["id"], content=hit["_source"]["content"], metadata=hit["_source"]["metadata"]))

        return chunks

    async def upsert(self, collection_id: int, chunks: List[Chunk], embeddings: List[list[float]]) -> None:
        actions = [
            {
                "_index": str(collection_id),
                "_source": {
                    "id": chunk.id,
                    "content": chunk.content,
                    "embedding": embedding,
                    "metadata": chunk.metadata,
                },
            }
            for chunk, embedding in zip(chunks, embeddings)
        ]

        await helpers.async_bulk(client=self, actions=actions, index=collection_id)
        await self.indices.refresh(index=str(collection_id))

    async def search(
        self,
        method: SearchMethod,
        collection_ids: List[int],
        query_prompt: str,
        query_vector: list[float],
        k: int,
        rff_k: Optional[int] = 20,
        score_threshold: float = 0.0,
    ) -> List[Search]:
        if method == SearchMethod.SEMANTIC:
            searches = await self._semantic_query(query_vector=query_vector, collection_ids=collection_ids, k=k, score_threshold=score_threshold)

        elif method == SearchMethod.LEXICAL:
            searches = await self._lexical_search(query_prompt=query_prompt, collection_ids=collection_ids, k=k, score_threshold=score_threshold)

        else:  # method == SearchMethod.HYBRID
            searches = await self._hybrid_search(query_prompt=query_prompt, query_vector=query_vector, collection_ids=collection_ids, k=k, rff_k=rff_k)  # fmt: off

        return searches

    async def _lexical_search(self, query_prompt: str, collection_ids: List[int], k: int) -> List[Search]:
        collection_ids = [str(x) for x in collection_ids]
        fuzziness = {"fuzziness": "AUTO"} if len(query_prompt.split()) < 25 else {}
        body = {"query": {"multi_match": {"query": query_prompt, **fuzziness}}, "size": k, "_source": {"excludes": ["embedding"]}}
        results = await AsyncElasticsearch.search(self, index=collection_ids, body=body)
        hits = [hit for hit in results["hits"]["hits"] if hit]
        searches = [
            Search(
                method=SearchMethod.LEXICAL.value,
                score=hit["_score"],
                chunk=Chunk(id=hit["_source"]["id"], content=hit["_source"]["content"], metadata=hit["_source"]["metadata"]),
            )
            for hit in hits
        ]
        return searches

    async def _semantic_query(self, query_vector: list[float], collection_ids: List[int], k: int, score_threshold: float = 0.0) -> List[Search]:  # fmt: off
        collection_ids = [str(x) for x in collection_ids]
        body = {"knn": {"field": "embedding", "query_vector": query_vector, "k": k, "num_candidates": 200}}
        results = await AsyncElasticsearch.search(self, index=collection_ids, body=body)
        hits = [hit for hit in results["hits"]["hits"] if hit]
        searches = [
            Search(
                method=SearchMethod.SEMANTIC.value,
                score=hit["_score"],
                chunk=Chunk(id=hit["_source"]["id"], content=hit["_source"]["content"], metadata=hit["_source"]["metadata"]),
            )
            for hit in hits
        ]

        searches = [search for search in searches if search.score >= score_threshold]
        searches = sorted(searches, key=lambda x: x.score, reverse=True)[:k]

        return searches

    async def _hybrid_search(self, query_prompt: str, query_vector: list[float], collection_ids: List[int], k: int, rff_k: int) -> List[Search]:
        """
        Hybrid search combines lexical and semantic search results using Reciprocal Rank Fusion (RRF).

        Args:
            query_prompt (str): The search prompt
            query_vector (list[float]): The query vector
            collection_ids (List[int]): The collection ids
            k (int): The number of results to return
            rff_k (int): The constant k in the RRF formula

        Returns:
            A combined list of searches with updated scores
        """
        lexical_searches = await self._lexical_search(query_prompt=query_prompt, collection_ids=collection_ids, k=k)
        semantic_searches = await self._semantic_query(query_vector=query_vector, collection_ids=collection_ids, k=k)

        combined_scores = {}
        search_map = {}
        for searches in [lexical_searches, semantic_searches]:
            for rank, search in enumerate(searches):
                chunk_id = search.chunk.id
                if chunk_id not in combined_scores:
                    combined_scores[chunk_id] = 0
                    search_map[chunk_id] = search
                else:
                    search_map[chunk_id].method = SearchMethod.HYBRID
                combined_scores[chunk_id] += 1 / (rff_k + rank + 1)

        ranked_scores = sorted(combined_scores.items(), key=lambda item: item[1], reverse=True)
        reranked_searches = []
        for chunk_id, rrf_score in ranked_scores:
            search = search_map[chunk_id]
            search.score = rrf_score
            reranked_searches.append(search)

        searches = reranked_searches[:k]

        return searches
