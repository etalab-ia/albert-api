from io import BytesIO
from typing import List

from fastapi import UploadFile
from pdfminer.high_level import extract_text_to_fp
from pdfminer.layout import LAParams

from app.schemas.core.data import ParserOutput

from ._baseparser import BaseParser


class PDFParser(BaseParser):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def parse(self, file: UploadFile) -> List[ParserOutput]:
        """
        Parse a PDF file and converts it into a list of parsed outputs.

        Args:
            file (PDFLoader): PDF file to be processed.

        Returns:
            List[ParserOutput]: List of parsed outputs.
        """

        output = BytesIO()
        extract_text_to_fp(BytesIO(file.file.read()), output, laparams=LAParams(), output_type="text", codec="utf-8")
        content = output.getvalue().decode("utf-8").strip()
        content = self.clean(text=content)
        metadata = {}
        output = ParserOutput(contents=[content], metadata=metadata)

        return output
