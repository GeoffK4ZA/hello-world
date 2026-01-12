"""
Digital Geoff Tool Integrations

MCP-first tool layer for connecting to external services:
- Microsoft 365 (Outlook, Teams, OneDrive)
- Google Workspace (Sheets, Slides, Drive)
- Asana
- Slack
- GitHub
- Notion
- Twilio (SMS)
"""

from .registry import ToolRegistry
from .base import BaseTool, ToolResult

__all__ = ["ToolRegistry", "BaseTool", "ToolResult"]
