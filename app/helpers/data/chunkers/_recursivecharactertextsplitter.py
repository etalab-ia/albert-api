from typing import List, Optional

from langchain_text_splitters import Language
from langchain_text_splitters import RecursiveCharacterTextSplitter as LangChainRecursiveCharacterTextSplitter

from app.schemas.chunks import Chunk
from app.schemas.parse import ParsedDocument

from ._basesplitter import BaseSplitter


class RecursiveCharacterTextSplitter(BaseSplitter):
    def __init__(self, chunk_min_size: int = 0, metadata: Optional[dict] = None, language: Optional[Language] = None, *args, **kwargs) -> None:
        super().__init__(chunk_min_size=chunk_min_size, metadata=metadata, language=language)
        if self.language:
            self.splitter = LangChainRecursiveCharacterTextSplitter.from_language(language=language, *args, **kwargs)
        else:
            self.splitter = LangChainRecursiveCharacterTextSplitter(*args, **kwargs)

    def split_document(self, document: ParsedDocument) -> List[Chunk]:
        chunks = list()
        i = 1

        for page in document.contents:
            content = page.model_dump().get("content", "")
            content_chunks = self.splitter.split_text(content)
            for chunk in content_chunks:
                if len(chunk) < self.chunk_min_size:
                    continue
                chunks.append(Chunk(id=i, content=chunk, metadata=page.metadata.model_dump() | self.metadata))
                i += 1

        return chunks
