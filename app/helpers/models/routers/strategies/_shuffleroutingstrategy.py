import random
from typing import List

from app.helpers.models.routers.strategies import BaseRoutingStrategy


class ShuffleRoutingStrategy(BaseRoutingStrategy):
    def __init__(self, clients: List[str]) -> None:
        super().__init__(clients)

    def choose_model_client(self) -> str:
        return random.choice(self.clients)
