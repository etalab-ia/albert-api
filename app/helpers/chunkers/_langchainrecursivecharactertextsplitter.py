from typing import List, Optional
import uuid

from langchain.docstore.document import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter

from app.schemas.chunks import Chunk


class LangchainRecursiveCharacterTextSplitter(RecursiveCharacterTextSplitter):
    def __init__(self, chunk_min_size: Optional[int] = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.chunk_min_size = chunk_min_size

    def split(self, document: Document) -> List[Chunk]:
        data = list()
        chunks = self.split_text(document.page_content)

        for chunk in chunks:
            if self.chunk_min_size and len(chunk) < self.chunk_min_size:
                continue
            data.append(Chunk(content=chunk, id=str(uuid.uuid4()), metadata=document.metadata))

        return data
