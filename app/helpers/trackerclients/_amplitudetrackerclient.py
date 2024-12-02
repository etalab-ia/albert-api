from typing import Any, Dict, Optional
import httpx

from app.helpers.trackerclients import TrackerClient
from app.utils.exceptions import AnalyticsException


class AmplitudeTrackerClient(TrackerClient):
    def __init__(self, url: str, api_key: str) -> None:
        self.url = url
        self.api_key = api_key
        self.client = httpx.AsyncClient()

    async def track_event(self, user_id: str, event_type: str, event_properties: Optional[Dict[str, Any]] = None) -> None:
        payload = {"api_key": self.api_key, "events": [{"user_id": user_id, "event_type": event_type, "event_properties": event_properties or {}}]}

        try:
            await self.client.post(self.url, json=payload)
        except Exception:
            raise AnalyticsException()

    async def close(self) -> None:
        await self.client.aclose()
