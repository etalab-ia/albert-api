from typing import List

from app.clients.model import BaseModelClient as ModelClient
from app.helpers.strategies._basemodelclientselectionstrategy import BaseModelClientSelectionStrategy


class LeastBusyModelClientSelectionStrategy(BaseModelClientSelectionStrategy):
    def __init__(self, clients: List[ModelClient]) -> None:
        super().__init__(clients)

    def choose_model_client(self) -> ModelClient:
        # TODO: Return the client with the smallest score (lowest time to first token)
        # time to first token is computed for each model client through the data gathered by the model router's metric tracker
        pass
