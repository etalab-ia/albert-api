from fastapi import APIRouter, Request, Response
from starlette.responses import JSONResponse

from app.schemas.models_providing import AddModelRequest, DeleteModelRequest, AddAliasesRequest, DeleteAliasesRequest, \
    RoutersResponse, ModelRouterSchema, ModelClientSchema

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
    return Response(status_code=201)


@router.delete(path=ENDPOINT__MODEL_DELETE, status_code=204)
async def delete_model(
    request: Request,
    body: DeleteModelRequest,
) -> Response:
    return Response(status_code=204)


@router.post(path=ENDPOINT__ALIAS_ADD, status_code=201)
async def add_alias(
    request: Request,
    body: AddAliasesRequest,
) -> Response:
    return Response(status_code=204)


@router.delete(path=ENDPOINT__ALIAS_DELETE, status_code=204)
async def delete_alias(
    request: Request,
    body: DeleteAliasesRequest,
) -> Response:
    return Response(status_code=204)


@router.get(path=ENDPOINT__ROUTERS, status_code=200, response_model=RoutersResponse)
async def get_routers(
    request: Request
) -> JSONResponse:
    # We get client & router "quickly" (before processing data) to avoid
    # weird data and inconsistency due to concurrence.
    routers = await global_context.models.get_router_instances()
    clients = [await r.get_clients() for r in routers]

    router_schemas = []

    for i, r in enumerate(routers):

        if len(clients[i]) == 0:
            # No clients, ModelRouter is about to get deleted
            continue

        client_schemas = []
        print(clients)

        for c in clients[i]:
            print(c)
            client_schemas.append(ModelClientSchema(
                model=c.model,
                api_url=None,
                timeout=c.timeout,
                costs=c.costs,
                carbon_footprint=c.carbon
            ))

        router_schemas.append(ModelRouterSchema(
            id=r.id,
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
