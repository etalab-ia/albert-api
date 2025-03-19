from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, Boolean, Index, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import declarative_base, relationship, backref
from app.schemas.auth import PermissionType, LimitType
from app.schemas.collections import CollectionVisibility

Base = declarative_base()


class Role(Base):
    __tablename__ = "role"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    default = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), nullable=False)

    __table_args__ = (Index("only_one_default_role", default, unique=True, postgresql_where=default),)


class Permission(Base):
    __tablename__ = "permission"

    id = Column(Integer, primary_key=True, index=True)
    role_id = Column(Integer, ForeignKey(column="role.id", ondelete="CASCADE"), nullable=False)
    permission = Column(Enum(PermissionType), nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)

    role = relationship(argument="Role", backref=backref(name="permission", cascade="all, delete-orphan"))

    __table_args__ = (UniqueConstraint("role_id", "permission", name="unique_permission_per_role"),)


class Limit(Base):
    __tablename__ = "limit"

    id = Column(Integer, primary_key=True, index=True)
    role_id = Column(Integer, ForeignKey(column="role.id", ondelete="CASCADE"), nullable=False)
    model = Column(String, nullable=False)
    type = Column(Enum(LimitType), nullable=False)
    value = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)

    role = relationship(argument="Role", backref=backref(name="rate_limit", cascade="all, delete-orphan"))

    __table_args__ = (UniqueConstraint("role_id", "model", "type", name="unique_rate_limit_per_role"),)


class User(Base):
    __tablename__ = "user"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, unique=True)
    password = Column(String, nullable=False)
    role_id = Column(Integer, ForeignKey(column="role.id"), nullable=False)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), nullable=False)


class Token(Base):
    __tablename__ = "token"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey(column="user.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=True)
    token = Column(String, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)

    user = relationship(argument="User", backref=backref(name="token", cascade="all, delete-orphan"))

    __table_args__ = (UniqueConstraint("user_id", "name", name="unique_token_name_per_user"),)


class Collection(Base):
    __tablename__ = "collection"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey(column="user.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    visibility = Column(Enum(CollectionVisibility), nullable=False)
    vector_size = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), nullable=False)

    user = relationship(argument="User", backref=backref(name="collection", cascade="all, delete-orphan"))

    __table_args__ = (UniqueConstraint("user_id", "name", name="unique_collection_name_per_user"),)


class Document(Base):
    __tablename__ = "document"

    id = Column(Integer, primary_key=True, index=True)
    collection_id = Column(Integer, ForeignKey(column="collection.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)

    collection = relationship(argument="Collection", backref=backref(name="document", cascade="all, delete-orphan"))

    __table_args__ = (UniqueConstraint("collection_id", "name", name="unique_document_name_per_collection"),)
