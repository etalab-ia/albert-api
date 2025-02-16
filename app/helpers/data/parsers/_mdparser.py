import re
import time
from typing import Dict, List, Tuple, Optional
import uuid

from bs4 import BeautifulSoup
from fastapi import UploadFile

from app.schemas.data import ParserOutput, ParserOutputMetadata

from . import HTMLParser
from ._baseparser import BaseParser


class MarkdownParser(BaseParser):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    def parse(self, file: UploadFile, metadata: Optional[Dict]) -> List[ParserOutput]:
        """
        Parse a Markdown file and converts it into a list of chunk objects.

        Args:
            file (UploadFile): Markdown file to parse.

        Returns:
            List[ParserOutput]: List of parsed outputs.
        """

        markdown_text = file.file.read().decode(encoding="utf-8")

        markdown_tups: List[Tuple[Optional[str], str]] = []
        lines = markdown_text.split("\n")

        title = None
        current_header = None
        current_lines = []
        in_code_block = False

        for line in lines:
            if line.startswith("```"):
                # This is the end of a code block if we are already in it, and vice versa.
                in_code_block = not in_code_block

            header_match = re.match(pattern=r"^#+\s", string=line)
            if not in_code_block and header_match:
                # Upon first header, skip if current text chunk is empty
                if current_header is not None or len(current_lines) > 0:
                    markdown_tups.append((current_header, "\n".join(current_lines)))
                if not title:
                    title = line
                current_header = line
                current_lines.clear()
            else:
                current_lines.append(line)

        # Append final text chunk
        if current_lines:
            markdown_tups.append((current_header, "\n".join(current_lines)))

        extracted_text = [f"{title}:\n{content}".format({title, content}) for (title, content) in markdown_tups]

        content = self.clean("\n".join(extracted_text).strip())

        name = file.filename.strip()

        document_metadata = ParserOutputMetadata(
            collection_id=self.collection_id,
            document_id=str(uuid.uuid4()),
            document_name=name,
            document_created_at=round(
                time.time(),
            ),
            title=title,
            **metadata,
        )

        output = [ParserOutput(content=content, metadata=document_metadata)]

        return output
