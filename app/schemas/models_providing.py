from pydantic import Field
from typing import List, Optional, Dict, Any

from app.schemas import BaseModel
from app.schemas.core.models import RoutingStrategy, ModelClientType
from app.schemas.core.settings import ModelClientCarbonFootprint
from app.schemas.models import ModelType, ModelCosts


URL_PATTERN = r"https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)"


class ModelClientSchema(BaseModel):
    name: str = Field(min_length=1, description="Name of the model.")
    api_url: str | None = Field(pattern=URL_PATTERN, description="URL to the model API.")
    api_key: Optional[str] = Field(default=None, description="Key to access the API.")
    timeout: int = Field(default=10, description="Duration before connection is considered timed out, in seconds")
    costs: ModelCosts = Field(description="Model costs.")
    carbon_footprint: ModelClientCarbonFootprint = Field(description="Model carbon footprint.")


class AddModelRequest(BaseModel):
    router_id: str = Field(min_length=1, description="ID of the ModelRouter to add the ModelClient to.")
    api_type: ModelClientType = Field(description="Type of API used.")
    model: ModelClientSchema = Field(description="Model to add.")

    # Optional fields
    model_type: Optional[ModelType] = Field(default=None, description="Model type. Required when creating a new ModelRouter.")
    aliases: Optional[List[str]] = Field(default=[], description="Aliases, to add for existing router, to set for new instance.")
    routing_strategy: Optional[RoutingStrategy] = Field(default=RoutingStrategy.ROUND_ROBIN, description="Routing Strategy when creating a new router.")
    owner: Optional[str] = Field(default="Albert API", description="ModelRouter owner when creating a new one.")

    additional_field: Optional[Dict[str, Any]] = Field(default=None, description="Additional or specific data")

class DeleteModelRequest(BaseModel):
    router_id: str = Field(min_length=1, description="ID of the ModelRouter to add the ModelClient to.")
    api_url: str = Field(pattern=URL_PATTERN, description="URL of the model API.")


class AddAliasesRequest(BaseModel):
    router_id: str = Field(min_length=1, description="ID of the targeted ModelRouter.")
    aliases: List[str] = Field(default=[], description="Aliases to add.")


class DeleteAliasesRequest(BaseModel):
    router_id: str = Field(min_length=1, description="ID of the targeted ModelRouter.")
    aliases: List[str] = Field(default=[], description="Aliases to delete.")


class ModelRouterSchema(BaseModel):
    id: str = Field(description="Model router id.")
    type: ModelType = Field(description="Type of models managed by the router.")
    owned_by: str = Field(description="Name of ModelRouter's owner")
    aliases: List[str] = Field(description="List of id's aliases.")
    routing_strategy: RoutingStrategy = Field(description="Describes how the model router chooses between its ModelClients")
    vector_size: int | None = Field(description="Size of vectors stored.")
    max_context_length: int = Field(description="Greatest amount of token a context can have.")
    created: int = Field("Time when the Router was created (Unix time).")
    clients: List[ModelClientSchema] = Field(description="Router's ModelClients.")


class RoutersResponse(BaseModel):
    routers: List[ModelRouterSchema] = Field(description="Currently existing ModelRouters.")
