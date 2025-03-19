import traceback
from typing import List, Optional
from uuid import UUID, uuid4

from fastapi import UploadFile
from qdrant_client import AsyncQdrantClient
from qdrant_client.http.models import Distance, FieldCondition, Filter, MatchAny, MatchValue, PointStruct, VectorParams
from sqlalchemy import delete, func, insert, or_, select, update
from sqlalchemy.exc import IntegrityError, NoResultFound

from app.clients.database import SQLDatabaseClient
from app.clients.model import BaseModelClient as ModelClient
from ._internetmanager import InternetManager
from app.helpers.data.chunkers import LangchainRecursiveCharacterTextSplitter, NoChunker
from app.helpers.data.parsers import HTMLParser, JSONParser, MarkdownParser, PDFParser
from app.schemas.chunks import Chunk, ChunkMetadata
from app.schemas.collections import Collection, CollectionVisibility
from app.schemas.core.data import ParserOutput
from app.schemas.documents import Document
from app.schemas.files import ChunkerName
from app.schemas.search import Search, SearchMethod
from app.sql.models import Collection as CollectionTable
from app.sql.models import Document as DocumentTable
from app.sql.models import User as UserTable
from app.utils.exceptions import (
    CollectionNotFoundException,
    DocumentNotFoundException,
    InvalidJSONFormatException,
    NotImplementedException,
    ParsingFileFailedException,
    UnsupportedFileTypeException,
)
from app.utils.logging import logger


class DocumentManager:
    BATCH_SIZE = 48  # TODO: retrieve batch size from model registry
    FILE_EXTENSION_PDF = "pdf"
    FILE_EXTENSION_JSON = "json"
    FILE_EXTENSION_HTML = "html"
    FILE_EXTENSION_MD = "md"
    SUPPORTED_FILE_EXTENSIONS = [FILE_EXTENSION_PDF, FILE_EXTENSION_JSON, FILE_EXTENSION_HTML, FILE_EXTENSION_MD]
    COLLECTION_DISPLAY_ID__INTERNET = "internet"

    def __init__(self, sql: SQLDatabaseClient, qdrant: AsyncQdrantClient, internet: InternetManager) -> None:
        self.sql = sql
        self.qdrant = qdrant
        self.internet = internet

    async def create_collection(
        self, vector_size: int, user_id: int, name: str, visibility: CollectionVisibility, description: Optional[str] = None
    ) -> int:
        async with self.sql.session() as session:
            await session.execute(
                statement=insert(table=CollectionTable).values(name=name, user_id=user_id, visibility=visibility, description=description)
            )
            await session.commit()

            # get the collection id
            result = await session.execute(statement=select(CollectionTable.id).where(CollectionTable.name == name))
            collection_id = result.scalar_one()

        await self.qdrant.create_collection(collection_name=collection_id, vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE))

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

    async def update_collection(self, collection_id: int, name: Optional[str] = None, visibility: Optional[CollectionVisibility] = None, description: Optional[str] = None) -> None:  # fmt: off
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
            statement = select(CollectionTable).offset(offset=offset).limit(limit=limit)

            if collection_id:
                statement = statement.where(CollectionTable.id == collection_id)
            if include_public:
                statement = statement.where(or_(CollectionTable.user_id == user_id, CollectionTable.visibility == CollectionVisibility.PUBLIC))
            else:
                statement = statement.where(CollectionTable.user_id == user_id)

            # TODO: add documents count

            result = await session.execute(statement=statement)
            collections = result.all()

            if collection_id and len(collections) == 0:
                raise CollectionNotFoundException()

            collections = [Collection(**row._mapping) for row in result.all()]

        return collections

    async def create_document(self, collection_id: int, user_id: int, file: UploadFile, chunker_name: ChunkerName, chunker_args: dict, model_client: ModelClient) -> int:  # fmt: off
        file_name = file.filename.strip()
        file_extension = file_name.rsplit(".", maxsplit=1)[-1]

        if file_extension not in self.SUPPORTED_FILE_EXTENSIONS:
            raise UnsupportedFileTypeException()

        document = self._parse(file=file, file_extension=file_extension)
        chunks = self._split(document=document, chunker_name=chunker_name, chunker_args=chunker_args)

        async with self.sql.session() as session:
            i = 0
            while True:
                try:
                    await session.execute(statement=insert(table=DocumentTable).values(name=file_name, collection_id=collection_id, user_id=user_id))
                    await session.commit()
                    break
                except IntegrityError:
                    i += 1
                    file_name, file_extension = file_name.rsplit(".", maxsplit=1)
                    file_name = f"{file_name} ({i}).{file_extension}"

            # get the document id
            result = await session.execute(statement=select(DocumentTable.id).where(DocumentTable.name == file_name))
            document_id = result.scalar_one()

        for i, chunk in enumerate(chunks):
            chunk.metadata.id = i + 1
            chunk.metadata.document_part = f"{i + 1}/{len(chunks)}"
            chunk.metadata.collection_id = collection_id
            chunk.metadata.document_id = document_id
            chunk.metadata.document_name = file_name

        try:
            await self._upsert(chunks=chunks, collection_id=collection_id, model_client=model_client)
        except Exception as e:
            logger.error(msg=f"Error during document creation: {e}")
            logger.debug(msg=traceback.format_exc())
            self.delete_document(document_id=document_id)

        return document_id

    async def get_documents(self, collection_id: int, document_id: Optional[int] = None, offset: int = 0, limit: int = 10) -> List[Document]:  # fmt: off
        async with self.sql.session() as session:
            statement = select(DocumentTable).offset(offset=offset).limit(limit=limit).where(DocumentTable.collection_id == collection_id)
            if document_id:
                statement = statement.where(DocumentTable.id == document_id)

            result = await session.execute(statement=statement)
            documents = result.all()

            if document_id and len(documents) == 0:
                raise DocumentNotFoundException()

            # TODO get document count
            documents = [Document(**row._mapping) for row in result.all()]

            return documents

    async def get_chunks(
        self, collection_id: int, document_id: int, chunk_id: Optional[int] = None, offset: Optional[UUID] = None, limit: int = 10
    ) -> List[Chunk]:
        # TODO: add chunk_id filter
        must = [FieldCondition(key="metadata.document_id", match=MatchAny(any=[document_id]))]
        if chunk_id:
            must.append(FieldCondition(key="metadata.id", match=MatchValue(value=chunk_id)))

        filter = Filter(must=must)
        data = await self.qdrant.scroll(collection_name=collection_id, scroll_filter=filter, limit=limit, offset=offset)[0]
        chunks = [Chunk(id=chunk.id, content=chunk.payload["content"], metadata=ChunkMetadata(**chunk.payload["metadata"])) for chunk in data]

        return chunks

    async def search(
        self,
        model_client: ModelClient,
        collection_ids: List[int],
        user_id: int,
        prompt: str,
        method: str,
        k: int,
        rff_k: int,
        user: str,
        score_threshold: float = 0.0,
        search_on_internet: bool = False,
    ) -> List[Search]:
        # internet search
        internet_chunks = []
        if search_on_internet:
            internet_chunks = await self.internet_manager.get_chunks(prompt=prompt)

            if internet_chunks:
                internet_collection_id = await self.create_collection(
                    name=f"tmp_internet_collection_{uuid4()}",
                    model_client=model_client,
                    user_id=user_id,
                )
                await self.search.upsert(chunks=internet_chunks, collection_id=internet_collection_id)
                collection_ids.append(internet_collection_id)

        searches = await self._query(
            model_client=model_client,
            prompt=prompt,
            collection_ids=collection_ids,
            method=method,
            k=k,
            rff_k=rff_k,
            score_threshold=score_threshold,
        )

        if internet_chunks:
            await self.search.delete_collection(collection_id=internet_collection_id)

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

        try:
            output = parser.parse(file=file)
        except Exception as e:  # TODO: simplify exception handling (only one exception)
            logger.error(msg=f"Error during file parsing: {e}")
            logger.debug(msg=traceback.format_exc())
            if isinstance(e, InvalidJSONFormatException):
                raise e
            else:
                raise ParsingFileFailedException()

        return output

    def _split(self, document: ParserOutput, chunker_name: ChunkerName, chunker_args: dict) -> List[Chunk]:
        if chunker_name == ChunkerName.LangchainRecursiveCharacterTextSplitter:
            chunker = LangchainRecursiveCharacterTextSplitter(**chunker_args)
        else:  # ChunkerName.NoChunker
            chunker = NoChunker()

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
                collection_name=collection_id,
                points=[
                    PointStruct(id=chunk.id, vector=embedding, payload={"content": chunk.content, "metadata": chunk.metadata.model_dump()})
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
        if method != SearchMethod.SEARCH_TYPE_SEMANTIC:
            raise NotImplementedException("Lexical and hybrid search are not available for Qdrant database.")

        response = await self._create_embeddings(input=[prompt], model=model_client.model)

        chunks = []
        for collection in collection_ids:
            results = self.qdrant.search(
                collection_name=collection.id,
                query_vector=response[0],
                limit=k,
                score_threshold=score_threshold,
                with_payload=True,
            )
            for result in results:
                result.payload["metadata"]["collection"] = collection.id
            chunks.extend(results)

        # sort by similarity score and get top k
        chunks = sorted(chunks, key=lambda x: x.score, reverse=True)[:k]
        searches = list()
        for chunk in chunks:
            chunk_id = chunk.payload["metadata"].pop("id")
            searches.append(
                Search(
                    method=method,
                    score=chunk.score,
                    chunk=Chunk(id=chunk_id, content=chunk.payload["content"], metadata=chunk.payload["metadata"]),
                )
            )

        return searches
