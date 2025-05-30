from typing import Optional

from fastapi import APIRouter, File, Form, Request, Security, UploadFile
from fastapi.responses import JSONResponse

from app.helpers import AccessController
from app.schemas.parse import Languages, ParsedDocumentOutputFormat, ParsedDocument
from app.utils.context import global_context
from app.utils.exceptions import FileSizeLimitExceededException
from app.utils.variables import ENDPOINT__PARSE

router = APIRouter()

page_range = Form(default=None, description="Page range to convert, specify comma separated page numbers or ranges. Example: '0,5-10,20'", example="0,5-10,20")  # fmt: off
languages = Form(default=Languages.FR, description="Comma separated list of languages to use for OCR. Must be either the names or codes from from https://github.com/VikParuchuri/surya/blob/master/surya/recognition/languages.py.", example=None)  # fmt: off
force_ocr = Form(default=False, description="Force OCR on all pages of the PDF.  Defaults to False.  This can lead to worse results if you have good text in your PDFs (which is true in most cases).")  # fmt: off
paginate_output = Form(default=False, description="Whether to paginate the output.  Defaults to False.  If set to True, each page of the output will be separated by a horizontal rule that contains the page number (2 newlines, {PAGE_NUMBER}, 48 - characters, 2 newlines).")  # fmt: off
output_format = Form(default=ParsedDocumentOutputFormat.MARKDOWN, description="The format to output the text in.  Can be 'markdown', 'json', or 'html'.  Defaults to 'markdown'.")  # fmt: off
use_llm = Form(default=False, description="Use LLM to improve conversion accuracy. Requires API key if using external services.")  # fmt: off
file = File(..., description="The PDF file to convert.")  # fmt: off


@router.post(path=ENDPOINT__PARSE, dependencies=[Security(dependency=AccessController())], status_code=200, response_model=ParsedDocument)
async def parse(
    request: Request,
    file: UploadFile = File(...),
    output_format: ParsedDocumentOutputFormat = output_format,
    force_ocr: bool = force_ocr,
    languages: Optional[Languages] = languages,
    page_range: Optional[str] = page_range,
    paginate_output: Optional[bool] = paginate_output,
    use_llm: Optional[bool] = use_llm,
):
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
