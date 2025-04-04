from typing import List

from langchain.text_splitter import RecursiveCharacterTextSplitter

from app.schemas.chunks import Chunk
from app.schemas.core.data import ParserOutput


class LangchainRecursiveCharacterTextSplitter(RecursiveCharacterTextSplitter):
    def __init__(self, chunk_min_size: int = 0, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.chunk_min_size = chunk_min_size

    def split(self, document: ParserOutput) -> List[Chunk]:
        metadata = document.metadata

        _chunks = list()
        for content in document.contents:
            _chunks.extend(self.split_text(content))

        chunks = list()
        for i, chunk in enumerate(_chunks):
            if len(chunk) < self.chunk_min_size:
                continue
            chunks.append(Chunk(id=i + 1, content=chunk, metadata=metadata))

        return chunks
