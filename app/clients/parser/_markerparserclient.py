from io import BytesIO
from typing import Optional

from fastapi import HTTPException, UploadFile
import requests

from app.schemas.core.data import FileType
from app.schemas.documents import Languages, ParsedDocument, ParsedDocumentOutputFormat

from ._baseparserclient import BaseParserClient


class MarkerParserClient(BaseParserClient):
    """
    Class to interact with the Marker PDF API for document analysis.
    """

    SUPPORTED_FORMAT = [FileType.PDF]

    def __init__(self, api_url: str, api_key: Optional[str] = None, timeout=120, *args, **kwargs) -> None:
        self.api_url = api_url
        self.api_key = api_key
        self.timeout = timeout
        self.headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}

    async def parse(
        self,
        file: UploadFile,
        output_format: Optional[ParsedDocumentOutputFormat] = None,
        force_ocr: bool = False,
        languages: Optional[Languages] = None,
        page_range: Optional[str] = None,
        paginate_output: bool = False,
        use_llm: bool = False,
    ) -> ParsedDocument:
        if file.content_type != FileType.PDF:
            raise HTTPException(status_code=400, detail="File must be a PDF.")

        file_content = await file.read()

        files = {"file": (file.filename, BytesIO(file_content), "application/pdf")}

        # TODO: leo clean this
        data = {
            "output_format": output_format,
            "force_ocr": str(force_ocr).lower(),
            "languages": languages,
            "paginate_output": str(paginate_output).lower(),
            "use_llm": str(use_llm).lower(),
        }

        if languages:
            data["languages"] = languages
        if page_range:
            data["page_range"] = page_range

        response = requests.post(f"{self.api_url}/marker/upload", files=files, data=data, headers=self.headers, timeout=self.timeout)
        response.raise_for_status()

        result = response.json()
        if not result.get("success", False):
            raise HTTPException(status_code=500, detail=result.get("error", "Parsing failed."))

        return ParsedDocument(**result)
