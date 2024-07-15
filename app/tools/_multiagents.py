from typing import List, Optional
from fastapi import HTTPException
from utils.lifespan import clients
from app.tools.multiagent.tools import go_pipeline
import redis


class MultiAgents:
    """
    MultiAgents, multiple agents for RAG: Recursive Document Retrival & Web Search.

    Args:
        embeddings_model (str): OpenAI embeddings model
        collection (List[Optional[str]]): Collection names. Defaults to "user" parameter.
        file_ids (Optional[List[str]], optional): List of file ids for user collections (after upload files). Defaults to None.
        k (int, optional): Top K per collection (max: 6). Defaults to 4.
        prompt_template (Optional[str], optional): Prompt template. Defaults to DEFAULT_PROMPT_TEMPLATE.
    """

    DEFAULT_PROMPT_TEMPLATE = "Réponds à la question suivante en te basant sur les documents ci-dessous : %(prompt)s\n\nDocuments :\n\n%(docs)s"
    MAX_K = 6

    def __init__(self, clients: dict, user: str):
        self.user = user
        self.clients = clients

    async def get_rag_prompt(
        self,
        embeddings_model: str,
        collections: List[Optional[str]],
        file_ids: Optional[List[str]] = None,
        k: Optional[int] = 4,
        prompt_template: Optional[str] = DEFAULT_PROMPT_TEMPLATE,
        **request,
    ) -> str:
        chat_id = request.get("chat_id")

        if k > self.MAX_K:
            raise HTTPException(
                status_code=400, detail=f"K must be less than or equal to {self.MAX_K}"
            )

        try:
            model_url = str(self.clients["openai"][embeddings_model].base_url)
            model_url = model_url.replace("/v1/", "/tei/")
        except KeyError:
            raise HTTPException(status_code=404, detail="Model not found.")

        prompt = request["messages"][-1]["content"]

        if self.user:
            if chat_id:
                try:
                    chat_history = clients["chathistory"].get_chat_history(user_id=request["user"], chat_id=chat_id)  # fmt: off
                    if "messages" in chat_history.keys():  # to avoid empty chat history
                        request["messages"] = chat_history["messages"] + request["messages"]
                except redis.exceptions.ResponseError as e:
                    print(f"Redis path error: {str(e)}")
                    request["messages"] = request["messages"]

            else:
                print("No chat_id provided")
        else:
            print("No user provided")

        history = request["messages"] if request["messages"] else list()

        answer, refs = await go_pipeline(
            prompt,
            docs=[],
            refs=[],
            n=0,
            fact=3,
            history=history,
        )

        answer = answer + "\n\n" + refs
        answer = answer.strip()

        return answer
