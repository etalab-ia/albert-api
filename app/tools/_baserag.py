from typing import List, Optional

from langchain_community.vectorstores import Qdrant
from langchain_huggingface import HuggingFaceEndpointEmbeddings
from fastapi import HTTPException
from qdrant_client.http import models as rest


class BaseRAG:
    """
Base RAG, basic retrival augmented generation.

Args:
    embeddings_model (str): OpenAI embeddings model
    collection_name (Optional[str], optional): Collection name. Defaults to "user" parameters.
    file_ids (Optional[List[str]], optional): List of file ids. Defaults to None.
    k (int, optional): Top K. Defaults to 4.
    prompt_template (Optional[str], optional): Prompt template. Defaults to DEFAULT_PROMPT_TEMPLATE.
    """

    DEFAULT_PROMPT_TEMPLATE = "Réponds à la question suivante en te basant sur les documents ci-dessous : %(prompt)s\n\nDocuments :\n\n%(docs)s"

    def __init__(self, clients: dict, user: str):
        self.user = user
        self.clients = clients

    def get_rag_prompt(
        self,
        embeddings_model: str,
        #@TODO: add multiple collections support
        collection_name: Optional[str] = None,
        file_ids: Optional[List[str]] = None,
        #@TODO: add max value of k to ensure that the value is not too high
        k: int = 4,
        prompt_template: Optional[str] = DEFAULT_PROMPT_TEMPLATE,
        **request,
    ) -> str:
        collection_name = collection_name or self.user

        try:
            model_url = str(self.clients["openai"][embeddings_model].base_url)
            model_url = model_url.replace("/v1/", "/tei/")
        except KeyError:
            raise HTTPException(status_code=404, detail="Model not found.")

        embeddings = HuggingFaceEndpointEmbeddings(
            model=model_url,
            huggingfacehub_api_token=self.clients["openai"][embeddings_model].api_key,
        )

        vectorstore = Qdrant(
            client=self.clients["vectors"],
            embeddings=embeddings,
            collection_name=collection_name,
        )
        filter = rest.Filter(must=[rest.FieldCondition(key="metadata.file_id", match=rest.MatchAny(any=file_ids))]) if file_ids else None # fmt: off

        prompt = request["messages"][-1]["content"]
        docs = vectorstore.similarity_search(prompt, k=k, filter=filter)
        docs = "\n\n".join([doc.page_content for doc in docs])

        prompt = prompt_template % {"docs": docs, "prompt": prompt}

        return prompt
