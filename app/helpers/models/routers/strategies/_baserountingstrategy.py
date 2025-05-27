from abc import ABC, abstractmethod
from typing import List
from app.schemas.strategymodelclient import StrategyModelClient


class BaseRoutingStrategy(ABC):
    # We pass a list composed of the client's URL and model name instead of a list of ModelClient to manipulate simpler objects in message consumer worker
    def __init__(self, clients: List[StrategyModelClient]) -> None:
        self.clients = clients

    @abstractmethod
    def choose_model_client(self) -> StrategyModelClient:
        """
        Choose a client (url + model name) among the model's clients list

        Returns:
           StrategyModelClient: The chosen client's information
        """
        pass
