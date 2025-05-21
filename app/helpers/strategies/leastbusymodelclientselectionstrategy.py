from typing import List

from app.helpers.strategies._basemodelclientselectionstrategy import BaseModelClientSelectionStrategy


class LeastBusyModelClientSelectionStrategy(BaseModelClientSelectionStrategy):
    def __init__(self, clients: List[str]) -> None:
        super().__init__(clients)

    def choose_model_client(self) -> str:
        # TODO: Return the client's url with the smallest score (lowest time to first token)
        # Time to first token is computed for each model client through the data gathered by the model router's metric tracker
        pass
