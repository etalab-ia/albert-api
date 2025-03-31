from typing import Optional

from fastapi import APIRouter, Body, Path, Query, Request, Security
from fastapi.responses import JSONResponse, Response

from app.helpers import Authorization
from app.schemas.auth import (
    PermissionType,
    Role,
    RoleRequest,
    Roles,
    RoleUpdateRequest,
    Token,
    TokenRequest,
    Tokens,
    User,
    UserRequest,
    Users,
    UserUpdateRequest,
)
from app.utils.lifespan import context
from app.utils.variables import ENDPOINT__ROLES, ENDPOINT__TOKENS, ENDPOINT__USERS

router = APIRouter()


@router.post(path=ENDPOINT__ROLES, dependencies=[Security(dependency=Authorization(permissions=[PermissionType.CREATE_ROLE]))])
async def create_role(request: Request, body: RoleRequest = Body(description="The role creation request.")) -> JSONResponse:
    """
    Create a new role.
    """

    role_id = await context.iam.create_role(name=body.name, default=body.default, permissions=body.permissions, limits=body.limits)

    return JSONResponse(status_code=201, content={"id": role_id})


@router.delete(path=ENDPOINT__ROLES + "/{role}", dependencies=[Security(dependency=Authorization(permissions=[PermissionType.DELETE_ROLE]))])
async def delete_role(request: Request, role: int = Path(description="The ID of the role to delete.")) -> Response:
    """
    Delete a role.
    """

    await context.iam.delete_role(role_id=role)

    return Response(status_code=204)


@router.patch(path=ENDPOINT__ROLES + "/{role:path}", dependencies=[Security(dependency=Authorization(permissions=[PermissionType.UPDATE_ROLE]))])
async def update_role(request: Request, role: int = Path(description="The ID of the role to update."), body: RoleUpdateRequest = Body(description="The role update request.")) -> Response:  # fmt: off
    """
    Update a role.
    """

    await context.iam.update_role(role_id=role, name=body.name, default=body.default, permissions=body.permissions, limits=body.limits)

    return Response(status_code=204)


@router.get(path=ENDPOINT__ROLES + "/me", dependencies=[Security(dependency=Authorization())])
async def get_current_role(request: Request) -> Role:
    """
    Get the current role.
    """

    roles = await context.iam.get_roles(role_id=request.app.state.user.role)

    return roles[0]


@router.get(path=ENDPOINT__ROLES + "/{role:path}", dependencies=[Security(dependency=Authorization(permissions=[PermissionType.READ_ROLE]))])
async def get_role(request: Request, role: int = Path(description="The ID of the role to get.")) -> Role:
    """
    Get a role by id.
    """

    roles = await context.iam.get_roles(role_id=role)

    return roles[0]


@router.get(path=ENDPOINT__ROLES, dependencies=[Security(dependency=Authorization(permissions=[PermissionType.READ_ROLE]))])
async def get_roles(
    request: Request,
    offset: int = Query(default=0, ge=0, description="The offset of the roles to get."),
    limit: int = Query(default=10, ge=1, le=100, description="The limit of the roles to get."),
) -> Roles:
    """
    Get all roles.
    """
    data = await context.iam.get_roles(offset=offset, limit=limit)

    return Roles(data=data)


@router.post(path=ENDPOINT__USERS, dependencies=[Security(dependency=Authorization(permissions=[PermissionType.CREATE_USER]))])
async def create_user(request: Request, body: UserRequest = Body(description="The user creation request.")) -> JSONResponse:
    """
    Create a new user.
    """

    user_id = await context.iam.create_user(name=body.name, role_id=body.role, expires_at=body.expires_at)

    return JSONResponse(status_code=201, content={"id": user_id})


@router.delete(path=ENDPOINT__USERS + "/{user:path}", dependencies=[Security(dependency=Authorization(permissions=[PermissionType.DELETE_USER]))])
async def delete_user(request: Request, user: int = Path(description="The ID of the user to delete.")) -> Response:
    """
    Delete a user.
    """
    await context.iam.delete_user(user_id=user)

    return Response(status_code=204)


@router.patch(path=ENDPOINT__USERS + "/{user:path}", dependencies=[Security(dependency=Authorization(permissions=[PermissionType.UPDATE_USER]))])
async def update_user(request: Request, user: int = Path(description="The ID of the user to update."), body: UserUpdateRequest = Body(description="The user update request.")) -> Response:  # fmt: off
    """
    Update a user.
    """

    await context.iam.update_user(user_id=user, name=body.name, role_id=body.role, expires_at=body.expires_at)

    return Response(status_code=204)


@router.get(path=ENDPOINT__USERS + "/me", dependencies=[Security(dependency=Authorization())])
async def get_current_user(request: Request) -> User:
    """
    Get the current user.
    """

    users = await context.iam.get_users(user_id=request.app.state.user.id)

    return users[0]


@router.get(path=ENDPOINT__USERS + "/{user:path}", dependencies=[Security(dependency=Authorization(permissions=[PermissionType.READ_USER]))])
async def get_user(request: Request, user: int = Path(description="The ID of the user to get.")) -> User:
    """
    Get a user by id.
    """

    users = await context.iam.get_users(user_id=user)

    return users[0]


@router.get(path=ENDPOINT__USERS, dependencies=[Security(dependency=Authorization(permissions=[PermissionType.READ_USER]))])
async def get_users(
    request: Request,
    role: Optional[int] = Query(default=None, description="The ID of the role to filter the users by."),
    offset: int = Query(default=0, ge=0, description="The offset of the users to get."),
    limit: int = Query(default=10, ge=1, le=100, description="The limit of the users to get."),
) -> Users:
    """
    Get all users.
    """

    data = await context.iam.get_users(role_id=role, offset=offset, limit=limit)

    return Users(data=data)


@router.post(path=ENDPOINT__TOKENS, dependencies=[Security(dependency=Authorization())])
async def create_token(request: Request, body: TokenRequest = Body(description="The token creation request.")) -> JSONResponse:
    """
    Create a new token.
    """

    user_id = body.user if body.user else request.app.state.user.id
    token_id, token = await context.iam.create_token(user_id=user_id, name=body.name, expires_at=body.expires_at)

    return JSONResponse(status_code=201, content={"id": token_id, "token": token})


@router.delete(path=ENDPOINT__TOKENS + "/{token:path}", dependencies=[Security(dependency=Authorization())])
async def delete_token(request: Request, token: int = Path(description="The token ID of the token to delete.")) -> Response:
    """
    Delete a token.
    """

    await context.iam.delete_token(user_id=request.app.state.user.id, token_id=token)

    return Response(status_code=204)


@router.get(path=ENDPOINT__TOKENS + "/{token:path}", dependencies=[Security(dependency=Authorization())])
async def get_token(request: Request, token: int = Path(description="The token ID of the token to get.")) -> Token:
    """
    Get your token by id.
    """

    tokens = await context.iam.get_tokens(user_id=request.app.state.user.id, token_id=token)

    return tokens[0]


@router.get(path=ENDPOINT__TOKENS, dependencies=[Security(dependency=Authorization())])
async def get_tokens(
    request: Request,
    offset: int = Query(default=0, ge=0, description="The offset of the tokens to get."),
    limit: int = Query(default=10, ge=1, le=100, description="The limit of the tokens to get."),
) -> Tokens:
    """
    Get all your tokens.
    """

    data = await context.iam.get_tokens(user_id=request.app.state.user.id, offset=offset, limit=limit)

    return Tokens(data=data)
