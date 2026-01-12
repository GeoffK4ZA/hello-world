"""
Base classes for Digital Geoff interfaces.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Optional
from enum import Enum


class MessagePriority(Enum):
    LOW = 1
    NORMAL = 5
    HIGH = 8
    URGENT = 10


@dataclass
class Message:
    """Incoming message from any channel."""
    id: str
    channel: str  # "sms", "slack", "teams", "email", "webhook"
    sender: str
    content: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    priority: MessagePriority = MessagePriority.NORMAL
    metadata: dict = field(default_factory=dict)
    reply_to: Optional[str] = None  # For threading

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "channel": self.channel,
            "sender": self.sender,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "priority": self.priority.value,
            "metadata": self.metadata
        }


@dataclass
class Response:
    """Outgoing response to any channel."""
    content: str
    channel: str
    recipient: str
    message_id: Optional[str] = None  # For threading
    metadata: dict = field(default_factory=dict)


class Interface(ABC):
    """
    Base class for all communication interfaces.

    Each interface:
    1. Receives messages from its channel
    2. Converts them to a standard Message format
    3. Passes them to the agent for processing
    4. Sends responses back through the channel
    """

    name: str = "base_interface"

    @abstractmethod
    async def start(self):
        """Start listening for messages."""
        pass

    @abstractmethod
    async def stop(self):
        """Stop listening."""
        pass

    @abstractmethod
    async def send(self, response: Response) -> bool:
        """Send a response through this interface."""
        pass

    @abstractmethod
    async def receive(self) -> Optional[Message]:
        """Receive a message (polling mode)."""
        pass

    def set_handler(self, handler: Callable[[Message], Response]):
        """Set the message handler callback."""
        self._handler = handler


class WebhookInterface(Interface):
    """
    Base for webhook-based interfaces.

    These interfaces receive messages via HTTP webhooks
    rather than polling.
    """

    def __init__(self, webhook_path: str):
        self.webhook_path = webhook_path
        self._handler = None

    async def handle_webhook(self, payload: dict) -> dict:
        """Handle an incoming webhook request."""
        message = self._parse_webhook(payload)
        if message and self._handler:
            response = await self._handler(message)
            return {"status": "ok", "response": response.content if response else None}
        return {"status": "ok"}

    @abstractmethod
    def _parse_webhook(self, payload: dict) -> Optional[Message]:
        """Parse webhook payload into a Message."""
        pass
