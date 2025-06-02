from typing import List, Optional

from langchain.text_splitter import RecursiveCharacterTextSplitter

from app.schemas.chunks import Chunk
from app.schemas.parse import ParsedDocument


class RecursiveCharacterTextSplitter(RecursiveCharacterTextSplitter):
    def __init__(self, chunk_min_size: int = 0, metadata: Optional[dict] = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.chunk_min_size = chunk_min_size
        self.metadata = metadata or {}

    def split(self, document: ParsedDocument) -> List[Chunk]:
        chunks = list()
        i = 1

        for page in document.contents:
            content = page.model_dump().get("content", "")
            content_chunks = self.split_text(content)
            for chunk in content_chunks:
                if len(chunk) < self.chunk_min_size:
                    continue
                chunks.append(Chunk(id=i, content=chunk, metadata=page.metadata | self.metadata | document.metadata.model_dump()))
                i += 1

        return chunks
