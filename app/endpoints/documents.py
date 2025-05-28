from typing import Optional, Union
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Path, Query, Request, Response, Security, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.helpers import AccessController
from app.schemas.documents import Document, Documents, Languages, ParsedDocument, ParsedDocumentOutputFormat
from app.sql.session import get_db as get_session
from app.utils.context import global_context, request_context
from app.utils.exceptions import CollectionNotFoundException, DocumentNotFoundException, FileSizeLimitExceededException
from app.utils.variables import ENDPOINT__DOCUMENTS, ENDPOINT__DOCUMENTS_PARSE

router = APIRouter()


@router.get(
    path=ENDPOINT__DOCUMENTS + "/{document:path}",
    dependencies=[Security(dependency=AccessController())],
    status_code=200,
    response_model=Document,
)
async def get_document(
    request: Request,
    document: int = Path(description="The document ID"),
    session: AsyncSession = Depends(get_session),
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
    session: AsyncSession = Depends(get_session),
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
    session: AsyncSession = Depends(get_session),
) -> Response:
    """
    Delete a document and relative collections.
    """
    if not global_context.documents:  # no vector store available
        raise DocumentNotFoundException()

    await global_context.documents.delete_document(session=session, document_id=document, user_id=request_context.get().user_id)

    return Response(status_code=204)


page_range = Form(default=None, description="Page range to convert, specify comma separated page numbers or ranges. Example: '0,5-10,20'", example="0,5-10,20")  # fmt: off
languages = Form(default=Languages.FR, description="Comma separated list of languages to use for OCR. Must be either the names or codes from from https://github.com/VikParuchuri/surya/blob/master/surya/recognition/languages.py.", example=None)  # fmt: off
force_ocr = Form(default=False, description="Force OCR on all pages of the PDF.  Defaults to False.  This can lead to worse results if you have good text in your PDFs (which is true in most cases).")  # fmt: off
paginate_output = Form(default=False, description="Whether to paginate the output.  Defaults to False.  If set to True, each page of the output will be separated by a horizontal rule that contains the page number (2 newlines, {PAGE_NUMBER}, 48 - characters, 2 newlines).")  # fmt: off
output_format = Form(default=ParsedDocumentOutputFormat.MARKDOWN, description="The format to output the text in.  Can be 'markdown', 'json', or 'html'.  Defaults to 'markdown'.")  # fmt: off
use_llm = Form(default=False, description="Use LLM to improve conversion accuracy. Requires API key if using external services.")  # fmt: off
file = File(..., description="The PDF file to convert.")  # fmt: off


@router.post(path=ENDPOINT__DOCUMENTS_PARSE, dependencies=[Security(dependency=AccessController())], status_code=200, response_model=ParsedDocument)
async def parse_document(
    file: UploadFile = File(...),
    output_format: ParsedDocumentOutputFormat = output_format,
    force_ocr: bool = force_ocr,
    languages: Optional[Languages] = languages,
    page_range: Optional[str] = page_range,
    paginate_output: Optional[bool] = paginate_output,
):
    """
    Parse a document.
    """

    if file.size > FileSizeLimitExceededException.MAX_CONTENT_SIZE:
        raise FileSizeLimitExceededException()

    response = await global_context.parser.parse(
        file=file,
        output_format=output_format,
        force_ocr=force_ocr,
        languages=languages.value,
        page_range=page_range,
        paginate_output=paginate_output,
    )
    return JSONResponse(content=ParsedDocument(response).model_dump(), status_code=200)
