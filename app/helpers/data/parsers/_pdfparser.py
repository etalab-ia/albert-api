from io import BytesIO
from typing import Dict, Any

from fastapi import UploadFile
from pdfminer.high_level import extract_text_to_fp
from pdfminer.layout import LAParams

from app.schemas.core.documents import ParserOutput
from app.clients.parser._markerparserclient import MarkerParserClient

from ._baseparser import BaseParser


class PDFParser(BaseParser):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.marker_parser = MarkerParserClient()

    async def simple_parse(self, file: UploadFile) -> ParserOutput:
        """
        Parse a PDF file and converts it into a parsed output using pdfminer.

        Args:
            file (UploadFile): PDF file to be processed.

        Returns:
            ParserOutput: Parsed output.
        """
        output = BytesIO()
        file_content = await file.read()
        extract_text_to_fp(BytesIO(file_content), output, laparams=LAParams(), output_type="text", codec="utf-8")
        content = output.getvalue().decode("utf-8").strip()
        content = self.clean(text=content)
        metadata = {}
        output = ParserOutput(contents=[content], metadata=metadata)

        return output

    async def parse(self, file: UploadFile, paginate: bool = True, use_llm: bool = False) -> ParserOutput:
        """
        Parse a PDF file using the Marker API and returns text with page numbers.

        Args:
            file (UploadFile): PDF file to be processed.
            paginate (bool): Whether to paginate the output.
            use_llm (bool): Whether to use LLM for enhanced parsing.

        Returns:
            ParserOutput: Parsed output with text and page numbers.
        """
        try:
            # Reset file pointer to beginning
            await file.seek(0)

            # Parse using Marker API
            marker_response = await self.marker_parser.parse_pdf(
                file=file,
                output_format="json",  # JSON format gives better structure
                paginate_output=paginate,
                use_llm=use_llm,
            )
            metadata: Dict[str, Any] = {}
            if marker_response.success:
                return ParserOutput(contents=marker_response["output"], metadata=metadata)

            else:
                # Fallback to simple parse if marker parsing fails
                await file.seek(0)
                return await self.simple_parse(file)

        except Exception as e:
            # Log the error and fallback to simple parse
            print(f"Error in marker parsing: {str(e)}")
            await file.seek(0)
            return await self.simple_parse(file)
