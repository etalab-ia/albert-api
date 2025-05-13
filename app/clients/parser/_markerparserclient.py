from io import BytesIO
import requests
from typing import Optional
from fastapi import HTTPException, UploadFile
from app.schemas.core.data import FileType
from app.utils.exceptions import FileSizeLimitExceededException

from app.schemas.parser import MarkerPDFResponse


class MarkerParserClient:
    """
    Class to interact with the Marker PDF API for document analysis.
    """

    def __init__(self, api_url: str, api_key: Optional[str] = None, timeout=120, *args, **kwargs) -> None:
        self.api_url = api_url
        self.api_key = api_key
        self.timeout = timeout
        self.headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}

    async def parse_pdf(
        self,
        file: UploadFile,
        output_format: str = "markdown",
        force_ocr: bool = False,
        languages: Optional[str] = "fr",
        page_range: Optional[str] = None,
        paginate_output: bool = False,
        use_llm: bool = False,
    ) -> MarkerPDFResponse:
        """
        Parse a PDF document using the Marker PDF API.
        - Extracts text with preserved formatting
        - Extracts images
        - Supports different output formats (markdown, json, html)
        - Enables OCR if necessary
        """

        if file.content_type != FileType.PDF:
            raise HTTPException(status_code=400, detail="Le fichier doit être un PDF")

        if file.size > FileSizeLimitExceededException.MAX_CONTENT_SIZE:
            raise FileSizeLimitExceededException()

        file_content = await file.read()

        files = {"file": (file.filename, BytesIO(file_content), "application/pdf")}
        data = {
            "output_format": output_format,
            "force_ocr": str(force_ocr).lower(),
            "paginate_output": str(paginate_output).lower(),
            "use_llm": str(use_llm).lower(),
        }

        if languages:
            data["languages"] = languages
        if page_range:
            data["page_range"] = page_range

        try:
            response = requests.post(f"{self.api_url}/parse", files=files, data=data, headers=self.headers, timeout=self.timeout)

            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail=f"Erreur lors de l'appel à l'API Marker PDF: {response.text}")

            result = response.json()
            if not result.get("success", False):
                raise HTTPException(status_code=500, detail=f"Erreur lors du parsing: {result.get('error', 'Erreur inconnue')}")
            return MarkerPDFResponse(**result)

        except requests.exceptions.RequestException as e:
            raise HTTPException(status_code=503, detail=f"Erreur de connexion à l'API Marker PDF: {str(e)}")
