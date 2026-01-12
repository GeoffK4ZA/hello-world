"""
SMS Interface using Twilio.

Provides bidirectional SMS communication:
- Receive commands via SMS webhook
- Send responses and notifications
"""

import asyncio
from typing import Optional
from datetime import datetime
import hashlib

from .base import Interface, Message, Response, WebhookInterface, MessagePriority


class TwilioSMSInterface(WebhookInterface):
    """
    Twilio SMS interface.

    Receives messages via webhook, sends via Twilio API.
    """

    name = "sms"

    def __init__(
        self,
        account_sid: str,
        auth_token: str,
        from_number: str,
        to_number: str,  # Primary user's number
        webhook_path: str = "/webhooks/sms"
    ):
        super().__init__(webhook_path)
        self.account_sid = account_sid
        self.auth_token = auth_token
        self.from_number = from_number
        self.to_number = to_number
        # Production: from twilio.rest import Client
        # self.client = Client(account_sid, auth_token)

    async def start(self):
        """SMS interface uses webhooks, no polling needed."""
        pass

    async def stop(self):
        """Nothing to stop for webhook-based interface."""
        pass

    async def send(self, response: Response) -> bool:
        """Send an SMS response."""
        try:
            recipient = response.recipient
            if recipient == "default":
                recipient = self.to_number

            content = response.content
            # Truncate for SMS
            if len(content) > 1600:
                content = content[:1597] + "..."

            # Production Twilio:
            # message = self.client.messages.create(
            #     body=content,
            #     from_=self.from_number,
            #     to=recipient
            # )

            print(f"[SMS] Sending to {recipient}: {content[:50]}...")
            return True
        except Exception as e:
            print(f"[SMS] Error sending: {e}")
            return False

    async def receive(self) -> Optional[Message]:
        """SMS uses webhooks, not polling."""
        return None

    def _parse_webhook(self, payload: dict) -> Optional[Message]:
        """Parse Twilio webhook payload."""
        # Twilio sends: From, To, Body, MessageSid, etc.
        body = payload.get("Body", "")
        sender = payload.get("From", "")
        message_sid = payload.get("MessageSid", "")

        if not body or not sender:
            return None

        # Determine priority from message content
        priority = MessagePriority.NORMAL
        if any(word in body.lower() for word in ["urgent", "asap", "emergency"]):
            priority = MessagePriority.URGENT
        elif any(word in body.lower() for word in ["important", "priority"]):
            priority = MessagePriority.HIGH

        return Message(
            id=message_sid or self._generate_id(body),
            channel="sms",
            sender=sender,
            content=body,
            priority=priority,
            metadata={
                "from_number": sender,
                "to_number": payload.get("To", ""),
                "num_media": payload.get("NumMedia", "0")
            }
        )

    def _generate_id(self, content: str) -> str:
        """Generate a message ID."""
        timestamp = datetime.utcnow().isoformat()
        return hashlib.sha256(f"{content}{timestamp}".encode()).hexdigest()[:16]


# --- SMS Response Formatting ---

def format_for_sms(content: str, max_length: int = 1600) -> str:
    """
    Format content for SMS delivery.

    - Strips markdown
    - Truncates appropriately
    - Adds continuation indicator if needed
    """
    # Strip markdown formatting
    content = content.replace("**", "").replace("*", "")
    content = content.replace("##", "").replace("#", "")
    content = content.replace("`", "")

    # Convert bullet points
    content = content.replace("- ", "• ")

    # Truncate if needed
    if len(content) > max_length:
        content = content[:max_length - 20] + "\n\n[Message truncated]"

    return content
