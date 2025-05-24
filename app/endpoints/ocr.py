import base64
from io import BytesIO

from fastapi import APIRouter, File, Form, HTTPException, Request, Security, UploadFile
from fastapi.responses import JSONResponse
from pdf2image import convert_from_bytes

from app.helpers import AccessController
from app.schemas.core.data import FileType
from app.schemas.ocr import OCR, OCRs
from app.schemas.usage import Usage
from app.utils.context import global_context
from app.utils.exceptions import FileSizeLimitExceededException
from app.utils.variables import ENDPOINT__OCR

router = APIRouter()

DEFAULT_PROMPT = """Tu es un système d'OCR très précis. Extrait tout le texte visible de cette image. 
Ne décris pas l'image, n'ajoute pas de commentaires. Réponds uniquement avec le texte brut extrait, 
en préservant les paragraphes, la mise en forme et la structure du document. 
Si aucun texte n'est visible, réponds avec 'Aucun texte détecté'. 
Je veux une sortie au format markdown. Tu dois respecter le format de sortie pour bien conserver les tableaux."""


@router.post(path=ENDPOINT__OCR, dependencies=[Security(dependency=AccessController())], status_code=200, response_model=OCRs)
async def ocr(
    request: Request,
    file: UploadFile = File(...),
    model: str = Form(default=...),
    dpi: int = Form(default=150),
    prompt: str = Form(default=DEFAULT_PROMPT),
) -> JSONResponse:
    """
    Extracts text from PDF files using OCR.
    """
    # check if file is a pdf
    if file.content_type != FileType.PDF:
        raise HTTPException(status_code=400, detail="File must be a PDF")

    # check file size
    if file.size > FileSizeLimitExceededException.MAX_CONTENT_SIZE:
        raise FileSizeLimitExceededException()

    # get model client
    model = global_context.models(model=model)
    client = model.get_client(endpoint=ENDPOINT__OCR)

    # convert pages into images
    images = convert_from_bytes(pdf_file=file.file.read(), dpi=dpi)
    content = OCRs(data=[], usage=Usage())

    for i, image in enumerate(images):
        # convert image to bytes
        img_byte_arr = BytesIO()
        image.save(img_byte_arr, format="PNG")
        img_byte_arr = img_byte_arr.getvalue()

        # forward request
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64.b64encode(img_byte_arr).decode("utf-8")}"}},
                    ],
                }
            ],
            "n": 1,
            "stream": False,
        }
        response = await client.forward_request(method="POST", json=payload)  # error are automatically raised
        response = response.json()
        text = response.get("choices", [{}])[0].get("message", {}).get("content", "")

        # format response
        content.data.append(OCR(page=i + 1, text=text))
        content.usage = Usage(**response.get("usage", {}))

    return JSONResponse(content=content.model_dump(), status_code=200)
