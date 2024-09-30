from typing import List

from app.schemas.files import JsonFile
from langchain.docstore.document import Document as LangchainDocument

from ._baseparser import BaseParser


class JSONParser(BaseParser):
    def __init__(self):
        pass

    def parse(self, file: JsonFile) -> List[LangchainDocument]:
        """
        Parse a JSON file and converts it into a list of Langchain documents.

        Args:
            file (JsonFile): JSON file to be processed.

        Returns:
            List[LangchainDocument]: List of Langchain documents.
        """

        document = [LangchainDocument(page_content=self.clean(document.text), metadata=document.metadata) for document in file]

        return document
