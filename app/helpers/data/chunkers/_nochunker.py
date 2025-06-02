from typing import List, Optional

from app.schemas.chunks import Chunk
from app.schemas.parse import ParsedDocument


class NoChunker:
    def __init__(self, chunk_min_size: int = 0, metadata: Optional[dict] = None, *args, **kwargs):
        self.chunk_min_size = chunk_min_size
        self.metadata = metadata or {}

    def split(self, document: ParsedDocument) -> List[Chunk]:
        chunks = list()
        i = 1

        for page in document.contents:
            content = page.model_dump().get("content", "")
            if len(content) < self.chunk_min_size:
                continue
            chunks.append(Chunk(id=i, content=content, metadata=page.metadata | self.metadata | document.metadata.model_dump()))
            i += 1

        return chunks
