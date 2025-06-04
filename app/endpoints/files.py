from io import BytesIO
import json
from pathlib import Path

from fastapi import APIRouter, Body, Depends, File, Security, UploadFile
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.datastructures import Headers

from app.helpers._accesscontroller import AccessController
from app.schemas.core.documents import JsonFile
from app.schemas.files import ChunkerArgs, FileResponse, FilesRequest
from app.schemas.parse import Languages, ParsedDocumentOutputFormat
from app.sql.session import get_db as get_session
from app.utils.context import global_context, request_context
from app.utils.exceptions import CollectionNotFoundException, FileSizeLimitExceededException, InvalidJSONFileFormatException
from app.utils.variables import ENDPOINT__FILES

router = APIRouter()


@router.post(path=ENDPOINT__FILES, status_code=201, response_model=FileResponse, dependencies=[Security(dependency=AccessController())])
async def upload_file(
    file: UploadFile = File(...),
    request: FilesRequest = Body(...),
    session: AsyncSession = Depends(get_session),
) -> JSONResponse:
    """
    **[DEPRECATED]** Upload a file to be processed, chunked, and stored into a vector database. Supported file types : pdf, html, json.

    Supported files types:
    - pdf: Portable Document Format file.
    - json: JavaScript Object Notation file.
        For JSON, file structure like a list of documents: [{"text": "hello world", "title": "my document", "metadata": {"autor": "me"}}, ...]} or [{"text": "hello world", "title": "my document"}, ...]}
        Each document must have a "text" and "title" keys and "metadata" key (optional) with dict type value.
    - html: Hypertext Markup Language file.
    - markdown: Markdown Language file.

    Max file size is 20MB.
    """
    if not global_context.documents:  # no vector store available
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

    filename = file.filename
    extension = Path(filename).suffix.lower()
    if extension == ".json" and file.content_type in ["application/json", "application/octet-stream"]:
        try:
            file = JsonFile(documents=json.loads(file.file.read())).documents
        except ValidationError as e:
            detail = "; ".join([f"{error["loc"][-1]}: {error["msg"]}" for error in e.errors()])
            raise InvalidJSONFileFormatException(detail=detail)

        files = list()

        for document in file:
            document_text = document.model_dump()
            text = document_text.get("text", "")
            metadata = document_text.get("metadata", {})
            name = f"{document_text["title"]}.json" if document_text.get("title") else f"{filename}.json"

            # Convert json into txt file
            file = UploadFile(filename=name, file=BytesIO(text.encode("utf-8")), headers=Headers({"content-type": "text/txt"}))
            files.append((file, metadata))
    else:
        files = [(file, None)]

    for file, metadata in files:
        document = await global_context.parser.parse_file(
            file=file,
            output_format=ParsedDocumentOutputFormat.MARKDOWN.value,
            force_ocr=False,
            languages=Languages.FR.value,
            page_range="",
            paginate_output=False,
            use_llm=False,
        )

        document_id = await global_context.documents.create_document(
            user_id=request_context.get().user_id,
            session=session,
            collection_id=request.collection,
            document=document,
            chunker_name=chunker_name,
            chunk_size=chunker_args["chunk_size"],
            chunk_overlap=chunker_args["chunk_overlap"],
            length_function=chunker_args["length_function"],
            is_separator_regex=chunker_args["is_separator_regex"],
            separators=chunker_args["separators"],
            chunk_min_size=chunker_args["chunk_min_size"],
            metadata=metadata,
        )

        file.file.close()

    return JSONResponse(status_code=201, content={"id": document_id})
