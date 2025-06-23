from typing import List, Literal, Optional, Tuple

from jose import JWTError, jwt
from sqlalchemy import Integer, cast, delete, distinct, insert, or_, select, text, update
from sqlalchemy.exc import IntegrityError, NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func

from app.schemas.auth import Limit, PermissionType, Role, Tag, Token, User, UserTag
from app.sql.models import Limit as LimitTable
from app.sql.models import Permission as PermissionTable
from app.sql.models import Role as RoleTable
from app.sql.models import Tag as TagTable
from app.sql.models import Token as TokenTable
from app.sql.models import User as UserTable
from app.sql.models import UserTag as UserTagTable
from app.utils.exceptions import (
    DeleteRoleWithUsersException,
    RoleAlreadyExistsException,
    RoleNotFoundException,
    TagAlreadyExistsException,
    TagNotFoundException,
    TokenNotFoundException,
    UserAlreadyExistsException,
    UserNotFoundException,
)
from app.utils.settings import settings


class IdentityAccessManager:
    TOKEN_PREFIX = "sk-"

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

    async def create_role(
        self,
        session: AsyncSession,
        name: str,
        limits: List[Limit] = [],
        permissions: List[PermissionType] = [],
    ) -> int:
        # create the role
        try:
            result = await session.execute(statement=insert(table=RoleTable).values(name=name).returning(RoleTable.id))
            role_id = result.scalar_one()
            await session.commit()
        except IntegrityError:
            raise RoleAlreadyExistsException()

        # create the limits
        for limit in limits:
            await session.execute(statement=insert(table=LimitTable).values(role_id=role_id, model=limit.model, type=limit.type, value=limit.value))  # fmt: off

        # create the permissions
        for permission in permissions:
            await session.execute(statement=insert(table=PermissionTable).values(role_id=role_id, permission=permission))

        await session.commit()

        return role_id

    async def delete_role(self, session: AsyncSession, role_id: int) -> None:
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
        session: AsyncSession,
        role_id: int,
        name: Optional[str] = None,
        limits: Optional[List[Limit]] = None,
        permissions: Optional[List[PermissionType]] = None,
    ) -> None:
        # check if role exists
        result = await session.execute(statement=select(RoleTable).where(RoleTable.id == role_id))
        try:
            role = result.scalar_one()
        except NoResultFound:
            raise RoleNotFoundException()

        # update the role
        if name is not None:
            await session.execute(statement=update(table=RoleTable).values(name=name).where(RoleTable.id == role.id))

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

    async def get_roles(
        self,
        session: AsyncSession,
        role_id: Optional[int] = None,
        offset: int = 0,
        limit: int = 10,
        order_by: Literal["id", "name", "created_at", "updated_at"] = "id",
        order_direction: Literal["asc", "desc"] = "asc",
    ) -> List[Role]:
        if role_id is None:
            # get the unique role IDs with pagination
            statement = select(RoleTable.id).offset(offset=offset).limit(limit=limit).order_by(text(f"{order_by} {order_direction}"))
            result = await session.execute(statement=statement)
            selected_roles = [row[0] for row in result.all()]
        else:
            selected_roles = [role_id]

        # Query basic role data with user count
        role_query = (
            select(
                RoleTable.id,
                RoleTable.name,
                cast(func.extract("epoch", RoleTable.created_at), Integer).label("created_at"),
                cast(func.extract("epoch", RoleTable.updated_at), Integer).label("updated_at"),
                func.count(distinct(UserTable.id)).label("users"),
            )
            .outerjoin(UserTable, RoleTable.id == UserTable.role_id)
            .where(RoleTable.id.in_(selected_roles))
            .group_by(RoleTable.id)
            .order_by(text(f"{order_by} {order_direction}"))
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

    @staticmethod
    async def _check_if_tags_exist(session: AsyncSession, tag_ids: List[int]) -> None:
        result = await session.execute(statement=select(TagTable.id).where(TagTable.id.in_(tag_ids)))
        existing_tag_ids = {row.id for row in result.all()}
        missing_tag_ids = set(tag_ids) - existing_tag_ids
        if missing_tag_ids:
            raise TagNotFoundException(f"Tags with IDs {missing_tag_ids} not found")

    async def create_user(
        self,
        session: AsyncSession,
        name: str,
        role_id: int,
        tags: Optional[List[UserTag]] = None,
        budget: Optional[float] = None,
        expires_at: Optional[int] = None,
    ) -> int:
        expires_at = func.to_timestamp(expires_at) if expires_at is not None else None

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
                    budget=budget,
                    expires_at=expires_at,
                )
                .returning(UserTable.id)
            )
            user_id = result.scalar_one()
        except IntegrityError:
            raise UserAlreadyExistsException()

        # create the user tags
        if tags:
            await self._check_if_tags_exist(session=session, tag_ids=[tag.id for tag in tags])

            for user_tag in tags:
                await session.execute(statement=insert(table=UserTagTable).values(user_id=user_id, tag_id=user_tag.id, value=user_tag.value))

        await session.commit()

        return user_id

    async def delete_user(self, session: AsyncSession, user_id: int) -> None:
        # check if user exists
        result = await session.execute(statement=select(UserTable.id).where(UserTable.id == user_id))
        try:
            result.scalar_one()
        except NoResultFound:
            raise UserNotFoundException()

        # delete the user (user tags will be deleted by CASCADE)
        await session.execute(statement=delete(table=UserTable).where(UserTable.id == user_id))
        await session.commit()

    async def update_user(
        self,
        session: AsyncSession,
        user_id: int,
        name: Optional[str] = None,
        role_id: Optional[int] = None,
        tags: Optional[List[UserTag]] = None,
        budget: Optional[float] = None,
        expires_at: Optional[int] = None,
    ) -> None:
        """
        Update user. Warning: budget and expires_at are always replaced by the values passed as parameters because None is a valid value for budget and expires_at.

        Args:
            session: The session to use.
            user_id: The ID of the user to update.
            name: The new name of the user.
            role_id: The new role ID of the user.
            tags: The new tags of the user.
            budget: The new budget of the user.
            expires_at: The new expiration timestamp of the user.
        """
        # check if user exists
        result = await session.execute(
            statement=select(
                UserTable.id,
                UserTable.name,
                UserTable.role_id,
                UserTable.budget,
                UserTable.expires_at,
                RoleTable.name.label("role"),
            )
            .join(RoleTable, UserTable.role_id == RoleTable.id)
            .where(UserTable.id == user_id)
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

        # update user basic info
        await session.execute(
            statement=update(table=UserTable).values(name=name, role_id=role_id, budget=budget, expires_at=expires_at).where(UserTable.id == user.id)
        )

        # update user tags if provided
        if tags is not None:
            await self._check_if_tags_exist(session=session, tag_ids=[tag.id for tag in tags])

            # delete existing user tags
            await session.execute(statement=delete(table=UserTagTable).where(UserTagTable.user_id == user.id))

            # create new user tags
            if tags:
                for user_tag in tags:
                    await session.execute(statement=insert(table=UserTagTable).values(user_id=user.id, tag_id=user_tag.id, value=user_tag.value))

        await session.commit()

    async def get_users(
        self,
        session: AsyncSession,
        user_id: Optional[int] = None,
        role_id: Optional[int] = None,
        offset: int = 0,
        limit: int = 10,
        order_by: Literal["id", "name", "created_at", "updated_at"] = "id",
        order_direction: Literal["asc", "desc"] = "asc",
    ) -> List[User]:
        statement = (
            select(
                UserTable.id,
                UserTable.name,
                UserTable.role_id.label("role"),
                UserTable.budget,
                cast(func.extract("epoch", UserTable.expires_at), Integer).label("expires_at"),
                cast(func.extract("epoch", UserTable.created_at), Integer).label("created_at"),
                cast(func.extract("epoch", UserTable.updated_at), Integer).label("updated_at"),
            )
            .offset(offset=offset)
            .limit(limit=limit)
            .order_by(text(f"{order_by} {order_direction}"))
        )
        if user_id is not None:
            statement = statement.where(UserTable.id == user_id)
        if role_id is not None:
            statement = statement.where(UserTable.role_id == role_id)

        result = await session.execute(statement=statement)
        user_rows = result.all()

        if user_id is not None and len(user_rows) == 0:
            raise UserNotFoundException()

        # Get user IDs for tag query
        user_ids = [row.id for row in user_rows]

        # Get user tags
        user_tags_dict = {}
        if user_ids:
            tags_statement = select(UserTagTable.user_id, UserTagTable.tag_id, UserTagTable.value).where(UserTagTable.user_id.in_(user_ids))

            tags_result = await session.execute(statement=tags_statement)
            for row in tags_result:
                if row.user_id not in user_tags_dict:
                    user_tags_dict[row.user_id] = []
                user_tags_dict[row.user_id].append(UserTag(id=row.tag_id, value=row.value))

        # Build users with tags
        users = []
        for row in user_rows:
            user_data = row._mapping
            user_data = dict(user_data)
            user_data["tags"] = user_tags_dict.get(row.id, [])
            users.append(User(**user_data))

        return users

    async def create_token(self, session: AsyncSession, user_id: int, name: str, expires_at: Optional[int] = None) -> Tuple[int, str]:
        # get the user id
        result = await session.execute(statement=select(UserTable).where(UserTable.id == user_id))
        try:
            user = result.scalar_one()
        except NoResultFound:
            raise UserNotFoundException()

        # create the token
        result = await session.execute(statement=insert(table=TokenTable).values(user_id=user.id, name=name).returning(TokenTable.id))
        token_id = result.scalar_one()
        await session.commit()

        # generate the token
        token = self._encode_token(user_id=user.id, token_id=token_id, expires_at=expires_at)

        # update the token
        expires_at = func.to_timestamp(expires_at) if expires_at is not None else None
        await session.execute(
            statement=update(table=TokenTable).values(token=f"{token[:8]}...{token[-8:]}", expires_at=expires_at).where(TokenTable.id == token_id)
        )
        await session.commit()

        return token_id, token

    async def delete_token(self, session: AsyncSession, user_id: int, token_id: int) -> None:
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
        self,
        session: AsyncSession,
        user_id: int,
        token_id: Optional[int] = None,
        exclude_expired: bool = False,
        offset: int = 0,
        limit: int = 10,
        order_by: Literal["id", "name", "created_at"] = "id",
        order_direction: Literal["asc", "desc"] = "asc",
    ) -> List[Token]:
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
            .order_by(text(f"{order_by} {order_direction}"))
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

    async def check_token(self, session: AsyncSession, token: str) -> Tuple[Optional[int], Optional[int]]:
        try:
            claims = self._decode_token(token=token)
        except JWTError:
            return None, None
        except IndexError:  # malformed token (no token prefix)
            return None, None

        try:
            await self.get_tokens(session, user_id=claims["user_id"], token_id=claims["token_id"], exclude_expired=True)
        except TokenNotFoundException:
            return None, None

        return claims["user_id"], claims["token_id"]

    async def create_tag(self, session: AsyncSession, name: str) -> int:
        """Create a new tag."""
        try:
            result = await session.execute(statement=insert(table=TagTable).values(name=name).returning(TagTable.id))
            tag_id = result.scalar_one()
            await session.commit()
            return tag_id
        except IntegrityError:
            raise TagAlreadyExistsException()

    async def delete_tag(self, session: AsyncSession, tag_id: int) -> None:
        """Delete a tag."""
        # check if tag exists
        result = await session.execute(statement=select(TagTable).where(TagTable.id == tag_id))
        try:
            result.scalar_one()
        except NoResultFound:
            raise TagNotFoundException()

        # delete the tag (user tags will be deleted by CASCADE)
        await session.execute(statement=delete(table=TagTable).where(TagTable.id == tag_id))
        await session.commit()

    async def update_tag(
        self,
        session: AsyncSession,
        tag_id: int,
        name: Optional[str] = None,
    ) -> None:
        """Update a tag."""
        # check if tag exists
        result = await session.execute(statement=select(TagTable).where(TagTable.id == tag_id))
        try:
            tag = result.scalar_one()
        except NoResultFound:
            raise TagNotFoundException()

        # update the tag
        if name is not None:
            try:
                await session.execute(statement=update(table=TagTable).values(name=name).where(TagTable.id == tag.id))
                await session.commit()
            except IntegrityError:
                raise TagAlreadyExistsException()

    async def get_tags(
        self,
        session: AsyncSession,
        tag_id: Optional[int] = None,
        offset: int = 0,
        limit: int = 10,
        order_by: Literal["id", "name", "created_at", "updated_at"] = "id",
        order_direction: Literal["asc", "desc"] = "asc",
    ) -> List[Tag]:
        """Get tags with pagination and ordering."""
        statement = (
            select(
                TagTable.id,
                TagTable.name,
                cast(func.extract("epoch", TagTable.created_at), Integer).label("created_at"),
                cast(func.extract("epoch", TagTable.updated_at), Integer).label("updated_at"),
            )
            .offset(offset=offset)
            .limit(limit=limit)
            .order_by(text(f"{order_by} {order_direction}"))
        )

        if tag_id is not None:
            statement = statement.where(TagTable.id == tag_id)

        result = await session.execute(statement=statement)
        tag_rows = result.all()

        if tag_id is not None and len(tag_rows) == 0:
            raise TagNotFoundException()

        tags = [Tag(**row._mapping) for row in tag_rows]

        return tags
