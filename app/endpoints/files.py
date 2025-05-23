from io import BytesIO
import json

from fastapi import APIRouter, Body, Depends, File, Security, UploadFile
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.helpers import AccessController
from app.schemas.auth import User
from app.schemas.core.data import FileType, JsonFile
from app.schemas.files import ChunkerArgs, FilesRequest, FileResponse
from app.sql.session import get_db as get_session
from app.utils.exceptions import CollectionNotFoundException, FileSizeLimitExceededException, InvalidJSONFileFormatException
from app.utils.lifespan import context
from app.utils.variables import ENDPOINT__FILES

router = APIRouter()


# TODO: turn into form data endpoint to log usages
@router.post(path=ENDPOINT__FILES, status_code=201, response_model=FileResponse)
async def upload_file(
    file: UploadFile = File(...),
    request: FilesRequest = Body(...),
    user: User = Security(dependency=AccessController()),
    session: AsyncSession = Depends(get_session),
) -> JSONResponse:
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
    if not context.documents:  # no vector store available
        raise CollectionNotFoundException()

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

    if file.content_type == FileType.JSON:
        try:
            file = JsonFile(documents=json.loads(file.file.read())).documents
        except ValidationError as e:
            detail = "; ".join([f"{error["loc"][-1]}: {error["msg"]}" for error in e.errors()])
            raise InvalidJSONFileFormatException(detail=detail)

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
        document_id = await context.documents.create_document(
            session=session,
            user_id=user.id,
            collection_id=request.collection,
            file=file,
            chunker_name=chunker_name,
            chunker_args=chunker_args,
        )

        file.file.close()

    return JSONResponse(status_code=201, content={"id": document_id})
