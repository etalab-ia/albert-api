# Global variable to store the current get_db function
_get_db_func = None


def set_get_db_func(get_db_func):
    """Set the get_db function to use throughout the app."""
    global _get_db_func
    _get_db_func = get_db_func


def get_db_dependency():
    """Get the current database dependency function."""
    if _get_db_func is None:
        # Fall back to default implementation
        from app.sql.session import get_db

        return get_db
    return _get_db_func


async def get_db_session():
    """FastAPI dependency to get database session."""
    get_db_func = get_db_dependency()
    async for session in get_db_func():
        yield session
