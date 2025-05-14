from fastapi import APIRouter, File, Form, HTTPException, Security, UploadFile
from io import BytesIO
import requests
from typing import Optional
from app.helpers import Authorization
from app.schemas.core.data import FileType
from app.utils.exceptions import FileSizeLimitExceededException
from app.utils.variables import ENDPOINT__PARSER
from app.schemas.parser import MarkerPDFResponse


MARKER_API_URL = "http://51.159.177.46:8002"
router = APIRouter()


@router.post(path=ENDPOINT__PARSER, dependencies=[Security(dependency=Authorization())], response_model=MarkerPDFResponse)
async def marker_pdf_parse(
    file: UploadFile = File(...),
    output_format: str = Form(default="markdown"),
    force_ocr: bool = Form(default=False),
    languages: Optional[str] = Form(default=None),
    page_range: Optional[str] = Form(default=None),
    paginate_output: bool = Form(default=False),
    use_llm: bool = Form(default=False),
):
    """
    Parse un document PDF en utilisant l'API Marker PDF.

    - Extraits le texte avec une mise en forme préservée
    - Extrait les images
    - Supporte différents formats de sortie (markdown, json, html)
    - Permet l'OCR si nécessaire
    """
    # Vérifier si le fichier est un PDF
    if file.content_type != FileType.PDF:
        raise HTTPException(status_code=400, detail="Le fichier doit être un PDF")

    # Vérifier la taille du fichier
    if file.size > FileSizeLimitExceededException.MAX_CONTENT_SIZE:
        raise FileSizeLimitExceededException()

    # Préparation du fichier à envoyer
    file_content = await file.read()

    # Préparation des données pour la requête à l'API Marker PDF
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
        # Envoi de la requête à l'API Marker PDF
        response = requests.post(f"{MARKER_API_URL}/marker/upload", files=files, data=data)

        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=f"Erreur lors de l'appel à l'API Marker PDF: {response.text}")

        result = response.json()
        if not result.get("success", False):
            raise HTTPException(status_code=500, detail=f"Erreur lors du parsing: {result.get('error', 'Erreur inconnue')}")

        return MarkerPDFResponse(**result)

    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=503, detail=f"Erreur de connexion à l'API Marker PDF: {str(e)}")
