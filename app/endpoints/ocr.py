import base64
from enum import Enum
from io import BytesIO

from fastapi import APIRouter, File, HTTPException, Security, UploadFile, Request
from pdf2image import convert_from_bytes

from app.schemas.ocr import OCRRequest, OCRResponse
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
async def ocr(request: Request, file: UploadFile = File(...), body: OCRRequest = None, user: User = Security(check_api_key)):
    """
    Extracts text from PDF files using OCR.
    """
    # Set default values if request is None
    if body is None:
        body = OCRRequest(model="mistralai/Mistral-Small-3.1-24B-Instruct-2503", dpi=150)

    # check if file is a pdf
    if file.content_type != FileTypes.PDF.value:
        raise HTTPException(status_code=400, detail="File must be a PDF")

    # check file size
    if file.size > FileSizeLimitExceededException.MAX_CONTENT_SIZE:
        raise FileSizeLimitExceededException()

    # convert pages into images
    images = convert_from_bytes(pdf_file=file.file.read(), dpi=body.dpi)
    data = []  # Initialize data list to store results

    # call model
    model = models.registry[body.model]
    client = model.get_client(endpoint=ENDPOINT__CHAT_COMPLETIONS)

    for i, image in enumerate(images):
        # Convert PpmImageFile to bytes
        img_byte_arr = BytesIO()
        image.save(img_byte_arr, format="PNG")
        img_byte_arr = img_byte_arr.getvalue()

        content = [
            {"type": "text", "text": body.prompt},
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{base64.b64encode(img_byte_arr).decode("utf-8")}",
                },
            },
        ]

        # forward request
        payload = {
            "model": body.model,
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
