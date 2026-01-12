"""
Digital Geoff - Main Application Entry Point

This is the main entry point for running the Digital Geoff agent.
It initializes all components and starts the agent loop.
"""

import asyncio
import os
from typing import Optional

from .core import DigitalGeoffAgent
from .memory import MemoryManager, VectorMemoryStore
from .knowledge import KnowledgeGraph, InMemoryGraphStore
from .tools.registry import ToolRegistry
from .tools.microsoft365 import OutlookCalendarTool, OutlookEmailTool, TeamsTool
from .tools.asana import AsanaTool
from .tools.slack import SlackTool
from .tools.twilio import TwilioSMSTool
from .tools.google import GoogleSheetsTool, GoogleSlidesTool
from .tools.notion import NotionTool
from .tools.github import GitHubTool
from .interfaces.router import InterfaceRouter
from .interfaces.sms import TwilioSMSInterface
from .interfaces.slack_interface import SlackInterface
from .execution import DurableExecutor, InMemoryCheckpointStore


class DigitalGeoffApp:
    """
    Main application class for Digital Geoff.

    Coordinates all components:
    - Agent core
    - Memory system
    - Knowledge graph
    - Tool integrations
    - Communication interfaces
    - Durable execution
    """

    def __init__(self):
        self.agent: Optional[DigitalGeoffAgent] = None
        self.tool_registry: Optional[ToolRegistry] = None
        self.interface_router: Optional[InterfaceRouter] = None
        self.executor: Optional[DurableExecutor] = None
        self._running = False

    async def initialize(self):
        """Initialize all components."""
        print("Initializing Digital Geoff...")

        # Initialize memory system
        print("  - Setting up memory layer...")
        episodic_store = VectorMemoryStore(collection_name="episodic")
        semantic_store = VectorMemoryStore(collection_name="semantic")
        procedural_store = VectorMemoryStore(collection_name="procedural")

        memory_manager = MemoryManager(
            episodic_store=episodic_store,
            semantic_store=semantic_store,
            procedural_store=procedural_store
        )

        # Initialize knowledge graph
        print("  - Setting up knowledge graph...")
        graph_store = InMemoryGraphStore()  # Replace with Neo4j in production
        knowledge_graph = KnowledgeGraph(store=graph_store)

        # Initialize tool registry
        print("  - Registering tools...")
        self.tool_registry = ToolRegistry()
        self._register_tools()

        # Initialize agent
        print("  - Creating agent core...")
        anthropic_api_key = os.getenv("ANTHROPIC_API_KEY", "")
        self.agent = DigitalGeoffAgent(
            anthropic_api_key=anthropic_api_key,
            memory_manager=memory_manager,
            knowledge_graph=knowledge_graph,
            tool_registry=self.tool_registry
        )

        # Initialize interface router
        print("  - Setting up communication interfaces...")
        self.interface_router = InterfaceRouter(
            agent_handler=self._handle_message
        )
        self._register_interfaces()

        # Initialize durable executor
        print("  - Setting up durable execution...")
        checkpoint_store = InMemoryCheckpointStore()  # Replace with Redis in production
        self.executor = DurableExecutor(
            checkpoint_store=checkpoint_store,
            step_executor=self._execute_step,
            approval_handler=self._handle_approval
        )

        print("Digital Geoff initialized successfully!")

    def _register_tools(self):
        """Register all tools with the registry."""
        # Microsoft 365 tools
        if all(os.getenv(k) for k in ["MS_CLIENT_ID", "MS_CLIENT_SECRET", "MS_TENANT_ID"]):
            self.tool_registry.register(OutlookCalendarTool(
                client_id=os.getenv("MS_CLIENT_ID", ""),
                client_secret=os.getenv("MS_CLIENT_SECRET", ""),
                tenant_id=os.getenv("MS_TENANT_ID", ""),
                user_email=os.getenv("MS_USER_EMAIL", "")
            ))
            self.tool_registry.register(OutlookEmailTool(
                client_id=os.getenv("MS_CLIENT_ID", ""),
                client_secret=os.getenv("MS_CLIENT_SECRET", ""),
                tenant_id=os.getenv("MS_TENANT_ID", ""),
                user_email=os.getenv("MS_USER_EMAIL", "")
            ))
            self.tool_registry.register(TeamsTool(
                client_id=os.getenv("MS_CLIENT_ID", ""),
                client_secret=os.getenv("MS_CLIENT_SECRET", ""),
                tenant_id=os.getenv("MS_TENANT_ID", "")
            ))

        # Asana
        if os.getenv("ASANA_TOKEN"):
            self.tool_registry.register(AsanaTool(
                personal_access_token=os.getenv("ASANA_TOKEN", "")
            ))

        # Slack
        if os.getenv("SLACK_BOT_TOKEN"):
            self.tool_registry.register(SlackTool(
                bot_token=os.getenv("SLACK_BOT_TOKEN", "")
            ))

        # Twilio SMS
        if all(os.getenv(k) for k in ["TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN"]):
            self.tool_registry.register(TwilioSMSTool(
                account_sid=os.getenv("TWILIO_ACCOUNT_SID", ""),
                auth_token=os.getenv("TWILIO_AUTH_TOKEN", ""),
                from_number=os.getenv("TWILIO_FROM_NUMBER", ""),
                to_number=os.getenv("TWILIO_TO_NUMBER", "")
            ))

        # Google tools
        if os.getenv("GOOGLE_CREDENTIALS_PATH"):
            self.tool_registry.register(GoogleSheetsTool(
                credentials_path=os.getenv("GOOGLE_CREDENTIALS_PATH", "")
            ))
            self.tool_registry.register(GoogleSlidesTool(
                credentials_path=os.getenv("GOOGLE_CREDENTIALS_PATH", "")
            ))

        # Notion
        if os.getenv("NOTION_API_KEY"):
            self.tool_registry.register(NotionTool(
                api_key=os.getenv("NOTION_API_KEY", "")
            ))

        # GitHub
        if os.getenv("GITHUB_TOKEN"):
            self.tool_registry.register(GitHubTool(
                token=os.getenv("GITHUB_TOKEN", "")
            ))

        print(f"    Registered {len(self.tool_registry.list_tools())} tools")

    def _register_interfaces(self):
        """Register all communication interfaces."""
        # SMS Interface
        if all(os.getenv(k) for k in ["TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN"]):
            self.interface_router.register(TwilioSMSInterface(
                account_sid=os.getenv("TWILIO_ACCOUNT_SID", ""),
                auth_token=os.getenv("TWILIO_AUTH_TOKEN", ""),
                from_number=os.getenv("TWILIO_FROM_NUMBER", ""),
                to_number=os.getenv("TWILIO_TO_NUMBER", "")
            ))

        # Slack Interface
        if os.getenv("SLACK_BOT_TOKEN"):
            self.interface_router.register(SlackInterface(
                bot_token=os.getenv("SLACK_BOT_TOKEN", ""),
                signing_secret=os.getenv("SLACK_SIGNING_SECRET", ""),
                default_channel=os.getenv("SLACK_DEFAULT_CHANNEL", "general")
            ))

        print(f"    Registered {len(self.interface_router.list_channels())} interfaces")

    async def _handle_message(self, message) -> str:
        """Handle incoming message from any channel."""
        if self.agent:
            return await self.agent.handle_interrupt(
                message=message.content,
                source=message.channel
            )
        return "Agent not initialized"

    async def _execute_step(self, step) -> any:
        """Execute a step in a durable workflow."""
        if self.tool_registry:
            parts = step.action.split(".")
            if len(parts) == 2:
                tool_name, action = parts
                return await self.tool_registry.execute(tool_name, action, step.parameters)
        return None

    async def _handle_approval(self, step) -> bool:
        """Handle approval request for a step."""
        # In production, this would send notification and wait for response
        # For now, auto-approve
        return True

    async def run(self):
        """Run the Digital Geoff agent."""
        if not self.agent:
            await self.initialize()

        self._running = True
        print("\nDigital Geoff is now running!")
        print("Listening for triggers and messages...\n")

        try:
            # Start interfaces
            if self.interface_router:
                await self.interface_router.start_all()

            # Run main agent loop
            if self.agent:
                await self.agent.run_loop()

        except KeyboardInterrupt:
            print("\nShutting down Digital Geoff...")
        finally:
            self._running = False
            if self.interface_router:
                await self.interface_router.stop_all()

    async def stop(self):
        """Stop the agent."""
        self._running = False
        if self.interface_router:
            await self.interface_router.stop_all()


# --- CLI Entry Point ---

def main():
    """Main entry point for CLI."""
    import argparse

    parser = argparse.ArgumentParser(description="Digital Geoff - Your AI Chief of Staff")
    parser.add_argument("--init", action="store_true", help="Initialize and test configuration")
    parser.add_argument("--run", action="store_true", help="Run the agent")

    args = parser.parse_args()

    app = DigitalGeoffApp()

    if args.init:
        asyncio.run(app.initialize())
        print("\nConfiguration test complete.")
        print(f"Tools available: {app.tool_registry.list_tools() if app.tool_registry else []}")
        print(f"Interfaces available: {app.interface_router.list_channels() if app.interface_router else []}")

    elif args.run:
        asyncio.run(app.run())

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
