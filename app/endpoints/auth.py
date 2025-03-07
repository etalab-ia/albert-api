from typing import Optional

from fastapi import APIRouter, Body, Path, Query, Request, Security
from fastapi.responses import PlainTextResponse, Response

from app.helpers import AuthManager, RateLimit
from app.schemas.login import LoginRequest
from app.schemas.roles import RateLimit as _RateLimit
from app.schemas.roles import Role, RoleRequest, Roles, RoleUpdateRequest
from app.schemas.tokens import Token, TokenRequest, Tokens
from app.schemas.users import User, UserRequest, Users, UserUpdateRequest
from app.utils.exceptions import InvalidPasswordException
from app.utils.lifespan import auth

router = APIRouter()


@router.post(path="/login")
async def login(request: Request, body: LoginRequest = Body(description="The login request.")) -> Response:
    """
    Login to the API.
    """

    users = await auth.manager.get_users(user_id=body.user_id)
    user = users[0]

    if not AuthManager._check_password(password=body.password, hashed_password=user.password):
        raise InvalidPasswordException()

    return Response(status_code=200)


@router.post(path="/roles")
async def create_role(
    request: Request, body: RoleRequest = Body(description="The role creation request."), user: User = Security(dependency=RateLimit(admin=True))
) -> PlainTextResponse:
    """
    Create a new role. If no limits are provided, the role will have all access without rate limits.
    """

    body = body.model_dump(exclude_none=True)
    body["role_id"] = body.pop("role")
    if body.get("limits"):
        body["limits"] = [_RateLimit(**limit) for limit in body["limits"]]
    role_id = await auth.manager.create_role(**body)

    return PlainTextResponse(status_code=201, content=str(role_id))


@router.delete(path="/roles/{role}")
async def delete_role(
    request: Request, role: str = Path(description="The id of the role to delete."), user: User = Security(dependency=RateLimit(admin=True))
) -> Response:
    """
    Delete a role.
    """

    await auth.manager.delete_role(role_id=role)

    return Response(status_code=204)


@router.patch(path="/roles/{role}")
async def update_role(
    request: Request,
    role: str = Path(description="The id of the role to update."),
    body: RoleUpdateRequest = Body(description="The role update request."),
    user: User = Security(dependency=RateLimit(admin=True)),
) -> Response:
    """
    Update a role.
    """

    body = body.model_dump()
    display_id = body.pop("role")
    await auth.manager.update_role(role_id=role, display_id=display_id, **body)

    return Response(status_code=201)


@router.get(path="/roles/{role}")
async def get_role(
    request: Request,
    role: str = Path(description="The id of the role to get."),
    user: User = Security(dependency=RateLimit(admin=True)),
) -> Role:
    """
    Get a role by id.
    """

    roles = await auth.manager.get_roles(role_id=[role])

    return roles[0]


@router.get(path="/roles")
async def get_roles(
    request: Request,
    offset: int = Query(default=0, ge=0, description="The offset of the roles to get."),
    limit: int = Query(default=10, ge=1, le=100, description="The limit of the roles to get."),
    user: User = Security(dependency=RateLimit(admin=True)),
) -> Roles:
    """
    Get all roles.
    """

    data = await auth.manager.get_roles(offset=offset, limit=limit)

    return Roles(data=data)


@router.post(path="/users")
async def create_user(
    request: Request, body: UserRequest = Body(description="The user creation request."), user: User = Security(dependency=RateLimit(admin=True))
) -> PlainTextResponse:
    """
    Create a new user.
    """

    body = body.model_dump(exclude_none=True)
    body["user_id"] = body.pop("user")
    body["role_id"] = body.pop("role")
    user = await auth.manager.create_user(**body)

    return PlainTextResponse(status_code=201, content=user)


@router.delete(path="/users/{user:path}")
async def delete_user(
    request: Request,
    user: str = Path(description="The id of the user to delete."),
    _: User = Security(dependency=RateLimit(admin=True)),
) -> Response:
    """
    Delete a user.
    """
    await auth.manager.delete_user(user_id=user)

    return Response(status_code=204)


@router.patch(path="/users/{user:path}")
async def update_user(
    request: Request,
    user: str = Path(description="The user name of the user to update."),
    body: UserUpdateRequest = Body(description="The user update request."),
    _: User = Security(dependency=RateLimit(admin=True)),
) -> Response:
    """
    Update a user.
    """

    body = body.model_dump()
    display_id = body.pop("user")
    await auth.manager.update_user(user_id=user, display_id=display_id, **body)

    return Response(status_code=201)


@router.get(path="/users/{user:path}")
async def get_user(
    request: Request, user: str = Path(description="The id of the user to get."), _: User = Security(dependency=RateLimit(admin=True))
) -> User:
    """
    Get a user by id.
    """

    users = await auth.manager.get_users(user_ids=[user])

    return users[0]


@router.get(path="/users")
async def get_users(
    request: Request,
    role: Optional[str] = Query(default=None, description="The id of the role to filter the users by."),
    offset: int = Query(default=0, ge=0, description="The offset of the users to get."),
    limit: int = Query(default=10, ge=1, le=100, description="The limit of the users to get."),
    user: User = Security(dependency=RateLimit(admin=True)),
) -> Users:
    """
    Get all users.
    """
    data = await auth.manager.get_users(role_id=role, offset=offset, limit=limit)

    return Users(data=data)


@router.post(path="/tokens")
async def create_token(
    request: Request,
    body: TokenRequest = Body(description="The token creation request."),
    _: User = Security(dependency=RateLimit(admin=True)),
) -> PlainTextResponse:
    """
    Create a new token.
    """

    token = await auth.manager.create_token(user_id=body.user, token_id=body.token, expires_at=body.expires_at)

    return PlainTextResponse(status_code=201, content=token)


@router.delete(path="/tokens/{user:path}/{token:path}")
async def delete_token(
    request: Request,
    user: str = Path(description="The user ID of the user to delete the token for."),
    token: str = Path(description="The token ID of the token to delete."),
    _: User = Security(dependency=RateLimit(admin=True)),
) -> Response:
    """
    Delete a token.
    """

    await auth.manager.delete_token(user_id=user, token_id=token)

    return Response(status_code=204)


@router.get(path="/tokens/{user:path}/{token:path}")
async def get_token(
    request: Request,
    user: str = Path(description="The user ID of the user to get the token for."),
    token: str = Path(description="The token ID of the token to get."),
    _: User = Security(dependency=RateLimit(admin=True)),
) -> Token:
    """
    Get a token by id.
    """

    tokens = await auth.manager.get_tokens(user_id=user, token_id=token, offset=0, limit=1)

    return tokens[0]


@router.get(path="/tokens/{user}")
async def get_tokens(
    request: Request,
    user: str = Path(description="The id of the user to filter the tokens by."),
    offset: int = Query(default=0, ge=0, description="The offset of the tokens to get."),
    limit: int = Query(default=10, ge=1, le=100, description="The limit of the tokens to get."),
    _: User = Security(dependency=RateLimit(admin=True)),
) -> Tokens:
    """
    Get all tokens of a user.
    """

    data = await auth.manager.get_tokens(user_id=user, offset=offset, limit=limit)

    return Tokens(data=data)
