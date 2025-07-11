from abc import ABC, abstractmethod
import importlib
from typing import Dict, List, Type

from app.schemas.agents import AgentsTool
from app.schemas.core.configuration import MCPBridgeType


class BaseMCPBridgeClient(ABC):
    @staticmethod
    def import_module(type: MCPBridgeType) -> "Type[BaseMCPBridgeClient]":
        """
        Import the module for the given MCP bridge type.
        """
        module = importlib.import_module(f"app.clients.mcp_bridge._{type.value}mcpbridgeclient")
        return getattr(module, f"{type.capitalize()}MCPBridgeClient")

    def __init__(self, url: str, headers: Dict[str, str], timeout: int, *args, **kwargs):
        self.url = url
        self.headers = headers
        self.timeout = timeout

    @abstractmethod
    async def get_tool_list(self) -> List[AgentsTool]:
        pass

    @abstractmethod
    async def call_tool(self, tool_name: str, params: str):
        pass
