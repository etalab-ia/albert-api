from fastapi import APIRouter, Body, Response, Security, UploadFile, File

from app.helpers._fileuploader import FileUploader
from app.schemas.files import ChunkerArgs, FilesRequest
from app.schemas.security import User
from app.utils.lifespan import clients
from app.utils.security import check_api_key

router = APIRouter()


@router.post("/files")
async def upload_file(file: UploadFile = File(...), request: FilesRequest = Body(...), user: User = Security(check_api_key)) -> Response:
    """
    Upload a file to be processed, chunked, and stored into a vector database. Supported file types : pdf, html, json.

    Supported files types:
    - pdf: Portable Document Format file.
    - json: JavaScript Object Notation file.
        For JSON, file structure like a list of documents: [{"text": "hello world", "title": "my document", "metadata": {"autor": "me"}}, ...]} or [{"text": "hello world", "title": "my document"}, ...]}
        Each document must have a "text" and "title" keys and "metadata" key (optional) with dict type value.
    - html: Hypertext Markup Language file.

    Max file size is 10MB.
    """

    if request.chunker:
        chunker_args = request.chunker.args.model_dump() if request.chunker.args else ChunkerArgs().model_dump()
        chunker_name = request.chunker.name
    else:
        chunker_args = ChunkerArgs().model_dump()
        chunker_name = None

    chunker_args["length_function"] = len if chunker_args["length_function"] == "len" else chunker_args["length_function"]

    uploader = FileUploader(vectors=clients.vectors, user=user, collection_id=request.collection)
    output = uploader.parse(file=file)
    chunks = uploader.split(input=output, chunker_name=chunker_name, chunker_args=chunker_args)
    uploader.upsert(chunks=chunks)

    return Response(status_code=201)
