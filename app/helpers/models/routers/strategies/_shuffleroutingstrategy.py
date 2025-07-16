import random
from typing import List, TYPE_CHECKING

from app.helpers.models.routers.strategies import BaseRoutingStrategy


if TYPE_CHECKING:
    # only for type‐checkers and linters, not at runtime
    # Used to break circular import
    from app.clients.model import BaseModelClient


class ShuffleRoutingStrategy(BaseRoutingStrategy):
    def __init__(self, clients: List["BaseModelClient"]) -> None:
        super().__init__(clients)

    def choose_model_client(self) -> "BaseModelClient":
        return random.choice(self.clients)
