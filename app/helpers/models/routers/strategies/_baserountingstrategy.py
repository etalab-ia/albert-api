from abc import ABC, abstractmethod
from typing import List


class BaseRoutingStrategy(ABC):
    def __init__(self, clients: List[str]) -> None:
        self.clients = clients

    @abstractmethod
    def choose_model_client(self) -> str:
        """
        Choose a client url among the model's clients urls list

        Returns:
           str: The chosen client's url
        """
        pass
