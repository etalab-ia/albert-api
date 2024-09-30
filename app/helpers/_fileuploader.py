import io
import json
from typing import Optional, Any, List, Literal
import uuid

from bs4 import BeautifulSoup
from docx import Document as DocxDocument
from langchain_community.document_loaders import PDFMinerLoader
import magic

from app.helpers.chunkers import *
from app.helpers.parsers import JSONParser, HTMLParser, PDFParser, DocxParser
from langchain.docstore.document import Document as LangchainDocument
from app.helpers import VectorStore
from app.schemas.files import JsonFile
from app.schemas.chunks import Chunk
from app.utils.variables import SUPPORTED_FILE_TYPES


class FileUploader:
    def __init__(
        self, file: io.BytesIO, collection_id: str, clients: dict, user: str, file_name: Optional[str] = None, file_type: Optional[str] = None
    ):
        self.clients = clients
        self.user = user
        self.collection_id = collection_id
        self.file = file.file
        self.file_name = file_name if file_name.strip() else file.filename.strip()
        self.file_id = str(uuid.uuid4())
        self.file_type = file_type

        self.file_type = file_type if file_type else magic.from_file(file, mime=True)
        assert self.file_type in SUPPORTED_FILE_TYPES, f"Unsupported file type: {self.file_type}"

        self.metadata = {"file_id": self.file_id, "file_name": self.file_name, "file_type": self.file_type}

    def load(self):
        if self.file_type == self.PDF_TYPE:
            loader = PDFMinerLoader(io.BytesIO(self.file.read()))
            file = loader.load()

        elif self.file_type == self.DOCX_TYPE:
            file = DocxDocument(io.BytesIO(self.file.read()))

        elif self.file_type == self.JSON_TYPE:
            file = json.load(self.file)
            file = JsonFile(**file)

        elif self.file_type == self.HTML_TYPE:
            file = self.file.read().decode("utf-8")
            file = BeautifulSoup(file, "html.parser")

        return file

    def parse(self, file: Any) -> List[LangchainDocument]:
        if self.file_type == self.PDF_TYPE:
            parser = PDFParser()

        elif self.file_type == self.DOCX_TYPE:
            parser = DocxParser()

        elif self.file_type == self.JSON_TYPE:
            parser = JSONParser()

        elif self.file_type == self.HTML_TYPE:
            parser = HTMLParser()

        documents = parser.parse(self.file)

        return documents

    def chunk(self, documents: List[LangchainDocument], chunker_name: Literal["TODO"], chunker_args: dict) -> List[Chunk]:
        chunks = list()
        chunker = locals()[chunker_name](**chunker_args)

        for document in documents:
            document_chunks = chunker.split_documents(document.page_content)
            for chunk in document_chunks:
                chunks.append(Chunk(id=str(uuid.uuid4)), content=chunk, metadata=document.metadata)

        return chunks

    def embed(self, chunks: List[Chunk], model: str):
        vectorstore = VectorStore(clients=self.clients, user=self.user)
        documents = [LangchainDocument(id=chunk.id, page_content=chunk.content, metadata=self.metadata | chunk.metadata) for chunk in chunks]
        vectorstore.from_documents(documents=documents, model=model, collection_name=self.collection_id)
