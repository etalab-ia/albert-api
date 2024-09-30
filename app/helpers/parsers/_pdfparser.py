from io import BytesIO
from typing import List

from langchain.docstore.document import Document as LangchainDocument
from pdfminer.high_level import extract_text_to_fp
from pdfminer.layout import LAParams

from ._baseparser import BaseParser


class PDFParser(BaseParser):
    def __init__(self):
        pass

    def parse(self, file: BytesIO) -> List[LangchainDocument]:
        """
        Parse a PDF file and converts it into a list of Langchain documents.

        Args:
            file (PDFLoader): PDF file to be processed.

        Returns:
            List[LangchainDocument]: List of Langchain documents.
        """

        output = BytesIO()
        extract_text_to_fp(BytesIO(file), output, laparams=LAParams(), output_type="text", codec="utf-8")
        file = output.getvalue().decode("utf-8").strip()

        documents = [LangchainDocument(page_content=self.clean(file), metadata={})]

        return documents
