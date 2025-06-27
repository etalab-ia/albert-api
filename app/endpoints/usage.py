from typing import Literal
from datetime import datetime, timedelta
import math

from fastapi import APIRouter, Depends, Query, Request, Security
from fastapi.responses import JSONResponse
from sqlalchemy import desc, asc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.helpers._accesscontroller import AccessController
from app.schemas.auth import User
from app.schemas.accounts import AccountUsageResponse, AccountUsage
from app.sql.models import Usage as UsageModel
from app.utils.depends import get_db_session
from app.utils.variables import ENDPOINT__USAGE
from sqlalchemy import func

router = APIRouter()


def _normalize_date_range(date_from: int = None, date_to: int = None) -> tuple[int, int]:
    """
    Normalize date range with default values if not provided.

    Args:
        date_from: Start date as Unix timestamp (default: 30 days ago)
        date_to: End date as Unix timestamp (default: now)

    Returns:
        Tuple of (date_from, date_to) as Unix timestamps
    """
    if date_to is None:
        date_to = int(datetime.now().timestamp())
    if date_from is None:
        date_from = int((datetime.now() - timedelta(days=30)).timestamp())
    return date_from, date_to


def _build_base_filter(user_id: str, date_from: int, date_to: int) -> tuple:
    """
    Build base filter conditions for usage queries.

    Args:
        user_id: Current user ID
        date_from: Start date as Unix timestamp
        date_to: End date as Unix timestamp

    Returns:
        Tuple of filter conditions
    """
    return (
        UsageModel.user_id == user_id,
        UsageModel.model.is_not(None),
        UsageModel.datetime >= datetime.fromtimestamp(date_from),
        UsageModel.datetime <= datetime.fromtimestamp(date_to),
    )


def _build_usage_query(base_filter: tuple, order_by: str, order_direction: str, page: int, limit: int):
    """
    Build the main usage query with ordering and pagination.

    Args:
        base_filter: Base filter conditions
        order_by: Field to order by
        order_direction: Order direction (asc/desc)
        page: Page number (1-based)
        limit: Number of records per page

    Returns:
        SQLAlchemy query object
    """
    query = select(UsageModel).where(*base_filter)

    # Apply ordering
    order_field = getattr(UsageModel, order_by)
    if order_direction == "desc":
        query = query.order_by(desc(order_field))
    else:
        query = query.order_by(asc(order_field))

    # Apply pagination
    offset = (page - 1) * limit
    query = query.offset(offset).limit(limit)

    return query


async def _get_usage_aggregation(session: AsyncSession, base_filter: tuple) -> dict:
    """
    Get aggregated usage statistics for the given filters.

    Args:
        session: Database session
        base_filter: Base filter conditions

    Returns:
        Dictionary with aggregated values
    """
    # Total count query
    count_query = select(func.count(UsageModel.id)).where(*base_filter)
    count_result = await session.execute(count_query)
    total_count = count_result.scalar()

    # Aggregated values query
    aggregation_query = select(
        func.count(UsageModel.id).label("total_requests"),
        func.coalesce(func.sum(UsageModel.cost), 0).label("total_albert_coins"),
        func.coalesce(func.sum(UsageModel.total_tokens), 0).label("total_tokens"),
        func.coalesce(func.avg((UsageModel.kgco2eq_min + UsageModel.kgco2eq_max) / 2) * 1000, 0).label("total_co2"),
    ).where(*base_filter)

    aggregation_result = await session.execute(aggregation_query)
    aggregation_data = aggregation_result.first()

    return {
        "total_count": total_count,
        "total_requests": aggregation_data.total_requests or 0,
        "total_albert_coins": float(aggregation_data.total_albert_coins) if aggregation_data.total_albert_coins else 0.0,
        "total_tokens": int(aggregation_data.total_tokens) if aggregation_data.total_tokens else 0,
        "total_co2": float(aggregation_data.total_co2) if aggregation_data.total_co2 else 0.0,
    }


def _convert_records_to_schema(usage_records) -> list[AccountUsage]:
    """
    Convert database records to AccountUsage schema objects.

    Args:
        usage_records: List of UsageModel records

    Returns:
        List of AccountUsage schema objects
    """
    usage_data = []
    for record in usage_records:
        usage_data.append(
            AccountUsage(
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
    return usage_data


def _calculate_pagination_metadata(total_count: int, page: int, limit: int) -> dict:
    """
    Calculate pagination metadata.

    Args:
        total_count: Total number of records
        page: Current page number
        limit: Records per page

    Returns:
        Dictionary with pagination metadata
    """
    total_pages = math.ceil(total_count / limit) if total_count > 0 else 1
    has_more = page < total_pages

    return {
        "total_pages": total_pages,
        "has_more": has_more,
    }


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
    session: AsyncSession = get_db_session(),
    current_user: User = Depends(AccessController()),
) -> JSONResponse:
    """
    Get usage records for the current authenticated account.

    Returns usage data filtered by the current account's ID, with configurable ordering and pagination.
    Supports pagination through page and limit parameters.
    """
    # Normalize date range
    date_from, date_to = _normalize_date_range(date_from, date_to)

    # Build base filter conditions
    base_filter = _build_base_filter(current_user.id, date_from, date_to)

    # Build and execute usage query
    query = _build_usage_query(base_filter, order_by, order_direction, page, limit)
    result = await session.execute(query)
    usage_records = result.scalars().all()

    # Get aggregated statistics
    aggregation_data = await _get_usage_aggregation(session, base_filter)

    # Convert records to schema format
    usage_data = _convert_records_to_schema(usage_records)

    # Calculate pagination metadata
    pagination_meta = _calculate_pagination_metadata(aggregation_data["total_count"], page, limit)

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
