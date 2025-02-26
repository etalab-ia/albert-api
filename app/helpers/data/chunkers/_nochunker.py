from typing import List
import uuid
from app.schemas.chunks import Chunk, ChunkMetadata
from app.schemas.data import ParserOutput


class NoChunker:
    def __init__(self, chunk_min_size: int = 0, *args, **kwargs):
        self.chunk_min_size = chunk_min_size

    def split(self, input: List[ParserOutput]) -> List[Chunk]:
        chunks = list()

        for document in input:
            if len(document.content) < self.chunk_min_size:
                continue

            document.metadata.document_part = 1
            metadata = ChunkMetadata(**document.metadata.model_dump())
            chunks.append(Chunk(content=document.content, id=str(uuid.uuid4()), metadata=metadata))

        return chunks
