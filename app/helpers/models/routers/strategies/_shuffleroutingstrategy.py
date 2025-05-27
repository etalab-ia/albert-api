import random
from typing import List

from app.helpers.models.routers.strategies import BaseRoutingStrategy
from app.schemas.strategymodelclient import StrategyModelClient


class ShuffleRoutingStrategy(BaseRoutingStrategy):
    def __init__(self, clients: List[StrategyModelClient]) -> None:
        super().__init__(clients)

    def choose_model_client(self) -> StrategyModelClient:
        return random.choice(self.clients)
