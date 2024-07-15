import dotenv
import os
import re

from qdrant_client import QdrantClient
from langchain.vectorstores import Qdrant
from langchain_community.embeddings import HuggingFaceEmbeddings

from .generic_rag import remove_french_stopwords

dotenv.load_dotenv(".env")
API_KEY = os.getenv("API_COLLECTIONS")
API_URL = os.getenv("URL_COLLECTIONS")
embedder = HuggingFaceEmbeddings(model_name="BAAI/bge-m3")

# List available collections
client = QdrantClient(url=API_URL, api_key=API_KEY)
colls = client.get_collections()
collection_names = [x["name"] for x in colls.dict()["collections"]]


def remove_duplicates(lst):
    seen = set()
    return [x for x in lst if not (x in seen or seen.add(x))]


def search_db(question, soft_keywords=True, k=10):  # db intstead of collection_names
    if soft_keywords:
        where_document = {}
    else:
        # Keywords retrivial on the question
        where_document = {
            "$or": [{"$contains": x} for x in remove_french_stopwords(question).lower().split(" ")]
        }

    # docs = db.similarity_search_with_score(question.lower(), filter=where_document, k=k)
    # Get all collections
    docs = []
    for coll in collection_names:
        db = Qdrant(client=client, collection_name=coll, embeddings=embedder)
        docs_ = db.similarity_search_with_score(question.lower(), filter=where_document, k=k)
        docs_ = [(*doc, coll) for doc in docs_]
        docs = docs + docs_

    sorted(docs, key=lambda x: x[1], reverse=True)

    # Get only chunk content without added info for the context
    doc_dict = {}
    for doc in docs:
        try:
            title = doc[0].metadata["title"]
            url = doc[0].metadata["url"]
            content = doc[0].page_content.split(" Extrait article : ")[-1]  # Only the good stuff
            # /!\ Some 'chunks' don't have any . or \n -> we ignore them cause they are weird
            if len(content) > 4000:
                continue
            doc_dict[content] = {}
            doc_dict[content]["url"] = url
            doc_dict[content]["title"] = title
        except Exception:
            pass

    docs = list(doc_dict.keys())
    if len(docs) == 0:
        return [], []

    # Construc refs and clean docs
    ref_tmp = []
    docs_tmp = []
    for doc in docs:
        title = doc_dict[doc]["title"]
        url = doc_dict[doc]["url"]
        ref_tmp.append(f"- '{title}'" + f" ({url})")
        docs_tmp.append(f"Extrait '{title}' : {doc}")
    ref_tmp = remove_duplicates(ref_tmp)
    return docs_tmp, ref_tmp


# Web retrieval
from duckduckgo_search import DDGS


# Five first sources
def find_official_sources(query, n=3):
    official_domains = [
        "service-public.fr",
        ".gouv.fr",
        "france-identite.gouv.fr",
        "caf.fr",
        "info-retraite.fr",
        "ameli.fr",
        "education.gouv.fr",
        "elysee.fr",
        "vie-publique.fr",
        "wikipedia.org",
    ]

    with DDGS() as ddgs:
        results = ddgs.text(query, region="fr-fr", safesearch="Off", max_results=10)
   
    results = [
        r for r in results if any(domain in r["href"].lower() for domain in official_domains)
    ][:n]

    return results


## Rag website
from bs4 import BeautifulSoup
import requests
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain.docstore.document import Document


def prep_soup_rag(url, embedder=embedder, rag_url=API_URL, api_key=API_KEY):
    # Get url Soup
    resp = requests.get(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X x.y; rv:10.0) Gecko/20100101 Firefox/10.0"
        },
    )
    text = ""
    for a in BeautifulSoup(resp.text).find("body").find_all([re.compile("^h[1-6]$"), "p"]):
        if str(a.name).startswith("h"):
            text = text + "\n\n" + a.text.strip() + "\n"  # <titre>
        else:
            text = text + a.text.strip() + "\n"  # <text>
    if len(text) < 20:  # If the website is JS, text will be empty
        return 400

    # Split soup
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=3000,
        chunk_overlap=100,
        length_function=len,
        separators=["\n\n", "\n", ". "],
    )

    docs = text_splitter.split_text(text=text)
    docs = [Document(page_content=doc, metadata={"url": url}) for doc in docs]

    # Add to tmp db
    Qdrant.from_documents(
        docs,
        embedding=embedder,
        url=rag_url,
        api_key=api_key,
        prefer_grpc=False,
        collection_name="tmp_collection",
    )
    return 200


def create_web_collection(results):
    for stuff in results:
        print(stuff["href"])
        prep_soup_rag(stuff["href"], embedder=embedder, rag_url=API_URL, api_key=API_KEY)
    return 200


def search_tmp_rag(question):
    db = Qdrant(client=client, collection_name="tmp_collection", embeddings=embedder)
    docs = db.similarity_search_with_score(question, k=5)

    docs_prep = []
    for doc in docs:
        url = f"URL : {doc[0].metadata['url']}\n"
        content = f"Extrait : {doc[0].page_content}\n"
        docs_prep.append(url + content)

    # Delete collection after research
    client.delete_collection("tmp_collection")

    return docs_prep
