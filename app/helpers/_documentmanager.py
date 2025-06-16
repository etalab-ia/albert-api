from functools import partial
from itertools import batched
import logging
import time
import traceback
from typing import Callable, List, Optional
from uuid import uuid4

from fastapi import UploadFile
from langchain_text_splitters import Language
from qdrant_client import AsyncQdrantClient
from sqlalchemy import Integer, cast, delete, distinct, func, insert, or_, select, update
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from app.helpers.data.chunkers import NoSplitter, RecursiveCharacterTextSplitter
from app.helpers.models.routers import ModelRouter
from app.schemas.chunks import Chunk
from app.schemas.collections import Collection, CollectionVisibility
from app.schemas.documents import Chunker, Document
from app.schemas.parse import Languages, ParsedDocument, ParsedDocumentOutputFormat
from app.schemas.search import Search, SearchMethod
from app.sql.models import Collection as CollectionTable
from app.sql.models import Document as DocumentTable
from app.sql.models import User as UserTable
from app.utils.exceptions import (
    ChunkingFailedException,
    CollectionNotFoundException,
    DocumentNotFoundException,
    MultiAgentsSearchNotAvailableException,
    VectorizationFailedException,
    WebSearchNotAvailableException,
)
from app.utils.variables import ENDPOINT__EMBEDDINGS

from ._parsermanager import ParserManager
from ._websearchmanager import WebSearchManager
from ._multiagents import MultiAgents

logger = logging.getLogger(__name__)


class DocumentManager:
    BATCH_SIZE = 32
    multi_agents: Optional[MultiAgents] = None

    def __init__(
        self,
        qdrant: AsyncQdrantClient,
        parser: ParserManager,
        web_search: Optional[WebSearchManager] = None,
        multi_agents_model: Optional[ModelRouter] = None,
        multi_agents_reranker_model: Optional[ModelRouter] = None,
    ) -> None:
        self.qdrant = qdrant
        self.web_search = web_search
        self.parser = parser
        if multi_agents_model and multi_agents_reranker_model:
            self.multi_agents = MultiAgents(multi_agents_model, multi_agents_reranker_model)

    async def create_collection(self, session: AsyncSession, user_id: int, name: str, visibility: CollectionVisibility, description: Optional[str] = None) -> int:  # fmt: off
        result = await session.execute(
            statement=insert(table=CollectionTable)
            .values(name=name, user_id=user_id, visibility=visibility, description=description)
            .returning(CollectionTable.id)
        )
        collection_id = result.scalar_one()
        await session.commit()

        await self.qdrant.create_collection(collection_id=collection_id, vector_size=self.qdrant.model._vector_size)

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

    async def create_document(
        self,
        session: AsyncSession,
        user_id: int,
        collection_id: int,
        document: ParsedDocument,
        chunker: Chunker,
        chunk_size: int,
        chunk_overlap: int,
        length_function: Callable,
        chunk_min_size: int,
        is_separator_regex: Optional[bool] = None,
        separators: Optional[List[str]] = None,
        language_separators: Optional[Language] = None,
        metadata: Optional[dict] = None,
    ) -> int:
        # check if collection exists and prepare document chunks in a single transaction
        result = await session.execute(
            statement=select(CollectionTable).where(CollectionTable.id == collection_id).where(CollectionTable.user_id == user_id)
        )
        try:
            result.scalar_one()
        except NoResultFound:
            raise CollectionNotFoundException()

        try:
            chunks = self._split(
                document=document,
                chunker=chunker,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                length_function=length_function,
                is_separator_regex=is_separator_regex,
                separators=separators,
                chunk_min_size=chunk_min_size,
                language_separators=language_separators,
                metadata=metadata,
            )
        except Exception as e:
            logger.exception(msg=f"Error during document splitting: {e}")
            raise ChunkingFailedException(detail=f"Chunking failed: {e}")

        document_name = document.data[0].metadata.document_name
        try:
            result = await session.execute(
                statement=insert(table=DocumentTable).values(name=document_name, collection_id=collection_id).returning(DocumentTable.id)
            )
        except Exception as e:
            if "foreign key constraint" in str(e).lower() or "fkey" in str(e).lower():
                raise CollectionNotFoundException(detail=f"Collection {collection_id} no longer exists")
        document_id = result.scalar_one()
        await session.commit()

        for chunk in chunks:
            chunk.metadata["collection_id"] = collection_id
            chunk.metadata["document_id"] = document_id
            chunk.metadata["document_created_at"] = round(time.time())
        try:
            await self._upsert(chunks=chunks, collection_id=collection_id)
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

    async def parse_file(
        self,
        file: UploadFile,
        output_format: ParsedDocumentOutputFormat,
        force_ocr: bool,
        languages: Languages,
        page_range: str,
        paginate_output: bool,
        use_llm: bool,
    ) -> ParsedDocument:
        return await self.parser.parse_file(
            file=file,
            output_format=output_format,
            force_ocr=force_ocr,
            languages=languages,
            page_range=page_range,
            paginate_output=paginate_output,
            use_llm=use_llm,
        )

    async def search_chunks(
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
        web_search_k: int = 5,
    ) -> List[Search]:
        # web search
        if not self.web_search and web_search:
            raise WebSearchNotAvailableException()

        web_collection_id = None
        if web_search:
            web_collection_id = await self._create_web_collection(session=session, user_id=user_id, prompt=prompt, k=web_search_k)
        if web_collection_id:
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

        if not collection_ids:
            return []  # to avoid a request to create a query vector

        response = await self._create_embeddings(input=[prompt])
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
            if not self.multi_agents:
                raise MultiAgentsSearchNotAvailableException()
            searches = await self.multi_agents.search(
                doc_search=partial(self.search_chunks, user_id=user_id),
                searches=searches,
                prompt=prompt,
                session=session,
                k=k,
            )

        if web_collection_id:
            await self.delete_collection(session=session, user_id=user_id, collection_id=web_collection_id)

        return searches

    async def _create_web_collection(
        self,
        session: AsyncSession,
        user_id: int,
        prompt: str,
        k: int = 5,
    ) -> Optional[int]:
        web_query = await self.web_search.get_web_query(prompt=prompt)
        web_results = await self.web_search.get_results(query=web_query, k=k)
        collection_id = None
        if web_results:
            collection_id = await self.create_collection(
                session=session,
                name=f"tmp_web_collection_{uuid4()}",
                user_id=user_id,
                visibility=CollectionVisibility.PRIVATE,
            )
            for file in web_results:
                document = await self.parse_file(
                    file=file,
                    output_format=ParsedDocumentOutputFormat.MARKDOWN.value,
                    force_ocr=False,
                    languages=Languages.EN.value,
                    page_range="",
                    paginate_output=False,
                    use_llm=False,
                )
                await self.create_document(
                    session=session,
                    user_id=user_id,
                    collection_id=collection_id,
                    document=document,
                    chunker=Chunker.RECURSIVE_CHARACTER_TEXT_SPLITTER,
                    chunk_overlap=0,
                    chunk_min_size=20,
                    chunk_size=2048,
                    length_function=len,
                    language_separators=Language.HTML.value,
                )

        return collection_id

    def _split(
        self,
        document: ParsedDocument,
        chunker: Chunker,
        chunk_size: int,
        chunk_min_size: int,
        chunk_overlap: int,
        length_function: Callable,
        separators: Optional[List[str]] = None,
        is_separator_regex: Optional[bool] = None,
        language_separators: Optional[Language] = None,
        metadata: Optional[dict] = None,
    ) -> List[Chunk]:
        if chunker == Chunker.RECURSIVE_CHARACTER_TEXT_SPLITTER:
            chunker = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_min_size=chunk_min_size,
                chunk_overlap=chunk_overlap,
                length_function=length_function,
                separators=separators,
                is_separator_regex=is_separator_regex,
                language_separators=language_separators,
                metadata=metadata,
            )
        else:  # Chunker.NoSplitter
            chunker = NoSplitter(chunk_min_size=chunk_min_size, language_separators=language_separators, metadata=metadata)

        chunks = chunker.split_document(document=document)

        return chunks

    async def _create_embeddings(self, input: List[str]) -> list[float] | list[list[float]] | dict:
        client = self.qdrant.model.get_client(endpoint=ENDPOINT__EMBEDDINGS)
        response = await client.forward_request(method="POST", json={"input": input, "model": self.qdrant.model.id, "encoding_format": "float"})

        return [vector["embedding"] for vector in response.json()["data"]]

    async def _upsert(self, chunks: List[Chunk], collection_id: int) -> None:
        batches = batched(iterable=chunks, n=self.BATCH_SIZE)
        for batch in batches:
            # create embeddings
            texts = [chunk.content for chunk in batch]
            embeddings = await self._create_embeddings(input=texts)

            # insert chunks and vectors
            await self.qdrant.upsert(collection_id=collection_id, chunks=batch, embeddings=embeddings)
