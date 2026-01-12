"""
Base classes for Digital Geoff tool integrations.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


@dataclass
class ToolResult:
    """Result from a tool execution."""
    success: bool
    data: Any = None
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }


class BaseTool(ABC):
    """
    Base class for all Digital Geoff tools.

    Tools can be implemented via:
    1. MCP (Model Context Protocol) - preferred
    2. Direct API calls
    3. SDK wrappers
    """

    name: str = "base_tool"
    description: str = "Base tool description"

    @abstractmethod
    async def execute(self, action: str, parameters: dict) -> ToolResult:
        """Execute an action with the given parameters."""
        pass

    @abstractmethod
    def get_actions(self) -> list[dict]:
        """Return list of available actions with their schemas."""
        pass

    def get_tool_definition(self) -> dict:
        """Return Claude-compatible tool definition."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "description": "The action to perform",
                        "enum": [a["name"] for a in self.get_actions()]
                    },
                    "parameters": {
                        "type": "object",
                        "description": "Parameters for the action"
                    }
                },
                "required": ["action"]
            }
        }


class MCPTool(BaseTool):
    """
    MCP-based tool that connects via Model Context Protocol.

    MCP provides standardized access to tools with:
    - Authentication handling
    - Schema validation
    - Error handling
    - Rate limiting
    """

    def __init__(self, mcp_server_url: str, auth_token: Optional[str] = None):
        self.mcp_server_url = mcp_server_url
        self.auth_token = auth_token
        # In production: Initialize MCP client
        # from mcp import Client
        # self.client = Client(mcp_server_url, auth_token)

    async def execute(self, action: str, parameters: dict) -> ToolResult:
        """Execute via MCP server."""
        try:
            # Production MCP call:
            # result = await self.client.call_tool(self.name, action, parameters)
            # return ToolResult(success=True, data=result)

            # Placeholder
            return ToolResult(
                success=True,
                data={"message": f"MCP call to {self.name}.{action}"},
                metadata={"mcp_server": self.mcp_server_url}
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))
