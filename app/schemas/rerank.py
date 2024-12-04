from typing import List
from pydantic import BaseModel


class RerankRequest(BaseModel):
    # See https://github.com/vllm-project/vllm/blob/main/vllm/entrypoints/openai/protocol.py
    prompt: str
    inputs: List[str]
    model: str
