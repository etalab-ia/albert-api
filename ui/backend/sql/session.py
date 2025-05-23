from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from ui.settings import settings

engine = create_engine(**settings.databases.sql.args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
