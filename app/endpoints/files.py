from typing import Optional, Union
from uuid import UUID

from fastapi import APIRouter, Body, HTTPException, Response, Security, UploadFile
from fastapi import File as FastApiFile
from fastapi.responses import JSONResponse
from qdrant_client.http.models import FieldCondition, Filter, MatchAny

from app.helpers import VectorStore
from app.helpers._fileuploader import FileUploader
from app.schemas.files import File, Files, FilesRequest, ChunkerArgs
from app.utils.lifespan import clients
from app.utils.security import check_api_key

router = APIRouter()


@router.post("/files")
async def upload_file(file: UploadFile = FastApiFile(...), request: FilesRequest = Body(...), user: str = Security(check_api_key)) -> Response:
    """
    Upload a file to be processed, chunked, and stored into a vector database. Supported file types : pdf, html, json.

    Supported files types:
    - pdf: Portable Document Format file.
    - json: JavaScript Object Notation file.
        For JSON, file structure like a list of documents: [{"text": "hello world", "metadata": {"title": "my document"}}, ...]} or [{"text": "hello world"}, ...]}
        Each document must have a "text" key and "metadata" key (optional) with dict type value.
    - html: Hypertext Markup Language file.

    Max file size is 20MB.
    """

    if request.chunker:
        chunker_args = request.chunker.args.model_dump() if request.chunker.args else ChunkerArgs().model_dump()
        chunker_name = request.chunker.name
    else:
        chunker_args = ChunkerArgs().model_dump()
        chunker_name = None

    chunker_args["length_function"] = len if chunker_args["length_function"] == "len" else None

    try:
        uploader = FileUploader(clients=clients, user=user, file=file, collection_id=request.collection, file_type=request.file_type)
        documents = uploader.parse()
        chunks = uploader.chunk(documents=documents, chunker_name=chunker_name, chunker_args=chunker_args)
        uploader.embed(chunks=chunks)

    except AssertionError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return JSONResponse(status_code=201, content={"id": uploader.file_id})


@router.get("/files/{collection}/{file}")
@router.get("/files/{collection}")
async def files(
    collection: UUID,
    file: Optional[UUID] = None,
    user: str = Security(check_api_key),
) -> Union[File, Files]:
    """
    Get files from a collection. Only files from private collections are returned.
    """

    collection = str(collection)
    file = str(file) if file else None
    vectorstore = VectorStore(clients=clients, user=user)
    filter = Filter(must=[FieldCondition(key="metadata.file_id", match=MatchAny(any=[file]))]) if file else None

    try:
        chunks = vectorstore.get_chunks(collection_id=collection, filter=filter)
    except AssertionError as e:
        raise HTTPException(status_code=400, detail=str(e))

    data = dict()
    for chunk in chunks:
        if chunk.metadata["file_id"] not in data:
            data[chunk.metadata["file_id"]] = File(
                id=chunk.metadata["file_id"],
                object="file",
                bytes=chunk.metadata.get("file_size", None),
                name=chunk.metadata.get("file_name", None),
                chunks=[chunk.id],
                created_at=chunk.metadata.get("created_at", None),
            )
        else:
            data[chunk.metadata["file_id"]].chunks.append(chunk.id)

    if file:
        if file not in data:
            raise HTTPException(status_code=404, detail="File not found.")
        else:
            return data[file]
    else:
        return Files(data=list(data.values()))


@router.delete("/files/{collection}/{file}")
async def delete_file(collection: UUID, file: Optional[UUID] = None, user: str = Security(check_api_key)) -> Response:
    """
    Delete files and relative collections. Only files from private collections can be deleted.
    """
    collection = str(collection)
    file = str(file) if file else None
    vectorstore = VectorStore(clients=clients, user=user)
    try:
        filter = Filter(must=[FieldCondition(key="metadata.file_id", match=MatchAny(any=[file]))])
        vectorstore.delete_chunks(collection_id=collection, filter=filter)
    except AssertionError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return Response(status_code=204)
