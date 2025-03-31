from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from ui.settings import settings

engine = create_engine(url=settings.playground.database_url.replace("+asyncpg", ""))
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
