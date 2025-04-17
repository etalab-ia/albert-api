from typing import Iterator, List

from app.clients.model import BaseModelClient as ModelClient
from app.helpers.strategies._basemodelclientselectionstrategy import BaseModelClientSelectionStrategy


class RoundRobinModelClientSelectionStrategy(BaseModelClientSelectionStrategy):
    def __init__(self, clients: List[ModelClient], cycle: Iterator[ModelClient]) -> None:
        super().__init__(clients)
        self.cycle = cycle

    def choose_model_client(self) -> ModelClient:
        return next(self.cycle)
