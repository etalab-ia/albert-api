from openai.types import Completion
from pydantic import BaseModel, Field
from typing import Dict, Iterable, List, Optional, Union


class CompletionRequest(BaseModel):
    prompt: Union[str, List[str], Iterable[int], Iterable[Iterable[int]]]
    model: str
    best_of: Optional[int] = None
    echo: Optional[bool] = False
    frequency_penalty: Optional[float] = 0.0
    logit_bias: Optional[Dict[str, float]] = None
    logprobs: Optional[int] = None
    max_tokens: Optional[int] = 16
    n: Optional[int] = 1
    presence_penalty: Optional[float] = 0.0
    seed: Optional[int] = None
    stop: Optional[Union[str, List[str]]] = Field(default_factory=list)
    stream: Optional[bool] = False
    suffix: Optional[str] = None
    temperature: Optional[float] = 1.0
    top_p: Optional[float] = 1.0
    user: Optional[str] = None


class Completions(Completion):
    pass
