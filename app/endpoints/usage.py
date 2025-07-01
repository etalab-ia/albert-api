from typing import Literal

from fastapi import APIRouter, Depends, Query, Request, Security
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.helpers._accesscontroller import AccessController
from app.helpers._usagemanager import UsageManager
from app.schemas.auth import User
from app.schemas.accounts import AccountUsageResponse
from app.sql.session import get_db_session
from app.utils.variables import ENDPOINT__USAGE

router = APIRouter()


@router.get(
    path=ENDPOINT__USAGE,
    dependencies=[Security(dependency=AccessController())],
    status_code=200,
    response_model=AccountUsageResponse,
)
async def get_account_usage(
    request: Request,
    limit: int = Query(default=50, ge=1, le=100, description="Number of records to return per page (1-100)"),
    page: int = Query(default=1, ge=1, description="Page number (1-based)"),
    order_by: Literal["datetime", "cost", "total_tokens"] = Query(default="datetime", description="Field to order by"),
    order_direction: Literal["asc", "desc"] = Query(default="desc", description="Order direction"),
    date_from: int = Query(default=None, description="Start date as Unix timestamp (default: 30 days ago)"),
    date_to: int = Query(default=None, description="End date as Unix timestamp (default: now)"),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(AccessController()),
) -> JSONResponse:
    """
    Get usage records for the current authenticated account.

    Returns usage data filtered by the current account's ID, with configurable ordering and pagination.
    Supports pagination through page and limit parameters.
    """
    # Normalize date range
    date_from, date_to = UsageManager.normalize_date_range(date_from, date_to)

    # Build base filter conditions
    base_filter = UsageManager.build_base_filter(current_user.id, date_from, date_to)

    # Build and execute usage query
    query = UsageManager.build_usage_query(base_filter, order_by, order_direction, page, limit)
    result = await session.execute(query)
    usage_records = result.scalars().all()

    # Get aggregated statistics
    aggregation_data = await UsageManager.get_usage_aggregation(session, base_filter)

    # Convert records to schema format
    usage_data = UsageManager.convert_records_to_schema(usage_records)

    # Calculate pagination metadata
    pagination_meta = UsageManager.calculate_pagination_metadata(aggregation_data["total_count"], page, limit)

    # Build response
    response = AccountUsageResponse(
        data=usage_data,
        total=aggregation_data["total_count"],
        total_requests=aggregation_data["total_requests"],
        total_albert_coins=aggregation_data["total_albert_coins"],
        total_tokens=aggregation_data["total_tokens"],
        total_co2=aggregation_data["total_co2"],
        page=page,
        limit=limit,
        total_pages=pagination_meta["total_pages"],
        has_more=pagination_meta["has_more"],
    )

    return JSONResponse(status_code=200, content=response.model_dump())
