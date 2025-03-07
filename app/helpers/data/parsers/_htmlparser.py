from typing import List
from fastapi import UploadFile
import uuid
import time

from bs4 import BeautifulSoup


from app.schemas.core.data import ParserOutput, ParserOutputMetadata
from ._baseparser import BaseParser


class HTMLParser(BaseParser):
    ALLOWED_TAGS = ["h1", "h2", "h3", "h4", "li", "p"]
    EXCLUDED_WORDS = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def parse(self, file: UploadFile) -> List[ParserOutput]:
        """
        Parse a HTML file and converts it into a list of chunk objects.

        Args:
            file (UploadFile): HTML file to parse.

        Returns:
            List[ParserOutput]: List of parsed outputs.
        """

        content = file.file.read().decode("utf-8")
        content = BeautifulSoup(content, "html.parser")

        first_element = None
        li_consecutive_count = 0
        li_temp_storage = []
        extracted_text = []
        extracted_title = []
        for element in content.descendants:
            if element.name in ["h1", "h2"]:
                text = element.get_text(" ", strip=True)
                if len(text.split()) > 1 and not any(word in text.lower() for word in self.EXCLUDED_WORDS):
                    extracted_title.append(text)
                    first_element = True
            if first_element is None and element.name in ["p"]:
                text = element.get_text(" ", strip=True)
                if len(text.split()) > 10 and not any(word in text.lower() for word in self.EXCLUDED_WORDS):
                    extracted_text.append(text)
            elif first_element and element.name in self.ALLOWED_TAGS:
                if element.name in ["h2", "h3", "p"]:
                    text = element.get_text(" ", strip=True)
                    if len(text.split()) > 3 and not any(word in text.lower() for word in self.EXCLUDED_WORDS):
                        if 1 <= li_consecutive_count <= 5:
                            processed_li_temp = "\n".join(li_temp_storage).strip()
                            extracted_text.append(processed_li_temp)
                        extracted_text.append(text)
                    li_consecutive_count = 0
                    li_temp_storage = []
                elif element.name in ["li"]:
                    text = element.get_text(" ", strip=True)
                    if len(text.split()) > 3 and not any(word in text.lower() for word in self.EXCLUDED_WORDS):
                        li_consecutive_count += 1
                        li_temp_storage.append(text)

        title = " - ".join(extracted_title).strip()
        title = max([(text, len(text.split())) for text in title.split(" - ")], key=lambda x: x[1])[0]

        content = self.clean("\n".join(extracted_text).strip())
        name = file.filename.strip()
        metadata = ParserOutputMetadata(
            collection_id=self.collection_id, document_id=str(uuid.uuid4()), document_name=name, document_created_at=round(time.time()), title=title
        )

        output = [ParserOutput(content=content, metadata=metadata)]

        return output
