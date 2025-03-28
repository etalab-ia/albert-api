import json
from io import BytesIO

from fastapi import APIRouter, Body, File, Security, UploadFile
from fastapi.responses import JSONResponse

from app.helpers import Authorization
from app.schemas.core.auth import UserInfo
from app.schemas.core.data import JsonFile
from app.schemas.files import ChunkerArgs, FilesRequest
from app.utils.exceptions import FileSizeLimitExceededException, InvalidJSONFileFormatException
from app.utils.lifespan import context
from app.utils.settings import settings
from app.utils.variables import ENDPOINT__EMBEDDINGS

router = APIRouter()


@router.post(path="/files")
async def upload_file(file: UploadFile = File(...), request: FilesRequest = Body(...), user: UserInfo = Security(dependency=Authorization())) -> JSONResponse:  # fmt: off
    """
    Upload a file to be processed, chunked, and stored into a vector database. Supported file types : pdf, html, json.

    Supported files types:
    - pdf: Portable Document Format file.
    - json: JavaScript Object Notation file.
        For JSON, file structure like a list of documents: [{"text": "hello world", "title": "my document", "metadata": {"autor": "me"}}, ...]} or [{"text": "hello world", "title": "my document"}, ...]}
        Each document must have a "text" and "title" keys and "metadata" key (optional) with dict type value.
    - html: Hypertext Markup Language file.
    - markdown: Markdown Language file.

    Max file size is 20MB.
    """
    file_size = len(file.file.read())
    if file_size > FileSizeLimitExceededException.MAX_CONTENT_SIZE:
        raise FileSizeLimitExceededException()
    file.file.seek(0)  # reset file pointer to the beginning of the file

    if request.chunker:
        chunker_args = request.chunker.args.model_dump() if request.chunker.args else ChunkerArgs().model_dump()
        chunker_name = request.chunker.name
    else:
        chunker_args = ChunkerArgs().model_dump()
        chunker_name = None

    chunker_args["length_function"] = len if chunker_args["length_function"] == "len" else chunker_args["length_function"]

    if file.content_type == "application/json":
        try:
            file = JsonFile(documents=json.loads(file.file.read())).documents
        except json.JSONDecodeError as e:
            raise InvalidJSONFileFormatException(detail=e)

        files = [
            UploadFile(
                filename=f"{document.title}.json",
                file=BytesIO(json.dumps(document.model_dump()).encode("utf-8")),
            )
            for document in file
        ]
    else:
        files = [file]

    for file in files:
        model = context.models(model=settings.general.documents_model)
        client = model.get_client(endpoint=ENDPOINT__EMBEDDINGS)

        document_id = await context.documents.create_document(
            user_id=user.user_id,
            model_client=client,
            collection_id=request.collection,
            file=file,
            chunker_name=chunker_name,
            chunker_args=chunker_args,
        )

        file.file.close()

    return JSONResponse(status_code=201, content={"id": document_id})
