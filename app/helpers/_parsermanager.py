from typing import Optional

from fastapi import UploadFile
from pydantic import BaseModel

from app.clients.parser import BaseParserClient as ParserClient
from app.schemas.core.documents import FileType
from app.schemas.parse import Languages, ParsedDocument, ParsedDocumentMetadata, ParsedDocumentOutputFormat, ParsedDocumentPage
from app.utils.exceptions import UnsupportedFileTypeException
import pymupdf


class ParserParams(BaseModel):
    file: UploadFile
    output_format: Optional[ParsedDocumentOutputFormat] = None
    force_ocr: bool = (False,)
    languages: Optional[Languages] = (None,)
    page_range: Optional[str] = (None,)
    paginate_output: bool = (False,)
    use_llm: bool = (False,)


class ParserManager:
    SUPPORTED_FORMATS = [FileType.PDF, FileType.HTML, FileType.MD, FileType.TXT]

    def __init__(self, parser: Optional[ParserClient] = None, *args, **kwargs):
        self.parser_client = parser

    async def parse_file(self, **params: ParserParams) -> ParsedDocument:
        params = ParserParams(**params)

        if params.file.content_type == FileType.PDF:
            return await self._parse_pdf(**params.model_dump())
        elif params.file.content_type == FileType.HTML:
            return await self._parse_html(**params.model_dump())
        elif params.file.content_type == FileType.MD:
            return await self.parse_md(**params.model_dump())
        elif params.file.content_type == FileType.TXT:
            return await self.parse_txt(**params.model_dump())
        else:
            raise UnsupportedFileTypeException

    async def _parse_pdf(self, **params: ParserParams) -> ParsedDocument:
        params = ParserParams(**params)
        if self.parser_client and FileType.PDF in self.parser_client.SUPPORTED_FORMATS:
            document = await self.parser_client.parse(**params.model_dump())

        else:
            # Lire le contenu du fichier uploadé
            file_content = await params.file.read()
            pdf = pymupdf.open(stream=file_content, filetype="pdf")

            pages = []
            for page_num in range(len(pdf)):
                print(page_num)
                page = pdf[page_num]
                text = page.get_text()
                pages.append(ParsedDocumentPage(content=text, images={}, metadata={"page": page_num + 1, **pdf.metadata}))

            document = ParsedDocument(
                format=ParsedDocumentOutputFormat.MARKDOWN, contents=pages, metadata=ParsedDocumentMetadata(document_name=params.file.filename)
            )
        return document

    async def _parse_html(self, **params: ParserParams) -> ParsedDocument:
        params = ParserParams(**params)
        if self.parser_client and FileType.HTML in self.parser_client.SUPPORTED_FORMATS:
            try:
                response = await self.parser_client.parse(**params.model_dump())
                return response
            except Exception as e:
                from fastapi import HTTPException

                raise HTTPException(status_code=500, detail=str(e))

        document = await params.file.read()
        document = ParsedDocument(
            format=params.output_format,
            contents=[ParsedDocumentPage(content=document, images={}, metadata={})],
            metadata=ParsedDocumentMetadata(document_name=params.file.filename),
        )

        return document

    async def _parse_md(self, **params: ParserParams) -> ParsedDocument:
        params = ParserParams(**params)
        if self.parser_client and FileType.MD in self.parser_client.SUPPORTED_FORMATS:
            response = await self.parser_client.parse(**params.model_dump())
            return response

        document = await params.file.read()
        document = ParsedDocument(
            format=params.output_format,
            contents=[ParsedDocumentPage(content=document, images={}, metadata={})],
            metadata=ParsedDocumentMetadata(document_name=params.file.filename),
        )
        return document

    async def _parse_txt(self, **params: ParserParams) -> ParsedDocument:
        params = ParserParams(**params)
        if self.parser_client and FileType.TXT in self.parser_client.SUPPORTED_FORMATS:
            document = await self.parser_client.parse(**params.model_dump())
            return document

        document = await params.file.read()
        document = ParsedDocument(
            format=params.output_format,
            contents=[ParsedDocumentPage(content=document, images={}, metadata={})],
            metadata=ParsedDocumentMetadata(document_name=params.file.filename),
        )

        return document
