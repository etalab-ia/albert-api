from typing import Iterator, List

from app.helpers.models.routers.strategies import BaseRoutingStrategy


class RoundRobinRoutingStrategy(BaseRoutingStrategy):
    def __init__(self, clients: List[str], cycle: Iterator[str]) -> None:
        super().__init__(clients)
        self.cycle = cycle

    def choose_model_client(self) -> str:
        return next(self.cycle)
