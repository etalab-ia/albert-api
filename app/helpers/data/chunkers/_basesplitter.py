from abc import ABC, abstractmethod
from typing import List, Optional

from langchain_text_splitters import Language

from app.schemas.chunks import Chunk
from app.schemas.parse import ParsedDocument


class BaseSplitter(ABC):
    def __init__(self, chunk_min_size: int = 0, metadata: Optional[dict] = None, language_separators: Optional[Language] = None) -> None:
        self.chunk_min_size = chunk_min_size
        self.metadata = metadata or {}
        self.splitter = None  # this will be set in the child class
        self.language_separators = language_separators

    @abstractmethod
    def split_document(self, document: ParsedDocument) -> List[Chunk]:
        pass
