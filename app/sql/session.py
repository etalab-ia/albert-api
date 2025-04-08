from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.utils.settings import settings

# Extract and sanitize the URL and connect_args
url = settings.databases.sql.args.get("url").replace("+asyncpg", "")
connect_args = settings.databases.sql.args.get("connect_args", {})
if "server_settings" in connect_args:
    connect_args["server_settings"] = {str(k): str(v) for k, v in connect_args["server_settings"].items()}

engine = create_engine(url=url, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
