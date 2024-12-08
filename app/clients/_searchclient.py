from abc import ABC, abstractmethod
from typing import List, Literal, Optional, Union
from uuid import UUID

from app.schemas.chunks import Chunk
from app.schemas.collections import Collection
from app.schemas.documents import Document
from app.schemas.search import Search
from app.schemas.security import User
from app.utils.variables import HYBRID_SEARCH_TYPE, LEXICAL_SEARCH_TYPE, SEMANTIC_SEARCH_TYPE, PRIVATE_COLLECTION_TYPE


class SearchClient(ABC):
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
    ) -> List[Search]:
        """
        Search for chunks in a collection.

        Args:
            prompt (str): The prompt to search for.
            user (User): The user searching for the chunks.
            collection_ids (List[str]): The ids of the collections to search in.
            method (Literal[LEXICAL_SEARCH_TYPE, SEMANTIC_SEARCH_TYPE, HYBRID_SEARCH_TYPE]): The method to use for the search, default: SEMENTIC_SEARCH_TYPE.
            k (Optional[int]): The number of chunks to return.
            rff_k (Optional[int]): The constant k in the RRF formula.
            score_threshold (Optional[float]): The score threshold for the chunks to return.

        Returns:
            List[Search]: A list of Search objects containing the retrieved chunks.
        """
        pass

    @abstractmethod
    def get_collections(self, user: User, collection_ids: List[str] = []) -> List[Collection]:
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
        self,
        collection_id: str,
        collection_name: str,
        collection_model: str,
        user: User,
        collection_type: str = PRIVATE_COLLECTION_TYPE,
        collection_description: Optional[str] = None,
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
    def get_chunks(self, collection_id: str, document_id: str, user: User, limit: int = 10, offset: Union[int, UUID] = None) -> List[Chunk]:
        """
        Get chunks from a collection and a document.
        Args:
            collection_id (str): The id of the collection to get chunks from.
            document_id (str): The id of the document to get chunks from.
            user (User): The user retrieving the chunks.
            limit (Optional[int]): The number of chunks to return.
            offset (Optional[int, UUID]): The offset of the chunks to return (UUID is for qdrant and int for elasticsearch).
        Returns:
            List[Chunk]: A list of Chunk objects containing the retrieved chunks.
        """
        pass

    @abstractmethod
    def get_documents(self, collection_id: str, user: User, limit: int = 10, offset: Union[int, UUID] = None) -> List[Document]:
        """
        Get documents from a collection.

        Args:
            collection_id (str): The id of the collection to get documents from.
            user (User): The user retrieving the documents.
            limit (int): The number of documents to return.
            offset (Optional[int]): The offset of the documents to return (UUID is for qdrant and int for elasticsearch).

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
