from typing import Optional, Dict, Set
import os
from pathlib import Path

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
    force_ocr: bool = False
    languages: Optional[Languages] = None
    page_range: Optional[str] = None
    paginate_output: bool = False
    use_llm: bool = False


class ParserManager:
    SUPPORTED_FORMATS = [FileType.PDF, FileType.HTML, FileType.MD, FileType.TXT]
    
    EXTENSION_MAP: Dict[str, FileType] = {
        '.pdf': FileType.PDF,
        '.html': FileType.HTML,
        '.htm': FileType.HTML,
        '.md': FileType.MD,
        '.markdown': FileType.MD,
        '.txt': FileType.TXT,
        '.text': FileType.TXT,
    }
    
    VALID_CONTENT_TYPES: Dict[FileType, Set[str]] = {
        FileType.PDF: {
            'application/pdf',
            'application/octet-stream',  
        },
        FileType.HTML: {
            'text/html',
            'text/plain',
            'application/octet-stream',  
        },
        FileType.MD: {
            'text/markdown',
            'text/x-markdown',
            'text/plain',
            'application/markdown',
            'application/octet-stream',  
        },
        FileType.TXT: {
            'text/plain',
            'text/txt',
            'application/octet-stream',  
        },
    }

    def __init__(self, parser: Optional[ParserClient] = None, *args, **kwargs):
        self.parser_client = parser

    def _detect_file_type(self, file: UploadFile) -> FileType:
        """
        Détecte le type de fichier en priorisant l'extension,
        puis vérifie la cohérence avec le content-type.
        """
        filename = file.filename or ""
        extension = Path(filename).suffix.lower()
        content_type = file.content_type or ""
        
        print(f"Fichier: {filename}")
        print(f"Extension: {extension}")
        print(f"Content-Type: {content_type}")
        
        detected_type = None
        if extension in self.EXTENSION_MAP:
            detected_type = self.EXTENSION_MAP[extension]
            print(f"Type détecté par extension: {detected_type}")
            
            valid_content_types = self.VALID_CONTENT_TYPES[detected_type]
            if content_type in valid_content_types:
                print(f"Content-type {content_type} compatible avec {detected_type}")
                return detected_type
            else:
                print(f"Warning: Content-type {content_type} ne correspond pas à l'extension {extension}")
                if content_type == "application/octet-stream":
                    print("Acceptation du fallback application/octet-stream")
                    return detected_type
                else:
                    print("Content-type incompatible, fallback sur content-type")
        
        for file_type, valid_content_types in self.VALID_CONTENT_TYPES.items():
            if content_type in valid_content_types and content_type != "application/octet-stream":
                print(f"Type détecté par content-type: {file_type}")
                return file_type
        
        if detected_type:
            print(f"Utilisation du type détecté par extension malgré content-type incompatible: {detected_type}")
            return detected_type
            
        raise UnsupportedFileTypeException(
            f"Type de fichier non supporté. Extension: {extension}, Content-Type: {content_type}"
        )

    def _validate_file_type(self, file_type: FileType) -> None:
        """Valide que le type de fichier est supporté."""
        if file_type not in self.SUPPORTED_FORMATS:
            raise UnsupportedFileTypeException(f"Type de fichier {file_type} non supporté")

    async def parse_file(self, **params) -> ParsedDocument:
        params = ParserParams(**params)
        
        try:
            file_type = self._detect_file_type(params.file)
            self._validate_file_type(file_type)
        except Exception as e:
            print('--------------------------------------------')
            print(f'Erreur de détection: {e}')
            print(f'Filename: {params.file.filename}')
            print(f'Content-Type: {params.file.content_type}')
            print('--------------------------------------------')
            raise

        method_map = {
            FileType.PDF: self._parse_pdf,
            FileType.HTML: self._parse_html,
            FileType.MD: self._parse_md,
            FileType.TXT: self._parse_txt,
        }
        
        parse_method = method_map[file_type]
        return await parse_method(**params.model_dump())

    async def _parse_pdf(self, **params: ParserParams) -> ParsedDocument:
        params = ParserParams(**params)
        if self.parser_client and FileType.PDF in self.parser_client.SUPPORTED_FORMATS:
            document = await self.parser_client.parse(**params.model_dump())

        else:
            file_content = await params.file.read()
            pdf = pymupdf.open(stream=file_content, filetype="pdf")

            pages = []
            for page_num in range(len(pdf)):
                print(page_num)
                page = pdf[page_num]
                text = page.get_text()
                pages.append(ParsedDocumentPage(content=text, images={}, metadata={"page": page_num + 1, **pdf.metadata}))

            document = ParsedDocument(
                format=params.output_format,  
                contents=pages, 
                metadata=ParsedDocumentMetadata(document_name=params.file.filename)
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

    async def _parse_md(self, **kwargs) -> ParsedDocument:
        params = ParserParams(**kwargs)
        
        if self.parser_client and FileType.MD in self.parser_client.SUPPORTED_FORMATS:
            response = await self.parser_client.parse(**params.model_dump())
            return response

        try:
            content_bytes = await params.file.read()
            
            try:
                content = content_bytes.decode('utf-8')
            except UnicodeDecodeError:
                try:
                    content = content_bytes.decode('latin-1')
                except UnicodeDecodeError:
                    content = content_bytes.decode('utf-8', errors='replace')
                    print(f"Warning: Problème d'encodage détecté pour {params.file.filename}")
            
            await params.file.seek(0)
            
            document = ParsedDocument(
                format=params.output_format,
                contents=[
                    ParsedDocumentPage(
                        content=content,
                        images={},
                        metadata={}
                    )
                ],
                metadata=ParsedDocumentMetadata(
                    document_name=params.file.filename
                ),
            )
            
            return document
            
        except Exception as e:
            print(f"Erreur lors du parsing du fichier Markdown {params.file.filename}: {e}")
            raise


    async def _parse_txt(self, **params: ParserParams) -> ParsedDocument:
        params = ParserParams(**params)
        if self.parser_client and FileType.TXT in self.parser_client.SUPPORTED_FORMATS:
            document = await self.parser_client.parse(**params.model_dump())
            return document
        
        text = await params.file.read()
        
        document = ParsedDocument(
            format=params.output_format,
            contents=[ParsedDocumentPage(content=text, images={}, metadata={})],
            metadata=ParsedDocumentMetadata(document_name=params.file.filename),
        )

        return document
