"""
Telegram Bot Interface for Digital Geoff (Zero-Cost Edition)

Telegram bots are completely FREE:
- Unlimited messages
- No per-message fees
- Works on mobile and desktop
- Supports rich formatting, buttons, files
- Push notifications built-in

This replaces Twilio SMS ($0.0075/msg) with zero cost.
"""

import asyncio
import os
from typing import Optional, Callable, Awaitable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class TelegramMessageType(Enum):
    """Types of Telegram messages."""
    TEXT = "text"
    COMMAND = "command"
    CALLBACK = "callback"  # Button press
    PHOTO = "photo"
    DOCUMENT = "document"


@dataclass
class TelegramMessage:
    """Incoming Telegram message."""
    chat_id: int
    user_id: int
    username: Optional[str]
    message_id: int
    text: str
    message_type: TelegramMessageType
    timestamp: datetime
    reply_to_message_id: Optional[int] = None


class TelegramBot:
    """
    Telegram bot interface.

    Uses long-polling (no webhook needed) or webhooks if you have HTTPS.
    Both are completely free.
    """

    def __init__(
        self,
        token: str,
        allowed_users: Optional[list[int]] = None,
        message_handler: Optional[Callable[[TelegramMessage], Awaitable[str]]] = None
    ):
        """
        Initialize Telegram bot.

        Args:
            token: Bot token from @BotFather
            allowed_users: List of user IDs allowed to use bot (security)
            message_handler: Async function to handle messages
        """
        self.token = token
        self.base_url = f"https://api.telegram.org/bot{token}"
        self.allowed_users = set(allowed_users) if allowed_users else None
        self.message_handler = message_handler
        self._running = False
        self._offset = 0

    async def send_message(
        self,
        chat_id: int,
        text: str,
        parse_mode: str = "Markdown",
        reply_to_message_id: Optional[int] = None,
        reply_markup: Optional[dict] = None
    ) -> dict:
        """Send a text message."""
        import httpx

        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode
        }

        if reply_to_message_id:
            payload["reply_to_message_id"] = reply_to_message_id

        if reply_markup:
            payload["reply_markup"] = reply_markup

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/sendMessage",
                json=payload,
                timeout=30.0
            )
            return response.json()

    async def send_typing_action(self, chat_id: int):
        """Show 'typing...' indicator."""
        import httpx

        async with httpx.AsyncClient() as client:
            await client.post(
                f"{self.base_url}/sendChatAction",
                json={"chat_id": chat_id, "action": "typing"},
                timeout=10.0
            )

    async def send_document(
        self,
        chat_id: int,
        document: bytes,
        filename: str,
        caption: Optional[str] = None
    ) -> dict:
        """Send a document/file."""
        import httpx

        files = {"document": (filename, document)}
        data = {"chat_id": chat_id}
        if caption:
            data["caption"] = caption

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/sendDocument",
                data=data,
                files=files,
                timeout=60.0
            )
            return response.json()

    async def get_updates(self, timeout: int = 30) -> list[dict]:
        """Long-poll for updates."""
        import httpx

        params = {
            "offset": self._offset,
            "timeout": timeout,
            "allowed_updates": ["message", "callback_query"]
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/getUpdates",
                params=params,
                timeout=timeout + 10
            )
            data = response.json()

            if data.get("ok") and data.get("result"):
                for update in data["result"]:
                    self._offset = max(self._offset, update["update_id"] + 1)
                return data["result"]

            return []

    def _parse_update(self, update: dict) -> Optional[TelegramMessage]:
        """Parse a Telegram update into our message format."""
        if "message" in update:
            msg = update["message"]
            text = msg.get("text", "")

            # Determine message type
            if text.startswith("/"):
                msg_type = TelegramMessageType.COMMAND
            elif "photo" in msg:
                msg_type = TelegramMessageType.PHOTO
                text = msg.get("caption", "[photo]")
            elif "document" in msg:
                msg_type = TelegramMessageType.DOCUMENT
                text = msg.get("caption", "[document]")
            else:
                msg_type = TelegramMessageType.TEXT

            return TelegramMessage(
                chat_id=msg["chat"]["id"],
                user_id=msg["from"]["id"],
                username=msg["from"].get("username"),
                message_id=msg["message_id"],
                text=text,
                message_type=msg_type,
                timestamp=datetime.fromtimestamp(msg["date"]),
                reply_to_message_id=msg.get("reply_to_message", {}).get("message_id")
            )

        elif "callback_query" in update:
            cb = update["callback_query"]
            return TelegramMessage(
                chat_id=cb["message"]["chat"]["id"],
                user_id=cb["from"]["id"],
                username=cb["from"].get("username"),
                message_id=cb["message"]["message_id"],
                text=cb["data"],
                message_type=TelegramMessageType.CALLBACK,
                timestamp=datetime.utcnow()
            )

        return None

    async def _process_message(self, message: TelegramMessage):
        """Process a single message."""
        # Security check
        if self.allowed_users and message.user_id not in self.allowed_users:
            await self.send_message(
                message.chat_id,
                "Sorry, you're not authorized to use this bot."
            )
            return

        # Show typing indicator
        await self.send_typing_action(message.chat_id)

        # Handle the message
        if self.message_handler:
            try:
                response = await self.message_handler(message)
                await self.send_message(
                    message.chat_id,
                    response,
                    reply_to_message_id=message.message_id
                )
            except Exception as e:
                await self.send_message(
                    message.chat_id,
                    f"Error processing request: {str(e)}"
                )

    async def run_polling(self):
        """Run bot with long-polling (no webhook needed)."""
        self._running = True
        print(f"Telegram bot started (polling mode)")

        while self._running:
            try:
                updates = await self.get_updates()

                for update in updates:
                    message = self._parse_update(update)
                    if message:
                        # Process in background to not block polling
                        asyncio.create_task(self._process_message(message))

            except Exception as e:
                print(f"Telegram polling error: {e}")
                await asyncio.sleep(5)

    def stop(self):
        """Stop the bot."""
        self._running = False


# --- Command Parser ---

TELEGRAM_COMMANDS = {
    "/start": "Start the bot and get help",
    "/status": "Get your current priority stack",
    "/tasks": "Get today's tasks",
    "/prep": "Get meeting prep (usage: /prep Meeting Name)",
    "/block": "Block strategic time (usage: /block 2h tomorrow)",
    "/note": "Save a quick note (usage: /note Your note here)",
    "/calendar": "Get today's calendar",
    "/help": "Show this help message"
}


def parse_command(text: str) -> tuple[str, str]:
    """
    Parse a Telegram command.

    Returns:
        (command, arguments)
    """
    if not text.startswith("/"):
        return ("message", text)

    parts = text.split(maxsplit=1)
    command = parts[0].lower()

    # Handle @botname suffix
    if "@" in command:
        command = command.split("@")[0]

    args = parts[1] if len(parts) > 1 else ""

    return (command, args)


def format_help() -> str:
    """Generate help message."""
    lines = ["*Digital Geoff Commands*\n"]
    for cmd, desc in TELEGRAM_COMMANDS.items():
        lines.append(f"`{cmd}` - {desc}")
    return "\n".join(lines)


# --- Keyboard Builders ---

def build_inline_keyboard(buttons: list[list[tuple[str, str]]]) -> dict:
    """
    Build an inline keyboard.

    Args:
        buttons: 2D list of (text, callback_data) tuples
    """
    return {
        "inline_keyboard": [
            [{"text": text, "callback_data": data} for text, data in row]
            for row in buttons
        ]
    }


def build_priority_keyboard() -> dict:
    """Build keyboard for priority selection."""
    return build_inline_keyboard([
        [("🔴 High", "priority:high"), ("🟡 Medium", "priority:medium")],
        [("🟢 Low", "priority:low"), ("⏭ Skip", "priority:skip")]
    ])


def build_confirmation_keyboard(action_id: str) -> dict:
    """Build keyboard for action confirmation."""
    return build_inline_keyboard([
        [("✅ Approve", f"approve:{action_id}"), ("❌ Reject", f"reject:{action_id}")]
    ])


# --- Integration with Digital Geoff ---

class TelegramInterface:
    """
    Full Telegram interface for Digital Geoff.

    Integrates the bot with the agent core.
    """

    def __init__(self, agent_handler: Callable[[str, str], Awaitable[str]]):
        """
        Initialize interface.

        Args:
            agent_handler: Async function that takes (message, source) and returns response
        """
        self.agent_handler = agent_handler
        self.bot: Optional[TelegramBot] = None

    async def start(self):
        """Start the Telegram interface."""
        token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not token:
            print("TELEGRAM_BOT_TOKEN not set, Telegram interface disabled")
            return

        # Get allowed users from env (comma-separated user IDs)
        allowed_users_str = os.getenv("TELEGRAM_ALLOWED_USERS", "")
        allowed_users = None
        if allowed_users_str:
            allowed_users = [int(uid.strip()) for uid in allowed_users_str.split(",")]

        self.bot = TelegramBot(
            token=token,
            allowed_users=allowed_users,
            message_handler=self._handle_message
        )

        # Start polling in background
        asyncio.create_task(self.bot.run_polling())

    async def stop(self):
        """Stop the Telegram interface."""
        if self.bot:
            self.bot.stop()

    async def _handle_message(self, message: TelegramMessage) -> str:
        """Handle incoming Telegram message."""
        command, args = parse_command(message.text)

        # Handle built-in commands
        if command == "/start" or command == "/help":
            return format_help()

        # Route to agent
        if command == "/status":
            query = "What's my current status and priority stack?"
        elif command == "/tasks":
            query = "What are my tasks for today?"
        elif command == "/prep":
            if args:
                query = f"Generate meeting prep for: {args}"
            else:
                query = "What meetings do I have coming up that need prep?"
        elif command == "/block":
            query = f"Block strategic time: {args}" if args else "Find and block 2 hours of strategic time tomorrow"
        elif command == "/note":
            query = f"Store this note: {args}" if args else "What notes have I saved recently?"
        elif command == "/calendar":
            query = "What's on my calendar today?"
        else:
            # Free-form message
            query = message.text

        # Send to agent
        response = await self.agent_handler(query, "telegram")

        # Truncate if too long for Telegram (4096 char limit)
        if len(response) > 4000:
            response = response[:3997] + "..."

        return response

    async def send_notification(
        self,
        message: str,
        priority: str = "normal",
        action_buttons: Optional[list[tuple[str, str]]] = None
    ):
        """Send a proactive notification."""
        if not self.bot:
            return

        # Get the primary user's chat ID
        chat_id = os.getenv("TELEGRAM_PRIMARY_CHAT_ID")
        if not chat_id:
            return

        # Add priority emoji
        if priority == "high":
            message = f"🔴 *URGENT*\n\n{message}"
        elif priority == "medium":
            message = f"🟡 {message}"

        reply_markup = None
        if action_buttons:
            reply_markup = build_inline_keyboard([action_buttons])

        await self.bot.send_message(
            chat_id=int(chat_id),
            text=message,
            reply_markup=reply_markup
        )
