from abc import ABC
from typing import List, Optional, Type
import importlib

from app.schemas.chunks import Chunk
from app.schemas.collections import Collection
from app.schemas.documents import Document
from app.schemas.search import Filter, Search
from app.schemas.security import User


def to_camel_case(chaine):
    mots = chaine.replace("_", " ").split()
    camel_case = "".join(mot.capitalize() for mot in mots)
    return camel_case


class SearchClient(ABC):
    @staticmethod
    def import_constructor(name: str) -> "Type[SearchClient]":
        module = importlib.import_module(f"app.helpers.searchclients._{name}searchclient")
        return getattr(module, f"{to_camel_case(name)}SearchClient")

    def upsert(self, chunks: List[Chunk], collection_id: str, user: User) -> None:
        """
        Add chunks to a collection.

        Args:
            chunks (List[Chunk]): A list of chunks to add to the collection.
            collection_id (str): The id of the collection to add the chunks to.
            user (User): The user adding the chunks.
        """
        pass

    def query(
        self,
        prompt: str,
        user: User,
        collection_ids: List[str] = [],
        k: Optional[int] = 4,
        score_threshold: Optional[float] = None,
        filter: Optional[Filter] = None,
    ) -> List[Search]:
        """
        Search for chunks in a collection.

        Args:
            prompt (str): The prompt to search for.
            user (User): The user searching for the chunks.
            collection_ids (List[str]): The ids of the collections to search in.
            k (Optional[int]): The number of chunks to return.
            score_threshold (Optional[float]): The score threshold for the chunks to return.
            filter (Optional[Filter]): The filter to apply to the chunks to return.

        Returns:
            List[Search]: A list of search objects containing the retrieved chunks.
        """
        pass

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

    def create_collection(self, collection: Collection) -> Collection:
        """
        Create a collection, if collection already exists, return the collection id.
        Args:
            collection_id (str): The id of the collection to create.
            collection_name (str): The name of the collection to create.
            collection_model (str): The model of the collection to create.
            collection_type (str): The type of the collection to create.
            user (User): The user creating the collection.
        """
        pass

    def delete_collection(self, collection_id: str, user: User) -> None:
        """
        Delete a collection and all its associated data.
        Args:
            collection_id (str): The id of the collection to delete.
            user (User): The user deleting the collection.
        """
        pass

    def get_chunks(self, collection_id: str, user: User, limit: Optional[int] = None, offset: Optional[int] = None) -> List[Chunk]:
        """
        Get chunks from a collection and a document.
        Args:
            collection_id (str): The id of the collection to get chunks from.
            document_id (str): The id of the document to get chunks from.
            user (User): The user retrieving the chunks.
            limit (Optional[int]): The number of chunks to return.
            offset (Optional[int]): The offset of the chunks to return.
        Returns:
            List[Chunk]: A list of Chunk objects containing the retrieved chunks.
        """
        pass

    def get_documents(self, collection_id: str, user: User, limit: Optional[int] = None, offset: Optional[int] = None) -> List[Document]:
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

    def delete_document(self, document_id: str, user: User) -> None:
        """
        Delete a document from a collection.

        Args:
            collection_id (str): The id of the collection to delete the document from.
            document_id (str): The id of the document to delete.
            user (User): The user deleting the document.
        """
        pass