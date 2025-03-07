from datetime import datetime

from app.schemas.roles import RateLimitType
from app.schemas.users import BudgetReset
from sqlalchemy import Column, DateTime, Enum, Float, ForeignKey, Integer, String, Boolean, Index, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import declarative_base, relationship, backref

Base = declarative_base()


class Role(Base):
    __tablename__ = "role"

    id = Column(Integer, primary_key=True, index=True)
    display_id = Column(String, unique=True, index=True)
    default = Column(Boolean, default=False)
    admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now())

    __table_args__ = (Index("only_one_default_role", default, unique=True, postgresql_where=default),)


class RateLimit(Base):
    __tablename__ = "rate_limit"

    id = Column(Integer, primary_key=True, index=True)
    role_id = Column(Integer, ForeignKey(column="role.id", ondelete="CASCADE"), nullable=False)
    model_id = Column(String, nullable=False)
    type = Column(Enum(RateLimitType), nullable=True)
    value = Column(Float, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now())

    role = relationship(argument="Role", backref=backref(name="rate_limit", cascade="all, delete-orphan"))


class User(Base):
    __tablename__ = "user"

    id = Column(Integer, primary_key=True, index=True)
    display_id = Column(String, index=True, unique=True)
    password = Column(String, nullable=False)
    role_id = Column(Integer, ForeignKey(column="role.id"), nullable=False)
    budget_allocation = Column(Float, nullable=True)
    budget_reset = Column(Enum(BudgetReset), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now)


class Token(Base):
    __tablename__ = "token"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey(column="user.id", ondelete="CASCADE"), nullable=False)
    display_id = Column(String, nullable=True)
    token = Column(String, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now())

    user = relationship(argument="User", backref=backref(name="token", cascade="all, delete-orphan"))

    __table_args__ = (UniqueConstraint("user_id", "display_id", name="unique_token_display_id_per_user"),)
