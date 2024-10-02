from typing import List
from io import BytesIO

from bs4 import BeautifulSoup
from langchain.docstore.document import Document as LangchainDocument

from ._baseparser import BaseParser


class HTMLParser(BaseParser):
    ALLOWED_TAGS = ["h1", "h2", "h3", "h4", "li", "p"]
    EXCLUDED_WORDS = []

    def __init__(self):
        pass

    def parse(self, file: BytesIO) -> List[LangchainDocument]:
        """
        Parse a HTML file and converts it into a list of Langchain documents.

        Args:
            file (BeautifulSoup): Parsed HTML content.

        Returns:
            List[LangchainDocument]: List of Langchain documents.
        """

        file = file.read().decode("utf-8")
        file = BeautifulSoup(file, "html.parser")

        first_element = None
        li_consecutive_count = 0
        li_temp_storage = []
        extracted_text = []
        extracted_title = []
        for element in file.descendants:
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
        text = "\n".join(extracted_text).strip()

        documents = [LangchainDocument(page_content=self.clean(text), metadata={"title": title})]

        return documents
