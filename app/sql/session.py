from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.utils.settings import settings

engine = create_engine(url=settings.databases.sql.args.get("url").replace("+asyncpg", ""))
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
