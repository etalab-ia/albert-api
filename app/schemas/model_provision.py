from pydantic import Field
from typing import List, Optional, Dict, Any

from app.schemas import BaseModel
from app.schemas.core.configuration import RoutingStrategy
from app.schemas.core.configuration import ModelProvider as ModelClientSchema, Model as ModelRouterSchema
from app.schemas.models import ModelType

URL_PATTERN = r"https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)"

class AddModelRequest(BaseModel):
    router_name: str = Field(min_length=1, description="ID of the ModelRouter to add the ModelClient to.")
    model: ModelClientSchema = Field(description="Model to add.")

    # Optional fields
    model_type: Optional[ModelType] = Field(default=None, description="Model type. Required when creating a new ModelRouter.")
    aliases: Optional[List[str]] = Field(default=[], description="Aliases, to add for existing router, to set for new instance.")
    routing_strategy: Optional[RoutingStrategy] = Field(default=RoutingStrategy.ROUND_ROBIN, description="Routing Strategy when creating a new router.")
    owner: Optional[str] = Field(default=None, description="ModelRouter owner when creating a new one.")

    additional_field: Optional[Dict[str, Any]] = Field(default=None, description="Additional or specific data")


class DeleteModelRequest(BaseModel):
    router_name: str = Field(min_length=1, description="ID of the ModelRouter to delete the ModelClient from.")
    url: str = Field(pattern=URL_PATTERN, description="URL of the model API.")
    model_name: str = Field(min_length=1, description="Name of the model to delete.")


class AddAliasesRequest(BaseModel):
    router_name: str = Field(min_length=1, description="ID of the targeted ModelRouter.")
    aliases: List[str] = Field(default=[], description="Aliases to add.")


class DeleteAliasesRequest(BaseModel):
    router_name: str = Field(min_length=1, description="ID of the targeted ModelRouter.")
    aliases: List[str] = Field(default=[], description="Aliases to delete.")


class RoutersResponse(BaseModel):
    routers: List[ModelRouterSchema] = Field(description="Currently existing ModelRouters.")
