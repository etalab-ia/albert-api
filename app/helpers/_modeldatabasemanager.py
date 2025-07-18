from sqlalchemy import select, insert, delete  # Integer, cast, delete, distinct, func, insert, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.sql.models import ModelRouter as ModelRouterTable
from app.sql.models import ModelRouterAlias as ModelRouterAliasTable
from app.sql.models import ModelClient as ModelClientTable
from app.helpers.models.routers import ModelRouter
from app.clients.model import BaseModelClient as ModelClient
from types import SimpleNamespace
from app.schemas.core.configuration import Configuration
from app.schemas.models_providing import ModelClientSchema
from app.schemas.core.configuration import ModelProviderType

class ModelDatabaseManager:
    def __init__(self):
        pass
    
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
                row[0] for row in (await session.execute(select(ModelClientTable).where(ModelClientTable.model_router_name == router.name))).fetchall()
            ]
            
            assert db_clients, f"No ModelClients found in database for ModelRouter {router.name}"

            providers = []
            for client in db_clients:
                providers.append(ModelClient.import_module(type=ModelProviderType(client.type))(
                    redis=dependencies.redis,
                    metrics_retention_ms=configuration.settings.metrics_retention_ms,
                    model_name=client.model_name,
                    url=client.url,
                    key=client.key,
                    timeout=client.timeout,
                    model_cost_prompt_tokens=client.model_cost_prompt_tokens,
                    model_cost_completion_tokens=client.model_cost_completion_tokens,
                    model_carbon_footprint_zone=client.model_carbon_footprint_zone,
                    model_carbon_footprint_active_params=client.model_carbon_footprint_active_params,
                    model_carbon_footprint_total_params=client.model_carbon_footprint_total_params,
                ))

            routers.append(
               ModelRouter(name=router.name, type=router.type, aliases=db_aliases, routing_strategy=router.routing_strategy, providers=providers, owned_by=router.owned_by, from_config=router.from_config)
            )
        return routers
    
    @staticmethod
    async def add_router(session: AsyncSession, router: ModelRouter):
        # @TODO Throw an error if the model already exists or let the db unique name requirement handle it ? 
        print(router.from_config)
        await session.execute(
            insert(ModelRouterTable).values(name=router.name, type=router.type, routing_strategy=router.routing_strategy, from_config=router.from_config, owned_by=router.owned_by)
        )

        for alias in router.aliases:
            await session.execute(insert(ModelRouterAliasTable).values(alias=alias, model_router_name=router.name))

        # @TODO Check why clients is private
        for client in router._providers:
            await session.execute(
                insert(ModelClientTable).values(
                    url = client.url,
                    key = client.key,
                    timeout = client.timeout,
                    model_name = client.name,
                    model_carbon_footprint_zone = client.carbon_footprint_zone,
                    model_carbon_footprint_total_params = client.carbon_footprint_total_params,
                    model_carbon_footprint_active_params = client.carbon_footprint_active_params,
                    model_cost_prompt_tokens = client.cost_prompt_tokens,
                    model_cost_completion_tokens = client.cost_completion_tokens,
                    metrics_retention_ms = client.metrics_retention_ms,
                    type = type(client).__name__.removesuffix("ModelClient").lower(),
                    model_router_name = router.name
                )
            )
        await session.commit()

    @staticmethod
    async def add_client(session: AsyncSession, router_name: str, client: ModelClient):
        client_result = (await session.execute(select(ModelClientTable)
                                  .where(ModelClientTable.router_name == router_name)
                                  .where(ModelClientTable.model_name == client.name)
                                  .where(ModelClientTable.url == client.url))).fetchall()

        assert not client_result, "tried adding already existing client"

        await session.execute(
            insert(ModelClientTable).values(
                url = client.url,
                key = client.key,
                timeout = client.timeout,
                model_name = client.name,
                model_carbon_footprint_zone = client.carbon_footprint_zone,
                model_carbon_footprint_total_params = client.carbon_footprint_total_params,
                model_carbon_footprint_active_params = client.carbon_footprint_active_params,
                model_cost_prompt_tokens = client.cost_prompt_tokens,
                model_cost_completion_tokens = client.cost_completion_tokens,
                metrics_retention_ms = client.metrics_retention_ms,
                type = type(client).__name__.removesuffix("ModelClient").lower(),
                model_router_name = router_name
            )
        )
        await session.commit()

    @staticmethod
    async def add_alias(session: AsyncSession, router_name: str, alias: str):
        alias_result = (await session.execute(select(ModelRouterAliasTable)
                                  .where(ModelRouterAliasTable.router_name == router_name)
                                  .where(ModelRouterAliasTable.alias == alias))).fetchall()

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
            await session.execute(select(ModelClientTable)
                                  .where(ModelClientTable.router_name == router_name)
                                  .where(ModelClientTable.model_name == model_name)
                                  .where(ModelClientTable.model_url == model_url))).fetchall()

        assert client_result, "tried to delete non-existing client"
        await session.execute(delete(ModelClientTable)
                                .where(ModelClientTable.router_name == router_name)
                                .where(ModelClientTable.model_name == model_name)
                                .where(ModelClientTable.model_url == model_url))
        
        await session.commit()

    @staticmethod
    async def delete_alias(session: AsyncSession, router_name: str, alias: str):
        alias_result = (
            await session.execute(select(ModelRouterAliasTable)
                                  .where(ModelRouterAliasTable.router_name == router_name)
                                  .where(ModelRouterAliasTable.alias == alias))).fetchall()

        assert alias_result, "tried to delete non-existing alias"
        await session.execute(delete(ModelRouterAliasTable)
                                .where(ModelRouterAliasTable.router_name == router_name)
                                .where(ModelRouterAliasTable.alias == alias))
    
        await session.commit()
    

