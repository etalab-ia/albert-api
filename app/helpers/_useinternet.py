import json
from app.helpers import UniversalParser
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS
from langchain.schema import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
import re
import requests
from typing import List, Optional


class UseInternet:
    LIMITED_DOMAINS = None
    USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X x.y; rv:10.0) Gecko/20100101 Firefox/10.0"
    PAGE_LOAD_TIMEOUT = 60
    parser = UniversalParser()

    def search_internet(self, query: str, n: int = 3) -> List[Document]:
        documents = self.search_on_web(query, limited_domains=self.LIMITED_DOMAINS, n=n)

        # Split documents into chunks
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=3000,
            chunk_overlap=100,
            length_function=len,
            separators=["\n\n", "\n", ". "],
        )

        split_docs = text_splitter.split_documents(documents)

        return split_docs

    def search_on_web(self, query: str, limited_domains: Optional[List] = None, n: int = 3) -> List:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, region="fr-fr", safesearch="Off", max_results=n))

        filtered_results = []
        for result in results:
            url = result["href"].lower()

            if limited_domains and not any([domain in url for domain in limited_domains]):
                continue

            html_content = self.fetch_webpage(url)
            soup = BeautifulSoup(html_content, "html.parser")
         
            docs = self.parser._html_to_chunks(
                html=soup,
                chunk_size=100,
                chunk_overlap=20,
                chunk_min_size=50
            )
            for doc in docs:
                doc.metadata["url"] = url

                if len(doc.page_content) < 20:
                    continue
                
                filtered_results.append(doc)

        return filtered_results

    def fetch_webpage(self, url: str) -> str:
        response = requests.get(url, headers={"User-Agent": self.USER_AGENT})
        return response.text

    # Remove multiple new lines, spaces and backslashes
    def clean_text(self, text: str) -> str:
        text = re.sub(r"\n{2,}", "\n", text)
        text = re.sub(r"\s{2,}", " ", text)
        text = re.sub(r"\\", "", text)
        text = text.strip()
        return text