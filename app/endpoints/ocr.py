import base64

from fastapi import APIRouter, Request, Security, UploadFile
from fastapi.responses import JSONResponse
import pymupdf

from app.helpers._accesscontroller import AccessController
from app.schemas.core.documents import FileType
from app.schemas.ocr import DPIForm, ModelForm, PromptForm
from app.schemas.parse import FileForm, ParsedDocument, ParsedDocumentMetadata, ParsedDocumentPage
from app.schemas.usage import Usage
from app.utils.context import global_context
from app.utils.exceptions import FileSizeLimitExceededException
from app.utils.variables import ENDPOINT__OCR

router = APIRouter()


@router.post(path=ENDPOINT__OCR, dependencies=[Security(dependency=AccessController())], status_code=200, response_model=ParsedDocument)
async def ocr(request: Request, file: UploadFile = FileForm, model: str = ModelForm, dpi: int = DPIForm, prompt: str = PromptForm) -> JSONResponse:
    """
    Extracts text from PDF files using OCR.
    """
    # check if file is a pdf (raises UnsupportedFileTypeException if not a PDF)
    global_context.document_manager.parser_manager._detect_file_type(file=file, type=FileType.PDF)

    # check file size
    if file.size > FileSizeLimitExceededException.MAX_CONTENT_SIZE:
        raise FileSizeLimitExceededException()

    # get model client
    model = global_context.model_registry(model=model)
    client = model.get_client(endpoint=ENDPOINT__OCR)

    file_content = await file.read()  # open document
    pdf = pymupdf.open(stream=file_content, filetype="pdf")
    document = ParsedDocument(data=[], usage=Usage())

    for i, page in enumerate(pdf):  # iterate through the pages
        image = page.get_pixmap(dpi=dpi)  # render page to an image
        img_byte_arr = image.tobytes("png")  # convert pixmap to PNG bytes

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
        document.data.append(
            ParsedDocumentPage(
                content=text,
                images={},
                metadata=ParsedDocumentMetadata(page=i, document_name=file.filename, **pdf.metadata),
            )
        )
        document.usage = Usage(**response.get("usage", {}))

    pdf.close()

    return JSONResponse(content=document.model_dump(), status_code=200)
