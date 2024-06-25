import base64
import uuid
import sys

from typing import List, Optional, Union
from fastapi import APIRouter, Response, Security, UploadFile, HTTPException
from langchain_huggingface import HuggingFaceEndpointEmbeddings
from botocore.exceptions import ClientError
from langchain_community.vectorstores import Qdrant as VectorStore
from qdrant_client.http import models as rest

sys.path.append("..")
from utils.schemas import (
    CollectionResponse,
    ToolResponse,
    ChatHistory,
    ChatHistoryResponse,
    File,
    FileResponse,
    FileUploadResponse,
)
from utils.config import logging
from utils.security import check_api_key
from utils.lifespan import clients
from helpers import S3FileLoader
from tools import *
from tools import __all__ as tools_list

router = APIRouter()


@router.get("/health")
def health(api_key: str = Security(check_api_key)):
    """
    Health check.
    """

    return Response(status_code=200)


@router.get("/chat/history/{user}/{id}")
@router.get("/chat/history/{user}")
async def chat_history(
    user: str, id: Optional[str] = None, api_key: str = Security(check_api_key)
) -> Union[ChatHistoryResponse, ChatHistory]:
    """
    Get chat history of a user.
    """
    chat_history = clients["chathistory"].get_chat_history(user_id=user, chat_id=id)

    return chat_history


@router.post("/files", tags=["Albert"])
async def upload_files(
    user: str,
    files: List[UploadFile],
    model: str,
    chunk_size: int = 3000,
    chunk_overlap: int = 400,
    chunk_min_size: int = 90,
    api_key: str = Security(check_api_key),
) -> FileUploadResponse:
    """
    Upload files into the configured files and vectors databases.
    """

    response = {"object": "list", "data": []}

    try:
        clients["files"].head_bucket(Bucket=user)
    except ClientError:
        clients["files"].create_bucket(Bucket=user)

    loader = S3FileLoader(
        s3=clients["files"],
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        chunk_min_size=chunk_min_size,
    )

    try:
        model_url = str(clients["openai"][model].base_url)
        model_url = model_url.replace("/v1/", "/tei/")
    except KeyError:
        raise HTTPException(status_code=404, detail="Model not found.")

    # @TODO: support openai embeddings class
    embedding = HuggingFaceEndpointEmbeddings(
        model=model_url,
        huggingfacehub_api_token=clients["openai"][model].api_key,
    )

    for file in files:
        status = "success"
        file_id = str(uuid.uuid4())
        file_name = file.filename.strip()

        encoded_file_name = base64.b64encode(file_name.encode("utf-8")).decode("ascii")
        try:
            # upload files into S3 bucket
            clients["files"].upload_fileobj(
                file.file,
                user,
                file_id,
                ExtraArgs={
                    "ContentType": file.content_type,
                    "Metadata": {
                        "filename": encoded_file_name,
                        "id": file_id,
                    },
                },
            )
        except Exception as e:
            logging.error(f"store {file_name}:\n{e}")
            status = "failed"
            response["data"].append({"object": "upload", "id": file_id, "filename": file_name, "status": status})  # fmt: off
            continue

        try:
            # convert files into langchain documents
            documents = loader._get_elements(file_id=file_id, bucket=user)
        except Exception as e:
            logging.error(f"convert {file_name} into documents:\n{e}")
            status = "failed"
            clients["files"].delete_object(Bucket=user, Key=file_id)
            response["data"].append({"object": "upload", "id": file_id, "filename": file_name, "status": status})  # fmt: off
            continue

        try:
            # create vectors from documents
            db = await VectorStore.afrom_documents(
                documents=documents,
                embedding=embedding,
                collection_name=user,
                url=clients["vectors"].url,
                api_key=clients["vectors"].api_key,
            )
        except Exception as e:
            logging.error(f"create vectors of {file_name}:\n{e}")
            status = "failed"
            clients["files"].delete_object(Bucket=user, Key=file_id)
            response["data"].append({"object": "upload", "id": file_id, "filename": file_name, "status": status})  # fmt: off
            continue

        response["data"].append(
            {"object": "upload", "id": file_id, "filename": file_name, "status": status}
        )

    return response


@router.get("/files/{user}/{file_id}")
@router.get("/files/{user}")
def files(
    user: str, file_id: Optional[str] = None, api_key: str = Security(check_api_key)
) -> Union[File, FileResponse]:
    response = {"object": "list", "metadata": {"files": 0, "vectors": 0}, "data": []}
    """
    Upload files can be used in tools. 
    Use Mistral IA conventions: https://docs.mistral.ai/api/#operation/files_api_routes_upload_file
    """

    try:
        clients["files"].head_bucket(Bucket=user)
    except ClientError:
        raise HTTPException(status_code=404, detail="Files not found")

    response = {"object": "list", "data": []}
    objects = clients["files"].list_objects_v2(Bucket=user).get("Contents", [])
    objects = [object | clients["files"].head_object(Bucket=user, Key=object["Key"])["Metadata"] for object in objects]  # fmt: off
    for object in objects:
        data = {
            "id": object["Key"],
            "object": "file",
            "bytes": object["Size"],
            "filename": base64.b64decode(object["filename"].encode("ascii")).decode("utf-8"),
            "created_at": round(object["LastModified"].timestamp()),
        }
        response["data"].append(data)

        if object["Key"] == file_id:
            return data

    if file_id:  # if loop pass without return data
        raise HTTPException(status_code=404, detail="File not found.")

    return response


@router.delete("/files/{user}/{file_id}")
@router.delete("/files/{user}")
def delete_file(
    user: str, file_id: Optional[str] = None, api_key: str = Security(check_api_key)
) -> Response:
    """
    Delete files from configured files and vectors databases.
    """

    try:
        clients["files"].head_bucket(Bucket=user)
    except ClientError:
        raise HTTPException(status_code=404, detail="Bucket not found")

    if file_id is None:
        objects = clients["files"].list_objects_v2(Bucket=user)
        if "Contents" in objects:
            objects = [{"Key": obj["Key"]} for obj in objects["Contents"]]
            clients["files"].delete_objects(Bucket=user, Delete={"Objects": objects})

        clients["files"].delete_bucket(Bucket=user)
        clients["vectors"].delete_collection(user)
    else:
        clients["files"].delete_object(Bucket=user, Key=file_id)
        filter = rest.Filter(must=[rest.FieldCondition(key="metadata.file_id", match=rest.MatchAny(any=[file_id]))])  # fmt: off
        clients["vectors"].delete(collection_name=user, points_selector=rest.FilterSelector(filter=filter))  # fmt: off

    return Response(status_code=204)


@router.get("/tools")
def tools(api_key: str = Security(check_api_key)) -> ToolResponse:
    """
    Get list a availables tools. Only RAG functions are currenty supported.
    """
    data = [
        {
            "id": globals()[tool].__name__,
            "description": globals()[tool].__doc__.strip(),
            "object": "tool",
        }
        for tool in tools_list
    ]
    response = {"object": "list", "data": data}

    return response


@router.get("/collections/{user}")
def collections(user: Optional[str], api_key: str = Security(check_api_key)) -> CollectionResponse:
    """
    Get list of collections.
    """

    response = clients["vectors"].get_collections()
    collections = [
        {
            "object": "collection",
            "name": collection,
            "type": "user" if collection == user else "public",
        }
        for collection in response.collections
        if collection.name.startswith("public_") or collection.name == user
    ]

    response = {"object": "list", "data": collections}
    return response
