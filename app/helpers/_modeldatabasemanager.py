from sqlalchemy import select, insert, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.sql.models import Model as ModelRouterTable
from app.sql.models import ModelRouterAlias as ModelRouterAliasTable
from app.sql.models import ModelClient as ModelClientTable
from types import SimpleNamespace
from app.schemas.core.configuration import Model as ModelRouterSchema
from app.schemas.core.configuration import ModelProvider as ModelProviderSchema
from app.schemas.core.configuration import Configuration


class ModelDatabaseManager:

    @staticmethod
    async def get_routers(session: AsyncSession, configuration: Configuration, dependencies: SimpleNamespace):
        routers = []

        # Get all ModelRouter rows and convert it from a list of 1-dimensional vectors to a list of ModelRouters
        db_routers = [row[0] for row in (await session.execute(select(ModelRouterTable))).fetchall()]

        if not db_routers:
            return []

        for router in db_routers:
            # Get all ModelAlias rows and convert from a list of 1-dimensional vectors to a list of values
            db_aliases = [
                row[0]
                for row in (await session.execute(select(ModelRouterAliasTable).where(ModelRouterAliasTable.model_router_name == router.name))).fetchall()
            ]

            db_clients = [
                row[0]
                for row in (await session.execute(select(ModelClientTable).where(ModelClientTable.model_router_name == router.name))).fetchall()
            ]
            
            assert db_clients, f"No ModelClients found in database for ModelRouter {router.name}"

            providers = [ModelProviderSchema.model_validate(client) for client in db_clients]
            routers.append(ModelRouterSchema.model_validate({**router.__dict__, "providers": providers, "aliases": db_aliases}))

        return routers
    
    @staticmethod
    async def add_router(session: AsyncSession, router: ModelRouterSchema):

        router_result = (await session.execute(select(ModelRouterTable).where(ModelRouterTable.name == router.name))).fetchall()

        assert not router_result, "tried adding already existing router"

        await session.execute(
            insert(ModelRouterTable).values(**router.model_dump(include={"name", "type", "routing_strategy", "owned_by", "from_config"}))
        )

        for alias in router.aliases:
            await session.execute(insert(ModelRouterAliasTable).values(alias=alias, model_router_name=router.name))

        for client in router.providers:
            await session.execute(
                insert(ModelClientTable).values(**client.model_dump(),
                    model_router_name = router.name
                )
            )
        await session.commit()

    @staticmethod
    async def add_client(session: AsyncSession, router_name: str, client: ModelProviderSchema):
        client_result = (
            await session.execute(
                select(ModelClientTable)
                    .where(ModelClientTable.model_router_name == router_name)
                    .where(ModelClientTable.model_name == client.name)
                    .where(ModelClientTable.url == client.url)
            )
        ).fetchall()

        assert not client_result, "tried adding already existing client"

        await session.execute(
            insert(ModelClientTable).values(**client.model_dump(),
                    model_router_name = router_name
                )
        )
        await session.commit()

    @staticmethod
    async def add_alias(session: AsyncSession, router_name: str, alias: str):
        alias_result = (
            await session.execute(
                select(ModelRouterAliasTable)
                    .where(ModelRouterAliasTable.model_router_name == router_name)
                    .where(ModelRouterAliasTable.alias == alias)
            )
        ).fetchall()

        assert not alias_result, "tried to add already-existing alias"
        await session.execute(insert(ModelRouterAliasTable).values(alias=alias, model_router_name=router_name))
    
        await session.commit()

    @staticmethod
    async def delete_router(session: AsyncSession, router_name: str):
        # Check if objects exist
        router_result = (await session.execute(select(ModelRouterTable).where(ModelRouterTable.name == router_name))).fetchall()
        alias_result = (await session.execute(delete(ModelRouterAliasTable).where(ModelRouterAliasTable.model_router_name == router_name))).fetchall()
        client_result = (await session.execute(select(ModelClientTable).where(ModelClientTable.model_router_name == router_name))).fetchall()
        
        assert router_result, f"ModelRouter {router_name} not found in DB"

        await session.execute(delete(ModelRouterTable).where(ModelRouterTable.name == router_name))

        if alias_result:
            await session.execute(delete(ModelRouterAliasTable).where(ModelRouterAliasTable.model_router_name == router_name))
        if client_result:
            await session.execute(delete(ModelClientTable).where(ModelClientTable.model_router_name == router_name))
        
        await session.commit()

    @staticmethod
    async def delete_client(session: AsyncSession, router_name: str, model_name: str, model_url: str):
        client_result = (
            await session.execute(
                select(ModelClientTable)
                    .where(ModelClientTable.model_router_name == router_name)
                    .where(ModelClientTable.model_name == model_name)
                    .where(ModelClientTable.url == model_url)
            )
        ).fetchall()

        assert client_result, "tried to delete non-existing client"
        await session.execute(
            delete(ModelClientTable)
                .where(ModelClientTable.model_router_name == router_name)
                .where(ModelClientTable.model_name == model_name)
                .where(ModelClientTable.url == model_url)
        )
        
        await session.commit()

    @staticmethod
    async def delete_alias(session: AsyncSession, router_name: str, alias: str):
        alias_result = (
            await session.execute(
                select(ModelRouterAliasTable)
                    .where(ModelRouterAliasTable.model_router_name == router_name)
                    .where(ModelRouterAliasTable.alias == alias)
            )
        ).fetchall()

        assert alias_result, "tried to delete non-existing alias"
        await session.execute(
            delete(ModelRouterAliasTable)
                .where(ModelRouterAliasTable.model_router_name == router_name)
                .where(ModelRouterAliasTable.alias == alias)
        )
    
        await session.commit()
