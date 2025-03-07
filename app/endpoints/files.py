from fastapi import APIRouter, Body, File, Response, Security, UploadFile

from app.helpers import Authorization
from app.helpers._fileuploader import FileUploader
from app.schemas.auth import PermissionType
from app.schemas.core.auth import AuthenticatedUser
from app.schemas.files import ChunkerArgs, FilesRequest
from app.utils.exceptions import FileSizeLimitExceededException
from app.utils.lifespan import databases

router = APIRouter()


@router.post(path="/files")
async def upload_file(
    file: UploadFile = File(...),
    request: FilesRequest = Body(...),
    user: AuthenticatedUser = Security(dependency=Authorization(permissions=[PermissionType.CREATE_PRIVATE_COLLECTION])),
) -> Response:
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

    uploader = FileUploader(search=databases.search, user=user, collection_id=request.collection)
    output = uploader.parse(file=file)
    chunks = uploader.split(input=output, chunker_name=chunker_name, chunker_args=chunker_args)
    await uploader.upsert(chunks=chunks)

    file.file.close()

    return Response(status_code=201)
