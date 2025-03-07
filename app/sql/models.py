from datetime import datetime

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, Boolean, Index, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import declarative_base, relationship, backref
from app.schemas.auth import PermissionType, LimitType

Base = declarative_base()


class Role(Base):
    __tablename__ = "role"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    default = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now())

    __table_args__ = (Index("only_one_default_role", default, unique=True, postgresql_where=default),)


class Permission(Base):
    __tablename__ = "permission"

    id = Column(Integer, primary_key=True, index=True)
    role_id = Column(Integer, ForeignKey(column="role.id", ondelete="CASCADE"), nullable=False)
    permission = Column(Enum(PermissionType), nullable=False)
    created_at = Column(DateTime, default=func.now())

    role = relationship(argument="Role", backref=backref(name="permission", cascade="all, delete-orphan"))

    __table_args__ = (UniqueConstraint("role_id", "permission", name="unique_permission_per_role"),)


class Limit(Base):
    __tablename__ = "limit"

    id = Column(Integer, primary_key=True, index=True)
    role_id = Column(Integer, ForeignKey(column="role.id", ondelete="CASCADE"), nullable=False)
    model = Column(String, nullable=False)
    type = Column(Enum(LimitType), nullable=False)
    value = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=func.now())

    role = relationship(argument="Role", backref=backref(name="rate_limit", cascade="all, delete-orphan"))

    __table_args__ = (UniqueConstraint("role_id", "model", "type", name="unique_rate_limit_per_role"),)


class User(Base):
    __tablename__ = "user"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, unique=True)
    password = Column(String, nullable=False)
    role_id = Column(Integer, ForeignKey(column="role.id"), nullable=False)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now)


class Token(Base):
    __tablename__ = "token"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey(column="user.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=True)
    token = Column(String, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now())

    user = relationship(argument="User", backref=backref(name="token", cascade="all, delete-orphan"))

    __table_args__ = (UniqueConstraint("user_id", "name", name="unique_token_name_per_user"),)
