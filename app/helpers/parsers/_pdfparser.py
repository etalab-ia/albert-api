from typing import List

from langchain.docstore.document import Document as LangchainDocument

from ._baseparser import BaseParser


class PDFParser(BaseParser):
    def __init__(self):
        pass

    def parse(self, file) -> List[LangchainDocument]:
        """
        Parse a PDF file and converts it into a list of Langchain documents.

        Args:
            file (PDFLoader): PDF file to be processed.

        Returns:
            List[LangchainDocument]: List of Langchain documents.
        """

        documents = [LangchainDocument(page_content=self.clean(file[0].page_content), metadata=None)]

        return documents
