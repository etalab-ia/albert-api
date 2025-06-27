from typing import Literal, Optional

from fastapi import APIRouter, Body, Path, Query, Request, Security
from fastapi.responses import JSONResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.helpers._accesscontroller import AccessController
from app.schemas.auth import (
    PermissionType,
    Role,
    RoleRequest,
    Roles,
    RolesResponse,
    RoleUpdateRequest,
    Token,
    TokenRequest,
    Tokens,
    TokensResponse,
    User,
    UserRequest,
    Users,
    UsersResponse,
    UserUpdateRequest,
)
from app.utils.depends import get_db_session
from app.utils.context import global_context, request_context
from app.utils.settings import settings
from app.utils.variables import ENDPOINT__ROLES, ENDPOINT__ROLES_ME, ENDPOINT__TOKENS, ENDPOINT__USERS, ENDPOINT__USERS_ME

router = APIRouter()


@router.post(
    path=ENDPOINT__ROLES,
    dependencies=[Security(dependency=AccessController(permissions=[PermissionType.CREATE_ROLE]))],
    include_in_schema=settings.general.log_level == "DEBUG",
    status_code=201,
    response_model=RolesResponse,
)
async def create_role(
    request: Request,
    body: RoleRequest = Body(description="The role creation request."),
    session: AsyncSession = get_db_session(),
) -> JSONResponse:
    """
    Create a new role.
    """

    role_id = await global_context.iam.create_role(session=session, name=body.name, permissions=body.permissions, limits=body.limits)

    return JSONResponse(status_code=201, content={"id": role_id})


@router.delete(
    path=ENDPOINT__ROLES + "/{role}",
    dependencies=[Security(dependency=AccessController(permissions=[PermissionType.DELETE_ROLE]))],
    include_in_schema=settings.general.log_level == "DEBUG",
    status_code=204,
)
async def delete_role(
    request: Request,
    role: int = Path(description="The ID of the role to delete."),
    session: AsyncSession = get_db_session(),
) -> Response:
    """
    Delete a role.
    """

    await global_context.iam.delete_role(session=session, role_id=role)

    return Response(status_code=204)


@router.patch(
    path=ENDPOINT__ROLES + "/{role:path}",
    dependencies=[Security(dependency=AccessController(permissions=[PermissionType.UPDATE_ROLE]))],
    include_in_schema=settings.general.log_level == "DEBUG",
    status_code=204,
)
async def update_role(
    request: Request,
    role: int = Path(description="The ID of the role to update."),
    body: RoleUpdateRequest = Body(description="The role update request."),
    session: AsyncSession = get_db_session(),
) -> Response:
    """
    Update a role.
    """

    await global_context.iam.update_role(
        session=session,
        role_id=role,
        name=body.name,
        permissions=body.permissions,
        limits=body.limits,
    )

    return Response(status_code=204)


@router.get(
    path=ENDPOINT__ROLES_ME,
    dependencies=[Security(dependency=AccessController())],
    include_in_schema=settings.general.log_level == "DEBUG",
    status_code=200,
    response_model=Role,
)
async def get_current_role(request: Request, session: AsyncSession = get_db_session()) -> JSONResponse:
    """
    Get the current role.
    """

    roles = await global_context.iam.get_roles(session=session, role_id=request_context.get().role_id)

    return JSONResponse(content=roles[0].model_dump(), status_code=200)


@router.get(
    path=ENDPOINT__ROLES + "/{role:path}",
    dependencies=[Security(dependency=AccessController(permissions=[PermissionType.READ_ROLE]))],
    include_in_schema=settings.general.log_level == "DEBUG",
    status_code=200,
    response_model=Role,
)
async def get_role(
    request: Request,
    role: int = Path(description="The ID of the role to get."),
    session: AsyncSession = get_db_session(),
) -> JSONResponse:
    """
    Get a role by id.
    """

    roles = await global_context.iam.get_roles(session=session, role_id=role)

    return JSONResponse(content=roles[0].model_dump(), status_code=200)


@router.get(
    path=ENDPOINT__ROLES,
    dependencies=[Security(dependency=AccessController(permissions=[PermissionType.READ_ROLE]))],
    include_in_schema=settings.general.log_level == "DEBUG",
    status_code=200,
    response_model=Roles,
)
async def get_roles(
    request: Request,
    offset: int = Query(default=0, ge=0, description="The offset of the roles to get."),
    limit: int = Query(default=10, ge=1, le=100, description="The limit of the roles to get."),
    order_by: Literal["id", "name", "created_at", "updated_at"] = Query(default="id", description="The field to order the roles by."),
    order_direction: Literal["asc", "desc"] = Query(default="asc", description="The direction to order the roles by."),
    session: AsyncSession = get_db_session(),
) -> JSONResponse:
    """
    Get all roles.
    """
    data = await global_context.iam.get_roles(session=session, offset=offset, limit=limit, order_by=order_by, order_direction=order_direction)

    return JSONResponse(content=Roles(data=data).model_dump(), status_code=200)


@router.post(
    path=ENDPOINT__USERS,
    dependencies=[Security(dependency=AccessController(permissions=[PermissionType.CREATE_USER]))],
    include_in_schema=settings.general.log_level == "DEBUG",
    status_code=201,
    response_model=UsersResponse,
)
async def create_user(
    request: Request,
    body: UserRequest = Body(description="The user creation request."),
    session: AsyncSession = get_db_session(),
) -> JSONResponse:
    """
    Create a new user.
    """

    user_id = await global_context.iam.create_user(session=session, name=body.name, role_id=body.role, budget=body.budget, expires_at=body.expires_at)  # fmt: off

    return JSONResponse(status_code=201, content={"id": user_id})


@router.delete(
    path=ENDPOINT__USERS + "/{user:path}",
    dependencies=[Security(dependency=AccessController(permissions=[PermissionType.DELETE_USER]))],
    include_in_schema=settings.general.log_level == "DEBUG",
    status_code=204,
)
async def delete_user(
    request: Request,
    user: int = Path(description="The ID of the user to delete."),
    session: AsyncSession = get_db_session(),
) -> Response:
    """
    Delete a user.
    """
    await global_context.iam.delete_user(session=session, user_id=user)

    return Response(status_code=204)


@router.patch(
    path=ENDPOINT__USERS + "/{user:path}",
    dependencies=[Security(dependency=AccessController(permissions=[PermissionType.UPDATE_USER]))],
    include_in_schema=settings.general.log_level == "DEBUG",
    status_code=204,
)
async def update_user(
    request: Request,
    user: int = Path(description="The ID of the user to update."),
    body: UserUpdateRequest = Body(description="The user update request."),
    session: AsyncSession = get_db_session(),
) -> Response:
    """
    Update a user.
    """
    await global_context.iam.update_user(
        session=session,
        user_id=user,
        name=body.name,
        role_id=body.role,
        budget=body.budget,
        expires_at=body.expires_at,
    )

    return Response(status_code=204)


@router.get(
    path=ENDPOINT__USERS_ME,
    dependencies=[Security(dependency=AccessController())],
    include_in_schema=settings.general.log_level == "DEBUG",
    status_code=200,
    response_model=User,
)
async def get_current_user(request: Request, session: AsyncSession = get_db_session()) -> JSONResponse:
    """
    Get the current user.
    """

    users = await global_context.iam.get_users(session=session, user_id=request_context.get().user_id)

    return JSONResponse(content=users[0].model_dump(), status_code=200)


@router.get(
    path=ENDPOINT__USERS + "/{user:path}",
    dependencies=[Security(dependency=AccessController(permissions=[PermissionType.READ_USER]))],
    include_in_schema=settings.general.log_level == "DEBUG",
    status_code=200,
)
async def get_user(
    request: Request, user: int = Path(description="The ID of the user to get."), session: AsyncSession = get_db_session()
) -> JSONResponse:
    """
    Get a user by id.
    """

    users = await global_context.iam.get_users(session=session, user_id=user)

    return JSONResponse(content=users[0].model_dump(), status_code=200)


@router.get(
    path=ENDPOINT__USERS,
    dependencies=[Security(dependency=AccessController(permissions=[PermissionType.READ_USER]))],
    include_in_schema=settings.general.log_level == "DEBUG",
    status_code=200,
)
async def get_users(
    request: Request,
    role: Optional[int] = Query(default=None, description="The ID of the role to filter the users by."),
    offset: int = Query(default=0, ge=0, description="The offset of the users to get."),
    limit: int = Query(default=10, ge=1, le=100, description="The limit of the users to get."),
    order_by: Literal["id", "name", "created_at", "updated_at"] = Query(default="id", description="The field to order the users by."),
    order_direction: Literal["asc", "desc"] = Query(default="asc", description="The direction to order the users by."),
    session: AsyncSession = get_db_session(),
) -> JSONResponse:
    """
    Get all users.
    """

    data = await global_context.iam.get_users(
        session=session, role_id=role, offset=offset, limit=limit, order_by=order_by, order_direction=order_direction
    )

    return JSONResponse(content=Users(data=data).model_dump(), status_code=200)


@router.post(path=ENDPOINT__TOKENS, dependencies=[Security(dependency=AccessController())], status_code=201, response_model=TokensResponse)
async def create_token(
    request: Request,
    body: TokenRequest = Body(description="The token creation request."),
    session: AsyncSession = get_db_session(),
) -> JSONResponse:
    """
    Create a new token.
    """

    user_id = body.user if body.user else request_context.get().user_id
    token_id, token = await global_context.iam.create_token(session=session, user_id=user_id, name=body.name, expires_at=body.expires_at)

    return JSONResponse(status_code=201, content={"id": token_id, "token": token})


@router.delete(path=ENDPOINT__TOKENS + "/{token:path}", dependencies=[Security(dependency=AccessController())], status_code=204)
async def delete_token(
    request: Request,
    token: int = Path(description="The token ID of the token to delete."),
    session: AsyncSession = get_db_session(),
) -> Response:
    """
    Delete a token.
    """

    await global_context.iam.delete_token(session=session, user_id=request_context.get().user_id, token_id=token)

    return Response(status_code=204)


@router.get(path=ENDPOINT__TOKENS + "/{token:path}", dependencies=[Security(dependency=AccessController())], status_code=200, response_model=Token)
async def get_token(
    request: Request,
    token: int = Path(description="The token ID of the token to get."),
    session: AsyncSession = get_db_session(),
) -> JSONResponse:
    """
    Get your token by id.
    """

    tokens = await global_context.iam.get_tokens(session=session, user_id=request_context.get().user_id, token_id=token)

    return JSONResponse(content=tokens[0].model_dump(), status_code=200)


@router.get(path=ENDPOINT__TOKENS, dependencies=[Security(dependency=AccessController())], status_code=200, response_model=Tokens)
async def get_tokens(
    request: Request,
    offset: int = Query(default=0, ge=0, description="The offset of the tokens to get."),
    limit: int = Query(default=10, ge=1, le=100, description="The limit of the tokens to get."),
    order_by: Literal["id", "name", "created_at"] = Query(default="id", description="The field to order the tokens by."),
    order_direction: Literal["asc", "desc"] = Query(default="asc", description="The direction to order the tokens by."),
    session: AsyncSession = get_db_session(),
) -> JSONResponse:
    """
    Get all your tokens.
    """

    data = await global_context.iam.get_tokens(
        session=session,
        user_id=request_context.get().user_id,
        offset=offset,
        limit=limit,
        order_by=order_by,
        order_direction=order_direction,
    )

    return JSONResponse(content=Tokens(data=data).model_dump(), status_code=200)
