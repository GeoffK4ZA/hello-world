"""
Slack Interface for Digital Geoff.

Provides Slack bot integration:
- Receive messages via Slack Events API
- Send messages and rich blocks
- Handle slash commands
"""

import asyncio
from typing import Optional
from datetime import datetime
import hashlib

from .base import Interface, Message, Response, WebhookInterface, MessagePriority


class SlackInterface(WebhookInterface):
    """
    Slack bot interface.

    Uses Slack Events API for receiving messages
    and Web API for sending.
    """

    name = "slack"

    def __init__(
        self,
        bot_token: str,
        signing_secret: str,
        default_channel: str,
        webhook_path: str = "/webhooks/slack/events"
    ):
        super().__init__(webhook_path)
        self.bot_token = bot_token
        self.signing_secret = signing_secret
        self.default_channel = default_channel
        self.bot_user_id: Optional[str] = None
        # Production: from slack_sdk.web.async_client import AsyncWebClient
        # self.client = AsyncWebClient(token=bot_token)

    async def start(self):
        """Initialize Slack connection and get bot user ID."""
        # Production:
        # response = await self.client.auth_test()
        # self.bot_user_id = response["user_id"]
        pass

    async def stop(self):
        """Nothing to stop for webhook-based interface."""
        pass

    async def send(self, response: Response) -> bool:
        """Send a Slack message."""
        try:
            channel = response.recipient
            if channel == "default":
                channel = self.default_channel

            # Production Slack API:
            # await self.client.chat_postMessage(
            #     channel=channel,
            #     text=response.content,
            #     thread_ts=response.message_id  # For threading
            # )

            print(f"[Slack] Sending to {channel}: {response.content[:50]}...")
            return True
        except Exception as e:
            print(f"[Slack] Error sending: {e}")
            return False

    async def receive(self) -> Optional[Message]:
        """Slack uses webhooks, not polling."""
        return None

    def _parse_webhook(self, payload: dict) -> Optional[Message]:
        """Parse Slack Events API payload."""
        # Handle URL verification challenge
        if payload.get("type") == "url_verification":
            return None  # Router handles this separately

        event = payload.get("event", {})
        event_type = event.get("type")

        # Handle message events
        if event_type == "message":
            # Ignore bot messages and message changes
            if event.get("bot_id") or event.get("subtype"):
                return None

            text = event.get("text", "")
            user = event.get("user", "")
            channel = event.get("channel", "")
            ts = event.get("ts", "")

            # Check if bot was mentioned
            is_mention = self.bot_user_id and f"<@{self.bot_user_id}>" in text
            is_dm = channel.startswith("D")  # DM channels start with D

            # Only respond to mentions or DMs
            if not is_mention and not is_dm:
                return None

            # Remove bot mention from text
            if self.bot_user_id:
                text = text.replace(f"<@{self.bot_user_id}>", "").strip()

            priority = MessagePriority.NORMAL
            if is_dm:
                priority = MessagePriority.HIGH  # DMs are usually more important

            return Message(
                id=ts,
                channel="slack",
                sender=user,
                content=text,
                priority=priority,
                metadata={
                    "channel_id": channel,
                    "thread_ts": event.get("thread_ts"),
                    "is_mention": is_mention,
                    "is_dm": is_dm
                },
                reply_to=event.get("thread_ts")  # For threading responses
            )

        # Handle app_mention events
        elif event_type == "app_mention":
            text = event.get("text", "")
            user = event.get("user", "")
            channel = event.get("channel", "")
            ts = event.get("ts", "")

            # Remove bot mention
            if self.bot_user_id:
                text = text.replace(f"<@{self.bot_user_id}>", "").strip()

            return Message(
                id=ts,
                channel="slack",
                sender=user,
                content=text,
                priority=MessagePriority.NORMAL,
                metadata={
                    "channel_id": channel,
                    "thread_ts": event.get("thread_ts")
                }
            )

        return None


class SlackSlashCommandInterface(WebhookInterface):
    """
    Handle Slack slash commands.

    Separate interface for /digitalgeoff commands.
    """

    name = "slack_commands"

    def __init__(
        self,
        signing_secret: str,
        webhook_path: str = "/webhooks/slack/commands"
    ):
        super().__init__(webhook_path)
        self.signing_secret = signing_secret

    async def start(self):
        pass

    async def stop(self):
        pass

    async def send(self, response: Response) -> bool:
        # Slash commands respond via the response_url in the original payload
        # This would be handled by the webhook handler returning the response
        return True

    async def receive(self) -> Optional[Message]:
        return None

    def _parse_webhook(self, payload: dict) -> Optional[Message]:
        """Parse Slack slash command payload."""
        command = payload.get("command", "")
        text = payload.get("text", "")
        user_id = payload.get("user_id", "")
        channel_id = payload.get("channel_id", "")
        trigger_id = payload.get("trigger_id", "")

        return Message(
            id=trigger_id,
            channel="slack_commands",
            sender=user_id,
            content=f"{command} {text}".strip(),
            priority=MessagePriority.HIGH,  # Slash commands are intentional
            metadata={
                "command": command,
                "channel_id": channel_id,
                "response_url": payload.get("response_url")
            }
        )
