from sqlalchemy import select, insert, delete  # Integer, cast, delete, distinct, func, insert, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.sql.models import ModelRouter as ModelRouterTable
from app.sql.models import ModelRouterAlias as ModelRouterAliasTable
from app.sql.models import ModelClient as ModelClientTable
from app.helpers.models.routers import ModelRouter
from app.clients.model import BaseModelClient as ModelClient

class ModelDatabaseManager:
    def __init__(self):
        pass
    
    async def get_routers(self, session: AsyncSession):
        routers = []
        # Get all ModelRouter rows and cnvert it from a list of 1-dimensional vectors to a list of ModelRouters
        db_routers = [row[0] for row in (await session.execute(select(ModelRouterTable))).fetchall()]

        if not db_routers:
            return []

        for router in db_routers:
            # Get all ModelAlias rows and convert from a list of 1-dimensional vectors to a list of values
            db_aliases = [
                row[0]
                for row in (await session.execute(select(ModelRouterAliasTable).where(ModelRouterAliasTable.model_router_id == router.id))).fetchall()
            ]

            db_clients = [
                row[0] for row in (await session.execute(select(ModelClientTable).where(ModelClientTable.model_router_id == router.id))).fetchall()
            ]
            
            assert db_clients, f"No ModelClients found in database for ModelRouter {router.id}"

            clients = []
            for client in db_clients:
                clients.append(ModelClient.from_orm(client))
                #clients.append(ModelClient(model=client.model, costs=client.costs, carbon=client.carbon))
                pass
                # @TODO functional client creation from database

            #routers.append(
            #    ModelRouter(id=router["id"], type=router["type"], aliases=db_aliases, routing_strategy=router["routing_strategy"], clients=clients)
            #)
        return routers
    
    async def add_router(self, router):
        pass
    
    async def delete_router(self, router):
        pass