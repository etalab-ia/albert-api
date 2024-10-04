from typing import List, Literal, Optional

from fastapi import UploadFile

from app.helpers import VectorStore
from app.schemas.data import ParserOutput
from app.helpers.chunkers import *
from app.helpers.parsers import HTMLParser, JSONParser, PDFParser
from app.schemas.chunks import Chunk
from app.schemas.security import User
from app.utils.variables import (
    CHUNKERS,
    DEFAULT_CHUNKER,
    HTML_TYPE,
    JSON_TYPE,
    PDF_TYPE,
)


class FileUploader:
    TYPE_DICT = {
        "json": JSON_TYPE,
        "html": HTML_TYPE,
        "pdf": PDF_TYPE,
    }

    def __init__(self, collection_id: str, clients: dict, user: User):
        self.vectorstore = VectorStore(clients=clients, user=user)
        self.collection = self.vectorstore.get_collections(collection_ids=[collection_id])[0]

        self.clients = clients
        self.user = user
        self.collection_id = collection_id

    def parse(self, file: UploadFile) -> List[ParserOutput]:
        file_type = file.filename.split(".")[-1]
        assert file_type in self.TYPE_DICT.keys(), f"Unsupported file type: {file_type}"

        file_type = self.TYPE_DICT[file.filename.split(".")[-1]]
        # try:
        if file_type == PDF_TYPE:
            parser = PDFParser(collection_id=self.collection_id)

        elif file_type == JSON_TYPE:
            parser = JSONParser(collection_id=self.collection_id)

        elif file_type == HTML_TYPE:
            parser = HTMLParser(collection_id=self.collection_id)

        output = parser.parse(file=file)

        return output

    # @TODO: check if document is empty raise an error
    def split(self, input: List[ParserOutput], chunker_name: Optional[Literal[*CHUNKERS]] = None, chunker_args: dict = {}) -> List[Chunk]:
        chunker_name = chunker_name if chunker_name else DEFAULT_CHUNKER
        chunker = globals()[chunker_name](**chunker_args)

        chunks = chunker.split(input=input)

        return chunks

    def upsert(self, chunks: List[Chunk]):
        self.vectorstore.upsert(chunks=chunks, collection_id=self.collection_id)
