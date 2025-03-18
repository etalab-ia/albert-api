import time
import traceback
from typing import List, Optional, Tuple

import bcrypt
from jose import JWTError, jwt
from sqlalchemy import Integer, cast, delete, insert, or_, select, update
from sqlalchemy.exc import IntegrityError, NoResultFound
from sqlalchemy.sql import func

from app.clients.database import SQLDatabaseClient
from app.schemas.auth import Limit, PermissionType, Role, Token, User
from app.schemas.collections import Collection, CollectionType
from app.schemas.core.auth import UserInfo
from app.schemas.documents import Document
from app.sql.models import Collection as CollectionTable
from app.sql.models import Document as DocumentTable
from app.sql.models import Limit as LimitTable
from app.sql.models import Permission as PermissionTable
from app.sql.models import Role as RoleTable
from app.sql.models import Token as TokenTable
from app.sql.models import User as UserTable
from app.utils.exceptions import (
    CollectionNotFoundException,
    DeleteRoleWithUsersException,
    DocumentNotFoundException,
    InvalidPasswordException,
    RoleAlreadyExistsException,
    RoleNotFoundException,
    TokenAlreadyExistsException,
    TokenNotFoundException,
    UserAlreadyExistsException,
    UserNotFoundException,
)
from app.utils.logging import logger
from app.utils.settings import settings
from app.utils.variables import ROOT_ROLE


class IdentityAccessManager:
    TOKEN_PREFIX = "sk-"

    def __init__(self, sql: SQLDatabaseClient) -> None:
        """
        Initialize the authentication manager: create the root user and role if they don't exist and check if the root password is correct and update it if needed
        """

        self.sql = sql

    async def setup(self):
        # initialize create the root role and user
        async with self.sql.session() as session:
            # get the currently root data
            result = await session.execute(
                statement=select(RoleTable.id.label("role_id"), UserTable.id.label("user_id"), TokenTable.token)
                .outerjoin(target=UserTable, onclause=RoleTable.id == UserTable.role_id)
                .outerjoin(target=TokenTable, onclause=UserTable.id == TokenTable.user_id)
                .where(RoleTable.name == ROOT_ROLE)
            )
            currently_root = result.all()

            if currently_root:
                assert len(currently_root) == 1, "Root role have more than one user or token, please check the database."
                currently_root = [row._mapping for row in currently_root][0]

                if currently_root["token"]:
                    assert self._check_password(password=settings.auth.root_key, hashed_password=currently_root["token"]), "Provided root key is not matching with stored root key"  # fmt: off

                # delete currently root user
                try:
                    await session.execute(statement=delete(table=UserTable).where(UserTable.id == currently_root["user_id"]))
                    await session.commit()
                except Exception:
                    logger.debug(msg=traceback.format_exc())
                    raise Exception("Failed to delete currently root user.")

                # delete the currently root role
                try:
                    await session.execute(statement=delete(table=RoleTable).where(RoleTable.id == currently_root["role_id"]))
                    await session.commit()
                except Exception:
                    logger.debug(msg=traceback.format_exc())
                    raise Exception("Failed to delete currently root role.")

            # create the root role
            try:
                await session.execute(statement=insert(table=RoleTable).values(name=ROOT_ROLE, default=False))
                await session.commit()
            except Exception:
                logger.debug(msg=traceback.format_exc())
                raise Exception("Failed to create default root role.")

            result = await session.execute(statement=select(RoleTable).where(RoleTable.name == ROOT_ROLE))
            self.root_role_id = result.scalar_one().id

            # create the root permissions
            values = [{"role_id": self.root_role_id, "permission": permission} for permission in PermissionType]
            try:
                await session.execute(statement=insert(table=PermissionTable).values(values))
                await session.commit()
            except Exception:
                logger.debug(msg=traceback.format_exc())
                raise Exception("Failed to create root permissions.")

            # create the root user
            try:
                await session.execute(
                    statement=insert(table=UserTable).values(
                        name=settings.auth.root_user,
                        password=self._get_hashed_password(password=settings.auth.root_password),
                        role_id=self.root_role_id,
                    )
                )
                await session.commit()
            except Exception:
                logger.debug(msg=traceback.format_exc())
                raise Exception("Failed to create root user.")

            result = await session.execute(statement=select(UserTable).where(UserTable.name == settings.auth.root_user))
            self.root_user_id = result.scalar_one().id

            # create the root token
            try:
                await session.execute(statement=insert(table=TokenTable).values(user_id=self.root_user_id, name=ROOT_ROLE))
                await session.commit()
            except Exception:
                logger.debug(msg=traceback.format_exc())
                raise Exception("Failed to create root token.")

    @staticmethod
    def _get_hashed_password(password: str) -> str:
        return bcrypt.hashpw(password=password.encode(encoding="utf-8"), salt=bcrypt.gensalt()).decode(encoding="utf-8")

    @staticmethod
    def _check_password(password: str, hashed_password: str) -> bool:
        return bcrypt.checkpw(password=password.encode(encoding="utf-8"), hashed_password=hashed_password.encode(encoding="utf-8"))

    @staticmethod
    def _decode_token(token: str) -> dict:
        token = token.split(IdentityAccessManager.TOKEN_PREFIX)[1]
        return jwt.decode(token=token, key=settings.auth.root_key, algorithms=["HS256"])

    @staticmethod
    def _encode_token(user_id: int, token_id: int, expires_at: Optional[int] = None) -> str:
        return IdentityAccessManager.TOKEN_PREFIX + jwt.encode(
            claims={"user_id": user_id, "token_id": token_id, "expires_at": expires_at},
            key=settings.auth.root_key,
            algorithm="HS256",
        )

    async def login(self, user_name: str, user_password: str) -> User:
        async with self.sql.session() as session:
            result = await session.execute(statement=select(UserTable).where(UserTable.name == user_name))
            try:
                user = result.scalar_one()
            except NoResultFound:
                raise UserNotFoundException()

            if not IdentityAccessManager._check_password(password=user_password, hashed_password=user.password):
                raise InvalidPasswordException()

            if user.expires_at is not None and user.expires_at < time.time():
                raise UserNotFoundException()

            user = User(id=user.id, name=user.name, role=user.role_id, expires_at=user.expires_at)

            return user

    async def create_role(self, name: str, default: bool = False, limits: List[Limit] = [], permissions: List[PermissionType] = []) -> int:
        async with self.sql.session() as session:
            # create the role
            try:
                await session.execute(statement=insert(table=RoleTable).values(name=name, default=default))
                await session.commit()
            except IntegrityError:
                raise RoleAlreadyExistsException()

            result = await session.execute(statement=select(RoleTable.id).where(RoleTable.name == name))
            role_id = result.scalar_one()

            # create the limits
            for limit in limits:
                await session.execute(statement=insert(table=LimitTable).values(role_id=role_id, model=limit.model, type=limit.type, value=limit.value))  # fmt: off

            # create the permissions
            for permission in permissions:
                await session.execute(statement=insert(table=PermissionTable).values(role_id=role_id, permission=permission))

            await session.commit()

            return role_id

    async def delete_role(self, role_id: int) -> None:
        async with self.sql.session() as session:
            # check if role exists
            try:
                result = await session.execute(statement=select(RoleTable).where(RoleTable.id == role_id))
                result.scalar_one()
            except NoResultFound:
                raise RoleNotFoundException()

            # delete the role
            try:
                await session.execute(statement=delete(table=RoleTable).where(RoleTable.id == role_id))
            except IntegrityError:
                raise DeleteRoleWithUsersException()

            await session.commit()

    async def update_role(
        self,
        role_id: int,
        name: Optional[str] = None,
        default: Optional[bool] = None,
        limits: Optional[List[Limit]] = None,
        permissions: Optional[List[PermissionType]] = None,
    ) -> None:
        async with self.sql.session() as session:
            # check if role exists
            try:
                result = await session.execute(statement=select(RoleTable).where(RoleTable.id == role_id))
                role = result.scalar_one()
            except NoResultFound:
                raise RoleNotFoundException()

            # update the role
            name = name if name is not None else role.name
            if default:
                # change the currently default role to not be default
                result = await session.execute(statement=select(RoleTable).where(RoleTable.default))
                existing_default_role = result.scalar_one()
                await session.execute(statement=update(table=RoleTable).values(default=False).where(RoleTable.id == existing_default_role.id))

            default = default if default is not None else role.default

            try:
                await session.execute(
                    statement=update(table=RoleTable).values(name=name, default=default, updated_at=func.now()).where(RoleTable.id == role.id)
                )
            except IntegrityError:
                raise RoleAlreadyExistsException()
            except NoResultFound:
                raise RoleNotFoundException()

            if limits is not None:
                # delete the existing limits
                await session.execute(statement=delete(table=LimitTable).where(LimitTable.role_id == role.id))

                # create the new limits
                values = [{"role_id": role.id, "model": limit.model, "type": limit.type, "value": limit.value} for limit in limits]
                if values:
                    await session.execute(statement=insert(table=LimitTable).values(values))

            if permissions is not None:
                # delete the existing permissions
                await session.execute(statement=delete(table=PermissionTable).where(PermissionTable.role_id == role.id))

                # Only insert if there are permissions to insert
                if permissions:
                    values = [{"role_id": role.id, "permission": permission} for permission in set(permissions)]
                    if values:
                        await session.execute(statement=insert(table=PermissionTable).values(values))

            await session.commit()

    async def get_roles(self, role_id: Optional[int] = None, offset: int = 0, limit: int = 10) -> List[Role]:
        async with self.sql.session() as session:
            if not role_id:
                # get the unique role IDs with pagination
                statement = select(RoleTable.id).offset(offset=offset).limit(limit=limit)

                if role_id:
                    statement = statement.where(RoleTable.id == role_id)

                result = await session.execute(statement=statement)
                selected_roles = [row[0] for row in result.all()]
            else:
                selected_roles = [role_id]

            # then get all the data for these specific role IDs
            statement = (
                select(
                    RoleTable.id,
                    RoleTable.name,
                    RoleTable.default,
                    cast(func.extract("epoch", RoleTable.created_at), Integer),
                    cast(func.extract("epoch", RoleTable.updated_at), Integer),
                    LimitTable.model,
                    LimitTable.type,
                    LimitTable.value,
                    PermissionTable.permission,
                )
                .outerjoin(target=LimitTable, onclause=RoleTable.id == LimitTable.role_id)
                .outerjoin(target=PermissionTable, onclause=RoleTable.id == PermissionTable.role_id)
                .where(RoleTable.id.in_(selected_roles))
            )

            result = await session.execute(statement=statement)
            results = [row._asdict() for row in result.all()]

            # format the results
            roles = {}
            for row in results:
                role = Role(
                    id=row["id"],
                    name=row["name"],
                    default=row["default"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                    limits=[],
                    permissions=[],
                )
                if role.id not in roles:
                    roles[role.id] = role
                if row.model:
                    rate_limit = Limit(model=row["model"], type=row["type"], value=row["value"])
                    roles[role.id].limits.append(rate_limit)
                if row["permission"]:
                    roles[role.id].permissions.append(PermissionType(value=row["permission"]))

            roles = list(roles.values())

            if role_id and len(roles) == 0:
                raise RoleNotFoundException()

        return roles

    async def create_user(self, name: str, password: str, role_id: int, expires_at: Optional[int] = None) -> int:
        password = self._get_hashed_password(password=password)
        expires_at = func.to_timestamp(expires_at) if expires_at is not None else None

        async with self.sql.session() as session:
            # check if role exists
            try:
                result = await session.execute(statement=select(RoleTable.id).where(RoleTable.id == role_id))
                result.scalar_one()
            except NoResultFound:
                raise RoleNotFoundException()

            # create the user
            try:
                await session.execute(statement=insert(table=UserTable).values(name=name, password=password, role_id=role_id, expires_at=expires_at))
            except IntegrityError:
                raise UserAlreadyExistsException()

            await session.commit()

            # get the user id
            result = await session.execute(statement=select(UserTable.id).where(UserTable.name == name))
            user_id = result.scalar_one()

            return user_id

    async def delete_user(self, user_id: int) -> None:
        async with self.sql.session() as session:
            # check if user exists
            try:
                result = await session.execute(statement=select(UserTable.id).where(UserTable.id == user_id))
                result.scalar_one()
            except NoResultFound:
                raise UserNotFoundException()

            # delete the user
            await session.execute(statement=delete(table=UserTable).where(UserTable.id == user_id))
            await session.commit()

    async def update_user(self, user_id: int, name: Optional[str] = None, password: Optional[str] = None, role_id: Optional[int] = None, expires_at: Optional[int] = None) -> None:  # fmt: off
        """
        TODO Attention ici car expires_at est toujours remplacé par la valeur passée en paramètre car None est une valeur valide pour expires_at.
        """
        async with self.sql.session() as session:
            # check if user exists
            result = await session.execute(
                statement=select(
                    UserTable.id,
                    UserTable.name,
                    UserTable.password,
                    UserTable.expires_at,
                    RoleTable.id.label("role_id"),
                    RoleTable.name.label("role"),
                ).where(UserTable.id == user_id)
            )
            try:
                user = result.all()[0]
            except IndexError:
                raise UserNotFoundException()

            # update the user
            name = name if name is not None else user.name
            password = self._get_hashed_password(password=password) if password is not None else user.password
            expires_at = func.to_timestamp(expires_at) if expires_at is not None else None

            if role_id is not None and role_id != user.role_id:
                # check if role exists
                result = await session.execute(statement=select(RoleTable.id).where(RoleTable.id == role_id))
                try:
                    result.scalar_one()
                except NoResultFound:
                    raise RoleNotFoundException()

            role_id = role_id if role_id is not None else user.role_id
            await session.execute(
                statement=update(table=UserTable)
                .values(name=name, password=password, role_id=role_id, expires_at=expires_at, updated_at=func.now())
                .where(UserTable.id == user.id)
            )
            await session.commit()

    async def get_users(self, user_id: Optional[str] = None, role_id: Optional[int] = None, offset: int = 0, limit: int = 10) -> List[User]:
        async with self.sql.session() as session:
            # then get all the data for these specific user IDs
            statement = (
                select(
                    UserTable.id,
                    UserTable.name,
                    UserTable.role_id.label("role"),
                    cast(func.extract("epoch", UserTable.expires_at), Integer),
                    cast(func.extract("epoch", UserTable.created_at), Integer),
                    cast(func.extract("epoch", UserTable.updated_at), Integer),
                )
                .offset(offset=offset)
                .limit(limit=limit)
            )
            if user_id:
                statement = statement.where(UserTable.id == user_id)
            if role_id:
                statement = statement.where(UserTable.role_id == role_id)

            result = await session.execute(statement=statement)

            # format the results
            users = [User(**row._mapping) for row in result.all()]

            if user_id and len(users) == 0:
                raise UserNotFoundException()

        return users

    async def create_token(self, name: str, user_id: int, expires_at: Optional[int] = None) -> Tuple[int, str]:
        async with self.sql.session() as session:
            # get the user id
            result = await session.execute(statement=select(UserTable).where(UserTable.id == user_id))
            try:
                user = result.scalar_one()
            except NoResultFound:
                raise UserNotFoundException()

            # create the token
            try:
                await session.execute(statement=insert(table=TokenTable).values(user_id=user.id, name=name))
                await session.commit()
            except IntegrityError:
                raise TokenAlreadyExistsException()

            # get the token id
            result = await session.execute(statement=select(TokenTable.id).where(TokenTable.name == name))
            token_id = result.scalar_one()

            # generate the token
            token = self._encode_token(user_id=user.id, token_id=token_id, expires_at=expires_at)

            # update the token
            expires_at = func.to_timestamp(expires_at) if expires_at is not None else None
            await session.execute(
                statement=update(table=TokenTable).values(token=f"{token[:8]}...{token[-8:]}", expires_at=expires_at).where(TokenTable.name == name)
            )
            await session.commit()

            return token_id, token

    async def delete_token(self, token_id: int) -> None:
        async with self.sql.session() as session:
            # check if token exists
            result = await session.execute(statement=select(TokenTable.id).where(TokenTable.id == token_id))
            try:
                result.scalar_one()
            except NoResultFound:
                raise TokenNotFoundException()

            # delete the token
            await session.execute(statement=delete(table=TokenTable).where(TokenTable.id == token_id))
            await session.commit()

    async def get_tokens(
        self, user_id: int, token_id: Optional[int] = None, exclude_expired: bool = False, offset: int = 0, limit: int = 10
    ) -> List[Token]:
        async with self.sql.session() as session:
            statement = (
                select(
                    TokenTable.id,
                    TokenTable.token,
                    TokenTable.name,
                    cast(func.extract("epoch", TokenTable.expires_at), Integer),
                    cast(func.extract("epoch", TokenTable.created_at), Integer),
                )
                .offset(offset=offset)
                .limit(limit=limit)
                .where(TokenTable.user_id == user_id)
            )
            if token_id:
                statement = statement.where(TokenTable.id == token_id)
            if exclude_expired:
                statement = statement.where(or_(TokenTable.expires_at.is_(None), TokenTable.expires_at >= func.now()))

            result = await session.execute(statement=statement)
            tokens = [Token(**row._mapping) for row in result.all()]

            if token_id and len(tokens) == 0:
                raise TokenNotFoundException()

            return tokens

    async def create_collection(self, name: str, user_id: int, type: CollectionType, description: Optional[str] = None) -> int:
        async with self.sql.session() as session:
            # check if user exists
            result = await session.execute(statement=select(UserTable.id).where(UserTable.id == user_id))
            try:
                result.scalar_one()
            except NoResultFound:
                raise UserNotFoundException()

            # create the collection
            await session.execute(statement=insert(table=CollectionTable).values(name=name, user_id=user_id, type=type, description=description))
            await session.commit()

            # get the collection id
            result = await session.execute(statement=select(CollectionTable.id).where(CollectionTable.name == name))
            collection_id = result.scalar_one()

            return collection_id

    async def delete_collection(self, collection_id: int) -> None:
        async with self.sql.session() as session:
            # check if collection exists
            result = await session.execute(statement=select(CollectionTable.id).where(CollectionTable.id == collection_id))
            try:
                result.scalar_one()
            except NoResultFound:
                raise CollectionNotFoundException()

            # delete the collection
            await session.execute(statement=delete(table=CollectionTable).where(CollectionTable.id == collection_id))
            await session.commit()

    async def update_collection(
        self, collection_id: int, name: Optional[str] = None, type: Optional[CollectionType] = None, description: Optional[str] = None
    ) -> None:
        async with self.sql.session() as session:
            # check if collection exists
            result = await session.execute(
                statement=select(CollectionTable)
                .join(target=UserTable, onclause=UserTable.id == CollectionTable.user_id)
                .where(CollectionTable.id == collection_id)
            )
            try:
                collection = result.scalar_one()
            except NoResultFound:
                raise CollectionNotFoundException()

            name = name if name is not None else collection.name
            type = type if type is not None else collection.type
            description = description if description is not None else collection.description

            await session.execute(
                statement=update(table=CollectionTable)
                .values(name=name, type=type, description=description, updated_at=func.now())
                .where(CollectionTable.id == collection.id)
            )
            await session.commit()

    async def get_collections(self, user_id: int, collection_id: Optional[int] = None, include_public: bool = True, offset: int = 0, limit: int = 10) -> List[Collection]:  # fmt: off
        async with self.sql.session() as session:
            statement = select(CollectionTable).offset(offset=offset).limit(limit=limit)

            if collection_id:
                statement = statement.where(CollectionTable.id == collection_id)
            if include_public:
                statement = statement.where(or_(CollectionTable.user_id == user_id, CollectionTable.type == CollectionType.PUBLIC))
            else:
                statement = statement.where(CollectionTable.user_id == user_id)

            # TODO: add documents count

            result = await session.execute(statement=statement)
            collections = result.all()

            if collection_id and len(collections) == 0:
                raise CollectionNotFoundException()

            collections = [Collection(**row._mapping) for row in result.all()]

        return collections

    async def create_document(self, name: str, collection_id: int, user_id: int) -> int:
        async with self.sql.session() as session:
            # check if collection exists
            result = await session.execute(statement=select(CollectionTable.documents).where(CollectionTable.id == collection_id))
            try:
                result.scalar_one()
            except NoResultFound:
                raise CollectionNotFoundException()

            await session.execute(statement=insert(table=DocumentTable).values(name=name, collection_id=collection_id, user_id=user_id))
            await session.commit()

            # get the document id
            result = await session.execute(statement=select(DocumentTable.id).where(DocumentTable.name == name))
            document_id = result.scalar_one()

            return document_id

    async def get_documents(self, collection_id: int, document_id: Optional[int] = None, offset: int = 0, limit: int = 10) -> List[Document]:  # fmt: off
        async with self.sql.session() as session:
            statement = select(DocumentTable).offset(offset=offset).limit(limit=limit).where(DocumentTable.collection_id == collection_id)

            if document_id:
                statement = statement.where(DocumentTable.id == document_id)

            result = await session.execute(statement=statement)
            documents = result.all()

            if document_id and len(documents) == 0:
                raise DocumentNotFoundException()

            documents = [Document(**row._mapping) for row in result.all()]

            return documents

    async def check_token(self, token: str, include_collections: bool = True) -> Optional[UserInfo]:
        # TODO: add cache
        async with self.sql.session() as session:
            if token == settings.auth.root_key:
                result = await session.execute(statement=select(UserTable.id).where(UserTable.name == settings.auth.root_user))
                user_id = result.scalar_one()
                users = await self.get_users(user_id=user_id)
                roles = await self.get_roles(role_id=users[0].role)

                return UserInfo.build(id=user_id, user=users[0], role=roles[0], collections=[])

            try:
                claims = self._decode_token(token=token)
            except JWTError:
                return
            except IndexError:  # malformed token (no token prefix)
                return

            try:
                tokens = await self.get_tokens(token_id=claims["token_id"], exclude_expired=True)
                assert tokens[0].user == claims["user_id"]
            except TokenNotFoundException:
                return

            users = await self.get_users(name=tokens[0].user)
            roles = await self.get_roles(name=users[0].role)
            collections = []
            if include_collections:
                collections = await self.get_collections(user=users[0].name)

            return UserInfo.build(id=users[0].id, user=users[0], role=roles[0], collections=collections)
