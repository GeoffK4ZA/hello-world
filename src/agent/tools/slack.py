"""
Slack Integration for Digital Geoff.

Provides messaging and notification capabilities:
- Send and receive messages
- Monitor channels for mentions
- DM delivery for notifications
"""

from typing import Optional
from .base import BaseTool, ToolResult


class SlackTool(BaseTool):
    """
    Slack messaging integration.

    Actions:
    - send_message: Send a message to a channel or DM
    - get_messages: Get recent messages from a channel
    - check_messages: Check for new messages (for triggers)
    - get_mentions: Get messages where the bot is mentioned
    - react: Add a reaction to a message
    - get_channels: List available channels
    """

    name = "slack"
    description = "Send and receive Slack messages, monitor channels"

    def __init__(self, bot_token: str, user_id: Optional[str] = None):
        self.bot_token = bot_token
        self.user_id = user_id
        # Production: from slack_sdk.web.async_client import AsyncWebClient
        # self.client = AsyncWebClient(token=bot_token)

    async def execute(self, action: str, parameters: dict) -> ToolResult:
        try:
            actions = {
                "send_message": self._send_message,
                "get_messages": self._get_messages,
                "check_messages": self._check_messages,
                "get_mentions": self._get_mentions,
                "react": self._react,
                "get_channels": self._get_channels
            }

            if action not in actions:
                return ToolResult(success=False, error=f"Unknown action: {action}")

            return await actions[action](parameters)
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    async def _send_message(self, params: dict) -> ToolResult:
        """Send a message to a channel or DM."""
        channel = params.get("channel")  # Channel ID or user ID for DM
        text = params.get("text")
        blocks = params.get("blocks")  # Rich message blocks

        if not channel or not text:
            return ToolResult(success=False, error="channel and text are required")

        # Production Slack API:
        # response = await self.client.chat_postMessage(
        #     channel=channel,
        #     text=text,
        #     blocks=blocks
        # )

        return ToolResult(
            success=True,
            data={
                "message_ts": "1234567890.123456",
                "channel": channel,
                "sent": True
            }
        )

    async def _get_messages(self, params: dict) -> ToolResult:
        """Get recent messages from a channel."""
        channel = params.get("channel")
        limit = params.get("limit", 20)

        if not channel:
            return ToolResult(success=False, error="channel is required")

        # Production: conversations.history API
        return ToolResult(
            success=True,
            data={
                "messages": [],
                "channel": channel
            }
        )

    async def _check_messages(self, params: dict) -> ToolResult:
        """Check for new messages (used by trigger system)."""
        # This would check for unread messages or mentions since last check
        return ToolResult(success=True, data=[])

    async def _get_mentions(self, params: dict) -> ToolResult:
        """Get messages where the bot/user is mentioned."""
        # Production: Search for mentions using search.messages API
        return ToolResult(
            success=True,
            data={"mentions": []}
        )

    async def _react(self, params: dict) -> ToolResult:
        """Add a reaction to a message."""
        channel = params.get("channel")
        timestamp = params.get("timestamp")
        emoji = params.get("emoji", "thumbsup")

        if not channel or not timestamp:
            return ToolResult(success=False, error="channel and timestamp are required")

        # Production: reactions.add API
        return ToolResult(
            success=True,
            data={"reacted": True, "emoji": emoji}
        )

    async def _get_channels(self, params: dict) -> ToolResult:
        """List available channels."""
        # Production: conversations.list API
        return ToolResult(
            success=True,
            data={
                "channels": [
                    {"id": "C123", "name": "general"},
                    {"id": "C456", "name": "engineering"},
                    {"id": "C789", "name": "project-alpha"}
                ]
            }
        )

    def get_actions(self) -> list[dict]:
        return [
            {"name": "send_message", "description": "Send a message to a channel or DM"},
            {"name": "get_messages", "description": "Get recent messages from a channel"},
            {"name": "check_messages", "description": "Check for new messages"},
            {"name": "get_mentions", "description": "Get messages where you are mentioned"},
            {"name": "react", "description": "Add a reaction to a message"},
            {"name": "get_channels", "description": "List available channels"}
        ]
