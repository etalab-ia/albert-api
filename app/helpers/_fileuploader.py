import traceback
from typing import List, Literal, Optional

from fastapi import UploadFile

# from app.clients.search import BaseSearchClient as SearchClient @TODO: split search into client and manager
from app.helpers.data.chunkers import *
from app.helpers.data.parsers import HTMLParser, JSONParser, MarkdownParser, PDFParser
from app.schemas.chunks import Chunk
from app.schemas.data import ParserOutput
from app.schemas.security import User
from app.utils.exceptions import InvalidJSONFormatException, NoChunksToUpsertException, ParsingFileFailedException, UnsupportedFileTypeException
from app.utils.logging import logger
from app.utils.variables import CHUNKERS, DEFAULT_CHUNKER, FILE_TYPE__HTML, FILE_TYPE__JSON, FILE_TYPE__MD, FILE_TYPE__PDF


class FileUploader:
    TYPE_DICT = {
        "json": FILE_TYPE__JSON,
        "html": FILE_TYPE__HTML,
        "pdf": FILE_TYPE__PDF,
        "md": FILE_TYPE__MD,
    }

    def __init__(self, collection_id: str, search, user: User):
        self.user = user
        self.search = search

        self.collection = self.search.get_collections(collection_ids=[collection_id], user=self.user)[0]
        self.collection_id = collection_id

    def parse(self, file: UploadFile) -> List[ParserOutput]:
        file_type = file.filename.split(".")[-1]
        if file_type not in self.TYPE_DICT.keys():
            raise UnsupportedFileTypeException()

        file_type = self.TYPE_DICT[file_type]

        if file_type == FILE_TYPE__PDF:
            parser = PDFParser(collection_id=self.collection_id)

        elif file_type == FILE_TYPE__JSON:
            parser = JSONParser(collection_id=self.collection_id)

        elif file_type == FILE_TYPE__HTML:
            parser = HTMLParser(collection_id=self.collection_id)

        elif file_type == FILE_TYPE__MD:
            parser = MarkdownParser(collection_id=self.collection_id)

        try:
            output = parser.parse(file=file)
        except Exception as e:
            logger.debug(traceback.format_exc())
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

    async def upsert(self, chunks: List[Chunk]) -> None:
        if not chunks:
            raise NoChunksToUpsertException()

        await self.search.upsert(chunks=chunks, collection_id=self.collection_id, user=self.user)
