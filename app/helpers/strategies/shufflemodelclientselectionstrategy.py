import random
from typing import List

from app.helpers.strategies._basemodelclientselectionstrategy import BaseModelClientSelectionStrategy


class ShuffleModelClientSelectionStrategy(BaseModelClientSelectionStrategy):
    def __init__(self, clients: List[str]) -> None:
        super().__init__(clients)

    def choose_model_client(self) -> str:
        return random.choice(self.clients)
