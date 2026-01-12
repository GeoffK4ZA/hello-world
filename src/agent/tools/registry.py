"""
Tool Registry for Digital Geoff.

Central registry that manages all available tools and their configurations.
"""

from typing import Any, Optional
from .base import BaseTool, ToolResult


class ToolRegistry:
    """
    Central registry for all Digital Geoff tools.

    Handles:
    - Tool registration and discovery
    - Execution routing
    - Tool definition generation for Claude
    """

    def __init__(self):
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool):
        """Register a tool with the registry."""
        self._tools[tool.name] = tool

    def get(self, name: str) -> Optional[BaseTool]:
        """Get a tool by name."""
        return self._tools.get(name)

    async def execute(
        self,
        tool_name: str,
        action: str,
        parameters: dict
    ) -> Any:
        """Execute a tool action."""
        tool = self._tools.get(tool_name)
        if not tool:
            raise ValueError(f"Unknown tool: {tool_name}")

        result = await tool.execute(action, parameters)
        if not result.success:
            raise RuntimeError(f"Tool execution failed: {result.error}")

        return result.data

    def get_tool_definitions(self) -> list[dict]:
        """Get Claude-compatible tool definitions for all registered tools."""
        definitions = []
        for tool in self._tools.values():
            definitions.append(tool.get_tool_definition())
        return definitions

    def list_tools(self) -> list[str]:
        """List all registered tool names."""
        return list(self._tools.keys())
