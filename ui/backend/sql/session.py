from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from ui.configuration import configuration

engine = create_engine(**configuration.playground.postgres)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
