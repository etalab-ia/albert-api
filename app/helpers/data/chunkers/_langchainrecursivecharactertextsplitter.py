from typing import List

from langchain.text_splitter import RecursiveCharacterTextSplitter

from app.schemas.chunks import Chunk, ChunkMetadata
from app.schemas.core.data import ParserOutput


class LangchainRecursiveCharacterTextSplitter(RecursiveCharacterTextSplitter):
    def __init__(self, chunk_min_size: int = 0, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.chunk_min_size = chunk_min_size

    def split(self, document: ParserOutput) -> List[Chunk]:
        chunks = list()
        metadata = ChunkMetadata(**document.metadata.model_dump())

        contents = [self.split_text(content) for content in document.contents]
        for i, content in enumerate(contents):
            if len(content) < self.chunk_min_size:
                continue
            metadata.document_part = f"{i + 1}/{len(contents)}"
            chunks.append(Chunk(content=content, id=i + 1, metadata=metadata))

        return chunks
