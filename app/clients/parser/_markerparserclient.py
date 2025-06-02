from io import BytesIO
import json
from typing import List, Optional

from fastapi import HTTPException
import httpx
import pymupdf

from app.schemas.core.documents import FileType, ParserParams
from app.schemas.parse import ParsedDocument, ParsedDocumentMetadata, ParsedDocumentPage

from ._baseparserclient import BaseParserClient


class MarkerParserClient(BaseParserClient):
    """
    Class to interact with the Marker PDF API for document analysis.
    """

    SUPPORTED_FORMATS = [FileType.PDF]

    def __init__(self, api_url: str, api_key: Optional[str] = None, timeout=120, *args, **kwargs) -> None:
        self.api_url = api_url
        self.api_key = api_key
        self.timeout = timeout
        self.headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}

        # Keep health check synchronous in __init__
        response = httpx.get(f"{self.api_url}/health", headers=self.headers, timeout=self.timeout)
        assert response.status_code == 200, "Marker API is not reachable."

    def convert_page_range(self, page_range: str, page_count: int) -> List[int]:
        if page_range == "":
            return [i for i in range(page_count)]

        page_ranges = page_range.split(",")
        pages = []
        for page_range in page_ranges:
            page_range = page_range.split("-")
            if len(page_range) == 1:
                pages.append(int(page_range[0]))
            else:
                for i in range(int(page_range[0]), int(page_range[1]) + 1):
                    pages.append(i)

        pages = list(set(pages))

        return pages

    async def parse(self, **params: ParserParams) -> ParsedDocument:
        params = ParserParams(**params)

        if params.file.content_type not in self.SUPPORTED_FORMATS:
            raise HTTPException(status_code=400, detail="File must be a PDF.")

        file_content = await params.file.read()

        try:
            # Correct way to open PDF from bytes with PyMuPDF
            pdf = pymupdf.open(stream=file_content, filetype="pdf")
            page_count = pdf.page_count
        except Exception as e:
            # Handle corrupted or invalid PDF files
            raise HTTPException(status_code=400, detail=f"Invalid PDF file: {str(e)}")

        data = []
        payload = {
            "output_format": params.output_format.value,
            "force_ocr": params.force_ocr,
            "languages": params.languages.value,
            "paginate_output": params.paginate_output,
            "use_llm": params.use_llm,
        }
        pages = self.convert_page_range(page_range=params.page_range, page_count=page_count)
        async with httpx.AsyncClient() as client:
            for i in pages:
                # Create a fresh BytesIO object for each request to avoid stream consumption issues
                files = {"file": (params.file.filename, BytesIO(file_content), "application/pdf")}
                payload["page_range"] = str(i)

                response = await client.post(
                    url=f"{self.api_url}/marker/upload",
                    files=files,
                    data=payload,
                    headers=self.headers,
                    timeout=self.timeout,
                )
                if response.status_code != 200:
                    raise HTTPException(status_code=response.status_code, detail=json.loads(response.text).get("detail", "Parsing failed."))

                result = response.json()
                if not result.get("success", False):
                    raise HTTPException(status_code=500, detail=result.get("error", "Parsing failed."))

                metadata = ParsedDocumentMetadata(**result["metadata"], page=i)
                data.append(ParsedDocumentPage(content=result["output"], images=result["images"], metadata=metadata))

        # Close the PDF document to free memory
        pdf.close()
        document = ParsedDocument(data=data)

        return document
