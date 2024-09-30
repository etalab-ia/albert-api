from io import BytesIO
import json
from typing import List
import uuid

from langchain.docstore.document import Document as LangchainDocument

from app.schemas.files import JsonFile

from ._baseparser import BaseParser


class JSONParser(BaseParser):
    def __init__(self):
        pass

    def parse(self, file: BytesIO) -> List[LangchainDocument]:
        """
        Parse a JSON file and converts it into a list of Langchain documents.

        Args:
            file (JsonFile): JSON file to be processed.

        Returns:
            List[LangchainDocument]: List of Langchain documents.
        """

        file = json.loads(file)
        try:
            file = JsonFile(documents=file)
        except Exception as e:
            raise AssertionError("Invalid JSON file format.")

        document = [
            LangchainDocument(
                page_content=self.clean(document.text),
                metadata=document.metadata | {"file_id": str(uuid.uuid4()), "file_name": document.title, "file_size": len(document.text)},
            )
            for document in file.documents
        ]

        return document
