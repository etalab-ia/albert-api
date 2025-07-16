from typing import Iterator, List, TYPE_CHECKING

from app.helpers.models.routers.strategies import BaseRoutingStrategy


if TYPE_CHECKING:
    # only for type‐checkers and linters, not at runtime
    # Used to break circular import
    from app.clients.model import BaseModelClient


class RoundRobinRoutingStrategy(BaseRoutingStrategy):
    def __init__(self, clients: List["BaseModelClient"], cycle: Iterator["BaseModelClient"]) -> None:
        super().__init__(clients)
        self.cycle = cycle

    def choose_model_client(self) -> "BaseModelClient":
        return next(self.cycle)
