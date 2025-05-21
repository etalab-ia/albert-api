import logging

import tiktoken

from app.schemas.core.settings import LimitsTokenizer
from app.utils.variables import ENDPOINT__CHAT_COMPLETIONS, ENDPOINT__EMBEDDINGS, ENDPOINT__OCR, ENDPOINT__RERANK, ENDPOINT__SEARCH

logger = logging.getLogger(__name__)


class UsageTokenizer:
    USAGE_COMPLETION_ENDPOINTS = {
        ENDPOINT__CHAT_COMPLETIONS: True,
        ENDPOINT__EMBEDDINGS: False,
        ENDPOINT__OCR: False,
        ENDPOINT__RERANK: False,
        ENDPOINT__SEARCH: False,
    }

    def __init__(self, tokenizer: LimitsTokenizer):
        if tokenizer == LimitsTokenizer.TIKTOKEN_O200K_BASE:
            self.tokenizer = tiktoken.get_encoding("o200k_base")
        elif tokenizer == LimitsTokenizer.TIKTOKEN_P50K_BASE:
            self.tokenizer = tiktoken.get_encoding("p50k_base")
        elif tokenizer == LimitsTokenizer.TIKTOKEN_R50K_BASE:
            self.tokenizer = tiktoken.get_encoding("r50k_base")
        elif tokenizer == LimitsTokenizer.TIKTOKEN_P50K_EDIT:
            self.tokenizer = tiktoken.get_encoding("p50k_edit")
        elif tokenizer == LimitsTokenizer.TIKTOKEN_CL100K_BASE:
            self.tokenizer = tiktoken.get_encoding("cl100k_base")
        elif tokenizer == LimitsTokenizer.TIKTOKEN_GPT2:
            self.tokenizer = tiktoken.get_encoding("gpt2")

    def get_prompt_tokens(self, endpoint: str, body: dict) -> int:
        prompt_tokens = 0

        if endpoint == ENDPOINT__CHAT_COMPLETIONS:
            contents = [message.get("content") for message in body.get("messages", []) if message.get("content")]
            prompt_tokens = sum([len(self.tokenizer.encode(content)) for content in contents])

        elif endpoint == ENDPOINT__EMBEDDINGS:
            prompt_tokens = sum([len(self.tokenizer.encode(str(input))) for input in body.get("input", [])])

        elif endpoint == ENDPOINT__RERANK:
            prompt_tokens = sum([len(self.tokenizer.encode(str(input))) for input in body.get("input", [])])

        elif endpoint == ENDPOINT__SEARCH:
            prompt_tokens = len(self.tokenizer.encode(str(body.get("prompt", ""))))

        elif endpoint == ENDPOINT__OCR:
            prompt_tokens = len(self.tokenizer.encode(str(body.get("prompt", ""))))

        else:
            raise ValueError(f"Endpoint {endpoint} not supported")

        return prompt_tokens

    def get_completion_tokens(self, endpoint: str, response: dict, stream: bool = False) -> int:
        """
        Get the completion tokens for the given endpoint and body.

        Args:
            endpoint (str): The endpoint to get the completion tokens for.
            response (dict): The response of the request. For stream requests, the response must be a dict with the keys being the index of the choice and the values being the content of the choice (concatenated each chunk content).
            stream (bool): Whether the request is a stream.
        """
        completion_tokens = 0

        if endpoint == ENDPOINT__CHAT_COMPLETIONS:
            if stream:
                completion_tokens = sum([len(self.tokenizer.encode(response[index])) for index in response.keys()])
            else:
                contents = [choice.get("message", {}).get("content", "") for choice in response.get("choices", [])]
                completion_tokens = sum([len(self.tokenizer.encode(content)) for content in contents])
        else:
            raise ValueError(f"Endpoint {endpoint} not supported")

        return completion_tokens
