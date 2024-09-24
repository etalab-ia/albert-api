from typing import List, Optional

from langchain.docstore.document import Document as LangchainDocument
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders.PDFMinerLoader import load as PDFLoader


class PDFParser:
    def __init__(self):
        pass

    def parse(
        self, file: PDFLoader, file_name: str, chunk_size: int, chunk_overlap: int, chunk_min_size: Optional[int] = None
    ) -> List[LangchainDocument]:
        """
        Parse a PDF file and converts it into a list of text chunks.

        Args:
            file_path (str): Path to the PDF file to be processed.
            chunk_size (int): Maximum size of each text chunk.
            chunk_overlap (int): Number of characters overlapping between chunks.
            chunk_min_size (int): Minimum size of a chunk to be considered valid.

        Returns:
            list: List of Langchain documents, where each document corresponds to a text chunk.
        """

        documents = []
        chunker = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size, chunk_overlap=chunk_overlap, length_function=len, is_separator_regex=False, separators=["\n\n", "\n"]
        )
        chunks = chunker.split_text(file[0].page_content)

        for chunk in chunks:
            if chunk_min_size and len(chunk) < chunk_min_size:
                continue

            document = LangchainDocument(page_content=self.cleaner.clean_string(chunk), metadata={"file_id": file_name})
            documents.append(document)

        return documents
