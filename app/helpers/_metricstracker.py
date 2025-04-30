from typing import List


# Class to compute and keep metrics about a model router's model clients
class MetricsTracker:
    def __init__(self, urls: List[str], refresh_rate: int, refresh_count_per_window: int) -> None:
        self.urls = urls
        self.refresh_rate = refresh_rate
        self.refresh_count_per_window = refresh_count_per_window

    async def monitor(self) -> None:
        # TODO: To implement
        pass

    async def stop_monitor(self) -> None:
        # TODO: To implement
        pass
