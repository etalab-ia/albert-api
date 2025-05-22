import random
from typing import List

from app.clients.model import BaseModelClient as ModelClient
from app.helpers.models.routers.strategies import BaseRoutingStrategy


class ShuffleRoutingStrategy(BaseRoutingStrategy):
    def __init__(self, clients: List[ModelClient]) -> None:
        super().__init__(clients)

    def choose_model_client(self) -> ModelClient:
        return random.choice(self.clients)
