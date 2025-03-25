import base64
from enum import Enum
from io import BytesIO

from fastapi import APIRouter, File, HTTPException, UploadFile
from pdf2image import convert_from_bytes

from app.utils.exceptions import FileSizeLimitExceededException
from app.utils.lifespan import models
from app.utils.variables import ENDPOINT__CHAT_COMPLETIONS

router = APIRouter()


class FileTypes(Enum):
    PDF = "application/pdf"


@router.post(path="/ocr")
async def ocr(file: UploadFile = File(...)):
    # INSTALL poppler (brew)
    # pip install pdf2image
    prompt = (
        "Tu es un système d'OCR très précis. Extrait tout le texte visible de cette image. Ne décris pas l'image, n'ajoute pas de commentaires. Réponds uniquement avec le texte brut extrait, en préservant les paragraphes, la mise en forme et la structure du document. Si aucun texte n'est visible, réponds avec 'Aucun texte détecté'. Je veux une sortie au format markdown. Tu dois respecter le format de sortie pour bien conserver les tableaux."
        ""
    )
    request = {
        "model": "mistralai/Mistral-Small-3.1-24B-Instruct-2503",
        "dpi": 150,
    }

    # check if file is a pdf
    if file.content_type != FileTypes.PDF.value:
        raise HTTPException(status_code=400, detail="File must be a PDF")  # TODO: convert into Exception

    # check file size
    file_size = len(file.file.read())
    if file_size > FileSizeLimitExceededException.MAX_CONTENT_SIZE:
        raise FileSizeLimitExceededException()
    file.file.seek(0)  # reset file pointer to the beginning of the file

    # convert pages into images
    images = convert_from_bytes(pdf_file=file.file.read(), dpi=request["dpi"])
    data = []  # Initialize data list to store results

    # call model
    model = models.registry[request["model"]]
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
        import requests

        base_url = client.base_url
        headers = {"Authorization": f"Bearer {client.api_key}", "Content-Type": "application/json"}

        payload = {
            "model": request["model"],
            "messages": [{"role": "user", "content": content}],
            "n": 1,
        }

        response = requests.post(
            url=f"{base_url}chat/completions",
            headers=headers,
            json=payload,  # Use json parameter instead of data to automatically handle JSON serialization
        )

        data_response = response.json()
        extracted_text = data_response.get("choices", [{}])[0].get("message", {}).get("content", "Erreur: Aucun contenu reçu")

        # format response
        data.append({"page": i + 1, "text": extracted_text})

    return {"object": "list", "data": data}
