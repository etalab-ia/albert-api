from sqlalchemy import Column, DateTime, Integer, String
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class User(Base):
    __tablename__ = "user"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, unique=True)
    password = Column(String, nullable=False)
    # admin = Column(Boolean, nullable=False, default=False)
    api_role_id = Column(Integer, nullable=False)
    api_user_id = Column(Integer, nullable=False)
    api_key = Column(String, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), nullable=False)

    # __table_args__ = (Index("only_one_admin_user", admin, unique=True, postgresql_where=admin),)
