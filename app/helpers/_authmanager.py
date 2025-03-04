import traceback
from typing import List, Optional

import bcrypt
from jose import JWTError, jwt
from sqlalchemy import Integer, cast, delete, insert, select, update, or_
from sqlalchemy.exc import IntegrityError, NoResultFound
from sqlalchemy.sql import func

from app.clients.database import SQLDatabaseClient
from app.schemas.roles import RateLimit, RateLimitType, Role
from app.schemas.tokens import Token
from app.schemas.users import User
from app.sql.models import RateLimit as RateLimitTable
from app.sql.models import Role as RoleTable
from app.sql.models import Token as TokenTable
from app.sql.models import User as UserTable
from app.utils.exceptions import (
    AddUserToMasterRoleException,
    CreateTokenForMasterUserException,
    DeleteMasterRoleException,
    DeleteMasterTokenException,
    DeleteMasterUserException,
    DeleteRoleWithUsersException,
    RoleAlreadyExistsException,
    RoleNotFoundException,
    TokenAlreadyExistsException,
    TokenNotFoundException,
    UpdateMasterRoleException,
    UpdateMasterUserException,
    UserAlreadyExistsException,
    UserNotFoundException,
)
from app.utils.logging import logger
from app.utils.settings import settings


# TODO: add documentation docstrings
class AuthManager:
    TOKEN_PREFIX = "sk-"
    MASTER_ROLE_ID = "master"
    MASTER_USER_ID = "master"
    MASTER_TOKEN = "master"

    # TODO: change user to user_id, etc
    # TODO: fix check_token
    # TODO: add cache to check_token
    # TODO: raise an error if database is not reachable
    # TODO: add docstrings

    def __init__(self, client: SQLDatabaseClient) -> None:
        """
        Initialize the authentication client: create the master user and role if they don't exist and check if the master password is correct and update it if needed
        """

        self.client = client

    async def setup(self):
        # initialize create the default master role and user
        async with self.client.session() as session:
            # get the currently master data
            result = await session.execute(
                statement=select(RoleTable.id.label("role_id"), UserTable.id.label("user_id"), TokenTable.token)
                .outerjoin(target=UserTable, onclause=RoleTable.id == UserTable.role_id)
                .outerjoin(target=TokenTable, onclause=UserTable.id == TokenTable.user_id)
                .where(RoleTable.display_id == self.MASTER_ROLE_ID)
            )
            currently_master = result.all()

            if currently_master:
                assert len(currently_master) == 1, "Master role have more than one user or token, please check the database."
                currently_master = [row._mapping for row in currently_master][0]

                if currently_master["token"]:
                    assert self._check_password(password=settings.auth.master_key, hashed_password=currently_master["token"]), "Provided master key is not matching with stored master key"  # fmt: off

                # delete currently master user
                try:
                    await session.execute(statement=delete(table=UserTable).where(UserTable.id == currently_master["user_id"]))
                    await session.commit()
                except Exception:
                    logger.debug(msg=traceback.format_exc())
                    raise Exception("Failed to delete currently master user.")

                # delete the currently master role
                try:
                    await session.execute(statement=delete(table=RoleTable).where(RoleTable.id == currently_master["role_id"]))
                    await session.commit()
                except Exception:
                    logger.debug(msg=traceback.format_exc())
                    raise Exception("Failed to delete currently master role.")

            # create the master role
            try:
                await session.execute(statement=insert(table=RoleTable).values(display_id=self.MASTER_ROLE_ID, default=True, admin=True))
                await session.commit()
            except Exception:
                logger.debug(msg=traceback.format_exc())
                raise Exception("Failed to create default master role.")

            result = await session.execute(statement=select(RoleTable).where(RoleTable.display_id == self.MASTER_ROLE_ID))
            self.master_role_id = result.scalar_one().id

            # create the master role limits
            try:
                await session.execute(
                    statement=insert(table=RateLimitTable).values(
                        [
                            {"role_id": self.master_role_id, "model_id": "*", "type": RateLimitType.RPD, "value": None},
                            {"role_id": self.master_role_id, "model_id": "*", "type": RateLimitType.RPM, "value": None},
                            {"role_id": self.master_role_id, "model_id": "*", "type": RateLimitType.TPM, "value": None},
                        ]
                    )
                )
                await session.commit()
            except Exception:
                logger.debug(msg=traceback.format_exc())
                raise Exception("Failed to create default master role limits.")

            # create the master user
            try:
                await session.execute(
                    statement=insert(table=UserTable).values(
                        display_id=self.MASTER_USER_ID,
                        password=self._get_hashed_password(password=settings.auth.master_password),
                        role_id=self.master_role_id,
                    )
                )
                await session.commit()
            except Exception:
                logger.debug(msg=traceback.format_exc())
                raise Exception("Failed to create master user.")

            result = await session.execute(statement=select(UserTable).where(UserTable.display_id == self.MASTER_USER_ID))
            self.master_user_id = result.scalar_one().id

            # create the master token
            try:
                await session.execute(
                    statement=insert(table=TokenTable).values(
                        user_id=self.master_user_id, display_id=self.MASTER_TOKEN, token=self._get_hashed_password(password=settings.auth.master_key)
                    )
                )
                await session.commit()
            except Exception:
                logger.debug(msg=traceback.format_exc())
                raise Exception("Failed to create master token.")

    @staticmethod
    def _get_hashed_password(password: str) -> str:
        return bcrypt.hashpw(password=password.encode(encoding="utf-8"), salt=bcrypt.gensalt()).decode(encoding="utf-8")

    @staticmethod
    def _check_password(password: str, hashed_password: str) -> bool:
        return bcrypt.checkpw(password=password.encode(encoding="utf-8"), hashed_password=hashed_password.encode(encoding="utf-8"))

    @staticmethod
    def _decode_token(token: str) -> dict:
        token = token.split(AuthManager.TOKEN_PREFIX)[1]
        return jwt.decode(token=token, key=settings.auth.master_key, algorithms=["HS256"])

    @staticmethod
    def _encode_token(user_id: int, token_id: int, expires_at: Optional[int] = None) -> str:
        return AuthManager.TOKEN_PREFIX + jwt.encode(
            claims={"user_id": user_id, "token_id": token_id, "expires_at": expires_at}, key=settings.auth.master_key, algorithm="HS256"
        )

    async def create_role(self, role_id: str, default: bool = False, admin: bool = False, limits: List[RateLimit] = []) -> str:
        async with self.client.session() as session:
            # create the role
            try:
                await session.execute(statement=insert(table=RoleTable).values(display_id=role_id, default=default, admin=admin))
                await session.commit()
            except IntegrityError:
                raise RoleAlreadyExistsException()

            # create the policies
            if limits:
                # get internal role id
                result = await session.execute(statement=select(RoleTable).where(RoleTable.display_id == role_id))
                role = result.scalar_one()

                for limit in limits:
                    await session.execute(
                        statement=insert(table=RateLimitTable).values(
                            role_id=role.id,
                            model_id=limit.model,
                            type=limit.type,
                            value=limit.value,
                        )
                    )
                await session.commit()
            return role_id

    async def delete_role(self, role_id: str) -> None:
        async with self.client.session() as session:
            if role_id == self.MASTER_ROLE_ID:
                raise DeleteMasterRoleException()

            # check if role exists
            await self.get_roles(role_id=role_id)

            # delete the role
            try:
                await session.execute(statement=delete(table=RoleTable).where(RoleTable.display_id == role_id))
            except IntegrityError:
                raise DeleteRoleWithUsersException()

            await session.commit()

    async def update_role(
        self,
        role_id: str,
        display_id: Optional[str] = None,
        default: Optional[bool] = None,
        admin: Optional[bool] = None,
        limits: Optional[List[RateLimit]] = None,
    ) -> None:
        async with self.client.session() as session:
            if role_id == self.MASTER_ROLE_ID:
                raise UpdateMasterRoleException()

            # check if role exists
            try:
                result = await session.execute(statement=select(RoleTable).where(RoleTable.display_id == role_id))
                role = result.scalar_one()
            except NoResultFound:
                raise RoleNotFoundException()

            # update the role
            display_id = display_id if display_id is not None else role.display_id
            if default:
                # change the currently default role to not be default
                result = await session.execute(statement=select(RoleTable).where(RoleTable.default))
                existing_default_role = result.scalar_one()
                await session.execute(statement=update(table=RoleTable).values(default=False).where(RoleTable.id == existing_default_role.id))

            default = default if default is not None else role.default
            admin = admin if admin is not None else role.admin

            try:
                await session.execute(
                    statement=update(table=RoleTable)
                    .values(display_id=display_id, default=default, admin=admin, updated_at=func.now())
                    .where(RoleTable.id == role.id)
                )
            except IntegrityError:
                raise RoleAlreadyExistsException()
            except NoResultFound:
                raise RoleNotFoundException()

            if limits:
                # delete the existing limits
                await session.execute(statement=delete(table=RateLimitTable).where(RateLimitTable.role_id == role.id))

                # create the new limits
                for limit in limits:
                    await session.execute(
                        statement=insert(table=RateLimitTable).values(role_id=role.id, model_id=limit.model, type=limit.type, value=limit.value)
                    )
            await session.commit()

    async def get_roles(self, role_id: Optional[str] = None, offset: int = 0, limit: int = 10) -> List[Role]:
        async with self.client.session() as session:
            statement = (
                select(
                    RoleTable.display_id.label("id"),
                    RoleTable.default,
                    RoleTable.admin,
                    cast(func.extract("epoch", RoleTable.created_at), Integer).label("created_at"),
                    cast(func.extract("epoch", RoleTable.updated_at), Integer).label("updated_at"),
                    RateLimitTable.model_id.label("limit_model_id"),
                    RateLimitTable.type.label("limit_type"),
                    RateLimitTable.value.label("limit_value"),
                    cast(func.extract("epoch", RateLimitTable.created_at), Integer).label("limit_created_at"),
                    cast(func.extract("epoch", RateLimitTable.updated_at), Integer).label("limit_updated_at"),
                )
                .outerjoin(target=RateLimitTable, onclause=RoleTable.id == RateLimitTable.role_id)
                .offset(offset=offset)
                .limit(limit=limit)
            )

            if role_id:
                statement = statement.where(RoleTable.display_id == role_id)

            result = await session.execute(statement=statement)
            results = result.all()

            # format the results
            roles = {}
            for row in results:
                role = Role(
                    id=row[0],
                    default=row[1],
                    admin=row[2],
                    created_at=row[3],
                    updated_at=row[4],
                    limits=[],
                )
                if row[0] not in roles:
                    roles[row[0]] = role

                if row[5]:
                    rate_limit = RateLimit(
                        model=row[5],
                        type=row[6]._value_ if row[6] else None,
                        value=row[7],
                        created_at=row[8],
                        updated_at=row[9],
                    )
                    roles[row[0]].limits.append(rate_limit)

            roles = list(roles.values())

            if role_id and len(roles) == 0:
                raise RoleNotFoundException()

        return roles

    async def create_user(
        self, user_id: str, password: str, role_id: str, budget_allocation: Optional[float] = None, budget_reset: Optional[str] = None
    ) -> str:
        password = self._get_hashed_password(password=password)

        async with self.client.session() as session:
            # get the role id
            try:
                result = await session.execute(statement=select(RoleTable).where(RoleTable.display_id == role_id))
                role = result.scalar_one()
            except NoResultFound:
                raise RoleNotFoundException()

            # create the user
            try:
                await session.execute(
                    statement=insert(table=UserTable).values(
                        display_id=user_id,
                        password=password,
                        role_id=role.id,
                        budget_allocation=budget_allocation,
                        budget_reset=budget_reset,
                    )
                )
            except IntegrityError:
                raise UserAlreadyExistsException()
            await session.commit()

        return user_id

    async def delete_user(self, user_id: str) -> None:
        async with self.client.session() as session:
            if user_id == self.MASTER_USER_ID:
                raise DeleteMasterUserException()

            # check if user exists
            await self.get_users(user_id=user_id)

            # delete the user
            await session.execute(statement=delete(table=UserTable).where(UserTable.display_id == user_id))
            await session.commit()

    async def update_user(
        self,
        user_id: str,
        display_id: Optional[str] = None,
        password: Optional[str] = None,
        role_id: Optional[str] = None,
        budget_allocation: Optional[float] = None,
        budget_reset: Optional[str] = None,
    ) -> None:
        async with self.client.session() as session:
            if user_id == self.MASTER_USER_ID:
                raise UpdateMasterUserException()

            if role_id == self.MASTER_ROLE_ID:
                raise AddUserToMasterRoleException()

            # check if user exists
            result = await session.execute(
                statement=select(
                    UserTable.id,
                    UserTable.display_id,
                    UserTable.password,
                    UserTable.budget_allocation,
                    UserTable.budget_reset,
                    RoleTable.id.label("role_id"),
                    RoleTable.display_id.label("role_display_id"),
                )
                .join(target=RoleTable, onclause=UserTable.role_id == RoleTable.id)
                .where(UserTable.display_id == user_id)
            )
            try:
                user = result.scalar_one()
            except NoResultFound:
                raise UserNotFoundException()

            # update the user
            display_id = display_id if display_id is not None else user.display_id
            password = self._get_hashed_password(password=password) if password is not None else user.password

            if role_id != user.role_display_id:
                # check if role exists
                result = await session.execute(statement=select(RoleTable).where(RoleTable.display_id == role_id))
                try:
                    role = result.scalar_one()
                except NoResultFound:
                    raise RoleNotFoundException()

                role_id = role.id

            role_id = role_id if role_id is not None else user.role_id
            budget_allocation = budget_allocation if budget_allocation is not None else user.budget_allocation
            budget_reset = budget_reset if budget_reset is not None else user.budget_reset
            await session.execute(
                statement=update(table=UserTable)
                .values(
                    display_id=display_id,
                    password=password,
                    role_id=role_id,
                    budget_allocation=budget_allocation,
                    budget_reset=budget_reset,
                    updated_at=func.now(),
                )
                .where(UserTable.id == user.id)
            )
            await session.commit()

    async def get_users(
        self, user_id: Optional[str] = None, role_id: Optional[str] = None, admin: bool = False, offset: int = 0, limit: int = 10
    ) -> List[User]:
        async with self.client.session() as session:
            statement = (
                select(
                    UserTable.display_id.label("id"),
                    cast(func.extract("epoch", UserTable.created_at), Integer).label("created_at"),
                    cast(func.extract("epoch", UserTable.updated_at), Integer).label("updated_at"),
                    RoleTable.display_id.label("role"),
                )
                .outerjoin(target=RoleTable, onclause=UserTable.role_id == RoleTable.id)
                .offset(offset=offset)
                .limit(limit=limit)
            )
            if admin:
                statement = statement.where(RoleTable.admin)
            if user_id:
                statement = statement.where(UserTable.display_id == user_id)
            if role_id:
                statement = statement.where(RoleTable.display_id == role_id)

            result = await session.execute(statement=statement)
            users = [User(**row._mapping) for row in result.all()]

            if user_id and len(users) == 0:
                raise UserNotFoundException()

        return users

    async def create_token(self, user_id: str, token_id: str, expires_at: Optional[int] = None) -> str:
        if user_id == self.MASTER_USER_ID:
            raise CreateTokenForMasterUserException()

        async with self.client.session() as session:
            # get the user id
            result = await session.execute(statement=select(UserTable).where(UserTable.display_id == user_id))
            try:
                user = result.scalar_one()
            except NoResultFound:
                raise UserNotFoundException()

            # create the token
            _expires_at = func.to_timestamp(expires_at) if expires_at is not None else None
            try:
                await session.execute(statement=insert(table=TokenTable).values(user_id=user.id, display_id=token_id, expires_at=_expires_at))
                await session.commit()
            except IntegrityError:
                raise TokenAlreadyExistsException()

            # get the token id
            result = await session.execute(statement=select(TokenTable).where(TokenTable.display_id == token_id))
            token = result.scalar_one()

            # generate the token
            token = self._encode_token(user_id=user.id, token_id=token.id, expires_at=expires_at)

            # update the token
            # TODO: [:8]
            await session.execute(statement=update(table=TokenTable).values(token=token).where(TokenTable.display_id == token_id))
            await session.commit()

        return token

    async def check_token(self, token: str, admin: bool = False) -> Optional[User]:
        if token == settings.auth.master_key:
            return User(id=self.MASTER_USER_ID, created_at=0, updated_at=0, role=self.MASTER_ROLE_ID)

        try:
            claims = self._decode_token(token=token)
        except JWTError:
            return
        except IndexError:  # malformed token (no token prefix)
            return

        async with self.client.session() as session:
            statement = (
                select(
                    UserTable.display_id.label("id"),
                    cast(func.extract("epoch", UserTable.created_at), Integer).label("created_at"),
                    cast(func.extract("epoch", UserTable.updated_at), Integer).label("updated_at"),
                    RoleTable.display_id.label("role"),
                )
                .select_from(TokenTable)
                .join(target=UserTable, onclause=TokenTable.user_id == UserTable.id)
                .join(target=RoleTable, onclause=UserTable.role_id == RoleTable.id)
                .where(TokenTable.user_id == claims["user_id"])
                .where(TokenTable.id == claims["token_id"])
                .where(or_(TokenTable.expires_at.is_(None), TokenTable.expires_at >= func.now()))
            )

            if admin:
                statement = statement.where(RoleTable.admin)

            result = await session.execute(statement=statement)
            user = result.first()

            if user is None:
                return

            return User(**user._mapping)

    async def delete_token(self, user_id: str, token_id: str) -> None:
        if user_id == self.MASTER_USER_ID:
            raise DeleteMasterTokenException()

        # check if user exists
        await self.get_users(user_id=user_id)

        # check if token exists and retrieve the internal token id
        async with self.client.session() as session:
            result = await session.execute(
                statement=select(TokenTable.id)
                .join(target=UserTable, onclause=TokenTable.user_id == UserTable.id)
                .where(UserTable.display_id == user_id)
                .where(TokenTable.display_id == token_id)
            )
            try:
                token = result.scalar_one()
            except NoResultFound:
                raise TokenNotFoundException()

            # delete the token
            await session.execute(statement=delete(table=TokenTable).where(TokenTable.id == token.id))
            await session.commit()

    async def get_tokens(self, user_id: Optional[str] = None, token_id: Optional[str] = None, offset: int = 0, limit: int = 10) -> List[Token]:
        statement = (
            select(
                TokenTable.display_id.label("id"),
                TokenTable.token,
                cast(func.extract("epoch", TokenTable.expires_at), Integer).label("expires_at"),
                cast(func.extract("epoch", TokenTable.created_at), Integer).label("created_at"),
                cast(func.extract("epoch", TokenTable.updated_at), Integer).label("updated_at"),
                UserTable.display_id.label("user"),
            )
            .join(target=UserTable, onclause=TokenTable.user_id == UserTable.id)
            .offset(offset=offset)
            .limit(limit=limit)
        )
        if user_id:
            statement = statement.where(UserTable.display_id == user_id)
        if token_id:
            statement = statement.where(TokenTable.display_id == token_id)

        async with self.client.session() as session:
            result = await session.execute(statement=statement)
            tokens = [Token(**row._mapping) for row in result.all()]

        if user_id and len(tokens) == 0:
            raise UserNotFoundException()

        if token_id and len(tokens) == 0:
            raise TokenNotFoundException()

        return tokens
