from typing import List, Optional
import uuid

from langchain.text_splitter import RecursiveCharacterTextSplitter

from app.schemas.chunks import Chunk, ChunkMetadata
from app.schemas.data import ParserOutput


class LangchainRecursiveCharacterTextSplitter(RecursiveCharacterTextSplitter):
    def __init__(self, chunk_min_size: Optional[int] = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.chunk_min_size = chunk_min_size

    def split(self, input: List[ParserOutput]) -> List[Chunk]:
        chunks = list()

        for document in input:
            contents = self.split_text(document.content)
            for i, content in enumerate(contents):
                if self.chunk_min_size and len(content) < self.chunk_min_size:
                    continue

                document.metadata.document_part = i + 1
                metadata = ChunkMetadata(**document.metadata.model_dump())
                chunks.append(Chunk(content=content, id=str(uuid.uuid4()), metadata=metadata))

        return chunks
