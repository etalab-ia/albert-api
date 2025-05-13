from fastapi import APIRouter, File, Form, Security, UploadFile
from typing import Optional
from app.helpers import Authorization

from app.utils.variables import ENDPOINT__PARSER
from app.schemas.parser import MarkerPDFResponse, Languages
from app.utils.lifespan import context

router = APIRouter()


@router.post(path=ENDPOINT__PARSER, dependencies=[Security(dependency=Authorization())], response_model=MarkerPDFResponse)
async def marker_pdf_parse(
    file: UploadFile = File(...),
    output_format: str = Form(default="markdown"),
    force_ocr: bool = Form(default=False),
    languages: Optional[Languages] = Form(default="fr"),
    page_range: Optional[str] = Form(default=None),
    paginate_output: bool = Form(default=False),
    use_llm: bool = Form(default=False),
):
    """
    Endpoint to parse a PDF document using the Marker PDF API.
    """
    return await context.parser.parse_pdf(
        file=file,
        output_format=output_format,
        force_ocr=force_ocr,
        languages=languages.value,
        page_range=page_range,
        paginate_output=paginate_output,
        use_llm=use_llm,
    )
