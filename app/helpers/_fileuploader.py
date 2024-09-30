import time
from typing import List, Literal, Optional
import uuid

from fastapi import UploadFile
from langchain.docstore.document import Document as LangchainDocument

from app.helpers import VectorStore
from app.helpers.chunkers import *
from app.helpers.parsers import HTMLParser, JSONParser, PDFParser
from app.schemas.chunks import Chunk
from app.utils.variables import CHUNKERS, DEFAULT_CHUNKER, HTML_TYPE, JSON_TYPE, PDF_TYPE, PRIVATE_COLLECTION_TYPE, SUPPORTED_FILE_TYPES


class FileUploader:
    MAX_FILE_SIZE = 536870912  # 512 MB
    TYPE_DICT = {
        "json": JSON_TYPE,
        "html": HTML_TYPE,
        "pdf": PDF_TYPE,
    }

    def __init__(
        self, file: UploadFile, collection_id: str, clients: dict, user: str, file_name: Optional[str] = None, file_type: Optional[str] = None
    ):
        self.clients = clients
        self.user = user
        self.collection_id = collection_id
        self.file_size = file.size
        assert self.file_size < self.MAX_FILE_SIZE, f"File size exceeds the maximum limit of {self.MAX_FILE_SIZE} bytes"
        self.file = file.file.read()
        self.file_name = file_name.strip() if file_name else file.filename.strip()
        self.file_id = str(uuid.uuid4())
        self.file_type = file_type

        self.file_type = file_type if file_type else self.TYPE_DICT[file.filename.split(".")[-1]]
        assert self.file_type in SUPPORTED_FILE_TYPES, f"Unsupported file type: {self.file_type}"

        self.vectorstore = VectorStore(clients=self.clients, user=self.user)
        collection = self.vectorstore.get_collection_metadata(collection_ids=[self.collection_id], type=PRIVATE_COLLECTION_TYPE)[0]
        self.model = collection.model
        self.metadata = {
            "file_id": self.file_id,
            "file_name": self.file_name,
            "file_type": self.file_type,
            "file_size": self.file_size,
            "created_at": round(time.time()),
        }

    def parse(self) -> List[LangchainDocument]:
        if self.file_type == PDF_TYPE:
            parser = PDFParser()

        elif self.file_type == JSON_TYPE:
            parser = JSONParser()

        elif self.file_type == HTML_TYPE:
            parser = HTMLParser()

        documents = parser.parse(file=self.file)

        return documents

    def split(self, documents: List[LangchainDocument], chunker_name: Optional[Literal[*CHUNKERS]] = None, chunker_args: dict = {}) -> List[Chunk]:
        chunks = list()
        chunker_name = chunker_name if chunker_name else DEFAULT_CHUNKER
        chunker = globals()[chunker_name](**chunker_args)

        for document in documents:
            document_chunks = chunker.chunk(document.page_content)
            for chunk in document_chunks:
                chunks.append(Chunk(id=str(uuid.uuid4()), content=chunk, metadata=document.metadata))

        return chunks

    def embed(self, chunks: List[Chunk]):
        documents = [LangchainDocument(id=chunk.id, page_content=chunk.content, metadata=self.metadata | chunk.metadata) for chunk in chunks]
        self.vectorstore.from_documents(documents=documents, model=self.model, collection_id=self.collection_id)
