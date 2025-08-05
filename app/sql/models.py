from http import HTTPMethod

from sqlalchemy import Column, DateTime, Enum, Float, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import backref, declarative_base, relationship

from app.schemas.auth import LimitType, PermissionType
from app.schemas.collections import CollectionVisibility

Base = declarative_base()


class Usage(Base):
    __tablename__ = "usage"

    id = Column(Integer, primary_key=True)
    datetime = Column(DateTime, nullable=False, default=func.now())
    duration = Column(Integer, nullable=True)
    time_to_first_token = Column(Integer, nullable=True)
    user_id = Column(ForeignKey(column="user.id", ondelete="CASCADE"), nullable=True)
    token_id = Column(ForeignKey(column="token.id", ondelete="SET NULL"), nullable=True)
    endpoint = Column(String, nullable=False)
    method = Column(Enum(HTTPMethod), nullable=True)
    model = Column(String, nullable=True)
    request_model = Column(String, nullable=True)
    prompt_tokens = Column(Integer)
    completion_tokens = Column(Float)
    total_tokens = Column(Integer)
    cost = Column(Float, nullable=True)
    status = Column(Integer, nullable=True)
    kwh_min = Column(Float, nullable=True)
    kwh_max = Column(Float, nullable=True)
    kgco2eq_min = Column(Float, nullable=True)
    kgco2eq_max = Column(Float, nullable=True)

    user = relationship(argument="User", backref=backref(name="usage", cascade="all, delete-orphan"))
    token = relationship(argument="Token", backref=backref(name="usage"))

    def __repr__(self):
        return f"<Usage (id={self.id}, datetime={self.datetime}, user_id={self.user_id}, token_id={self.token_id}, endpoint={self.endpoint}, duration={self.duration})>"


class Role(Base):
    __tablename__ = "role"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String, unique=True, index=True, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), nullable=False, onupdate=func.now())


class Permission(Base):
    __tablename__ = "permission"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    role_id = Column(Integer, ForeignKey(column="role.id", ondelete="CASCADE"), nullable=False)
    permission = Column(Enum(PermissionType), nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)

    role = relationship(argument="Role", backref=backref(name="permission", cascade="all, delete-orphan"))

    __table_args__ = (UniqueConstraint("role_id", "permission", name="unique_permission_per_role"),)


class Limit(Base):
    __tablename__ = "limit"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    role_id = Column(Integer, ForeignKey(column="role.id", ondelete="CASCADE"), nullable=False)
    model = Column(String, nullable=False)
    type = Column(Enum(LimitType), nullable=False)
    value = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)

    role = relationship(argument="Role", backref=backref(name="limit", cascade="all, delete-orphan"))

    __table_args__ = (UniqueConstraint("role_id", "model", "type", name="unique_rate_limit_per_role"),)


class User(Base):
    __tablename__ = "user"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String, index=True, unique=True, nullable=False)
    role_id = Column(Integer, ForeignKey(column="role.id"), nullable=False)
    budget = Column(Float, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), nullable=False, onupdate=func.now())
    sub = Column(String, unique=True, nullable=True)
    email = Column(String, index=True, nullable=True)


class Token(Base):
    __tablename__ = "token"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey(column="user.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=True)
    token = Column(String, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)

    user = relationship(argument="User", backref=backref(name="token", cascade="all, delete-orphan"))


class Collection(Base):
    __tablename__ = "collection"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey(column="user.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    visibility = Column(Enum(CollectionVisibility), nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), nullable=False, onupdate=func.now())

    user = relationship(argument="User", backref=backref(name="collection", cascade="all, delete-orphan"))


class Document(Base):
    __tablename__ = "document"

    id = Column(Integer, primary_key=True, index=True)
    collection_id = Column(Integer, ForeignKey(column="collection.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)

    collection = relationship(argument="Collection", backref=backref(name="document", cascade="all, delete-orphan"))
