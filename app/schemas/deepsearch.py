from typing import List, Union

from pydantic import BaseModel, Field

from app.schemas.usage import Usage


class DeepSearchRequest(BaseModel):
    prompt: str = Field(description="Question or query for the deep search")
    model: str = Field(description="ID of the model to use for DeepSearch")
    k: int = Field(default=5, ge=1, le=10, description="Number of results per search query")
    iteration_limit: int = Field(default=2, ge=1, le=5, description="Maximum number of search iterations")
    num_queries: int = Field(default=2, ge=1, le=5, description="Number of queries to generate per iteration")
    lang: str = Field(default="fr", description="Language for the search (fr or en)")
    limited_domains: Union[bool, List[str]] = Field(default=True, description="Allowed domains handling: True = use default config, False = all domains allowed, [list] = custom domains")  # fmt: off


class DeepSearchMetadata(BaseModel):
    total_input_tokens: int = Field(description="Total input tokens used")
    total_output_tokens: int = Field(description="Total output tokens used")
    elapsed_time: float = Field(description="Total elapsed time in seconds")
    iterations: int = Field(description="Number of iterations performed")
    total_queries: int = Field(description="Total number of queries generated")
    sources_found: int = Field(description="Number of sources found")
    model_used: str = Field(description="Model used for the search")


class DeepSearchResponse(BaseModel):
    object: str = "deepsearch_result"
    prompt: str = Field(description="Original request")
    response: str = Field(description="Generated response based on the sources found")
    sources: List[str] = Field(description="List of source URLs")
    metadata: DeepSearchMetadata = Field(description="Metadata about the search process")
    usage: Usage = Field(description="Usage information for the request")
