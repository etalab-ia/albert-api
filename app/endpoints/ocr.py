import base64
from enum import Enum
from io import BytesIO

from fastapi import APIRouter, File, HTTPException, Security, UploadFile, Request, Form
from pdf2image import convert_from_bytes

from app.schemas.ocr import OCRResponse
from app.schemas.security import User
from app.utils.exceptions import FileSizeLimitExceededException
from app.utils.lifespan import limiter, models
from app.utils.security import check_api_key, check_rate_limit
from app.utils.variables import ENDPOINT__CHAT_COMPLETIONS, ENDPOINT__OCR

router = APIRouter()


class FileTypes(Enum):
    PDF = "application/pdf"


@router.post(path=ENDPOINT__OCR, response_model=OCRResponse)
@limiter.limit(limit_value="10/minute", key_func=lambda request: check_rate_limit(request=request))
async def ocr(
    request: Request,
    file: UploadFile = File(...),
    model: str = Form(default="mistralai/Mistral-Small-3.1-24B-Instruct-2503"),
    dpi: int = Form(default=150),
    prompt: str = Form(
        default=(
            "Tu es un système d'OCR très précis. Extrait tout le texte visible de cette image. "
            "Ne décris pas l'image, n'ajoute pas de commentaires. Réponds uniquement avec le texte brut extrait, "
            "en préservant les paragraphes, la mise en forme et la structure du document. "
            "Si aucun texte n'est visible, réponds avec 'Aucun texte détecté'. "
            "Je veux une sortie au format markdown. Tu dois respecter le format de sortie pour bien conserver les tableaux."
        )
    ),
    user: User = Security(check_api_key),
):
    """
    Extracts text from PDF files using OCR.
    """
    # check if file is a pdf
    if file.content_type != FileTypes.PDF.value:
        raise HTTPException(status_code=400, detail="File must be a PDF")

    # check file size
    if file.size > FileSizeLimitExceededException.MAX_CONTENT_SIZE:
        raise FileSizeLimitExceededException()

    # convert pages into images
    images = convert_from_bytes(pdf_file=file.file.read(), dpi=dpi)
    data = []  # Initialize data list to store results

    # call model
    model = models.registry[model]
    client = model.get_client(endpoint=ENDPOINT__CHAT_COMPLETIONS)

    for i, image in enumerate(images):
        # Convert PpmImageFile to bytes
        img_byte_arr = BytesIO()
        image.save(img_byte_arr, format="PNG")
        img_byte_arr = img_byte_arr.getvalue()

        content = [
            {"type": "text", "text": prompt},
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{base64.b64encode(img_byte_arr).decode("utf-8")}",
                },
            },
        ]

        # forward request
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": content}],
            "n": 1,
        }

        response = await client.forward_request(
            method="POST",
            json=payload,
        )

        data_response = response.json()
        extracted_text = data_response.get("choices", [{}])[0].get("message", {}).get("content", "Erreur: Aucun contenu reçu")

        # format response
        data.append({"page": i + 1, "text": extracted_text})

    return OCRResponse(data=data)
