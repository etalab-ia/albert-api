import traceback

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.sql import text

from app.utils.logging import logger


class SQLDatabaseClient:
    def __init__(self, *args, **kwargs):
        """
        Async SQLDatabaseClient with check if database is reachable when API startup.
        """
        self.engine = create_async_engine(*args, **kwargs)  # TODO add timeout
        self.session = async_sessionmaker(bind=self.engine, expire_on_commit=False)

        # initialize the database with a sync session and create the default master role and user
        engine = create_engine(url=kwargs.get("url", "").replace("+asyncpg", ""))

        with engine.connect() as connection:
            try:
                connection.execute(statement=text("SELECT 1"))
            except Exception:
                logger.debug(msg=traceback.format_exc())
                raise ValueError("SQL database is not reachable.")
            finally:
                connection.close()
