from abc import ABC, abstractmethod
from typing import List

from app.clients.model import BaseModelClient as ModelClient
from app.schemas.core.settings import Model as ModelSettings


class BaseModelClientSelectionStrategy(ABC):
    def __init__(self, clients: List[ModelSettings]) -> None:
        self.clients = clients

    @abstractmethod
    def choose_model_client(self) -> ModelClient:
        """
        Choose a client among the model's clients list

        Returns:
           BaseModelClient: The chosen client
        """
        pass
