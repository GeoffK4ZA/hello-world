"""
Twilio SMS Integration for Digital Geoff.

Provides SMS-based communication for:
- Sending alerts and notifications
- Receiving commands via text
- Two-way conversational interface
"""

from typing import Optional
from .base import BaseTool, ToolResult


class TwilioSMSTool(BaseTool):
    """
    Twilio SMS integration.

    Actions:
    - send: Send an SMS message
    - check_messages: Check for incoming SMS messages (webhook-based in production)
    """

    name = "sms"
    description = "Send and receive SMS messages via Twilio"

    def __init__(
        self,
        account_sid: str,
        auth_token: str,
        from_number: str,
        to_number: str  # Primary recipient (you)
    ):
        self.account_sid = account_sid
        self.auth_token = auth_token
        self.from_number = from_number
        self.to_number = to_number
        # Production: from twilio.rest import Client
        # self.client = Client(account_sid, auth_token)

    async def execute(self, action: str, parameters: dict) -> ToolResult:
        try:
            if action == "send":
                return await self._send(parameters)
            elif action == "check_messages":
                return await self._check_messages()
            else:
                return ToolResult(success=False, error=f"Unknown action: {action}")
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    async def _send(self, params: dict) -> ToolResult:
        """Send an SMS message."""
        message = params.get("message")
        to = params.get("to", self.to_number)

        if not message:
            return ToolResult(success=False, error="message is required")

        # Truncate for SMS length limits
        if len(message) > 1600:
            message = message[:1597] + "..."

        # Production Twilio API:
        # message = self.client.messages.create(
        #     body=message,
        #     from_=self.from_number,
        #     to=to
        # )

        return ToolResult(
            success=True,
            data={
                "message_sid": "SM123456789",
                "to": to,
                "status": "sent",
                "body_length": len(message)
            }
        )

    async def _check_messages(self) -> ToolResult:
        """
        Check for incoming SMS messages.

        In production, this would be webhook-based.
        The webhook would push messages to a queue that this method reads.
        """
        # Production: Read from message queue populated by webhook
        return ToolResult(success=True, data=[])

    def get_actions(self) -> list[dict]:
        return [
            {"name": "send", "description": "Send an SMS message"},
            {"name": "check_messages", "description": "Check for incoming SMS messages"}
        ]


# --- SMS Command Parser ---

SMS_COMMANDS = {
    "status": {
        "description": "Get current priority stack and status",
        "example": "status"
    },
    "tasks": {
        "description": "Get today's tasks from Asana",
        "example": "tasks"
    },
    "prep": {
        "description": "Get meeting prep for a specific meeting",
        "example": "prep Architecture Review"
    },
    "block": {
        "description": "Block strategic time on calendar",
        "example": "block 2h tomorrow"
    },
    "remind": {
        "description": "Set a reminder",
        "example": "remind me to call Sarah at 3pm"
    },
    "note": {
        "description": "Store a quick note",
        "example": "note Decision: Go with vendor A for data platform"
    }
}


def parse_sms_command(message: str) -> dict:
    """
    Parse an incoming SMS into a command structure.

    Returns:
        {
            "command": str,
            "args": str,
            "raw": str
        }
    """
    message = message.strip()
    parts = message.split(maxsplit=1)

    if not parts:
        return {"command": "unknown", "args": "", "raw": message}

    command = parts[0].lower()
    args = parts[1] if len(parts) > 1 else ""

    if command in SMS_COMMANDS:
        return {"command": command, "args": args, "raw": message}

    # If no known command, treat as a general query
    return {"command": "query", "args": message, "raw": message}
