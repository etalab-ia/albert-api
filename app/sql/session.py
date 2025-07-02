from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.utils.configuration import configuration


engine = create_async_engine(**configuration.dependencies.postgres.model_dump())
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Global variable to store the current get_db function for dependency injection
_get_db_func = None


def set_get_db_func(get_db_func):
    """Set the get_db function to use throughout the app."""
    global _get_db_func
    _get_db_func = get_db_func


def get_db_dependency():
    """Get the current database dependency function."""
    if _get_db_func is None:
        # Fall back to default implementation
        return get_db
    return _get_db_func


async def get_db():
    """Create and manage database session with guaranteed cleanup."""
    async with async_session() as session:
        yield session


async def get_db_session():
    """FastAPI dependency to get database session."""
    get_db_func = get_db_dependency()
    async for session in get_db_func():
        yield session
