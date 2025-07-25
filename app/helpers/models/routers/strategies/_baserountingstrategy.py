from abc import ABC, abstractmethod
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    # only for type‐checkers and linters, not at runtime
    # Used to break circular import
    from app.clients.model import BaseModelClient



class BaseRoutingStrategy(ABC):
    def __init__(self, clients: List["BaseModelClient"]) -> None:
        self.clients = clients

    @abstractmethod
    def choose_model_client(self) -> "BaseModelClient":
        """
        Choose a client among the model's clients list

        Returns:
           BaseModelClient: The chosen client
        """
        pass
