import time
import traceback
from typing import List, Optional
from uuid import uuid4

from fastapi import UploadFile
from qdrant_client import AsyncQdrantClient
from qdrant_client.http.exceptions import ResponseHandlingException
from qdrant_client.http.models import (
    Distance,
    FieldCondition,
    Filter,
    FilterSelector,
    IntegerIndexType,
    MatchAny,
    MatchValue,
    OrderBy,
    PointStruct,
    VectorParams,
)
from sqlalchemy import Integer, cast, delete, distinct, func, insert, or_, select, update
from sqlalchemy.exc import IntegrityError, NoResultFound

from app.clients.database import SQLDatabaseClient
from app.clients.model import BaseModelClient as ModelClient
from app.helpers.data.chunkers import LangchainRecursiveCharacterTextSplitter, NoChunker
from app.helpers.data.parsers import HTMLParser, JSONParser, MarkdownParser, PDFParser
from app.schemas.chunks import Chunk
from app.schemas.collections import Collection, CollectionVisibility
from app.schemas.core.data import ParserOutput
from app.schemas.documents import Document
from app.schemas.files import ChunkerName
from app.schemas.search import Search, SearchMethod
from app.sql.models import Collection as CollectionTable
from app.sql.models import Document as DocumentTable
from app.sql.models import User as UserTable
from app.utils.exceptions import (
    ChunkingFailedException,
    CollectionAlreadyExistsException,
    CollectionNotFoundException,
    DocumentNotFoundException,
    NotImplementedException,
    ParsingDocumentFailedException,
    UnsupportedFileTypeException,
    VectorizationFailedException,
    WebSearchNotAvailableException,
)
from app.utils.logging import logger
from app.utils.variables import ENDPOINT__CHAT_COMPLETIONS, ENDPOINT__EMBEDDINGS

from ._modelrouter import ModelRouter
from ._websearchmanager import WebSearchManager


class DocumentManager:
    BATCH_SIZE = 48  # @TODO: retrieve batch size from model registry
    FILE_EXTENSION_PDF = "pdf"
    FILE_EXTENSION_JSON = "json"
    FILE_EXTENSION_HTML = "html"
    FILE_EXTENSION_MD = "md"
    SUPPORTED_FILE_EXTENSIONS = [FILE_EXTENSION_PDF, FILE_EXTENSION_JSON, FILE_EXTENSION_HTML, FILE_EXTENSION_MD]

    def __init__(
        self,
        sql: SQLDatabaseClient,
        qdrant: AsyncQdrantClient,
        qdrant_model: ModelRouter,
        web_search: Optional[WebSearchManager] = None,
        web_search_model: Optional[ModelRouter] = None,
    ) -> None:
        self.sql = sql
        self.qdrant = qdrant
        self.qdrant_model = qdrant_model
        self.web_search = web_search
        self.web_search_model = web_search_model

    async def create_collection(self, user_id: int, name: str, visibility: CollectionVisibility, description: Optional[str] = None) -> int:
        try:
            async with self.sql.session() as session:
                result = await session.execute(
                    statement=insert(table=CollectionTable)
                    .values(name=name, user_id=user_id, visibility=visibility, description=description)
                    .returning(CollectionTable.id)
                )
                collection_id = result.scalar_one()
                await session.commit()
        except IntegrityError as e:
            raise CollectionAlreadyExistsException()

        await self.qdrant.create_collection(
            collection_name=str(collection_id),
            vectors_config=VectorParams(size=self.qdrant_model._vector_size, distance=Distance.COSINE),
        )
        await self.qdrant.create_payload_index(collection_name=str(collection_id), field_name="id", field_schema=IntegerIndexType.INTEGER)

        return collection_id

    async def delete_collection(self, user_id: int, collection_id: int) -> None:
        async with self.sql.session() as session:
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

            # delete the collection from qdrant
        await self.qdrant.delete_collection(collection_name=str(collection_id))

    async def update_collection(self, user_id: int, collection_id: int, name: Optional[str] = None, visibility: Optional[CollectionVisibility] = None, description: Optional[str] = None) -> None:  # fmt: off
        async with self.sql.session() as session:
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
                .values(name=name, visibility=visibility, description=description, updated_at=func.now())
                .where(CollectionTable.id == collection.id)
            )
            await session.commit()

    async def get_collections(self, user_id: int, collection_id: Optional[int] = None, include_public: bool = True, offset: int = 0, limit: int = 10) -> List[Collection]:  # fmt: off
        async with self.sql.session() as session:
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

    async def create_document(self, user_id: int, collection_id: int, file: UploadFile, chunker_name: ChunkerName, chunker_args: dict) -> int:  # fmt: off
        # check if collection exists
        async with self.sql.session() as session:
            result = await session.execute(
                statement=select(CollectionTable).where(CollectionTable.id == collection_id).where(CollectionTable.user_id == user_id)
            )
            try:
                collection = result.scalar_one()
            except NoResultFound:
                raise CollectionNotFoundException()

        file_name = file.filename.strip()
        file_extension = file_name.rsplit(".", maxsplit=1)[-1]

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

        async with self.sql.session() as session:
            result = await session.execute(
                statement=insert(table=DocumentTable).values(name=file_name, collection_id=collection_id).returning(DocumentTable.id)
            )
            document_id = result.scalar_one()
            await session.commit()

        client = self.qdrant_model.get_client(endpoint=ENDPOINT__EMBEDDINGS)
        for i, chunk in enumerate(chunks):
            chunk.metadata["document_part"] = f"{i + 1}/{len(chunks)}"
            chunk.metadata["collection_id"] = collection.id
            chunk.metadata["collection_name"] = collection.name
            chunk.metadata["document_id"] = document_id
            chunk.metadata["document_name"] = file_name
            chunk.metadata["document_created_at"] = round(time.time())
        try:
            await self._upsert(chunks=chunks, collection_id=collection_id, model_client=client)
        except Exception as e:
            logger.error(msg=f"Error during document creation: {e}")
            logger.debug(msg=traceback.format_exc())
            await self.delete_document(user_id=user_id, document_id=document_id)
            raise VectorizationFailedException(detail=f"Vectorization failed: {e}")

        return document_id

    async def get_documents(self, user_id: int, collection_id: Optional[int] = None, document_id: Optional[int] = None, offset: int = 0, limit: int = 10) -> List[Document]:  # fmt: off
        async with self.sql.session() as session:
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
                .where(CollectionTable.user_id == user_id)
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
            try:
                chunks_count = await self.qdrant.count(
                    collection_name=str(document.collection_id),
                    count_filter=Filter(must=[FieldCondition(key="metadata.document_id", match=MatchAny(any=[document.id]))]),
                )
                document.chunks = chunks_count.count
            except ResponseHandlingException as e:
                document.chunks = None

        return documents

    async def delete_document(self, user_id: int, document_id: int) -> None:
        # check if document exists
        async with self.sql.session() as session:
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

            # delete the document from qdrant
            filter = Filter(must=[FieldCondition(key="metadata.document_id", match=MatchAny(any=[document_id]))])
            await self.qdrant.delete(collection_name=str(document.collection_id), points_selector=FilterSelector(filter=filter))

    async def get_chunks(self, user_id: int, document_id: int, chunk_id: Optional[int] = None, offset: int = 0, limit: int = 10) -> List[Chunk]:
        # check if document exists
        async with self.sql.session() as session:
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

        # check if document exists
        must = [FieldCondition(key="metadata.document_id", match=MatchAny(any=[document_id]))]
        if chunk_id:
            must.append(FieldCondition(key="metadata.id", match=MatchValue(value=chunk_id)))

        filter = Filter(must=must)
        data = await self.qdrant.scroll(
            collection_name=document.collection_id,
            scroll_filter=filter,
            order_by=OrderBy(key="id", start_from=offset),
            limit=limit,
        )
        data = data[0]
        chunks = [Chunk(id=chunk.payload["id"], content=chunk.payload["content"], metadata=chunk.payload["metadata"]) for chunk in data]

        return chunks

    async def search(
        self,
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

        web_results = []
        qdrant_client = self.qdrant_model.get_client(endpoint=ENDPOINT__EMBEDDINGS)
        if web_search:
            client = self.web_search_model.get_client(endpoint=ENDPOINT__CHAT_COMPLETIONS)
            web_query = await self.web_search.get_web_query(prompt=prompt, model_client=client)
            web_results = await self.web_search.get_results(query=web_query, n=3)
            if web_results:
                web_collection_id = await self.create_collection(
                    name=f"tmp_web_collection_{uuid4()}",
                    user_id=user_id,
                    visibility=CollectionVisibility.PRIVATE,
                )
                for file in web_results:
                    await self.create_document(
                        user_id=user_id,
                        collection_id=web_collection_id,
                        file=file,
                        chunker_name=ChunkerName.LANGCHAIN_RECURSIVE_CHARACTER_TEXT_SPLITTER,
                        chunker_args={"chunk_overlap": 0, "chunk_min_size": 20, "chunk_size": 1000},
                    )
                collection_ids.append(web_collection_id)

        searches = await self._query(
            model_client=qdrant_client,
            prompt=prompt,
            collection_ids=collection_ids,
            method=method,
            k=k,
            rff_k=rff_k,
            score_threshold=score_threshold,
        )

        if web_results:
            await self.delete_collection(user_id=user_id, collection_id=web_collection_id)

        if score_threshold:
            searches = [search for search in searches if search.score >= score_threshold]

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
                collection_name=str(collection_id),
                points=[
                    PointStruct(id=str(uuid4()), vector=embedding, payload={"id": chunk.id, "content": chunk.content, "metadata": chunk.metadata})
                    for chunk, embedding in zip(batch, embeddings)
                ],
            )

    async def _query(
        self,
        model_client: ModelClient,
        prompt: str,
        collection_ids: List[int],
        method: SearchMethod,
        k: Optional[int] = 4,
        rff_k: Optional[int] = 20,
        score_threshold: Optional[float] = None,
    ) -> List[Search]:
        if method != SearchMethod.SEMANTIC:
            raise NotImplementedException("Lexical and hybrid search are not available for Qdrant database.")

        response = await self._create_embeddings(input=[prompt], model_client=model_client)

        chunks = []
        async with self.sql.session() as session:
            for collection_id in collection_ids:
                result = await session.execute(statement=select(CollectionTable).where(CollectionTable.id == collection_id))
                try:
                    collection = result.scalar_one()
                except NoResultFound:
                    raise CollectionNotFoundException()

                results = await self.qdrant.search(
                    collection_name=str(collection_id),
                    query_vector=response[0],
                    limit=k,
                    score_threshold=score_threshold,
                    with_payload=True,
                )
                chunks.extend(results)

        # sort by similarity score and get top k
        chunks = sorted(chunks, key=lambda x: x.score, reverse=True)[:k]
        searches = [
            Search(
                method=method,
                score=chunk.score,
                chunk=Chunk(id=chunk.payload["id"], content=chunk.payload["content"], metadata=chunk.payload["metadata"]),
            )
            for chunk in chunks
        ]

        return searches
