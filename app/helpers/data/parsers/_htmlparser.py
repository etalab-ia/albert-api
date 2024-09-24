from typing import List, Optional

from bs4 import BeautifulSoup
from langchain.docstore.document import Document as LangchainDocument
from langchain.text_splitter import RecursiveCharacterTextSplitter


class HTMLParser:
    ALLOWED_TAGS = ["h1", "h2", "h3", "h4", "li", "p"]
    EXCLUDED_WORDS = []
    EXTRACTED_TEXT = []
    EXTRACTED_TITLE = []
    FIRST_ELEMENT = None
    LI_CONSECUTIVE_COUNT = 0
    LI_TEMP_STORAGE = []

    def __init__(self):
        pass

    def parse(
        self, file: BeautifulSoup, file_name: str, chunk_size: int, chunk_overlap: int, chunk_min_size: Optional[int] = None
    ) -> List[LangchainDocument]:
        """
        Converts HTML content into a list of text chunks.

        Args:
            file (BeautifulSoup): Parsed HTML content.
            file_name: File name.
            chunk_size (int): Maximum size of each text chunk.
            chunk_overlap (int): Number of characters overlapping between chunks.
            chunk_min_size (int): Minimum size of a chunk to be considered valid.

        Returns:
            List[LangchainDocument]: List of Langchain documents, where each document corresponds to a text chunk.
        """

        documents = []
        chunker = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size, chunk_overlap=chunk_overlap, length_function=len, is_separator_regex=False, separators=["\n\n", "\n"]
        )

        for element in file.descendants:
            if element.name in ["h1", "h2"]:
                text = element.get_text(" ", strip=True)
                if len(text.split()) > 1 and not any(word in text.lower() for word in self.EXCLUDED_WORDS):
                    self.EXTRACTED_TITLE.append(text)
                    first_element = True
            if first_element is None and element.name in ["p"]:
                text = element.get_text(" ", strip=True)
                if len(text.split()) > 10 and not any(word in text.lower() for word in self.EXCLUDED_WORDS):
                    self.EXTRACTED_TEXT.append(text)
            elif first_element and element.name in self.ALLOWED_TAGS:
                if element.name in ["h2", "h3", "p"]:
                    text = element.get_text(" ", strip=True)
                    if len(text.split()) > 3 and not any(word in text.lower() for word in self.EXCLUDED_WORDS):
                        if 1 <= self.LI_CONSECUTIVE_COUNT <= 5:
                            processed_li_temp = "\n".join(self.LI_TEMP_STORAGE).strip()
                            self.EXTRACTED_TEXT.append(processed_li_temp)
                        self.EXTRACTED_TEXT.append(text)
                    li_consecutive_count = 0
                    li_temp_storage = []
                elif element.name in ["li"]:
                    text = element.get_text(" ", strip=True)
                    if len(text.split()) > 3 and not any(word in text.lower() for word in self.EXCLUDED_WORDS):
                        li_consecutive_count += 1
                        li_temp_storage.append(text)

        processed_title = " - ".join(self.EXTRACTED_TITLE).strip()
        processed_title = max([(text, len(text.split())) for text in processed_title.split(" - ")], key=lambda x: x[1])[0]
        processed_text = "\n".join(self.EXTRACTED_TEXT).strip()

        chunks = chunker.split_text(processed_text)

        for chunk in chunks:
            if chunk_min_size and len(chunks) < chunk_min_size:
                continue

            document = LangchainDocument(page_content=self.cleaner.clean_string(chunk), metadata={"file_id": file_name, "title": processed_title})
            documents.append(document)

        return documents
