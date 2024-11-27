from abc import ABC, abstractmethod
from typing import List, Literal, Optional, Type, Union
from uuid import UUID
import importlib

from app.schemas.chunks import Chunk
from app.schemas.collections import Collection
from app.schemas.documents import Document
from app.schemas.search import Filter, Search
from app.schemas.security import User
from app.utils.variables import HYBRID_SEARCH_TYPE, LEXICAL_SEARCH_TYPE, SEMANTIC_SEARCH_TYPE


def to_camel_case(chaine):
    mots = chaine.replace("_", " ").split()
    camel_case = "".join(mot.capitalize() for mot in mots)
    return camel_case


class SearchClient(ABC):
    @staticmethod
    def import_constructor(name: str) -> "Type[SearchClient]":
        module = importlib.import_module(f"app.helpers.searchclients._{name}searchclient")
        return getattr(module, f"{to_camel_case(name)}SearchClient")

    @abstractmethod
    def upsert(self, chunks: List[Chunk], collection_id: str, user: User) -> None:
        """
        Add chunks to a collection.

        Args:
            chunks (List[Chunk]): A list of chunks to add to the collection.
            collection_id (str): The id of the collection to add the chunks to.
            user (User): The user adding the chunks.
        """
        pass

    @abstractmethod
    def query(
        self,
        prompt: str,
        user: User,
        collection_ids: List[str] = [],
        method: Literal[HYBRID_SEARCH_TYPE, LEXICAL_SEARCH_TYPE, SEMANTIC_SEARCH_TYPE] = SEMANTIC_SEARCH_TYPE,
        k: Optional[int] = 4,
        rff_k: Optional[int] = 20,
        score_threshold: Optional[float] = None,
        query_filter: Optional[Filter] = None,
    ) -> List[Search]:
        """
        Search for chunks in a collection.

        Args:
            prompt (str): The prompt to search for.
            user (User): The user searching for the chunks.
            collection_ids (List[str]): The ids of the collections to search in.
            method (Literal[LEXICAL_SEARCH_TYPE, SEMANTIC_SEARCH_TYPE]): The method to use for the search.
            k (Optional[int]): The number of chunks to return.
            score_threshold (Optional[float]): The score threshold for the chunks to return.
            filter (Optional[Filter]): The filter to apply to the chunks to return.

        Returns:
            List[Search]: A list of search objects containing the retrieved chunks.
        """
        pass

    @abstractmethod
    def get_collections(self, collection_ids: List[str], user: User) -> List[Collection]:
        """
        Get metadata of collections.

        Args:
            user (User): The user retrieving the collections.
            collection_ids (List[str]): List of collection ids to retrieve metadata for. If is an empty list, all collections will be considered.

        Returns:
            List[Collection]: A list of Collection objects containing the metadata for the specified collections.
        """
        pass

    @abstractmethod
    def create_collection(
        self, collection_id: str, collection_name: str, collection_model: str, collection_type: str, collection_description: str, user: User
    ) -> Collection:
        """
        Create a collection, if collection already exists, return the collection id.
        Args:
            collection_id (str): The id of the collection to create.
            collection_name (str): The name of the collection to create.
            collection_model (str): The model of the collection to create.
            collection_type (str): The type of the collection to create.
            collection_description (str): The description of the collection to create.
            user (User): The user creating the collection.
        """
        pass

    @abstractmethod
    def delete_collection(self, collection_id: str, user: User) -> None:
        """
        Delete a collection and all its associated data.
        Args:
            collection_id (str): The id of the collection to delete.
            user (User): The user deleting the collection.
        """
        pass

    @abstractmethod
    def get_chunks(
        self, collection_id: str, document_id: str, user: User, limit: Optional[int] = None, offset: Union[int, UUID] = None
    ) -> List[Chunk]:
        """
        Get chunks from a collection and a document.
        Args:
            collection_id (str): The id of the collection to get chunks from.
            document_id (str): The id of the document to get chunks from.
            user (User): The user retrieving the chunks.
            limit (Optional[int]): The number of chunks to return.
            offset (Optional[int, UUID]): The offset of the chunks to return (UUID is for qdrant and int for elasticsearch)
        Returns:
            List[Chunk]: A list of Chunk objects containing the retrieved chunks.
        """
        pass

    @abstractmethod
    def get_documents(self, collection_id: str, user: User, limit: Optional[int] = None, offset: Union[int, UUID] = None) -> List[Document]:
        """
        Get documents from a collection.

        Args:
            collection_id (str): The id of the collection to get documents from.
            user (User): The user retrieving the documents.
            limit (Optional[int]): The number of documents to return.
            offset (Optional[int]): The offset of the documents to return.

        Returns:
            List[Document]: A list of Document objects containing the retrieved documents.
        """
        pass

    @abstractmethod
    def delete_document(self, collection_id: str, document_id: str, user: User):
        """
        Delete a document from a collection.

        Args:
            collection_id (str): The id of the collection to delete the document from.
            document_id (str): The id of the document to delete.
            user (User): The user deleting the document.
        """
        pass

    @staticmethod
    def build_ranked_searches(searches_list: List[List[Search]], limit: int, rff_k: Optional[int] = 20):
        """
        Combine search results using Reciprocal Rank Fusion (RRF)
        :param searches_list: A list of searches from different query
        :param limit: The number of results to return
        :param rff_k: The constant k in the RRF formula
        :return: A combined list of searches with updated scores
        """

        combined_scores = {}
        search_map = {}
        for searches in searches_list:
            for rank, search in enumerate(searches):
                chunk_id = search.chunk.id
                if chunk_id not in combined_scores:
                    combined_scores[chunk_id] = 0
                    search_map[chunk_id] = search
                else:
                    search_map[chunk_id].method = search_map[chunk_id].method + "/" + search.method
                combined_scores[chunk_id] += 1 / (rff_k + rank + 1)

        ranked_scores = sorted(combined_scores.items(), key=lambda item: item[1], reverse=True)
        reranked_searches = []
        for chunk_id, rrf_score in ranked_scores:
            search = search_map[chunk_id]
            search.score = rrf_score
            reranked_searches.append(search)

        if limit:
            return reranked_searches[:limit]
        return reranked_searches
