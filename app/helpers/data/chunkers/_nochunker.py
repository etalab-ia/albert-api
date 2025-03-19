from typing import List
from app.schemas.chunks import Chunk, ChunkMetadata
from app.schemas.core.data import ParserOutput


class NoChunker:
    def __init__(self, chunk_min_size: int = 0, *args, **kwargs):
        self.chunk_min_size = chunk_min_size

    def split(self, document: ParserOutput) -> List[Chunk]:
        chunks = list()

        metadata = ChunkMetadata(**document.metadata.model_dump())
        contents = [document.content]

        for i, content in enumerate(contents):
            if len(content) < self.chunk_min_size:
                continue

            metadata.document_part = f"{i + 1}/{len(contents)}"
            chunks.append(Chunk(content=content, id=i + 1, metadata=metadata))

        return chunks
