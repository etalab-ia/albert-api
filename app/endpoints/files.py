from typing import Optional, Union
import uuid

from fastapi import APIRouter, HTTPException, Response, Security, UploadFile
from qdrant_client.http.models import FieldCondition, Filter, MatchAny

from app.helpers import FileUploader, VectorStore
from app.schemas.files import File, Files, FilesRequest
from app.utils.lifespan import clients
from app.utils.security import check_api_key

router = APIRouter()


@router.post("/files")
async def upload_file(request: FilesRequest, file: UploadFile, user: str = Security(check_api_key)) -> Response:
    """
    Upload multiple files to be processed, chunked, and stored into a vector database. Supported file types : docx, pdf, json.

    **Args**:
    - **collection** (string): The collection name where the files will be stored.
    - **embeddings_model** (string): The embedding model to use for creating vectors. A collection must have only one embedding model.
    - **chunk_size** (int): The maximum number of characters of each text chunk.
    - **chunk_overlap** (int): The number of characters overlapping between chunks.
    - **chunk_min_size** (int): The minimum number of characters of a chunk to be considered valid.

    Supported files types:
    - **docx**: Microsoft Word file.
    - **pdf**: Portable Document Format file.
    - **json**: JavaScript Object Notation file.
        For JSON, file structure like: {"documents": [{"text": "hello world", "metadata": {"title": "my document"}}, ...]} or {"documents": [{"text": "hello world"}, ...]}
        Each document must have a "text" key and "metadata" key (optional) with dict type value.
    - **html**: Hypertext Markup Language file.

    **Request body**
    - **files** : Files to upload.
    """

    file_id = str(uuid.uuid4())
    file_name = file.filename.strip()

    try:
        uploader = FileUploader(
            clients=clients, user=user, file=file, collection_id=request.collection_id, file_name=request.file_name, file_type=request.file_type
        )

        # load
        file = uploader.load()

        # parse
        documents = uploader.parse(file=file)

        # chunk
        chunks = uploader.chunk(chunker_name=request.chunker.name, chunker_args=request.chunker.args)

        # embed
        uploader.embed(model=request.embeddings_model, collection_id=request.collection)

    # TODO: replace exception by AssertionError after catch every possible errors
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    return Response(status_code=201)


@router.get("/files/{collection}/{file}")
@router.get("/files/{collection}")
async def files(
    collection: str,
    file: Optional[str] = None,
    user: str = Security(check_api_key),
) -> Union[File, Files]:
    """
    Get files from a collection. Only files from private collections are returned.
    """
    data = list()
    vectorstore = VectorStore(clients=clients, user=user)
    collection = vectorstore.get_collection_metadata(collection_ids=[collection])[0]
    filter = Filter(must=[FieldCondition(key="metadata.file_id", match=MatchAny(any=file))]) if file else None

    try:
        chunks = vectorstore.get_chunks(collection_name=collection.name, filter=filter)
    except AssertionError as e:
        raise HTTPException(status_code=400, detail=str(e))

    data = list()
    for chunk in chunks:
        if chunk.metadata["file_id"] not in data:
            data[chunk.metadata["file_id"]] = File(
                id=chunk.metadata["file_id"],
                object="file",
                bytes=chunk.metadata["size"],
                name=chunk.metadata["file_name"],
                chunks=[chunk.id],
                created_at=round(chunk.metadata["created_at"].timestamp()),
            )
        else:
            data[chunk.metadata["file_id"]].chunks.append(chunk.id)

    if file:
        if file not in data:
            raise HTTPException(status_code=404, detail="File not found.")
        else:
            return data[file]
    else:
        data = list(data.values())
        return Files(data=data)


@router.delete("/files/{collection}/{file}")
async def delete_file(collection: str, file: Optional[str] = None, user: str = Security(check_api_key)) -> Response:
    """
    Delete files and relative collections. Only files from private collections can be deleted.

    Args:
        collection (str): The collection name where the files will be deleted.
        file (str): The file name to delete.
    """

    vectorstore = VectorStore(clients=clients, user=user)
    try:
        filter = Filter(must=[FieldCondition(key="metadata.file_id", match=MatchAny(any=[file]))])
        vectorstore.delete_chunks(collection_id=collection, filter=filter)
    except AssertionError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return Response(status_code=204)
