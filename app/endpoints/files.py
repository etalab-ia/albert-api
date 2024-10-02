from uuid import UUID

from fastapi import APIRouter, Body, HTTPException, Response, Security, UploadFile
from fastapi import File as FastApiFile
from fastapi.responses import JSONResponse
from qdrant_client.http.models import FieldCondition, Filter, MatchAny

from app.helpers import VectorStore
from app.helpers._fileuploader import FileUploader
from app.schemas.files import ChunkerArgs, File, Files, FilesRequest
from app.schemas.security import User
from app.utils.lifespan import clients
from app.utils.security import check_api_key

router = APIRouter()


@router.post("/files")
async def upload_file(file: UploadFile = FastApiFile(...), request: FilesRequest = Body(...), user: User = Security(check_api_key)) -> Response:
    """
    Upload a file to be processed, chunked, and stored into a vector database. Supported file types : pdf, html, json.

    Supported files types:
    - pdf: Portable Document Format file.
    - json: JavaScript Object Notation file.
        For JSON, file structure like a list of documents: [{"text": "hello world", "metadata": {"title": "my document"}}, ...]} or [{"text": "hello world"}, ...]}
        Each document must have a "text" key and "metadata" key (optional) with dict type value.
    - html: Hypertext Markup Language file.

    Max file size is 10MB.
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
        chunks = uploader.split(documents=documents, chunker_name=chunker_name, chunker_args=chunker_args)
        uploader.embed(chunks=chunks)

    except AssertionError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return JSONResponse(status_code=201, content={"id": uploader.file_id})


@router.get("/files/{collection}")
async def get_files(collection: UUID, user: User = Security(check_api_key)) -> Files:
    """
    Get all files ID from a collection.
    """
    collection = str(collection)
    vectorstore = VectorStore(clients=clients, user=user)

    try:
        chunks = vectorstore.get_chunks(collection_id=collection)
    except AssertionError as e:
        raise HTTPException(status_code=400, detail=str(e))

    data = list(set(chunk.metadata["file_id"] for chunk in chunks))

    return Files(data=data)


@router.get("/files/{collection}/{file}")
async def files(collection: UUID, file: UUID, user: User = Security(check_api_key)) -> File:
    """
    Get information about a file from a collection.
    """

    collection, file = str(collection), str(file)
    vectorstore = VectorStore(clients=clients, user=user)
    filter = Filter(must=[FieldCondition(key="metadata.file_id", match=MatchAny(any=[file]))])

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

    if file not in data:
        raise HTTPException(status_code=404, detail="File not found.")

    return data[file]


@router.delete("/files/{collection}/{file}")
async def delete_file(collection: UUID, file: UUID, user: User = Security(check_api_key)) -> Response:
    """
    Delete files and relative collections.
    """
    collection, file = str(collection), str(file)
    vectorstore = VectorStore(clients=clients, user=user)

    # @TODO: raise 404 if file not found
    try:
        filter = Filter(must=[FieldCondition(key="metadata.file_id", match=MatchAny(any=[file]))])
        vectorstore.delete_chunks(collection_id=collection, filter=filter)
    except AssertionError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return Response(status_code=204)
