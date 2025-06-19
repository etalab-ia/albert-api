from io import BytesIO
import json
from typing import Optional

from fastapi import HTTPException
import httpx
import pymupdf

from app.schemas.core.documents import FileType, ParserParams
from app.schemas.parse import ParsedDocument

from ._baseparserclient import BaseParserClient


class AlbertParserClient(BaseParserClient):
    """
    Class to interact with the Albert PDF API for document analysis.
    """

    SUPPORTED_FORMATS = [FileType.PDF]

    def __init__(self, api_url: str, api_key: Optional[str] = None, timeout=120, *args, **kwargs) -> None:
        self.api_url = api_url
        self.api_key = api_key
        self.timeout = timeout
        self.headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}

        # Keep health check synchronous in __init__
        response = httpx.get(f"{self.api_url}/health", headers=self.headers, timeout=self.timeout)
        assert response.status_code == 200, f"Albert API is not reachable: {response.text} {response.status_code}"

    async def parse(self, **params: ParserParams) -> ParsedDocument:
        params = ParserParams(**params)
        file_content = await params.file.read()

        try:
            # Correct way to open PDF from bytes with PyMuPDF
            pdf = pymupdf.open(stream=file_content, filetype="pdf")
        except Exception as e:
            # Handle corrupted or invalid PDF files
            raise HTTPException(status_code=400, detail=f"Invalid PDF file: {str(e)}")

        payload = {
            "output_format": params.output_format.value if params.output_format else None,
            "force_ocr": params.force_ocr,
            "paginate_output": params.paginate_output,
            "use_llm": params.use_llm,
        }

        async with httpx.AsyncClient() as client:
            files = {"file": (params.file.filename, BytesIO(file_content), "application/pdf")}
            response = await client.post(
                url=f"{self.api_url}/v1/parse-beta",
                files=files,
                data=payload,
                headers=self.headers,
                timeout=self.timeout,
            )
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail=json.loads(response.text).get("detail", "Parsing failed."))

            result = response.json()

        # Close the PDF document to free memory
        pdf.close()
        document = ParsedDocument(data=result["data"])

        return document
