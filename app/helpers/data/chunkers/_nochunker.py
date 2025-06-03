from typing import List, Optional

from langchain_text_splitters import Language

from app.schemas.chunks import Chunk
from app.schemas.parse import ParsedDocument

from ._basesplitter import BaseSplitter


class NoChunker(BaseSplitter):
    def __init__(self, chunk_min_size: int = 0, metadata: Optional[dict] = None, language: Optional[Language] = None, *args, **kwargs) -> None:
        super().__init__(chunk_min_size=chunk_min_size, metadata=metadata, language=language)

    def split_document(self, document: ParsedDocument) -> List[Chunk]:
        chunks = list()
        i = 1

        for page in document.data:
            content = page.model_dump().get("content", "")
            if len(content) < self.chunk_min_size:
                continue
            chunks.append(Chunk(id=i, content=content, metadata=page.metadata.model_dump() | self.metadata))
            i += 1

        return chunks
