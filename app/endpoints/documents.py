import json
from typing import List, Literal, Optional, Union
from uuid import UUID

from fastapi import APIRouter, Path, Query, Request, Response, Security, UploadFile
from fastapi.responses import JSONResponse
from langchain_text_splitters import Language
from sqlalchemy.ext.asyncio import AsyncSession

from app.helpers._accesscontroller import AccessController
from app.schemas.documents import (
    Chunker,
    ChunkerForm,
    ChunkMinSizeForm,
    ChunkOverlapForm,
    ChunkSizeForm,
    CollectionForm,
    Document,
    DocumentResponse,
    Documents,
    IsSeparatorRegexForm,
    LanguageSeparatorsForm,
    LengthFunctionForm,
    MetadataForm,
    SeparatorsForm,
)
from app.schemas.parse import (
    FileForm,
    ForceOCRForm,
    OutputFormatForm,
    PageRangeForm,
    PaginateOutputForm,
    ParsedDocumentOutputFormat,
)
from app.utils.context import global_context, request_context
from app.utils.depends import get_db_session
from app.utils.exceptions import CollectionNotFoundException, DocumentNotFoundException, FileSizeLimitExceededException, InvalidJSONFormatException
from app.utils.variables import ENDPOINT__DOCUMENTS

router = APIRouter()


@router.post(path=ENDPOINT__DOCUMENTS, status_code=201, dependencies=[Security(dependency=AccessController())], response_model=DocumentResponse)
async def create_document(
    request: Request,
    session: AsyncSession = get_db_session(),
    file: UploadFile = FileForm,
    collection: int = CollectionForm,
    # parse params
    paginate_output: Optional[bool] = PaginateOutputForm,
    page_range: str = PageRangeForm,
    force_ocr: bool = ForceOCRForm,
    output_format: ParsedDocumentOutputFormat = OutputFormatForm,
    # chunker params
    chunker: Chunker = ChunkerForm,
    chunk_size: int = ChunkSizeForm,
    chunk_min_size: int = ChunkMinSizeForm,
    chunk_overlap: int = ChunkOverlapForm,
    length_function: Literal["len"] = LengthFunctionForm,
    is_separator_regex: bool = IsSeparatorRegexForm,
    separators: List[str] = SeparatorsForm,
    language_separators: Union[Language, Literal[""]] = LanguageSeparatorsForm,
    metadata: str = MetadataForm,
) -> JSONResponse:
    """
    Parse a file and create a document.
    """
    language_separators = None if language_separators == "" else language_separators

    try:
        metadata = json.loads(metadata)
    except Exception as e:
        raise InvalidJSONFormatException(f"Invalid JSON string for metadata: {e}")

    if not global_context.documents:  # no vector store available
        raise CollectionNotFoundException()

    file_size = len(file.file.read())
    if file_size > FileSizeLimitExceededException.MAX_CONTENT_SIZE:
        raise FileSizeLimitExceededException()
    file.file.seek(0)  # reset file pointer to the beginning of the file

    length_function = len if length_function == "len" else length_function

    document = await global_context.documents.parse_file(
        file=file,
        paginate_output=paginate_output,
        page_range=page_range,
        force_ocr=force_ocr,
        output_format=output_format,
    )

    document_id = await global_context.documents.create_document(
        user_id=request_context.get().user_id,
        session=session,
        collection_id=collection,
        document=document,
        chunker=chunker,
        chunk_size=chunk_size,
        chunk_min_size=chunk_min_size,
        chunk_overlap=chunk_overlap,
        length_function=length_function,
        is_separator_regex=is_separator_regex,
        separators=separators,
        language_separators=language_separators,
        metadata=metadata,
    )

    return JSONResponse(content=DocumentResponse(id=document_id).model_dump(), status_code=201)


@router.get(
    path=ENDPOINT__DOCUMENTS + "/{document:path}",
    dependencies=[Security(dependency=AccessController())],
    status_code=200,
    response_model=Document,
)
async def get_document(
    request: Request,
    document: int = Path(description="The document ID"),
    session: AsyncSession = get_db_session(),
) -> JSONResponse:
    """
    Get a document by ID.
    """
    if not global_context.documents:  # no vector store available
        raise DocumentNotFoundException()

    documents = await global_context.documents.get_documents(session=session, document_id=document, user_id=request_context.get().user_id)

    return JSONResponse(content=documents[0].model_dump(), status_code=200)


@router.get(path=ENDPOINT__DOCUMENTS, dependencies=[Security(dependency=AccessController())], status_code=200)
async def get_documents(
    request: Request,
    collection: Optional[int] = Query(default=None, description="Filter documents by collection ID"),
    limit: Optional[int] = Query(default=10, ge=1, le=100, description="The number of documents to return"),
    offset: Union[int, UUID] = Query(default=0, description="The offset of the first document to return"),
    session: AsyncSession = get_db_session(),
) -> JSONResponse:
    """
    Get all documents ID from a collection.
    """

    if not global_context.documents:  # no vector store available
        if collection:
            raise CollectionNotFoundException()

        return Documents(data=[])

    data = await global_context.documents.get_documents(
        session=session,
        collection_id=collection,
        limit=limit,
        offset=offset,
        user_id=request_context.get().user_id,
    )

    return JSONResponse(content=Documents(data=data).model_dump(), status_code=200)


@router.delete(path=ENDPOINT__DOCUMENTS + "/{document:path}", dependencies=[Security(dependency=AccessController())], status_code=204)
async def delete_document(
    request: Request,
    document: int = Path(description="The document ID"),
    session: AsyncSession = get_db_session(),
) -> Response:
    """
    Delete a document.
    """
    if not global_context.documents:  # no vector store available
        raise DocumentNotFoundException()

    await global_context.documents.delete_document(session=session, document_id=document, user_id=request_context.get().user_id)

    return Response(status_code=204)
