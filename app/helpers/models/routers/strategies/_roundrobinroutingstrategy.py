from typing import Iterator, List

from app.helpers.models.routers.strategies import BaseRoutingStrategy
from app.schemas.strategymodelclient import StrategyModelClient


class RoundRobinRoutingStrategy(BaseRoutingStrategy):
    def __init__(self, clients: List[StrategyModelClient], cycle: Iterator[StrategyModelClient]) -> None:
        super().__init__(clients)
        self.cycle = cycle

    def choose_model_client(self) -> StrategyModelClient:
        return next(self.cycle)
