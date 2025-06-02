from typing import Optional

from fastapi import APIRouter, File, Request, Security, UploadFile
from fastapi.responses import JSONResponse

from app.helpers import AccessController
from app.schemas.parse import (
    ForceOCRForm,
    Languages,
    LanguagesForm,
    OutputFormatForm,
    PageRangeForm,
    PaginateOutputForm,
    ParsedDocument,
    ParsedDocumentOutputFormat,
    UseLLMForm,
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
    languages: Optional[Languages] = LanguagesForm,
    page_range: str = PageRangeForm,
    paginate_output: Optional[bool] = PaginateOutputForm,
    use_llm: Optional[bool] = UseLLMForm,
) -> JSONResponse:
    """
    Parse a document.
    """

    if file.size > FileSizeLimitExceededException.MAX_CONTENT_SIZE:
        raise FileSizeLimitExceededException()

    document = await global_context.parser.parse(
        file=file,
        output_format=output_format,
        force_ocr=force_ocr,
        languages=languages.value,
        page_range=page_range,
        paginate_output=paginate_output,
        use_llm=use_llm,
    )
    return JSONResponse(content=document.model_dump(), status_code=200)
