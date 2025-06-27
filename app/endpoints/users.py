from typing import Literal

from fastapi import APIRouter, Depends, Query, Request, Security
from fastapi.responses import JSONResponse
from sqlalchemy import desc, asc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.helpers._accesscontroller import AccessController
from app.schemas.auth import User
from app.schemas.users import UserUsageResponse, UserUsage
from app.sql.models import Usage as UsageModel
from app.utils.depends import get_db_session
from app.utils.variables import ENDPOINT__USERS_USAGE

router = APIRouter()


@router.get(
    path=ENDPOINT__USERS_USAGE,
    dependencies=[Security(dependency=AccessController())],
    status_code=200,
    response_model=UserUsageResponse,
)
async def get_user_usage(
    request: Request,
    limit: int = Query(default=50, ge=1, le=100, description="Number of records to return (1-100)"),
    order_by: Literal["datetime", "cost", "total_tokens"] = Query(default="datetime", description="Field to order by"),
    order_direction: Literal["asc", "desc"] = Query(default="desc", description="Order direction"),
    session: AsyncSession = get_db_session(),
    current_user: User = Depends(AccessController()),
) -> JSONResponse:
    """
    Get usage records for the current authenticated user.

    Returns usage data filtered by the current user's ID, with configurable ordering and pagination.
    """

    # Build the query to get usage data for the current user
    query = select(UsageModel).where(UsageModel.user_id == current_user.id)

    # Apply ordering
    order_field = getattr(UsageModel, order_by)
    if order_direction == "desc":
        query = query.order_by(desc(order_field))
    else:
        query = query.order_by(asc(order_field))

    # Apply pagination
    query = query.limit(limit)

    # Execute query
    result = await session.execute(query)
    usage_records = result.scalars().all()

    # Get total count for this user
    count_query = select(UsageModel.id).where(UsageModel.user_id == current_user.id)
    count_result = await session.execute(count_query)
    total_count = len(count_result.scalars().all())

    # Convert to response format
    usage_data = []
    for record in usage_records:
        usage_data.append(
            UserUsage(
                id=record.id,
                datetime=int(record.datetime.timestamp()),
                duration=record.duration,
                time_to_first_token=record.time_to_first_token,
                user_id=record.user_id,
                token_id=record.token_id,
                endpoint=record.endpoint,
                method=record.method.value if record.method else None,
                model=record.model,
                request_model=record.request_model,
                prompt_tokens=record.prompt_tokens,
                completion_tokens=record.completion_tokens,
                total_tokens=record.total_tokens,
                cost=record.cost,
                status=record.status,
                kwh_min=record.kwh_min,
                kwh_max=record.kwh_max,
                kgco2eq_min=record.kgco2eq_min,
                kgco2eq_max=record.kgco2eq_max,
            )
        )

    has_more = len(usage_records) == limit and total_count > limit

    response = UserUsageResponse(data=usage_data, total=total_count, has_more=has_more)

    return JSONResponse(status_code=200, content=response.model_dump())
