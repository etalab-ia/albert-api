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

    user = await context.iam.login(user_name=body.user_name, user_password=body.user_password)

    return user


@router.post(path="/roles", dependencies=[Security(dependency=Authorization(permissions=[PermissionType.CREATE_ROLE]))])
async def create_role(request: Request, body: RoleRequest = Body(description="The role creation request.")) -> JSONResponse:
    """
    Create a new role.
    """

    role_id = await context.iam.create_role(name=body.name, default=body.default, permissions=body.permissions, limits=body.limits)

    return JSONResponse(status_code=201, content={"id": role_id})


@router.delete(path="/roles/{role}", dependencies=[Security(dependency=Authorization(permissions=[PermissionType.DELETE_ROLE])), Depends(dependency=delete_root_role)])  # fmt: off
async def delete_role(request: Request, role: int = Path(description="The ID of the role to delete.")) -> Response:
    """
    Delete a role.
    """

    await context.iam.delete_role(role_id=role)

    return Response(status_code=204)


@router.patch(path="/roles/{role}", dependencies=[Security(dependency=Authorization(permissions=[PermissionType.UPDATE_ROLE])), Depends(dependency=update_root_role)])  # fmt: off
async def update_role(request: Request, role: int = Path(description="The ID of the role to update."), body: RoleUpdateRequest = Body(description="The role update request.")) -> Response:  # fmt: off
    """
    Update a role.
    """

    await context.iam.update_role(role_id=role, name=body.name, default=body.default, permissions=body.permissions, limits=body.limits)

    return Response(status_code=204)


@router.get(path="/roles/{role}", dependencies=[Security(dependency=Authorization(permissions=[PermissionType.READ_ROLE]))])
async def get_role(request: Request, role: int = Path(description="The ID of the role to get.")) -> Role:
    """
    Get a role by id.
    """

    roles = await context.iam.get_roles(role_id=role)

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
    data = await context.iam.get_roles(offset=offset, limit=limit)

    return Roles(data=data)


@router.post(path="/users", dependencies=[Security(dependency=Authorization(permissions=[PermissionType.CREATE_USER]))])
async def create_user(request: Request, body: UserRequest = Body(description="The user creation request.")) -> JSONResponse:
    """
    Create a new user.
    """

    user_id = await context.iam.create_user(name=body.name, role=body.role, password=body.password, expires_at=body.expires_at)

    return JSONResponse(status_code=201, content={"id": user_id})


@router.delete(path="/users/{user:path}", dependencies=[Security(dependency=Authorization(permissions=[PermissionType.DELETE_USER])), Depends(dependency=delete_root_user)])  # fmt: off
async def delete_user(request: Request, user: int = Path(description="The ID of the user to delete.")) -> Response:
    """
    Delete a user.
    """
    await context.iam.delete_user(user_id=user)

    return Response(status_code=204)


@router.patch(path="/users/{user:path}", dependencies=[Security(dependency=Authorization(permissions=[PermissionType.UPDATE_USER])), Depends(dependency=update_root_user)])  # fmt: off
async def update_user(request: Request, user: int = Path(description="The ID of the user to update."), body: UserUpdateRequest = Body(description="The user update request.")) -> Response:  # fmt: off
    """
    Update a user.
    """

    await context.iam.update_user(user_id=user, name=body.name, password=body.password, role=body.role, expires_at=body.expires_at)

    return Response(status_code=204)


@router.get(path="/users/{user:path}", dependencies=[Security(dependency=Authorization(permissions=[PermissionType.READ_USER]))])
async def get_user(request: Request, user: int = Path(description="The ID of the user to get.")) -> User:
    """
    Get a user by id.
    """

    users = await context.iam.get_users(user_id=user)

    return users[0]


@router.get(path="/users", dependencies=[Security(dependency=Authorization(permissions=[PermissionType.READ_USER]))])
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


@router.post(path="/tokens", dependencies=[Security(dependency=Authorization(permissions=[PermissionType.CREATE_TOKEN]))])
async def create_token(request: Request, body: TokenRequest = Body(description="The token creation request.")) -> JSONResponse:
    """
    Create a new token.
    """

    token_id, token = await context.iam.create_token(name=body.name, user_id=body.user, expires_at=body.expires_at)

    return JSONResponse(status_code=201, content={"id": token_id, "token": token})


@router.delete(path="/tokens/{user:path}/{token:path}", dependencies=[Security(dependency=Authorization(permissions=[PermissionType.DELETE_TOKEN])), Depends(dependency=delete_root_token)])  # fmt: off
async def delete_token(request: Request, user: str = Path(description="The user ID of the user to delete the token for."), token: str = Path(description="The token ID of the token to delete.")) -> Response:  # fmt: off
    """
    Delete a token.
    """

    await context.iam.delete_token(name=token, user=user)

    return Response(status_code=204)


@router.get(path="/tokens/{user:path}/{token:path}", dependencies=[Security(dependency=Authorization(permissions=[PermissionType.READ_TOKEN]))])
async def get_token(request: Request, user: str = Path(description="The user ID of the user to get the token for."), token: str = Path(description="The token ID of the token to get.")) -> Token:  # fmt: off
    """
    Get a token by id.
    """

    tokens = await context.iam.get_tokens(name=token, user=user)

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

    data = await context.iam.get_tokens(user=user, offset=offset, limit=limit)

    return Tokens(data=data)
