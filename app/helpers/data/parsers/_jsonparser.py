from typing import List, Optional

from langchain.docstore.document import Document as LangchainDocument
from langchain.text_splitter import RecursiveCharacterTextSplitter

from app.schemas.files import JsonFile


class JSONParser:
    def __init__(self):
        pass

    def parse(
        self, file: JsonFile, file_name: str, chunk_size: Optional[int], chunk_overlap: Optional[int], chunk_min_size: Optional[int] = None
    ) -> List[LangchainDocument]:
        """
        Converts a JSON file into a list of chunks.

        Args:
            file (JsonFile):
            file_name (str):
            chunk_size (int): Maximum size of each text chunk.
            chunk_overlap (int): Number of characters overlapping between chunks.
            chunk_min_size (int): Minimum size of a chunk to be considered valid.

        Returns:
            list: List of Langchain documents, where each document corresponds to a text chunk.
        """

        documents = []
        chunker = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size, chunk_overlap=chunk_overlap, length_function=len, is_separator_regex=False, separators=["\n"]
        )

        for document in file.documents:
            if document.metadata:
                document.metadata["file_id"] = file_name
            else:
                document.metadata = {"file_id": file_name}

            chunks = chunker.split_text(document.text)
            for chunk in chunks:
                if chunk_min_size and len(chunk) < chunk_min_size:
                    continue

                document = LangchainDocument(page_content=self.cleaner.clean_string(chunk), metadata=document.metadata)
                documents.append(document)

        return document
