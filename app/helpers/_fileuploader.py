from typing import List, Literal, Optional

from fastapi import UploadFile

from app.helpers.chunkers import *
from app.helpers.parsers import HTMLParser, JSONParser, PDFParser, MarkdownParser
from app.schemas.chunks import Chunk
from app.schemas.data import ParserOutput
from app.schemas.security import User
from app.utils.exceptions import InvalidJSONFormatException, NoChunksToUpsertException, ParsingFileFailedException, UnsupportedFileTypeException
from app.utils.variables import CHUNKERS, DEFAULT_CHUNKER, HTML_TYPE, JSON_TYPE, PDF_TYPE, MARKDOWN_TYPE

from .searchclients._searchclient import SearchClient


class FileUploader:
    TYPE_DICT = {
        "json": JSON_TYPE,
        "html": HTML_TYPE,
        "pdf": PDF_TYPE,
        "md": MARKDOWN_TYPE,
    }

    def __init__(self, collection_id: str, search_client: SearchClient, user: User):
        self.user = user
        self.search_client = search_client

        self.collection = self.search_client.get_collections(collection_ids=[collection_id], user=self.user)[0]
        self.collection_id = collection_id

    def parse(self, file: UploadFile) -> List[ParserOutput]:
        file_type = file.filename.split(".")[-1]
        if file_type not in self.TYPE_DICT.keys():
            raise UnsupportedFileTypeException()

        file_type = self.TYPE_DICT[file_type]

        if file_type == PDF_TYPE:
            parser = PDFParser(collection_id=self.collection_id)

        elif file_type == JSON_TYPE:
            parser = JSONParser(collection_id=self.collection_id)

        elif file_type == HTML_TYPE:
            parser = HTMLParser(collection_id=self.collection_id)

        elif file_type == MARKDOWN_TYPE:
            parser = MarkdownParser(collection_id=self.collection_id)

        try:
            output = parser.parse(file=file)
        except Exception as e:
            if isinstance(e, InvalidJSONFormatException):
                raise e
            else:
                raise ParsingFileFailedException()

        return output

    def split(self, input: List[ParserOutput], chunker_name: Optional[Literal[*CHUNKERS]] = None, chunker_args: dict = {}) -> List[Chunk]:
        chunker_name = chunker_name if chunker_name else DEFAULT_CHUNKER
        chunker = globals()[chunker_name](**chunker_args)

        chunks = chunker.split(input=input)

        return chunks

    def upsert(self, chunks: List[Chunk]) -> None:
        if not chunks:
            raise NoChunksToUpsertException()

        self.search_client.upsert(chunks=chunks, collection_id=self.collection_id, user=self.user)
