from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Type
import importlib


def to_camel_case(chaine):
    mots = chaine.replace("_", " ").split()
    camel_case = "".join(mot.capitalize() for mot in mots)
    return camel_case


class TrackerClient(ABC):
    @staticmethod
    def import_constructor(name: str) -> "Type[TrackerClient]":
        module = importlib.import_module(f"app.helpers.trackerclients._{name}trackerclient")
        return getattr(module, f"{to_camel_case(name)}TrackerClient")

    @abstractmethod
    async def track_event(self, user_id: str, event_type: str, event_properties: Optional[Dict[str, Any]] = None) -> None:
        pass
