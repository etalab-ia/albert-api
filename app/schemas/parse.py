from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from fastapi import File, Form, UploadFile

from app.schemas import BaseModel
from app.utils.variables import AUDIO_SUPPORTED_LANGUAGES

LANGUAGES = {key.title(): value for key, value in AUDIO_SUPPORTED_LANGUAGES.items()}
LANGUAGES = list(LANGUAGES.keys()) + list(LANGUAGES.values())
LANGUAGES = {str(lang).upper(): str(lang) for lang in sorted(set(LANGUAGES))}

Languages = Enum("Language", LANGUAGES, type=str)


class ParsedDocumentOutputFormat(str, Enum):
    MARKDOWN = "markdown"
    JSON = "json"
    HTML = "html"


class ParsedDocumentMetadata(BaseModel):
    document_name: str


class ParsedDocumentPage(BaseModel):
    content: str
    images: dict[str, str]
    metadata: Dict[str, Any]


class ParsedDocument(BaseModel):
    object: Literal["parsedDocument"] = "parsedDocument"
    format: ParsedDocumentOutputFormat
    contents: List[ParsedDocumentPage]
    metadata: ParsedDocumentMetadata


FileForm: UploadFile = File(..., description="The file to parse.")  # fmt: off
PaginateOutputForm: Optional[bool] = Form(default=False, description="Whether to paginate the output.  Defaults to False.  If set to True, each page of the output will be separated by a horizontal rule that contains the page number (2 newlines, {PAGE_NUMBER}, 48 - characters, 2 newlines).")  # fmt: off
PageRangeForm: Optional[str] = Form(default=None, description="Page range to convert, specify comma separated page numbers or ranges. Example: '0,5-10,20'", example="0,5-10,20")  # fmt: off
LanguagesForm: Optional[Languages] = Form(default=Languages.FR, description="Comma separated list of languages to use for OCR. Must be either the names or codes from from https://github.com/VikParuchuri/surya/blob/master/surya/recognition/languages.py.", example=None)  # fmt: off
ForceOcrForm: bool = Form(default=False, description="Force OCR on all pages of the PDF.  Defaults to False.  This can lead to worse results if you have good text in your PDFs (which is true in most cases).")  # fmt: off
OutputFormatForm: ParsedDocumentOutputFormat = Form(default=ParsedDocumentOutputFormat.MARKDOWN, description="The format to output the text in.  Can be 'markdown', 'json', or 'html'.  Defaults to 'markdown'.")  # fmt: off
UseLlmForm: Optional[bool] = Form(default=False, description="Use LLM to improve conversion accuracy. Requires API key if using external services.")  # fmt: off
