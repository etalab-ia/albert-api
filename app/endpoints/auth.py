from typing import Optional

from fastapi import APIRouter, Body, Depends, Path, Query, Request, Security
from fastapi.responses import JSONResponse, Response

from app.helpers import Authorization
from app.schemas.auth import (
    LoginRequest,
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
    PermissionType,
)
from app.utils.depends import delete_root_role, delete_root_token, delete_root_user, update_root_role, update_root_user
from app.utils.lifespan import context

router = APIRouter()


@router.post(path="/login")
async def login(request: Request, body: LoginRequest = Body(description="The login request.")) -> User:
    """
    Login to the API.
    """

    user = await context.auth.login(user=body.user, password=body.password)

    return user


@router.post(path="/roles", dependencies=[Security(dependency=Authorization(permissions=[PermissionType.CREATE_ROLE]))])
async def create_role(request: Request, body: RoleRequest = Body(description="The role creation request.")) -> JSONResponse:
    """
    Create a new role.
    """

    await context.auth.create_role(name=body.role, default=body.default, permissions=body.permissions, limits=body.limits)

    return JSONResponse(status_code=201, content={"id": body.role})


@router.delete(path="/roles/{role}", dependencies=[Security(dependency=Authorization(permissions=[PermissionType.DELETE_ROLE])), Depends(dependency=delete_root_role)])  # fmt: off
async def delete_role(request: Request, role: str = Path(description="The id of the role to delete.")) -> Response:
    """
    Delete a role.
    """

    await context.auth.delete_role(name=role)

    return Response(status_code=204)


@router.patch(path="/roles/{role}", dependencies=[Security(dependency=Authorization(permissions=[PermissionType.UPDATE_ROLE])), Depends(dependency=update_root_role)])  # fmt: off
async def update_role(request: Request, role: str = Path(description="The id of the role to update."), body: RoleUpdateRequest = Body(description="The role update request.")) -> Response:  # fmt: off
    """
    Update a role.
    """

    await context.auth.update_role(name=role, new_name=body.role, default=body.default, permissions=body.permissions, limits=body.limits)

    return JSONResponse(status_code=200, content={"id": role})


@router.get(path="/roles/{role}", dependencies=[Security(dependency=Authorization(permissions=[PermissionType.READ_ROLE]))])
async def get_role(request: Request, role: str = Path(description="The id of the role to get.")) -> Role:
    """
    Get a role by id.
    """

    roles = await context.auth.get_roles(name=role)

    return roles[0]


@router.get(path="/roles", dependencies=[Security(dependency=Authorization(permissions=[PermissionType.READ_ROLE]))])
async def get_roles(
    request: Request,
    offset: int = Query(default=0, ge=0, description="The offset of the roles to get."),
    limit: int = Query(default=10, ge=1, le=100, description="The limit of the roles to get."),
) -> Roles:
    """
    Get all roles.
    """
    data = await context.auth.get_roles(offset=offset, limit=limit)

    return Roles(data=data)


@router.post(path="/users", dependencies=[Security(dependency=Authorization(permissions=[PermissionType.CREATE_USER]))])
async def create_user(request: Request, body: UserRequest = Body(description="The user creation request.")) -> JSONResponse:
    """
    Create a new user.
    """

    user = await context.auth.create_user(name=body.user, role=body.role, password=body.password, expires_at=body.expires_at)

    return JSONResponse(status_code=201, content={"id": user})


@router.delete(path="/users/{user:path}", dependencies=[Security(dependency=Authorization(permissions=[PermissionType.DELETE_USER])), Depends(dependency=delete_root_user)])  # fmt: off
async def delete_user(request: Request, user: str = Path(description="The id of the user to delete.")) -> Response:
    """
    Delete a user.
    """
    await context.auth.delete_user(name=user)

    return Response(status_code=204)


@router.patch(path="/users/{user:path}", dependencies=[Security(dependency=Authorization(permissions=[PermissionType.UPDATE_USER])), Depends(dependency=update_root_user)])  # fmt: off
async def update_user(request: Request, user: str = Path(description="The user name of the user to update."), body: UserUpdateRequest = Body(description="The user update request.")) -> Response:  # fmt: off
    """
    Update a user.
    """

    await context.auth.update_user(name=user, new_name=body.user, password=body.password, role=body.role, expires_at=body.expires_at)

    return JSONResponse(status_code=200, content={"id": user})


@router.get(path="/users/{user:path}", dependencies=[Security(dependency=Authorization(permissions=[PermissionType.READ_USER]))])
async def get_user(request: Request, user: str = Path(description="The id of the user to get.")) -> User:
    """
    Get a user by id.
    """

    users = await context.auth.get_users(name=user)

    return users[0]


@router.get(path="/users", dependencies=[Security(dependency=Authorization(permissions=[PermissionType.READ_USER]))])
async def get_users(
    request: Request,
    role: Optional[str] = Query(default=None, description="The id of the role to filter the users by."),
    offset: int = Query(default=0, ge=0, description="The offset of the users to get."),
    limit: int = Query(default=10, ge=1, le=100, description="The limit of the users to get."),
) -> Users:
    """
    Get all users.
    """

    data = await context.auth.get_users(role=role, offset=offset, limit=limit)

    return Users(data=data)


@router.post(path="/tokens", dependencies=[Security(dependency=Authorization(permissions=[PermissionType.CREATE_TOKEN]))])
async def create_token(request: Request, body: TokenRequest = Body(description="The token creation request.")) -> JSONResponse:
    """
    Create a new token.
    """

    token = await context.auth.create_token(name=body.token, user=body.user, expires_at=body.expires_at)

    return JSONResponse(status_code=201, content={"id": token})


@router.delete(path="/tokens/{user:path}/{token:path}", dependencies=[Security(dependency=Authorization(permissions=[PermissionType.DELETE_TOKEN])), Depends(dependency=delete_root_token)])  # fmt: off
async def delete_token(request: Request, user: str = Path(description="The user ID of the user to delete the token for."), token: str = Path(description="The token ID of the token to delete.")) -> Response:  # fmt: off
    """
    Delete a token.
    """

    await context.auth.delete_token(name=token, user=user)

    return Response(status_code=204)


@router.get(path="/tokens/{user:path}/{token:path}", dependencies=[Security(dependency=Authorization(permissions=[PermissionType.READ_TOKEN]))])
async def get_token(request: Request, user: str = Path(description="The user ID of the user to get the token for."), token: str = Path(description="The token ID of the token to get.")) -> Token:  # fmt: off
    """
    Get a token by id.
    """

    tokens = await context.auth.get_tokens(name=token, user=user)

    return tokens[0]


@router.get(path="/tokens/{user}", dependencies=[Security(dependency=Authorization(permissions=[PermissionType.READ_TOKEN]))])
async def get_tokens(
    request: Request,
    user: str = Path(description="The id of the user to filter the tokens by."),
    offset: int = Query(default=0, ge=0, description="The offset of the tokens to get."),
    limit: int = Query(default=10, ge=1, le=100, description="The limit of the tokens to get."),
) -> Tokens:
    """
    Get all tokens of a user.
    """

    data = await context.auth.get_tokens(user=user, offset=offset, limit=limit)

    return Tokens(data=data)
