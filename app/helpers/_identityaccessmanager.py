from typing import List, Optional, Tuple

from jose import JWTError, jwt
from sqlalchemy import Integer, cast, delete, distinct, insert, or_, select, update
from sqlalchemy.exc import IntegrityError, NoResultFound
from sqlalchemy.sql import func

from app.clients.database import SQLDatabaseClient
from app.schemas.auth import Limit, PermissionType, Role, Token, User
from app.sql.models import Limit as LimitTable
from app.sql.models import Permission as PermissionTable
from app.sql.models import Role as RoleTable
from app.sql.models import Token as TokenTable
from app.sql.models import User as UserTable
from app.utils.exceptions import (
    DeleteRoleWithUsersException,
    RoleAlreadyExistsException,
    RoleNotFoundException,
    TokenAlreadyExistsException,
    TokenNotFoundException,
    UserAlreadyExistsException,
    UserNotFoundException,
)
from app.utils.settings import settings


class IdentityAccessManager:
    TOKEN_PREFIX = "sk-"

    def __init__(self, sql: SQLDatabaseClient) -> None:
        self.sql = sql

    @staticmethod
    def _decode_token(token: str) -> dict:
        token = token.split(IdentityAccessManager.TOKEN_PREFIX)[1]
        return jwt.decode(token=token, key=settings.auth.master_key, algorithms=["HS256"])

    @staticmethod
    def _decode_token(token: str) -> dict:
        token = token.split(IdentityAccessManager.TOKEN_PREFIX)[1]
        return jwt.decode(token=token, key=settings.auth.master_key, algorithms=["HS256"])

    @staticmethod
    def _encode_token(user_id: int, token_id: int, expires_at: Optional[int] = None) -> str:
        return IdentityAccessManager.TOKEN_PREFIX + jwt.encode(
            claims={"user_id": user_id, "token_id": token_id, "expires_at": expires_at},
            key=settings.auth.master_key,
            algorithm="HS256",
        )

    async def create_role(self, name: str, default: bool = False, limits: List[Limit] = [], permissions: List[PermissionType] = []) -> int:
        async with self.sql.session() as session:
            # create the role
            try:
                result = await session.execute(statement=insert(table=RoleTable).values(name=name).returning(RoleTable.id))
                role_id = result.scalar_one()
                await session.commit()
            except IntegrityError:
                raise RoleAlreadyExistsException()

            # set the role as default if needed
            if default:
                # change the currently default role to not be default
                result = await session.execute(statement=select(RoleTable).where(RoleTable.default))
                existing_default_role = result.scalar_one_or_none()
                if existing_default_role:
                    await session.execute(statement=update(table=RoleTable).values(default=False).where(RoleTable.id == existing_default_role.id))

            await session.execute(statement=update(table=RoleTable).values(default=default).where(RoleTable.id == role_id))

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
            result = await session.execute(statement=select(RoleTable).where(RoleTable.id == role_id))
            try:
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
            result = await session.execute(statement=select(RoleTable).where(RoleTable.id == role_id))
            try:
                role = result.scalar_one()
            except NoResultFound:
                raise RoleNotFoundException()

            # update the role
            name = name if name is not None else role.name
            if default:
                # change the currently default role to not be default
                result = await session.execute(statement=select(RoleTable).where(RoleTable.default))
                existing_default_role = result.scalar_one_or_none()
                if existing_default_role:
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
            if role_id is None:
                # get the unique role IDs with pagination
                statement = select(RoleTable.id).offset(offset=offset).limit(limit=limit)
                result = await session.execute(statement=statement)
                selected_roles = [row[0] for row in result.all()]
            else:
                selected_roles = [role_id]

            # Query basic role data with user count
            role_query = (
                select(
                    RoleTable.id,
                    RoleTable.name,
                    RoleTable.default,
                    cast(func.extract("epoch", RoleTable.created_at), Integer).label("created_at"),
                    cast(func.extract("epoch", RoleTable.updated_at), Integer).label("updated_at"),
                    func.count(distinct(UserTable.id)).label("users"),
                )
                .outerjoin(UserTable, RoleTable.id == UserTable.role_id)
                .where(RoleTable.id.in_(selected_roles))
                .group_by(RoleTable.id)
            )

            result = await session.execute(role_query)
            role_results = [row._asdict() for row in result.all()]

            if role_id is not None and len(role_results) == 0:
                raise RoleNotFoundException()

            # Build roles dictionary
            roles = {}
            for row in role_results:
                roles[row["id"]] = Role(
                    id=row["id"],
                    name=row["name"],
                    default=row["default"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                    users=row["users"],
                    limits=[],
                    permissions=[],
                )

            # Query limits for these roles
            if roles:
                limits_query = select(LimitTable.role_id, LimitTable.model, LimitTable.type, LimitTable.value).where(
                    LimitTable.role_id.in_(list(roles.keys()))
                )

                result = await session.execute(limits_query)
                for row in result:
                    role_id = row.role_id
                    if role_id in roles:
                        roles[role_id].limits.append(Limit(model=row.model, type=row.type, value=row.value))

                # Query permissions for these roles
                permissions_query = select(PermissionTable.role_id, PermissionTable.permission).where(PermissionTable.role_id.in_(list(roles.keys())))

                result = await session.execute(permissions_query)
                for row in result:
                    role_id = row.role_id
                    if role_id in roles:
                        roles[role_id].permissions.append(PermissionType(value=row.permission))

            return list(roles.values())

    async def create_user(self, name: str, role_id: int, expires_at: Optional[int] = None) -> int:
        expires_at = func.to_timestamp(expires_at) if expires_at is not None else None

        async with self.sql.session() as session:
            # check if role exists
            result = await session.execute(statement=select(RoleTable.id).where(RoleTable.id == role_id))
            try:
                result.scalar_one()
            except NoResultFound:
                raise RoleNotFoundException()

            # create the user
            try:
                result = await session.execute(
                    statement=insert(table=UserTable)
                    .values(
                        name=name,
                        role_id=role_id,
                        expires_at=expires_at,
                    )
                    .returning(UserTable.id)
                )
                user_id = result.scalar_one()
            except IntegrityError:
                raise UserAlreadyExistsException()

            await session.commit()

            return user_id

    async def delete_user(self, user_id: int) -> None:
        async with self.sql.session() as session:
            # check if user exists
            result = await session.execute(statement=select(UserTable.id).where(UserTable.id == user_id))
            try:
                result.scalar_one()
            except NoResultFound:
                raise UserNotFoundException()

            # delete the user
            await session.execute(statement=delete(table=UserTable).where(UserTable.id == user_id))
            await session.commit()

    async def update_user(self, user_id: int, name: Optional[str] = None, role_id: Optional[int] = None, expires_at: Optional[int] = None) -> None:
        """
        Attention ici car expires_at est toujours remplacé par la valeur passée en paramètre car None est une valeur valide pour expires_at.
        """
        async with self.sql.session() as session:
            # check if user exists
            result = await session.execute(
                statement=select(
                    UserTable.id,
                    UserTable.name,
                    # UserTable.password,
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
                .values(name=name, role_id=role_id, expires_at=expires_at, updated_at=func.now())
                .where(UserTable.id == user.id)
            )
            await session.commit()

    async def get_users(self, user_id: Optional[int] = None, role_id: Optional[int] = None, offset: int = 0, limit: int = 10) -> List[User]:
        async with self.sql.session() as session:
            # then get all the data for these specific user IDs
            statement = (
                select(
                    UserTable.id,
                    UserTable.name,
                    UserTable.role_id.label("role"),
                    cast(func.extract("epoch", UserTable.expires_at), Integer).label("expires_at"),
                    cast(func.extract("epoch", UserTable.created_at), Integer).label("created_at"),
                    cast(func.extract("epoch", UserTable.updated_at), Integer).label("updated_at"),
                )
                .offset(offset=offset)
                .limit(limit=limit)
            )
            if user_id is not None:
                statement = statement.where(UserTable.id == user_id)
            if role_id is not None:
                statement = statement.where(UserTable.role_id == role_id)

            result = await session.execute(statement=statement)
            users = [User(**row._mapping) for row in result.all()]

            if user_id is not None and len(users) == 0:
                raise UserNotFoundException()

        return users

    async def create_token(self, user_id: int, name: str, expires_at: Optional[int] = None) -> Tuple[int, str]:
        async with self.sql.session() as session:
            # get the user id
            result = await session.execute(statement=select(UserTable).where(UserTable.id == user_id))
            try:
                user = result.scalar_one()
            except NoResultFound:
                raise UserNotFoundException()

            # create the token
            try:
                result = await session.execute(statement=insert(table=TokenTable).values(user_id=user.id, name=name).returning(TokenTable.id))
                token_id = result.scalar_one()
                await session.commit()
            except IntegrityError:
                raise TokenAlreadyExistsException()

            # generate the token
            token = self._encode_token(user_id=user.id, token_id=token_id, expires_at=expires_at)

            # update the token
            expires_at = func.to_timestamp(expires_at) if expires_at is not None else None
            await session.execute(
                statement=update(table=TokenTable).values(token=f"{token[:8]}...{token[-8:]}", expires_at=expires_at).where(TokenTable.name == name)
            )
            await session.commit()

            return token_id, token

    async def delete_token(self, user_id: int, token_id: int) -> None:
        async with self.sql.session() as session:
            # check if token exists
            result = await session.execute(statement=select(TokenTable.id).where(TokenTable.id == token_id).where(TokenTable.user_id == user_id))
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
                    TokenTable.name,
                    TokenTable.token,
                    TokenTable.user_id.label("user"),
                    cast(func.extract("epoch", TokenTable.expires_at), Integer).label("expires_at"),
                    cast(func.extract("epoch", TokenTable.created_at), Integer).label("created_at"),
                )
                .offset(offset=offset)
                .limit(limit=limit)
            ).where(TokenTable.user_id == user_id)

            if token_id is not None:
                statement = statement.where(TokenTable.id == token_id)
            if exclude_expired is not None:
                statement = statement.where(or_(TokenTable.expires_at.is_(None), TokenTable.expires_at >= func.now()))

            result = await session.execute(statement=statement)
            tokens = [Token(**row._mapping) for row in result.all()]

            if token_id is not None and len(tokens) == 0:
                raise TokenNotFoundException()

            return tokens

    async def check_token(self, token: str) -> Optional[Tuple[int, int]]:
        async with self.sql.session() as session:
            try:
                claims = self._decode_token(token=token)
            except JWTError:
                return
            except IndexError:  # malformed token (no token prefix)
                return

            try:
                tokens = await self.get_tokens(user_id=claims["user_id"], token_id=claims["token_id"], exclude_expired=True)
            except TokenNotFoundException:
                return

            return claims["user_id"], claims["token_id"]
