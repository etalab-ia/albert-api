from http.client import HTTPException

from fastapi import APIRouter, Request, Response
from starlette.responses import JSONResponse

from app.clients.model import BaseModelClient
from app.schemas.models_providing import AddModelRequest, DeleteModelRequest, AddAliasesRequest, DeleteAliasesRequest, \
    RoutersResponse, ModelRouterSchema, ModelClientSchema
from app.utils.configuration import configuration

from app.utils.variables import (
    ENDPOINT__MODEL_ADD,
    ENDPOINT__MODEL_DELETE,
    ENDPOINT__ALIAS_ADD,
    ENDPOINT__ALIAS_DELETE,
    ENDPOINT__ROUTERS
)

from app.utils.context import global_context

router = APIRouter()


# @router.post(path=ENDPOINT__DOCUMENTS + "/{document:path}", dependencies=[Security(dependency=AccessController())], status_code=201)
@router.post(path=ENDPOINT__MODEL_ADD, status_code=201)
async def add_model(
    request: Request,
    body: AddModelRequest,
) -> Response:

    client_kwargs = body.additional_field if body.additional_field is not None else {}

    redis = global_context.limiter.connection_pool  # not quite clean

    client = BaseModelClient.import_module(type=body.api_type)(
        model_name=body.model.name,
        model_cost_prompt_tokens=body.model.prompt_tokens,
        model_cost_completion_tokens=body.model.completion_tokens,
        model_carbon_footprint_zone=body.model.carbon_footprint_zone,
        model_carbon_footprint_active_params=body.model.carbon_footprint_active_params,
        model_carbon_footprint_total_params=body.model.carbon_footprint_total_params,
        url=body.model.url,
        key=body.model.key,
        timeout=body.model.timeout,
        redis=redis,
        metrics_retention_ms=configuration.settings.metrics_retention_ms,
        **client_kwargs,
    )

    try:
        await global_context.model_registry.add_client(
            body.router_id,
            client,
            model_type=body.model_type,
            aliases=body.aliases,
            routing_strategy=body.routing_strategy,
            owner=body.owner
        )
    except AssertionError as e:
        raise HTTPException(status_code=500, detail=str(e))

    return Response(status_code=201)


@router.delete(path=ENDPOINT__MODEL_DELETE, status_code=204)
async def delete_model(
    request: Request,
    body: DeleteModelRequest,
) -> Response:
    try:
        await global_context.model_registry.delete_client(
            router_id=body.router_id,
            api_url=body.api_url,
            model_name=body.model_name,
        )
    except AssertionError as e:
        raise HTTPException(status_code=500, detail=str(e))

    return Response(status_code=204)


@router.post(path=ENDPOINT__ALIAS_ADD, status_code=201)
async def add_alias(
    request: Request,
    body: AddAliasesRequest,
) -> Response:
    await global_context.model_registry.add_aliases(
        router_id=body.router_id,
        aliases=body.aliases,
    )
    return Response(status_code=201)


@router.delete(path=ENDPOINT__ALIAS_DELETE, status_code=204)
async def delete_alias(
    request: Request,
    body: DeleteAliasesRequest,
) -> Response:
    await global_context.model_registry.delete_aliases(
        router_id=body.router_id,
        aliases=body.aliases,
    )
    return Response(status_code=204)


@router.get(path=ENDPOINT__ROUTERS, status_code=200, response_model=RoutersResponse)
async def get_routers(
    request: Request
) -> JSONResponse:
    # We get client & router "quickly" (before processing data) to avoid
    # weird data and inconsistency due to concurrence.
    routers = await global_context.model_registry.get_router_instances()
    clients = [await r.get_clients() for r in routers]

    router_schemas = []

    for i, r in enumerate(routers):

        if len(clients[i]) == 0:
            # No clients, ModelRouter is about to get deleted
            continue

        client_schemas = []

        for c in clients[i]:
            client_schemas.append(ModelClientSchema(
                name=c.name,
                url=None,
                timeout=c.timeout,
                prompt_tokens=c.cost_prompt_tokens,
                completion_tokens=c.cost_completion_tokens,
                carbon_footprint_zone=c.carbon_footprint_zone,
                carbon_footprint_total_params=c.carbon_footprint_total_params,
                carbon_footprint_active_params=c.carbon_footprint_active_params,
            ))

        router_schemas.append(ModelRouterSchema(
            id=r.name,
            type=r.type,
            owned_by=r.owned_by,
            aliases=r.aliases,
            routing_strategy=r.routing_strategy,
            vector_size=r.vector_size,
            max_context_length=r.max_context_length,
            created=r.created,
            clients=client_schemas
        ))

    return JSONResponse(content=RoutersResponse(routers=router_schemas).model_dump(), status_code=200)
