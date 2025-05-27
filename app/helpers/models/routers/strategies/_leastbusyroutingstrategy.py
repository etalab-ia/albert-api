from typing import List

from app.helpers.models.routers.strategies import BaseRoutingStrategy
from app.schemas.strategymodelclient import StrategyModelClient


class LeastBusyRoutingStrategy(BaseRoutingStrategy):
    def __init__(self, clients: List[StrategyModelClient]) -> None:
        super().__init__(clients)

    def choose_model_client(self) -> StrategyModelClient:
        # TODO: Return the client's information with the smallest score (lowest time to first token)
        # Time to first token is computed for each model client from the data gathered by the table Usage
        pass
