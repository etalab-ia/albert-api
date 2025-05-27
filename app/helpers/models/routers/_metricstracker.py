from typing import List

from app.schemas.strategymodelclient import StrategyModelClient


# Class to compute and keep metrics about a model router's model clients
class MetricsTracker:
    def __init__(self, clients: List[StrategyModelClient], refresh_rate: int, refresh_count_per_window: int) -> None:
        self.clients = clients
        self.refresh_rate = refresh_rate
        self.refresh_count_per_window = refresh_count_per_window

    async def start_monitoring(self) -> None:
        # TODO: To implement with calls to get_server_metrics
        pass

    async def stop_monitoring(self) -> None:
        # TODO: To implement
        pass
