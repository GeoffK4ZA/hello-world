"""
Interface Router for Digital Geoff.

Routes messages from all channels to the agent and responses back.
"""

import asyncio
from typing import Any, Callable, Dict, Optional
from .base import Interface, Message, Response


class InterfaceRouter:
    """
    Central router for all communication interfaces.

    Responsibilities:
    - Register and manage interfaces
    - Route incoming messages to the agent
    - Route responses back to the correct channel
    - Handle channel-specific formatting
    """

    def __init__(self, agent_handler: Callable[[Message], Response]):
        self._interfaces: Dict[str, Interface] = {}
        self._agent_handler = agent_handler
        self._running = False

    def register(self, interface: Interface):
        """Register an interface with the router."""
        self._interfaces[interface.name] = interface
        interface.set_handler(self._handle_message)

    def get(self, name: str) -> Optional[Interface]:
        """Get an interface by name."""
        return self._interfaces.get(name)

    async def _handle_message(self, message: Message) -> Optional[Response]:
        """Handle an incoming message by passing to agent."""
        try:
            # Call the agent's interrupt handler
            response_content = await self._agent_handler(message)

            if response_content:
                return Response(
                    content=response_content,
                    channel=message.channel,
                    recipient=message.sender,
                    message_id=message.id
                )
            return None
        except Exception as e:
            # Return error response
            return Response(
                content=f"Error processing request: {str(e)}",
                channel=message.channel,
                recipient=message.sender
            )

    async def send(self, channel: str, recipient: str, content: str, **kwargs) -> bool:
        """Send a message through a specific channel."""
        interface = self._interfaces.get(channel)
        if not interface:
            raise ValueError(f"Unknown channel: {channel}")

        response = Response(
            content=content,
            channel=channel,
            recipient=recipient,
            metadata=kwargs
        )
        return await interface.send(response)

    async def broadcast(self, content: str, channels: Optional[list[str]] = None):
        """Broadcast a message to multiple channels."""
        target_channels = channels or list(self._interfaces.keys())

        tasks = []
        for channel in target_channels:
            interface = self._interfaces.get(channel)
            if interface:
                # Use default recipient for each channel
                response = Response(
                    content=content,
                    channel=channel,
                    recipient="default"  # Each interface handles this
                )
                tasks.append(interface.send(response))

        await asyncio.gather(*tasks, return_exceptions=True)

    async def start_all(self):
        """Start all interfaces."""
        self._running = True
        tasks = [interface.start() for interface in self._interfaces.values()]
        await asyncio.gather(*tasks)

    async def stop_all(self):
        """Stop all interfaces."""
        self._running = False
        tasks = [interface.stop() for interface in self._interfaces.values()]
        await asyncio.gather(*tasks)

    def list_channels(self) -> list[str]:
        """List all registered channels."""
        return list(self._interfaces.keys())
