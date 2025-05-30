from typing import List
from app.schemas.chunks import Chunk
from app.schemas.core.documents import ParserOutput


class NoChunker:
    def __init__(self, chunk_min_size: int = 0, *args, **kwargs):
        self.chunk_min_size = chunk_min_size

    def split(self, document: ParserOutput) -> List[Chunk]:
        chunks = list()
        metadata = document.metadata
        contents = document.contents  # no split

        for i, content in enumerate(contents):
            if len(content) < self.chunk_min_size:
                continue

            chunks.append(Chunk(content=content, id=i + 1, metadata=metadata))

        return chunks
