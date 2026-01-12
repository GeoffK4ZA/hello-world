"""
Digital Geoff Interface Layer

Multi-channel communication interfaces:
- SMS (Twilio)
- Slack
- Microsoft Teams
- Email
- Webhooks

All interfaces funnel into the agent's interrupt handler.
"""

from .base import Interface, Message
from .router import InterfaceRouter

__all__ = ["Interface", "Message", "InterfaceRouter"]
