from fastapi import APIRouter, File, Request, Security, UploadFile
from fastapi.responses import JSONResponse

from app.helpers._accesscontroller import AccessController
from app.schemas.parse import (
    ForceOCRForm,
    OutputFormatForm,
    PageRangeForm,
    PaginateOutputForm,
    ParsedDocument,
    ParsedDocumentOutputFormat,
)
from app.utils.context import global_context
from app.utils.exceptions import FileSizeLimitExceededException
from app.utils.variables import ENDPOINT__PARSE

router = APIRouter()


@router.post(path=ENDPOINT__PARSE, dependencies=[Security(dependency=AccessController())], status_code=200, response_model=ParsedDocument)
async def parse(
    request: Request,
    file: UploadFile = File(...),
    output_format: ParsedDocumentOutputFormat = OutputFormatForm,
    force_ocr: bool = ForceOCRForm,
    page_range: str = PageRangeForm,
    paginate_output: bool = PaginateOutputForm,
) -> JSONResponse:
    """
    Parse a document.
    """
    if file.size > FileSizeLimitExceededException.MAX_CONTENT_SIZE:
        raise FileSizeLimitExceededException()

    document = await global_context.document_manager.parse_file(
        file=file,
        output_format=output_format,
        force_ocr=force_ocr,
        page_range=page_range,
        paginate_output=paginate_output,
    )
    return JSONResponse(content=document.model_dump(), status_code=200)
