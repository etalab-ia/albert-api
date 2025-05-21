from functools import partial
import logging
import time
import traceback
from typing import List, Optional
from uuid import uuid4

from fastapi import UploadFile
from qdrant_client import AsyncQdrantClient
from sqlalchemy import Integer, cast, delete, distinct, func, insert, or_, select, update
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.model import BaseModelClient as ModelClient
from app.helpers.data.chunkers import LangchainRecursiveCharacterTextSplitter, NoChunker
from app.helpers.data.parsers import HTMLParser, JSONParser, MarkdownParser, PDFParser
from app.helpers.models.routers import ModelRouter
from app.schemas.chunks import Chunk
from app.schemas.collections import Collection, CollectionVisibility
from app.schemas.core.data import ParserOutput
from app.schemas.documents import Document
from app.schemas.files import ChunkerName
from app.schemas.search import Search, SearchMethod
from app.sql.models import Collection as CollectionTable
from app.sql.models import Document as DocumentTable
from app.sql.models import User as UserTable
from app.utils.multiagents import MultiAgents
from app.utils.exceptions import (
    ChunkingFailedException,
    CollectionNotFoundException,
    DocumentNotFoundException,
    ParsingDocumentFailedException,
    UnsupportedFileTypeException,
    VectorizationFailedException,
    WebSearchNotAvailableException,
)
from app.utils.variables import ENDPOINT__CHAT_COMPLETIONS, ENDPOINT__EMBEDDINGS

from ._websearchmanager import WebSearchManager

logger = logging.getLogger(__name__)


class DocumentManager:
    BATCH_SIZE = 48  # @TODO: retrieve batch size from model registry
    FILE_EXTENSION_PDF = "pdf"
    FILE_EXTENSION_JSON = "json"
    FILE_EXTENSION_HTML = "html"
    FILE_EXTENSION_MD = "md"
    SUPPORTED_FILE_EXTENSIONS = [FILE_EXTENSION_PDF, FILE_EXTENSION_JSON, FILE_EXTENSION_HTML, FILE_EXTENSION_MD]

    def __init__(
        self,
        qdrant: AsyncQdrantClient,
        qdrant_model: ModelRouter,
        web_search: Optional[WebSearchManager] = None,
        multi_agents_search_model: Optional[ModelRouter] = None,
    ) -> None:
        self.qdrant = qdrant
        self.qdrant_model = qdrant_model
        self.web_search = web_search
        self.multi_agents_search_model = multi_agents_search_model

    async def create_collection(self, session: AsyncSession, user_id: int, name: str, visibility: CollectionVisibility, description: Optional[str] = None) -> int:  # fmt: off
        result = await session.execute(
            statement=insert(table=CollectionTable)
            .values(name=name, user_id=user_id, visibility=visibility, description=description)
            .returning(CollectionTable.id)
        )
        collection_id = result.scalar_one()
        await session.commit()

        await self.qdrant.create_collection(collection_id=collection_id, vector_size=self.qdrant_model._vector_size)

        return collection_id

    async def delete_collection(self, session: AsyncSession, user_id: int, collection_id: int) -> None:
        # check if collection exists
        result = await session.execute(
            statement=select(CollectionTable.id).where(CollectionTable.id == collection_id).where(CollectionTable.user_id == user_id)
        )
        try:
            result.scalar_one()
        except NoResultFound:
            raise CollectionNotFoundException()

        # delete the collection
        await session.execute(statement=delete(table=CollectionTable).where(CollectionTable.id == collection_id))
        await session.commit()

        # delete the collection from vector store
        await self.qdrant.delete_collection(collection_id=collection_id)

    async def update_collection(self, session: AsyncSession, user_id: int, collection_id: int, name: Optional[str] = None, visibility: Optional[CollectionVisibility] = None, description: Optional[str] = None) -> None:  # fmt: off
        # check if collection exists
        result = await session.execute(
            statement=select(CollectionTable)
            .join(target=UserTable, onclause=UserTable.id == CollectionTable.user_id)
            .where(CollectionTable.id == collection_id)
            .where(UserTable.id == user_id)
        )
        try:
            collection = result.scalar_one()
        except NoResultFound:
            raise CollectionNotFoundException()

        name = name if name is not None else collection.name
        visibility = visibility if visibility is not None else collection.visibility
        description = description if description is not None else collection.description

        await session.execute(
            statement=update(table=CollectionTable)
            .values(name=name, visibility=visibility, description=description)
            .where(CollectionTable.id == collection.id)
        )
        await session.commit()

    async def get_collections(self, session: AsyncSession, user_id: int, collection_id: Optional[int] = None, include_public: bool = True, offset: int = 0, limit: int = 10) -> List[Collection]:  # fmt: off
        # Query basic collection data
        statement = (
            select(
                CollectionTable.id,
                CollectionTable.name,
                UserTable.name.label("owner"),
                CollectionTable.visibility,
                CollectionTable.description,
                func.count(distinct(DocumentTable.id)).label("documents"),
                cast(func.extract("epoch", CollectionTable.created_at), Integer).label("created_at"),
                cast(func.extract("epoch", CollectionTable.updated_at), Integer).label("updated_at"),
            )
            .outerjoin(DocumentTable, CollectionTable.id == DocumentTable.collection_id)
            .outerjoin(UserTable, CollectionTable.user_id == UserTable.id)
            .group_by(CollectionTable.id, UserTable.name)
            .offset(offset=offset)
            .limit(limit=limit)
        )

        if collection_id:
            statement = statement.where(CollectionTable.id == collection_id)
        if include_public:
            statement = statement.where(or_(CollectionTable.user_id == user_id, CollectionTable.visibility == CollectionVisibility.PUBLIC))
        else:
            statement = statement.where(CollectionTable.user_id == user_id)

        result = await session.execute(statement=statement)
        collections = [Collection(**row._asdict()) for row in result.all()]

        if collection_id and len(collections) == 0:
            raise CollectionNotFoundException()

        return collections

    async def create_document(self, session: AsyncSession, user_id: int, collection_id: int, file: UploadFile, chunker_name: ChunkerName, chunker_args: dict) -> int:  # fmt: off
        # check if collection exists
        result = await session.execute(
            statement=select(CollectionTable).where(CollectionTable.id == collection_id).where(CollectionTable.user_id == user_id)
        )
        try:
            collection = result.scalar_one()
        except NoResultFound:
            raise CollectionNotFoundException()

        document_name = file.filename.strip()
        file_extension = document_name.rsplit(".", maxsplit=1)[-1]

        try:
            document = self._parse(file=file, file_extension=file_extension)
        except Exception as e:
            logger.error(msg=f"Error during file parsing: {e}")
            logger.debug(msg=traceback.format_exc())
            raise ParsingDocumentFailedException(detail=f"Parsing document failed: {e}")

        try:
            chunks = self._split(document=document, chunker_name=chunker_name, chunker_args=chunker_args)
        except Exception as e:
            logger.error(msg=f"Error during document splitting: {e}")
            logger.debug(msg=traceback.format_exc())
            raise ChunkingFailedException(detail=f"Chunking failed: {e}")

        result = await session.execute(
            statement=insert(table=DocumentTable).values(name=document_name, collection_id=collection_id).returning(DocumentTable.id)
        )
        document_id = result.scalar_one()
        await session.commit()

        client = self.qdrant_model.get_client(endpoint=ENDPOINT__EMBEDDINGS)
        for i, chunk in enumerate(chunks):
            chunk.metadata["collection_id"] = collection.id
            chunk.metadata["document_id"] = document_id
            chunk.metadata["document_name"] = document_name
            chunk.metadata["document_created_at"] = round(time.time())
        try:
            await self._upsert(chunks=chunks, collection_id=collection_id, model_client=client)
        except Exception as e:
            logger.error(msg=f"Error during document creation: {e}")
            logger.debug(msg=traceback.format_exc())
            await self.delete_document(session=session, user_id=user_id, document_id=document_id)
            raise VectorizationFailedException(detail=f"Vectorization failed: {e}")

        return document_id

    async def get_documents(self, session: AsyncSession, user_id: int, collection_id: Optional[int] = None, document_id: Optional[int] = None, offset: int = 0, limit: int = 10) -> List[Document]:  # fmt: off
        statement = (
            select(
                DocumentTable.id,
                DocumentTable.name,
                DocumentTable.collection_id,
                cast(func.extract("epoch", DocumentTable.created_at), Integer).label("created_at"),
            )
            .offset(offset=offset)
            .limit(limit=limit)
            .outerjoin(CollectionTable, DocumentTable.collection_id == CollectionTable.id)
            .where(or_(CollectionTable.user_id == user_id, CollectionTable.visibility == CollectionVisibility.PUBLIC))
        )
        if collection_id:
            statement = statement.where(DocumentTable.collection_id == collection_id)
        if document_id:
            statement = statement.where(DocumentTable.id == document_id)

        result = await session.execute(statement=statement)
        documents = [Document(**row._asdict()) for row in result.all()]

        if document_id and len(documents) == 0:
            raise DocumentNotFoundException()

        # chunks count
        for document in documents:
            document.chunks = await self.qdrant.get_chunk_count(collection_id=document.collection_id, document_id=document.id)

        return documents

    async def delete_document(self, session: AsyncSession, user_id: int, document_id: int) -> None:
        # check if document exists
        result = await session.execute(
            statement=select(DocumentTable)
            .join(CollectionTable, DocumentTable.collection_id == CollectionTable.id)
            .where(DocumentTable.id == document_id)
            .where(CollectionTable.user_id == user_id)
        )
        try:
            document = result.scalar_one()
        except NoResultFound:
            raise DocumentNotFoundException()

        await session.execute(statement=delete(table=DocumentTable).where(DocumentTable.id == document_id))
        await session.commit()

        # delete the document from vector store
        await self.qdrant.delete_document(collection_id=document.collection_id, document_id=document_id)

    async def get_chunks(
        self,
        session: AsyncSession,
        user_id: int,
        document_id: int,
        chunk_id: Optional[int] = None,
        offset: int = 0,
        limit: int = 10,
    ) -> List[Chunk]:
        # check if document exists
        result = await session.execute(
            statement=select(DocumentTable)
            .join(CollectionTable, DocumentTable.collection_id == CollectionTable.id)
            .where(DocumentTable.id == document_id)
            .where(CollectionTable.user_id == user_id)
        )
        try:
            document = result.scalar_one()
        except NoResultFound:
            raise DocumentNotFoundException()

        chunks = await self.qdrant.get_chunks(
            collection_id=document.collection_id,
            document_id=document_id,
            offset=offset,
            limit=limit,
            chunk_id=chunk_id,
        )

        return chunks

    async def search(
        self,
        session: AsyncSession,
        collection_ids: List[int],
        user_id: int,
        prompt: str,
        method: str,
        k: int,
        rff_k: int,
        score_threshold: float = 0.0,
        web_search: bool = False,
    ) -> List[Search]:
        # web search
        if not self.web_search and web_search:
            raise WebSearchNotAvailableException()

        web_collection_id = None
        qdrant_client = self.qdrant_model.get_client(endpoint=ENDPOINT__EMBEDDINGS)
        if web_search:
            client = self.web_search_model.get_client(endpoint=ENDPOINT__CHAT_COMPLETIONS)
            web_query = await self.web_search.get_web_query(prompt=prompt, model_client=client)
            web_results = await self.web_search.get_results(query=web_query, n=3)
            if web_results:
                web_collection_id = await self.create_collection(
                    session=session,
                    name=f"tmp_web_collection_{uuid4()}",
                    user_id=user_id,
                    visibility=CollectionVisibility.PRIVATE,
                )
                for file in web_results:
                    await self.create_document(
                        session=session,
                        user_id=user_id,
                        collection_id=web_collection_id,
                        file=file,
                        chunker_name=ChunkerName.LANGCHAIN_RECURSIVE_CHARACTER_TEXT_SPLITTER,
                        chunker_args={"chunk_overlap": 0, "chunk_min_size": 20, "chunk_size": 1000},
                    )
                collection_ids.append(web_collection_id)

        # check if collections exist
        for collection_id in collection_ids:
            result = await session.execute(
                statement=select(CollectionTable)
                .where(CollectionTable.id == collection_id)
                .where(or_(CollectionTable.user_id == user_id, CollectionTable.visibility == CollectionVisibility.PUBLIC))
            )
            try:
                result.scalar_one()
            except NoResultFound:
                raise CollectionNotFoundException(detail=f"Collection {collection_id} not found.")

        response = await self._create_embeddings(input=[prompt], model_client=qdrant_client)
        query_vector = response[0]
        if method == SearchMethod.MULTIAGENT:
            qdrant_method = SearchMethod.SEMANTIC
        else:
            qdrant_method = method

        searches = await self.qdrant.search(
            method=qdrant_method,
            collection_ids=collection_ids,
            query_prompt=prompt,
            query_vector=query_vector,
            k=k,
            rff_k=rff_k,
            score_threshold=score_threshold,
        )
        if method == SearchMethod.MULTIAGENT:
            searches = await MultiAgents.search(
                partial(self.search, user_id=user_id),
                searches,
                prompt,
                session,
                k,
            )

        if web_collection_id:
            await self.delete_collection(session=session, user_id=user_id, collection_id=web_collection_id)

        return searches

    def _parse(self, file: UploadFile, file_extension: str) -> ParserOutput:
        if file_extension == self.FILE_EXTENSION_PDF:
            parser = PDFParser()

        elif file_extension == self.FILE_EXTENSION_JSON:
            parser = JSONParser()

        elif file_extension == self.FILE_EXTENSION_HTML:
            parser = HTMLParser()

        elif file_extension == self.FILE_EXTENSION_MD:
            parser = MarkdownParser()
        else:
            raise UnsupportedFileTypeException()

        output = parser.parse(file=file)

        return output

    def _split(self, document: ParserOutput, chunker_name: ChunkerName, chunker_args: dict) -> List[Chunk]:
        if chunker_name == ChunkerName.LANGCHAIN_RECURSIVE_CHARACTER_TEXT_SPLITTER:
            chunker = LangchainRecursiveCharacterTextSplitter(**chunker_args)
        else:  # ChunkerName.NoChunker
            chunker = NoChunker(**chunker_args)

        chunks = chunker.split(document=document)

        return chunks

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
                collection_id=collection_id,
                chunks=batch,
                embeddings=embeddings,
            )
