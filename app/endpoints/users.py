from typing import Literal, Optional

from fastapi import APIRouter, Body, Depends, Path, Query, Request, Security
from fastapi.responses import JSONResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.helpers._accesscontroller import AccessController
from app.schemas.auth import (
    PermissionType,
    User,
    UserRequest,
    Users,
    UsersResponse,
    UserUpdateRequest,
)
from app.sql.session import get_db_session
from app.utils.configuration import configuration
from app.utils.context import global_context, request_context
from app.utils.variables import ENDPOINT__USERS, ENDPOINT__USERS_ME

router = APIRouter()


@router.post(
    path=ENDPOINT__USERS,
    dependencies=[Security(dependency=AccessController(permissions=[PermissionType.CREATE_USER]))],
    include_in_schema=configuration.settings.log_level == "DEBUG",
    status_code=201,
    response_model=UsersResponse,
)
async def create_user(
    request: Request,
    body: UserRequest = Body(description="The user creation request."),
    session: AsyncSession = Depends(get_db_session),
) -> JSONResponse:
    """
    Create a new user.
    """

    user_id = await global_context.identity_access_manager.create_user(session=session, name=body.name, role_id=body.role, budget=body.budget, expires_at=body.expires_at)  # fmt: off

    return JSONResponse(status_code=201, content={"id": user_id})


@router.delete(
    path=ENDPOINT__USERS + "/{user:path}",
    dependencies=[Security(dependency=AccessController(permissions=[PermissionType.DELETE_USER]))],
    include_in_schema=configuration.settings.log_level == "DEBUG",
    status_code=204,
)
async def delete_user(
    request: Request,
    user: int = Path(description="The ID of the user to delete."),
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    """
    Delete a user.
    """
    await global_context.identity_access_manager.delete_user(session=session, user_id=user)

    return Response(status_code=204)


@router.patch(
    path=ENDPOINT__USERS + "/{user:path}",
    dependencies=[Security(dependency=AccessController(permissions=[PermissionType.UPDATE_USER]))],
    include_in_schema=configuration.settings.log_level == "DEBUG",
    status_code=204,
)
async def update_user(
    request: Request,
    user: int = Path(description="The ID of the user to update."),
    body: UserUpdateRequest = Body(description="The user update request."),
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    """
    Update a user.
    """
    await global_context.identity_access_manager.update_user(
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
    include_in_schema=configuration.settings.log_level == "DEBUG",
    status_code=200,
    response_model=User,
)
async def get_current_user(request: Request, session: AsyncSession = Depends(get_db_session)) -> JSONResponse:
    """
    Get the current user.
    """

    users = await global_context.identity_access_manager.get_users(session=session, user_id=request_context.get().user_id)

    return JSONResponse(content=users[0].model_dump(), status_code=200)


@router.get(
    path=ENDPOINT__USERS + "/{user:path}",
    dependencies=[Security(dependency=AccessController(permissions=[PermissionType.READ_USER]))],
    include_in_schema=configuration.settings.log_level == "DEBUG",
    status_code=200,
)
async def get_user(
    request: Request, user: int = Path(description="The ID of the user to get."), session: AsyncSession = Depends(get_db_session)
) -> JSONResponse:
    """
    Get a user by id.
    """

    users = await global_context.identity_access_manager.get_users(session=session, user_id=user)

    return JSONResponse(content=users[0].model_dump(), status_code=200)


@router.get(
    path=ENDPOINT__USERS,
    dependencies=[Security(dependency=AccessController(permissions=[PermissionType.READ_USER]))],
    include_in_schema=configuration.settings.log_level == "DEBUG",
    status_code=200,
)
async def get_users(
    request: Request,
    role: Optional[int] = Query(default=None, description="The ID of the role to filter the users by."),
    offset: int = Query(default=0, ge=0, description="The offset of the users to get."),
    limit: int = Query(default=10, ge=1, le=100, description="The limit of the users to get."),
    order_by: Literal["id", "name", "created_at", "updated_at"] = Query(default="id", description="The field to order the users by."),
    order_direction: Literal["asc", "desc"] = Query(default="asc", description="The direction to order the users by."),
    session: AsyncSession = Depends(get_db_session),
) -> JSONResponse:
    """
    Get all users.
    """

    data = await global_context.identity_access_manager.get_users(
        session=session, role_id=role, offset=offset, limit=limit, order_by=order_by, order_direction=order_direction
    )

    return JSONResponse(content=Users(data=data).model_dump(), status_code=200)
