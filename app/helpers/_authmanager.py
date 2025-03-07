import traceback
from typing import List, Optional

import bcrypt
from jose import JWTError, jwt
from sqlalchemy import Integer, cast, delete, insert, or_, select, update
from sqlalchemy.exc import IntegrityError, NoResultFound
from sqlalchemy.sql import func

from app.clients.database import SQLDatabaseClient
from app.schemas.auth import Limit, PermissionType, Role, Token, User
from app.schemas.core.auth import AuthenticatedUser
from app.sql.models import Limit as LimitTable
from app.sql.models import Permission as PermissionTable
from app.sql.models import Role as RoleTable
from app.sql.models import Token as TokenTable
from app.sql.models import User as UserTable
from app.utils.exceptions import (
    DeleteRoleWithUsersException,
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


class AuthManager:
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
        token = token.split(AuthManager.TOKEN_PREFIX)[1]
        return jwt.decode(token=token, key=settings.auth.root_key, algorithms=["HS256"])

    @staticmethod
    def _encode_token(user_id: int, token_id: int, expires_at: Optional[int] = None) -> str:
        return AuthManager.TOKEN_PREFIX + jwt.encode(
            claims={"user_id": user_id, "token_id": token_id, "expires_at": expires_at},
            key=settings.auth.root_key,
            algorithm="HS256",
        )

    async def login(self, user: str, password: str) -> str:
        async with self.sql.session() as session:
            result = await session.execute(statement=select(UserTable).where(UserTable.name == user))
            try:
                user = result.scalar_one()
            except NoResultFound:
                raise UserNotFoundException()

            if not AuthManager._check_password(password=password, hashed_password=user.password):
                raise InvalidPasswordException()

            user = await self.get_users(name=user.name)

            return user[0]

    async def create_role(self, name: str, default: bool = False, limits: List[Limit] = [], permissions: List[PermissionType] = []) -> None:  # fmt: off
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

    async def delete_role(self, name: str) -> None:
        async with self.sql.session() as session:
            # check if role exists
            try:
                result = await session.execute(statement=select(RoleTable).where(RoleTable.name == name))
                result.scalar_one()
            except NoResultFound:
                raise RoleNotFoundException()

            # delete the role
            try:
                await session.execute(statement=delete(table=RoleTable).where(RoleTable.name == name))
            except IntegrityError:
                raise DeleteRoleWithUsersException()

            await session.commit()

    async def update_role(
        self,
        name: str,
        new_name: Optional[str] = None,
        default: Optional[bool] = None,
        limits: Optional[List[Limit]] = None,
        permissions: Optional[List[PermissionType]] = None,
    ) -> None:
        async with self.sql.session() as session:
            # check if role exists
            try:
                result = await session.execute(statement=select(RoleTable).where(RoleTable.name == name))
                role = result.scalar_one()
            except NoResultFound:
                raise RoleNotFoundException()

            # update the role
            name = new_name if new_name is not None else role.name
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

    async def get_roles(self, name: Optional[str] = None, offset: int = 0, limit: int = 10) -> List[Role]:
        async with self.sql.session() as session:
            # get the unique role IDs with pagination
            statement = select(RoleTable.id).offset(offset=offset).limit(limit=limit)

            if name:
                statement = statement.where(RoleTable.name == name)

            result = await session.execute(statement=statement)
            role_ids = [row[0] for row in result.all()]

            if name and len(role_ids) == 0:
                raise RoleNotFoundException()

            # then get all the data for these specific role IDs
            statement = (
                select(
                    RoleTable.name.label("id"),
                    RoleTable.default,
                    cast(func.extract("epoch", RoleTable.created_at), Integer).label("created_at"),
                    cast(func.extract("epoch", RoleTable.updated_at), Integer).label("updated_at"),
                    LimitTable.model.label("limit_model"),
                    LimitTable.type.label("limit_type"),
                    LimitTable.value.label("limit_value"),
                    PermissionTable.permission.label("permission"),
                )
                .outerjoin(target=LimitTable, onclause=RoleTable.id == LimitTable.role_id)
                .outerjoin(target=PermissionTable, onclause=RoleTable.id == PermissionTable.role_id)
                .where(RoleTable.id.in_(role_ids))
            )

            result = await session.execute(statement=statement)
            results = result.all()

            # format the results
            roles = {}
            for row in results:
                role = Role(id=row[0], default=row[1], created_at=row[2], updated_at=row[3], limits=[], permissions=[])
                if row[0] not in roles:
                    roles[row[0]] = role

                if row[4]:
                    rate_limit = Limit(model=row[4], type=row[5], value=row[6])
                    roles[row[0]].limits.append(rate_limit)
                if row[7]:
                    roles[row[0]].permissions.append(PermissionType(value=row[7]))

            roles = list(roles.values())

        return roles

    async def create_user(self, name: str, password: str, role: str, expires_at: Optional[int] = None) -> None:
        password = self._get_hashed_password(password=password)
        expires_at = func.to_timestamp(expires_at) if expires_at is not None else None

        async with self.sql.session() as session:
            # get the role id
            try:
                result = await session.execute(statement=select(RoleTable.id).where(RoleTable.name == role))
                role_id = result.scalar_one()
            except NoResultFound:
                raise RoleNotFoundException()

            # create the user
            try:
                await session.execute(statement=insert(table=UserTable).values(name=name, password=password, role_id=role_id, expires_at=expires_at))
            except IntegrityError:
                raise UserAlreadyExistsException()

            await session.commit()

    async def delete_user(self, name: str) -> None:
        async with self.sql.session() as session:
            # check if user exists
            try:
                result = await session.execute(statement=select(UserTable.id).where(UserTable.name == name))
                user_id = result.scalar_one()
            except NoResultFound:
                raise UserNotFoundException()

            # delete the user
            await session.execute(statement=delete(table=UserTable).where(UserTable.id == user_id))
            await session.commit()

    async def update_user(
        self, name: str, new_name: Optional[str] = None, password: Optional[str] = None, role: Optional[str] = None, expires_at: Optional[int] = None
    ) -> None:
        """
        Attention ici car expires_at est toujours remplacé par la valeur passée en paramètre car None est une valeur valide pour expires_at.
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
                    RoleTable.name.label("role_name"),
                )
                .join(target=RoleTable, onclause=UserTable.role_id == RoleTable.id)
                .where(UserTable.name == name)
            )
            try:
                user = result.all()[0]
            except NoResultFound:
                raise UserNotFoundException()

            # update the user
            name = new_name if new_name is not None else user.name
            password = self._get_hashed_password(password=password) if password is not None else user.password
            expires_at = func.to_timestamp(expires_at) if expires_at is not None else None

            role_id = None
            if role is not None and role != user.role_name:
                # check if role exists
                result = await session.execute(statement=select(RoleTable.id).where(RoleTable.name == role))
                try:
                    role_id = result.scalar_one()
                except NoResultFound:
                    raise RoleNotFoundException()

            role_id = role_id if role_id is not None else user.role_id
            await session.execute(
                statement=update(table=UserTable)
                .values(
                    name=name,
                    password=password,
                    role_id=role_id,
                    expires_at=expires_at,
                    updated_at=func.now(),
                )
                .where(UserTable.id == user.id)
            )
            await session.commit()

    async def get_users(self, name: Optional[str] = None, role: Optional[str] = None, offset: int = 0, limit: int = 10) -> List[User]:
        async with self.sql.session() as session:
            # get the unique user IDs with pagination
            statement = select(UserTable.id).offset(offset=offset).limit(limit=limit)

            if name:
                statement = statement.where(UserTable.name == name)
            if role:
                statement = statement.where(RoleTable.name == role)

            result = await session.execute(statement=statement)
            user_ids = [row[0] for row in result.all()]

            if (name or role) and len(user_ids) == 0:
                raise UserNotFoundException()

            # then get all the data for these specific user IDs
            statement = (
                select(
                    UserTable.name.label("id"),
                    cast(func.extract("epoch", UserTable.expires_at), Integer).label("expires_at"),
                    cast(func.extract("epoch", UserTable.created_at), Integer).label("created_at"),
                    cast(func.extract("epoch", UserTable.updated_at), Integer).label("updated_at"),
                    RoleTable.name.label("role"),
                )
                .outerjoin(target=RoleTable, onclause=UserTable.role_id == RoleTable.id)
                .where(UserTable.id.in_(user_ids))
            )
            result = await session.execute(statement=statement)

            # format the results
            users = [User(**row._mapping) for row in result.all()]

        return users

    async def create_token(self, name: str, user: str, expires_at: Optional[int] = None) -> None:
        async with self.sql.session() as session:
            # get the user id
            result = await session.execute(statement=select(UserTable).where(UserTable.name == user))
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
            result = await session.execute(statement=select(TokenTable).where(TokenTable.name == name))
            token = result.scalar_one()

            # generate the token
            token = self._encode_token(user_id=user.id, token_id=token.id, expires_at=expires_at)

            # update the token
            expires_at = func.to_timestamp(expires_at) if expires_at is not None else None
            await session.execute(
                statement=update(table=TokenTable).values(token=f"{token[:8]}...{token[-8:]}", expires_at=expires_at).where(TokenTable.name == name)
            )
            await session.commit()

    async def check_token(self, token: str) -> Optional[AuthenticatedUser]:
        def get_user_and_role(token: str) -> tuple[User, Role]:
            # TODO FINISH THIS
            statement = (
                select(
                    UserTable.id.label("id"),
                    UserTable.name.label("user"),
                    RoleTable.name.label("role"),
                    cast(func.extract("epoch", UserTable.expires_at), Integer).label("expires_at"),
                    PermissionTable.permission.label("permission"),
                    LimitTable.model.label("limit_model"),
                    LimitTable.type.label("limit_type"),
                    LimitTable.value.label("limit_value"),
                )
                .select_from(TokenTable)
                .join(target=UserTable, onclause=TokenTable.user_id == UserTable.id)
                .join(target=RoleTable, onclause=UserTable.role_id == RoleTable.id)
                .outerjoin(target=PermissionTable, onclause=RoleTable.id == PermissionTable.role_id)
                .outerjoin(target=LimitTable, onclause=RoleTable.id == LimitTable.role_id)
                .where(TokenTable.user_id == claims["user_id"])
                .where(TokenTable.id == claims["token_id"])
                .where(or_(TokenTable.expires_at.is_(None), TokenTable.expires_at >= func.now()))
            ).limit(limit=1)

            results = result.all()

        async with self.sql.session() as session:
            if token == settings.auth.root_key:
                result = await session.execute(statement=select(UserTable.id).where(UserTable.name == settings.auth.root_user))
                user_id = result.scalar_one()
                users = await self.get_users(name=settings.auth.root_user)
                roles = await self.get_roles(name=ROOT_ROLE)

                return AuthenticatedUser.from_user_and_role(id=user_id, user=users[0], role=roles[0])

            try:
                claims = self._decode_token(token=token)
            except JWTError:
                return
            except IndexError:  # malformed token (no token prefix)
                return

            statement = (
                select(
                    UserTable.id.label("id"),
                    UserTable.name.label("user"),
                    RoleTable.name.label("role"),
                )
                .select_from(TokenTable)
                .join(target=UserTable, onclause=TokenTable.user_id == UserTable.id)
                .join(target=RoleTable, onclause=UserTable.role_id == RoleTable.id)
                .where(TokenTable.user_id == claims["user_id"])
                .where(TokenTable.id == claims["token_id"])
                .where(or_(TokenTable.expires_at.is_(None), TokenTable.expires_at >= func.now()))
            )

            result = await session.execute(statement=statement)
            user = result.first()

            if user is None:
                return

            users = await self.get_users(name=user.user)
            roles = await self.get_roles(name=user.role)

            return AuthenticatedUser.from_user_and_role(id=user.id, user=users[0], role=roles[0])

    async def delete_token(self, name: str, user: str) -> None:
        async with self.sql.session() as session:
            # check if user exists
            try:
                result = await session.execute(statement=select(UserTable.id).where(UserTable.name == user))
                user_id = result.scalar_one()
            except NoResultFound:
                raise TokenNotFoundException()

            # check if token exists and retrieve the internal token id
            result = await session.execute(
                statement=select(TokenTable.id)
                .join(target=UserTable, onclause=TokenTable.user_id == UserTable.id)
                .where(UserTable.id == user_id)
                .where(TokenTable.name == name)
            )
            try:
                token_id = result.scalar_one()
            except NoResultFound:
                raise TokenNotFoundException()

            # delete the token
            await session.execute(statement=delete(table=TokenTable).where(TokenTable.id == token_id))
            await session.commit()

    async def get_tokens(
        self, name: Optional[str] = None, user: Optional[str] = None, exclude_expired: bool = False, offset: int = 0, limit: int = 10
    ) -> List[Token]:
        statement = (
            select(
                TokenTable.name.label("id"),
                TokenTable.token,
                cast(func.extract("epoch", TokenTable.expires_at), Integer).label("expires_at"),
                cast(func.extract("epoch", TokenTable.created_at), Integer).label("created_at"),
                UserTable.name.label("user"),
            )
            .join(target=UserTable, onclause=TokenTable.user_id == UserTable.id)
            .offset(offset=offset)
            .limit(limit=limit)
        )
        if name:
            statement = statement.where(TokenTable.name == name)
        if user:
            statement = statement.where(UserTable.name == user)
        if exclude_expired:
            statement = statement.where(or_(TokenTable.expires_at.is_(None), TokenTable.expires_at >= func.now()))

        async with self.sql.session() as session:
            result = await session.execute(statement=statement)
            tokens = [Token(**row._mapping) for row in result.all()]

        if name and len(tokens) == 0:
            raise TokenNotFoundException()

        return tokens
