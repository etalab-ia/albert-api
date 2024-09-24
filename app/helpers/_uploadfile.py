import io
import json
from typing import Optional, Any, List
import uuid

from bs4 import BeautifulSoup
from docx import Document
from langchain_community.document_loaders import PDFMinerLoader
import magic

from app.helpers.data.chunkers import RecursiveCharacterTextSplitter
from app.helpers.data.parsers import JSONParser, HTMLParser, PDFParser, DocxParser
from app.helpers.data import VectorStore
from app.schemas.files import JsonFile


class UploadFile(VectorStore):
    DOCX_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    PDF_TYPE = "application/pdf"
    JSON_TYPE = "application/json"
    TXT_TYPE = "text/plain"
    HTML_TYPE = "text/html"

    SUPPORTED_FILE_TYPES = [DOCX_TYPE, PDF_TYPE, JSON_TYPE, HTML_TYPE]

    def __init__(
        self, file: io.BytesIO, collection_id: str, clients: dict, user: str, file_name: Optional[str] = None, file_type: Optional[str] = None
    ):
        super().__init__(clients=clients, user=user)

        self.collection_id = collection_id
        self.file = file.file
        self.file_name = file_name if file_name.strip() else file.filename.strip()
        self.file_id = str(uuid.uuid4())
        self.file_type = file_type

        self.file_type = file_type if file_type else magic.from_file(file, mime=True)
        assert self.file_type in self.SUPPORTED_FILE_TYPES, f"Unsupported file type: {self.file_type}"

        self.metadata = {"file_id": self.file_id, "file_name": self.file_name, "file_type": self.file_type}

    def open(self):
        if self.file_type == self.PDF_TYPE:
            loader = PDFMinerLoader(io.BytesIO(self.file.read()))
            file = loader.load()

        elif self.file_type == self.DOCX_TYPE:
            file = Document(io.BytesIO(self.file.read()))

        elif self.file_type == self.JSON_TYPE:
            file = json.load(self.file)
            file = JsonFile(**file)

        elif self.file_type == self.HTML_TYPE:
            file = self.file.read().decode("utf-8")
            file = BeautifulSoup(file, "html.parser")

        return file

    def parse(self, file: Any) -> List[str]:
        if self.file_type == self.PDF_TYPE:
            parser = PDFParser()

        elif self.file_type == self.DOCX_TYPE:
            parser = DocxParser()

        elif self.file_type == self.JSON_TYPE:
            parser = JSONParser()

        elif self.file_type == self.HTML_TYPE:
            parser = HTMLParser()

        texts = parser.parse(self.file)

        return texts

    def chunk(self, texts: List[str]) -> List[str]:
        chunker = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        chunks = chunker.split_documents(texts)

        return chunks

    def store(self, chunks: List[str], model: str, collection_id: str):
        self.metadata["collection_id"] = collection_id
        documents = [Document(id=str(uuid.uuid4()), page_content=chunk, metadata=self.metadata) for chunk in chunks]

        self.from_documents(documents=documents, model=model, collection_name=collection_id)
