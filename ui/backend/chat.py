from typing import List, Tuple

from openai import OpenAI
import requests
import streamlit as st

from ui.settings import settings


def generate_stream(messages: List[dict], params: dict, rag: bool, rerank: bool) -> Tuple[str, List[str]]:
    sources = []
    if rag:
        prompt = messages[-1]["content"]
        k = params["rag"]["k"] * 2 if rerank else params["rag"]["k"]
        data = {"collections": params["rag"]["collections"], "k": k, "prompt": messages[-1]["content"], "score_threshold": None}
        response = requests.post(
            url=f"{settings.playground.api_url}/v1/search", json=data, headers={"Authorization": f"Bearer {st.session_state["user"].api_key}"}
        )
        assert response.status_code == 200, f"{response.status_code} - {response.json()}"

        prompt_template = """Réponds à la question suivante de manière claire en te basant sur les extraits de documents ci-dessous. Si les documents ne sont pas pertinents pour répondre à la question, réponds que tu ne sais pas ou réponds directement la question à l'aide de tes connaissances. Réponds en français.
La question de l'utilisateur est : {prompt}

Les documents sont :

{chunks}
"""
        chunks = [chunk["chunk"] for chunk in response.json()["data"]]

        if rerank:
            data = {
                "prompt": prompt,
                "input": [chunk["content"] for chunk in chunks],
            }
            response = requests.post(
                url=f"{settings.playground.api_url}/v1/rerank", json=data, headers={"Authorization": f"Bearer {st.session_state["user"].api_key}"}
            )
            assert response.status_code == 200, f"{response.status_code} - {response.json()}"

            rerank_scores = sorted(response.json()["data"], key=lambda x: x["score"])
            chunks = [chunks[result["index"]] for result in rerank_scores[: params["rag"]["k"]]]

        sources = list(set([chunk["metadata"]["document_name"] for chunk in chunks]))
        chunks = [chunk["content"] for chunk in chunks]
        prompt = prompt_template.format(prompt=prompt, chunks="\n\n".join(chunks))
        messages = messages[:-1] + [{"role": "user", "content": prompt}]

    client = OpenAI(base_url=f"{settings.playground.api_url}/v1", api_key=st.session_state["user"].api_key)
    stream = client.chat.completions.create(stream=True, messages=messages, **params["sampling_params"])

    return stream, sources
