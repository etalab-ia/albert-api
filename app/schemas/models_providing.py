from pydantic import Field
from typing import List, Optional, Dict, Any

from app.schemas import BaseModel
from app.schemas.core.configuration import RoutingStrategy, ModelProviderType, CountryCodes
from app.schemas.models import ModelType, ModelCosts


URL_PATTERN = r"https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)"

# TODO refacto: ModelCost and ModelClientCarbonFootprint were deleted, and several field names changed.
class ModelClientSchema(BaseModel):
    name: str = Field(min_length=1, description="Name of the model.")
    url: str | None = Field(pattern=URL_PATTERN, description="URL to the model API.")
    key: Optional[str] = Field(default=None, description="Key to access the API.")
    timeout: int = Field(default=10, description="Duration before connection is considered timed out, in seconds")

    # Model costs
    prompt_tokens: float = Field(default=0.0, ge=0.0,
                                 description="Cost of a million prompt tokens (decrease user budget)")
    completion_tokens: float = Field(default=0.0, ge=0.0,
                                     description="Cost of a million completion tokens (decrease user budget)")

    # Carbon Footprint
    carbon_footprint_zone: CountryCodes = Field(default=CountryCodes.WOR,
                                                description="Country code of the location of the model (ISO 3166-1 alpha-3 format)")
    carbon_footprint_active_params: Optional[int] = Field(default=None, description="Active parameters, for carbon footprint calculation")
    carbon_footprint_total_params: Optional[int] = Field(default=None, description="Total parameters, for carbon footprint calculation")


class AddModelRequest(BaseModel):
    router_id: str = Field(min_length=1, description="ID of the ModelRouter to add the ModelClient to.")
    api_type: ModelProviderType = Field(description="Type of API used.")
    model: ModelClientSchema = Field(description="Model to add.")

    # Optional fields
    model_type: Optional[ModelType] = Field(default=None, description="Model type. Required when creating a new ModelRouter.")
    aliases: Optional[List[str]] = Field(default=[], description="Aliases, to add for existing router, to set for new instance.")
    routing_strategy: Optional[RoutingStrategy] = Field(default=RoutingStrategy.ROUND_ROBIN, description="Routing Strategy when creating a new router.")
    owner: Optional[str] = Field(default="Albert API", description="ModelRouter owner when creating a new one.")

    additional_field: Optional[Dict[str, Any]] = Field(default=None, description="Additional or specific data")


class DeleteModelRequest(BaseModel):
    router_id: str = Field(min_length=1, description="ID of the ModelRouter to delete the ModelClient from.")
    api_url: str = Field(pattern=URL_PATTERN, description="URL of the model API.")
    model_name: str = Field(min_length=1, description="Name of the model to delete.")


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
    max_context_length: int | None = Field(description="Greatest amount of token a context can have.")
    created: int = Field("Time when the Router was created (Unix time).")
    clients: List[ModelClientSchema] = Field(description="Router's ModelClients.")


class RoutersResponse(BaseModel):
    routers: List[ModelRouterSchema] = Field(description="Currently existing ModelRouters.")
