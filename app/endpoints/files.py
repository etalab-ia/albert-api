from typing import Optional, Union
import uuid

from botocore.exceptions import ClientError
from fastapi import APIRouter, HTTPException, Response, Security, UploadFile
from qdrant_client.http.models import FieldCondition, Filter, MatchAny

from app.helpers import S3FileLoader, VectorStore
from app.schemas.files import File, Files, FilesRequest
from app.utils.config import LOGGER
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

    loader = S3FileLoader(
        s3=clients["files"], chunk_size=request.chunk_size, chunk_overlap=request.chunk_overlap, chunk_min_size=request.chunk_min_size
    )
    vectorstore = VectorStore(clients=clients, user=user)

    try:
        clients["files"].head_bucket(Bucket=request.collection)
    except ClientError:
        clients["files"].create_bucket(Bucket=request.collection)

    file_id = str(uuid.uuid4())
    file_name = file.filename.strip()

    try:
        # convert files into chunks (Langchain documents format)
        documents = loader._get_elements(file_id=file_id, bucket=request.collection)
        for document in documents:
            document.id = str(uuid.uuid4())
        # create vectors from documents
        vectorstore.from_documents(documents=documents, model=request.embeddings_model, collection_name=request.collection)

    except Exception as e:
        LOGGER.error(f"upload file {file_name}:\n{e}")
        raise HTTPException(status_code=400, detail=f"error during file conversion: {e}")

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
    chunks = vectorstore.get_chunks(collection_name=collection.name, filter=filter)

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
        vectorstore.delete_chunks(collection_name=collection, filter=filter)
    except AssertionError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return Response(status_code=204)
