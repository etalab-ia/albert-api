from typing import Dict, Iterable, List, Optional, Union

from openai.types import Completion
from pydantic import BaseModel, Field, model_validator

from app.utils.lifespan import clients
from app.utils.variables import LANGUAGE_MODEL_TYPE
from app.utils.exceptions import WrongModelTypeException, ContextLengthExceededException, MaxTokensExceededException


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

    @model_validator(mode="before")
    def validate_model(cls, value):
        if clients.models[value["model"]].type != LANGUAGE_MODEL_TYPE:
            raise WrongModelTypeException()

        if not clients.models[value["model"]].check_context_length(messages=value["messages"]):
            raise ContextLengthExceededException()

        if value["max_tokens"] is not None and value["max_tokens"] > clients.models[value["model"]].max_context_length:
            raise MaxTokensExceededException()


class Completions(Completion):
    pass
