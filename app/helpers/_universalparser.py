import json
from typing import List, Optional

from bs4 import BeautifulSoup
from docx import Document as DocxLoader
from langchain.docstore.document import Document as LangchainDocument
from langchain_community.document_loaders import PDFMinerLoader
import magic

from app.helpers.parsers import DocxParser, HTMLParser, JSONParser, PDFParser
from app.schemas.files import JsonFile

from ._textcleaner import TextCleaner


class UniversalParser:
    DOCX_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    PDF_TYPE = "application/pdf"
    JSON_TYPE = "application/json"
    TXT_TYPE = "text/plain"
    HTML_TYPE = "text/html"

    SUPPORTED_FILE_TYPES = [DOCX_TYPE, PDF_TYPE, JSON_TYPE, HTML_TYPE]

    def __init__(self):
        """
        Initializes the class instance.

        Attributes:
            cleaner (TextCleaner): An instance of TextCleaner used for cleaning text.
        """
        self.cleaner = TextCleaner()
        pass

    def parse_and_chunk(self, file_path: str, chunk_size: int, chunk_overlap: int, chunk_min_size: Optional[int] = None) -> List[LangchainDocument]:
        """
        Parses a file and splits it into text chunks based on the file type.

        Args:
            file_path (str): Path to the file to be processed.
            chunk_size (int): Maximum size of each text chunk.
            chunk_overlap (int): Number of characters overlapping between chunks.
            chunk_min_size (int): Minimum size of a chunk to be considered valid.

        Returns:
            list: List of Langchain documents, where each document corresponds to a text chunk.

        Raises:
            NotImplementedError: If the file type is not supported.
        """
        file_type = magic.from_file(file_path, mime=True)
        file_name = file_path.split("/")[-1]

        if file_type not in self.SUPPORTED_FILE_TYPES:
            raise NotImplementedError(f"Unsupported input file format ({file_path}): {file_type}")

        # @TODO: check if it a possible option ?
        if file_type == self.TXT_TYPE:
            # In the case the json file is stored as text/plain instead of application/json
            with open(file_path, "r") as file:
                content = file.read()
                try:
                    data = json.loads(content)
                    file_type = self.JSON_TYPE
                except json.JSONDecodeError:
                    pass

        if file_type not in self.SUPPORTED_FILE_TYPES:
            raise NotImplementedError(f"Unsupported input file format ({file_path}): {file_type}")

        if file_type == self.PDF_TYPE:
            loader = PDFMinerLoader(file_path)
            file = loader.load()
            parser = PDFParser()

        elif file_type == self.DOCX_TYPE:
            file = DocxLoader(file_path)
            parser = DocxParser()

        elif file_type == self.JSON_TYPE:
            file = json.load(open(file_path, "r"))
            file = JsonFile(**data)
            parser = JSONParser()

        elif file_type == self.HTML_TYPE:
            file = open(file_path, "r").read()
            file = BeautifulSoup(file, "html.parser")
            parser = HTMLParser()

        documents = parser.parse_and_chunk(
            file=file, file_name=file_name, chunk_size=chunk_size, chunk_overlap=chunk_overlap, chunk_min_size=chunk_min_size
        )

        return documents
