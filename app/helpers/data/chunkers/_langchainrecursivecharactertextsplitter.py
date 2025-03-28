from typing import List

from langchain.text_splitter import RecursiveCharacterTextSplitter

from app.schemas.chunks import Chunk, ChunkMetadata
from app.schemas.core.data import ParserOutput


class LangchainRecursiveCharacterTextSplitter(RecursiveCharacterTextSplitter):
    def __init__(self, chunk_min_size: int = 0, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.chunk_min_size = chunk_min_size

    def split(self, document: ParserOutput) -> List[Chunk]:
        metadata = ChunkMetadata(**document.metadata)

        _chunks = list()
        for content in document.contents:
            _chunks.extend(self.split_text(content))

        chunks = list()
        for i, chunk in enumerate(_chunks):
            if len(chunk) < self.chunk_min_size:
                continue
            metadata.document_part = f"{i + 1}/{len(_chunks)}"
            chunks.append(Chunk(content=chunk, id=i + 1, metadata=metadata))

        return chunks
