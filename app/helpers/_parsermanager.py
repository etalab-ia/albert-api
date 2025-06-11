import logging
from pathlib import Path
from typing import Dict, Optional, Set

from fastapi import HTTPException, UploadFile
import pymupdf

from app.clients.parser import BaseParserClient as ParserClient
from app.schemas.core.documents import FileType, ParserParams
from app.schemas.parse import ParsedDocument, ParsedDocumentMetadata, ParsedDocumentPage
from app.utils.exceptions import UnsupportedFileTypeException

logger = logging.getLogger(__name__)


class ParserManager:
    EXTENSION_MAP: Dict[str, FileType] = {
        ".pdf": FileType.PDF,
        ".html": FileType.HTML,
        ".htm": FileType.HTML,
        ".md": FileType.MD,
        ".markdown": FileType.MD,
        ".txt": FileType.TXT,
        ".text": FileType.TXT,
    }

    VALID_CONTENT_TYPES: Dict[FileType, Set[str]] = {
        FileType.PDF: {
            "application/pdf",
            "application/octet-stream",
        },
        FileType.HTML: {
            "text/html",
            "text/plain",
            "application/html",
            "application/octet-stream",
        },
        FileType.MD: {
            "text/markdown",
            "text/x-markdown",
            "text/plain",
            "application/markdown",
            "application/octet-stream",
        },
        FileType.TXT: {
            "text/plain",
            "text/txt",
            "application/octet-stream",
        },
    }

    def __init__(self, parser: Optional[ParserClient] = None, *args, **kwargs):
        self.parser_client = parser

    def _detect_file_type(self, file: UploadFile, type: Optional[FileType] = None) -> FileType:
        """
        Detect file type by extension, then check content-type.
        """
        try:
            filename = file.filename or ""
            extension = Path(filename).suffix.lower()
            content_type = file.content_type or ""
        except Exception as e:
            logger.exception(f"Failed to get filename or content-type from file: {e}")
            raise HTTPException(status_code=400, detail="Invalid file.")

        # detect type by extension and content-type
        detected_type = None
        if extension in self.EXTENSION_MAP:
            file_type = self.EXTENSION_MAP[extension]
            if content_type in self.VALID_CONTENT_TYPES[file_type]:
                detected_type = file_type
        else:
            # detect type only by content-type (less robust because it stops after first match)
            for file_type, valid_content_types in self.VALID_CONTENT_TYPES.items():
                if content_type in valid_content_types and content_type != "application/octet-stream":
                    detected_type = file_type

        if detected_type is None:
            logger.debug(f"Failed to detect file type: extension={extension}, content_type={content_type}")
            raise UnsupportedFileTypeException()

        if type and type != detected_type:
            raise UnsupportedFileTypeException(f"File must be a {type.value} file.")

        return detected_type

    async def parse_file(self, **params) -> ParsedDocument:
        params = ParserParams(**params)
        file_type = self._detect_file_type(params.file)

        method_map = {FileType.PDF: self._parse_pdf, FileType.HTML: self._parse_html, FileType.MD: self._parse_md, FileType.TXT: self._parse_txt}

        return await method_map[file_type](**params.model_dump())

    async def _parse_pdf(self, **params: ParserParams) -> ParsedDocument:
        params = ParserParams(**params)

        if self.parser_client and FileType.PDF in self.parser_client.SUPPORTED_FORMATS:
            document = await self.parser_client.parse(**params.model_dump())
            return document

        try:
            file_content = await params.file.read()
            pdf = pymupdf.open(stream=file_content, filetype="pdf")

            document = ParsedDocument(data=[])
            for page_num in range(len(pdf)):
                page = pdf[page_num]
                text = page.get_text()
                document.data.append(
                    ParsedDocumentPage(
                        content=text,
                        images={},
                        metadata=ParsedDocumentMetadata(document_name=params.file.filename, page=page_num),
                    )
                )
            pdf.close()
            return document

        except Exception as e:
            logger.exception(f"Failed to parse pdf file: {e}")
            raise HTTPException(status_code=500, detail="Failed to parse pdf file.")

    async def _parse_html(self, **params: ParserParams) -> ParsedDocument:
        params = ParserParams(**params)

        if self.parser_client and FileType.HTML in self.parser_client.SUPPORTED_FORMATS:
            document = await self.parser_client.parse(**params.model_dump())
            return document

        try:
            document = await params.file.read()
            document = ParsedDocument(
                data=[
                    ParsedDocumentPage(
                        content=document,
                        images={},
                        metadata=ParsedDocumentMetadata(document_name=params.file.filename),
                    )
                ]
            )
            return document

        except Exception as e:
            logger.exception(f"Failed to parse html file: {e}")
            raise HTTPException(status_code=500, detail="Failed to parse html file.")

    async def _parse_md(self, **kwargs) -> ParsedDocument:
        params = ParserParams(**kwargs)

        if self.parser_client and FileType.MD in self.parser_client.SUPPORTED_FORMATS:
            response = await self.parser_client.parse(**params.model_dump())
            return response

        try:
            content_bytes = await params.file.read()

            try:
                content = content_bytes.decode("utf-8")
            except UnicodeDecodeError:
                try:
                    content = content_bytes.decode("latin-1")
                except UnicodeDecodeError:
                    content = content_bytes.decode("utf-8", errors="replace")
                    logger.debug(f"Warning: Encoding problem detected for {params.file.filename}")

            await params.file.seek(0)

            document = ParsedDocument(
                data=[
                    ParsedDocumentPage(
                        content=content,
                        images={},
                        metadata=ParsedDocumentMetadata(document_name=params.file.filename),
                    )
                ]
            )
            return document

        except Exception as e:
            logger.exception(f"Failed to parse markdown file: {e}")
            raise HTTPException(status_code=500, detail="Failed to parse markdown file.")

    async def _parse_txt(self, **params: ParserParams) -> ParsedDocument:
        params = ParserParams(**params)

        if self.parser_client and FileType.TXT in self.parser_client.SUPPORTED_FORMATS:
            document = await self.parser_client.parse(**params.model_dump())
            return document

        try:
            text = await params.file.read()
            document = ParsedDocument(
                data=[
                    ParsedDocumentPage(
                        content=text,
                        images={},
                        metadata=ParsedDocumentMetadata(document_name=params.file.filename),
                    )
                ]
            )
            return document

        except Exception as e:
            logger.exception(f"Failed to parse text file: {e}")
            raise HTTPException(status_code=500, detail="Failed to parse text file.")
