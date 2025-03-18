from typing import List, Optional
from uuid import UUID

from qdrant_client import AsyncQdrantClient
from qdrant_client.http.models import FieldCondition, Filter, MatchAny, PointStruct
from sqlalchemy import delete, func, insert, or_, select, update
from sqlalchemy.exc import NoResultFound

from app.clients.database import SQLDatabaseClient
from app.clients.model import BaseModelClient as ModelClient
from app.schemas.chunks import Chunk, ChunkMetadata
from app.schemas.collections import Collection, CollectionType
from app.schemas.documents import Document
from app.sql.models import Collection as CollectionTable
from app.sql.models import Document as DocumentTable
from app.sql.models import User as UserTable
from app.utils.exceptions import CollectionNotFoundException, DocumentNotFoundException, UserNotFoundException


class DocumentManager:
    BATCH_SIZE = 48  # TODO: retrieve batch size from model registry

    def __init__(self, sql: SQLDatabaseClient, qdrant: AsyncQdrantClient) -> None:
        """
        Initialize the authentication manager: create the root user and role if they don't exist and check if the root password is correct and update it if needed
        """

        self.sql = sql
        self.qdrant = qdrant

    async def create_collection(self, name: str, user_id: int, type: CollectionType, description: Optional[str] = None) -> int:
        async with self.sql.session() as session:
            # check if user exists
            result = await session.execute(statement=select(UserTable.id).where(UserTable.id == user_id))
            try:
                result.scalar_one()
            except NoResultFound:
                raise UserNotFoundException()

            # create the collection
            await session.execute(statement=insert(table=CollectionTable).values(name=name, user_id=user_id, type=type, description=description))
            await session.commit()

            # get the collection id
            result = await session.execute(statement=select(CollectionTable.id).where(CollectionTable.name == name))
            collection_id = result.scalar_one()

            return collection_id

    async def delete_collection(self, collection_id: int) -> None:
        async with self.sql.session() as session:
            # check if collection exists
            result = await session.execute(statement=select(CollectionTable.id).where(CollectionTable.id == collection_id))
            try:
                result.scalar_one()
            except NoResultFound:
                raise CollectionNotFoundException()

            # delete the collection
            await session.execute(statement=delete(table=CollectionTable).where(CollectionTable.id == collection_id))
            await session.commit()

    async def update_collection(
        self, collection_id: int, name: Optional[str] = None, type: Optional[CollectionType] = None, description: Optional[str] = None
    ) -> None:
        async with self.sql.session() as session:
            # check if collection exists
            result = await session.execute(
                statement=select(CollectionTable)
                .join(target=UserTable, onclause=UserTable.id == CollectionTable.user_id)
                .where(CollectionTable.id == collection_id)
            )
            try:
                collection = result.scalar_one()
            except NoResultFound:
                raise CollectionNotFoundException()

            name = name if name is not None else collection.name
            type = type if type is not None else collection.type
            description = description if description is not None else collection.description

            await session.execute(
                statement=update(table=CollectionTable)
                .values(name=name, type=type, description=description, updated_at=func.now())
                .where(CollectionTable.id == collection.id)
            )
            await session.commit()

    async def get_collections(self, user_id: int, collection_id: Optional[int] = None, include_public: bool = True, offset: int = 0, limit: int = 10) -> List[Collection]:  # fmt: off
        async with self.sql.session() as session:
            statement = select(CollectionTable).offset(offset=offset).limit(limit=limit)

            if collection_id:
                statement = statement.where(CollectionTable.id == collection_id)
            if include_public:
                statement = statement.where(or_(CollectionTable.user_id == user_id, CollectionTable.type == CollectionType.PUBLIC))
            else:
                statement = statement.where(CollectionTable.user_id == user_id)

            # TODO: add documents count

            result = await session.execute(statement=statement)
            collections = result.all()

            if collection_id and len(collections) == 0:
                raise CollectionNotFoundException()

            collections = [Collection(**row._mapping) for row in result.all()]

        return collections

    async def create_document(self, name: str, collection_id: int, user_id: int) -> int:
        async with self.sql.session() as session:
            # check if collection exists
            result = await session.execute(statement=select(CollectionTable.documents).where(CollectionTable.id == collection_id))
            try:
                result.scalar_one()
            except NoResultFound:
                raise CollectionNotFoundException()

            await session.execute(statement=insert(table=DocumentTable).values(name=name, collection_id=collection_id, user_id=user_id))
            await session.commit()

            # get the document id
            result = await session.execute(statement=select(DocumentTable.id).where(DocumentTable.name == name))
            document_id = result.scalar_one()

            return document_id

    async def _create_embeddings(self, input: List[str], model_client: ModelClient) -> list[float] | list[list[float]] | dict:
        response = await model_client.embeddings.create(input=input, model=model_client.model, encoding_format="float")

        return [vector.embedding for vector in response.data]

    async def _upsert(self, chunks: List[Chunk], collection_id: int, model_client: ModelClient) -> None:
        for i in range(0, len(chunks), self.BATCH_SIZE):
            batch = chunks[i : i + self.BATCH_SIZE]
            # create embeddings
            texts = [chunk.content for chunk in batch]

            embeddings = await self._create_embeddings(input=texts, model_client=model_client)

            # insert chunks and vectors
            await self.qdrant.upsert(
                collection_name=collection_id,
                points=[
                    PointStruct(id=chunk.id, vector=embedding, payload={"content": chunk.content, "metadata": chunk.metadata.model_dump()})
                    for chunk, embedding in zip(batch, embeddings)
                ],
            )

    async def get_documents(self, collection_id: int, document_id: Optional[int] = None, offset: int = 0, limit: int = 10) -> List[Document]:  # fmt: off
        async with self.sql.session() as session:
            statement = select(DocumentTable).offset(offset=offset).limit(limit=limit).where(DocumentTable.collection_id == collection_id)
            if document_id:
                statement = statement.where(DocumentTable.id == document_id)

            result = await session.execute(statement=statement)
            documents = result.all()

            if document_id and len(documents) == 0:
                raise DocumentNotFoundException()

            documents = [Document(**row._mapping) for row in result.all()]

            return documents

    async def get_chunks(self, collection_id: int, document_id: int, offset: Optional[UUID] = None, limit: int = 10) -> List[Chunk]:
        # TODO: add chunk_id filter
        filter = Filter(must=[FieldCondition(key="metadata.document_id", match=MatchAny(any=[document_id]))])
        data = await self.qdrant.scroll(collection_name=collection_id, scroll_filter=filter, limit=limit, offset=offset)[0]
        chunks = [Chunk(id=chunk.id, content=chunk.payload["content"], metadata=ChunkMetadata(**chunk.payload["metadata"])) for chunk in data]

        return chunks
