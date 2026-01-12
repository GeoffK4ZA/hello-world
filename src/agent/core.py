"""
Digital Geoff Agent Core

The central reasoning engine that orchestrates memory, knowledge, and actions.
Uses Claude as the LLM backbone with persistent state and tool use.
"""

import asyncio
import json
from datetime import datetime
from typing import Any, Optional
from dataclasses import dataclass, field
from enum import Enum
import anthropic

from .memory import MemoryManager
from .knowledge import KnowledgeGraph
from .tools import ToolRegistry


class AgentState(Enum):
    """Agent execution states for durable execution."""
    IDLE = "idle"
    THINKING = "thinking"
    EXECUTING = "executing"
    WAITING_APPROVAL = "waiting_approval"
    INTERRUPTED = "interrupted"


@dataclass
class AgentContext:
    """Current working context for the agent."""
    current_task: Optional[str] = None
    active_projects: list[str] = field(default_factory=list)
    pending_actions: list[dict] = field(default_factory=list)
    conversation_history: list[dict] = field(default_factory=list)
    last_checkpoint: Optional[datetime] = None
    state: AgentState = AgentState.IDLE


@dataclass
class Trigger:
    """Represents an event that activates the agent."""
    type: str  # "scheduled", "message", "event", "interrupt"
    source: str  # "sms", "slack", "teams", "calendar", "internal"
    payload: dict
    timestamp: datetime = field(default_factory=datetime.utcnow)
    priority: int = 5  # 1-10, 10 being highest


class DigitalGeoffAgent:
    """
    The core autonomous agent.

    This is not a chatbot. It's an autonomous system that:
    - Maintains persistent memory across all interactions
    - Builds and queries a knowledge graph of your work
    - Reasons about priorities, relationships, and context
    - Takes actions on your behalf via integrated tools
    - Can be interrupted and resumed at any point
    """

    SYSTEM_PROMPT = """You are Digital Geoff, a high-performing virtual Chief of Staff and Solution/Data Architect Partner.

## Core Identity
- Proactive, highly organised, decisive
- Comfortable with ambiguity but relentlessly execution-focused
- You perform both strategic thinking and hands-on delivery
- You operate across multiple projects and roles simultaneously

## Your Purpose
Help your principal (the user) to:
- Move faster
- Make better decisions
- Communicate clearly
- Deliver high-quality outputs without burnout

## How You Operate
You have access to:
1. MEMORY: Episodic (past conversations), semantic (facts), procedural (how things are done)
2. KNOWLEDGE GRAPH: Projects, people, decisions, relationships
3. TOOLS: Calendar, tasks, communications, documents

Before responding or acting:
1. Retrieve relevant memory and knowledge
2. Consider relationships and context
3. Plan your approach
4. Execute with precision
5. Update memory with outcomes

## Output Standards
- Crisp, sharp, professional
- Minimal fluff
- Always include next actions
- Use structured formats (bullets, tables, headings)

## Behaviour Rules
- Be proactive - suggest improvements and automations
- Prefer execution over explanation
- Maintain confidentiality
- Keep momentum - outputs over discussion
- When uncertain, investigate before confirming assumptions
"""

    def __init__(
        self,
        anthropic_api_key: str,
        memory_manager: MemoryManager,
        knowledge_graph: KnowledgeGraph,
        tool_registry: ToolRegistry,
        model: str = "claude-sonnet-4-20250514"
    ):
        self.client = anthropic.Anthropic(api_key=anthropic_api_key)
        self.memory = memory_manager
        self.knowledge = knowledge_graph
        self.tools = tool_registry
        self.model = model
        self.context = AgentContext()
        self._checkpoint_store = {}  # Replace with Redis/Postgres in production

    async def run_loop(self):
        """
        Main agent loop - runs continuously.

        This is the core execution model:
        1. Check for triggers (scheduled, messages, events)
        2. Retrieve relevant context from memory and knowledge graph
        3. Reason about what to do
        4. Execute actions with checkpointing
        5. Update memory with outcomes
        6. Handle any interrupts
        """
        while True:
            try:
                # Check for triggers
                triggers = await self._check_triggers()

                if triggers:
                    for trigger in sorted(triggers, key=lambda t: -t.priority):
                        await self._handle_trigger(trigger)

                # Proactive checks (even without triggers)
                await self._proactive_scan()

                # Brief pause before next iteration
                await asyncio.sleep(1)

            except Exception as e:
                await self._handle_error(e)
                await asyncio.sleep(5)  # Back off on errors

    async def _check_triggers(self) -> list[Trigger]:
        """Check all trigger sources for new events."""
        triggers = []

        # Check scheduled events (calendar)
        calendar_triggers = await self.tools.execute(
            "calendar", "check_upcoming", {"minutes": 120}
        )
        for event in calendar_triggers:
            triggers.append(Trigger(
                type="scheduled",
                source="calendar",
                payload=event,
                priority=8 if event.get("needs_prep") else 5
            ))

        # Check message queues (SMS, Slack, Teams)
        for channel in ["sms", "slack", "teams"]:
            messages = await self.tools.execute(
                channel, "check_messages", {}
            )
            for msg in messages:
                triggers.append(Trigger(
                    type="message",
                    source=channel,
                    payload=msg,
                    priority=msg.get("priority", 5)
                ))

        # Check task deadlines
        task_triggers = await self.tools.execute(
            "asana", "check_due_soon", {"hours": 24}
        )
        for task in task_triggers:
            triggers.append(Trigger(
                type="event",
                source="asana",
                payload=task,
                priority=7
            ))

        return triggers

    async def _handle_trigger(self, trigger: Trigger):
        """Process a single trigger through the full agent loop."""
        self.context.state = AgentState.THINKING

        # 1. Retrieve relevant memory
        memories = await self.memory.retrieve(
            query=json.dumps(trigger.payload),
            memory_types=["episodic", "semantic", "procedural"]
        )

        # 2. Query knowledge graph for relationships
        knowledge = await self.knowledge.query_relevant(trigger.payload)

        # 3. Build context for reasoning
        context = self._build_context(trigger, memories, knowledge)

        # 4. Agent reasons about what to do
        plan = await self._reason(context)

        # 5. Execute plan with checkpointing
        self.context.state = AgentState.EXECUTING
        for step in plan["steps"]:
            # Checkpoint before each step
            await self._checkpoint()

            # Check for approval gates
            if step.get("requires_approval"):
                self.context.state = AgentState.WAITING_APPROVAL
                approved = await self._request_approval(step)
                if not approved:
                    continue
                self.context.state = AgentState.EXECUTING

            # Execute the step
            result = await self._execute_step(step)

            # Update memory with outcome
            await self.memory.store(
                content=f"Executed: {step['action']} -> Result: {result}",
                memory_type="episodic",
                metadata={"trigger": trigger.type, "source": trigger.source}
            )

        self.context.state = AgentState.IDLE

    async def _proactive_scan(self):
        """Proactive checks the agent does even without triggers."""
        # Check if it's time for daily briefing
        now = datetime.utcnow()
        if now.hour == 6 and now.minute < 2:  # 6:00-6:02 AM
            await self._generate_daily_briefing()

        # Check for stale tasks
        stale = await self.tools.execute("asana", "find_stale_tasks", {"days": 3})
        if stale:
            await self._handle_stale_tasks(stale)

        # Check calendar for upcoming prep needs
        upcoming = await self.tools.execute(
            "calendar", "get_next_meeting", {"hours": 2}
        )
        if upcoming and not await self._has_prep(upcoming):
            await self._generate_meeting_prep(upcoming)

    async def _reason(self, context: str) -> dict:
        """
        Core reasoning - uses Claude to think about what to do.

        Returns a structured plan with steps to execute.
        """
        messages = [
            {"role": "user", "content": context}
        ]

        response = self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=self.SYSTEM_PROMPT,
            messages=messages,
            tools=self.tools.get_tool_definitions()
        )

        # Parse response into executable plan
        plan = {"steps": []}

        for block in response.content:
            if block.type == "tool_use":
                plan["steps"].append({
                    "action": block.name,
                    "parameters": block.input,
                    "requires_approval": self._needs_approval(block.name)
                })
            elif block.type == "text":
                plan["reasoning"] = block.text

        return plan

    async def _execute_step(self, step: dict) -> Any:
        """Execute a single step from the plan."""
        tool_name = step["action"].split(".")[0] if "." in step["action"] else step["action"]
        action = step["action"].split(".")[1] if "." in step["action"] else "execute"

        return await self.tools.execute(tool_name, action, step["parameters"])

    def _build_context(self, trigger: Trigger, memories: list, knowledge: dict) -> str:
        """Build the context string for reasoning."""
        return f"""## Current Trigger
Type: {trigger.type}
Source: {trigger.source}
Time: {trigger.timestamp.isoformat()}
Payload: {json.dumps(trigger.payload, indent=2)}

## Relevant Memories
{self._format_memories(memories)}

## Knowledge Graph Context
{self._format_knowledge(knowledge)}

## Current State
- Active Projects: {', '.join(self.context.active_projects) or 'None loaded'}
- Pending Actions: {len(self.context.pending_actions)}
- Time: {datetime.utcnow().isoformat()}

## Your Task
Analyze this trigger in context of the memories and knowledge above.
Determine what actions to take. Use tools to execute.
Think about: What would the principal want done here? What's the smartest response?
"""

    def _format_memories(self, memories: list) -> str:
        """Format memories for context."""
        if not memories:
            return "No relevant memories found."
        return "\n".join([f"- [{m['type']}] {m['content']}" for m in memories])

    def _format_knowledge(self, knowledge: dict) -> str:
        """Format knowledge graph results for context."""
        if not knowledge:
            return "No relevant knowledge found."

        parts = []
        if "entities" in knowledge:
            parts.append("Entities: " + ", ".join(knowledge["entities"]))
        if "relationships" in knowledge:
            for rel in knowledge["relationships"]:
                parts.append(f"  {rel['from']} --[{rel['type']}]--> {rel['to']}")
        return "\n".join(parts)

    def _needs_approval(self, action: str) -> bool:
        """Determine if an action needs human approval."""
        high_risk_actions = [
            "send_email", "post_message", "create_meeting",
            "delete", "cancel", "decline"
        ]
        return any(risk in action.lower() for risk in high_risk_actions)

    async def _checkpoint(self):
        """Save current state for durable execution."""
        checkpoint = {
            "context": {
                "current_task": self.context.current_task,
                "active_projects": self.context.active_projects,
                "pending_actions": self.context.pending_actions,
                "state": self.context.state.value
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        self._checkpoint_store[datetime.utcnow().isoformat()] = checkpoint
        self.context.last_checkpoint = datetime.utcnow()

    async def _request_approval(self, step: dict) -> bool:
        """Request human approval for high-risk actions."""
        # Send approval request via preferred channel
        await self.tools.execute("sms", "send", {
            "message": f"🔔 Approval needed:\n{step['action']}\n\nReply YES to approve, NO to skip."
        })

        # Wait for response (with timeout)
        # In production, this would be event-driven
        return True  # Placeholder

    async def _handle_error(self, error: Exception):
        """Handle errors gracefully."""
        await self.memory.store(
            content=f"Error occurred: {str(error)}",
            memory_type="episodic",
            metadata={"type": "error", "error_class": error.__class__.__name__}
        )

    async def _generate_daily_briefing(self):
        """Generate and send the morning briefing."""
        pass  # Implemented in briefing module

    async def _handle_stale_tasks(self, tasks: list):
        """Handle tasks that have gone stale."""
        pass  # Implemented in task management module

    async def _generate_meeting_prep(self, meeting: dict):
        """Generate preparation materials for an upcoming meeting."""
        pass  # Implemented in meeting prep module

    async def _has_prep(self, meeting: dict) -> bool:
        """Check if prep already exists for a meeting."""
        return False  # Check memory/knowledge graph

    # --- Interrupt Handling ---

    async def handle_interrupt(self, message: str, source: str) -> str:
        """
        Handle an interrupt from any channel.

        This is called when the user sends a message via SMS, Slack, etc.
        The agent pauses its current work, handles the request, and resumes.
        """
        self.context.state = AgentState.INTERRUPTED

        # Store the interrupt in memory
        await self.memory.store(
            content=f"Interrupt from {source}: {message}",
            memory_type="episodic"
        )

        # Retrieve relevant context
        memories = await self.memory.retrieve(query=message)
        knowledge = await self.knowledge.query_relevant({"query": message})

        # Process the interrupt
        response = await self._process_interrupt(message, source, memories, knowledge)

        # Resume previous state
        self.context.state = AgentState.IDLE

        return response

    async def _process_interrupt(
        self,
        message: str,
        source: str,
        memories: list,
        knowledge: dict
    ) -> str:
        """Process an interrupt message and generate response."""

        context = f"""## Interrupt Received
Source: {source}
Message: {message}

## Relevant Memories
{self._format_memories(memories)}

## Knowledge Context
{self._format_knowledge(knowledge)}

## Instructions
The principal has sent you a message. Respond helpfully and take any requested actions.
If they're asking for status, provide it concisely.
If they're asking you to do something, do it using tools.
Keep response concise - this may be delivered via SMS.
"""

        messages = [{"role": "user", "content": context}]

        response = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            system=self.SYSTEM_PROMPT,
            messages=messages,
            tools=self.tools.get_tool_definitions()
        )

        # Execute any tool calls
        for block in response.content:
            if block.type == "tool_use":
                await self._execute_step({
                    "action": block.name,
                    "parameters": block.input
                })

        # Return text response
        for block in response.content:
            if block.type == "text":
                return block.text

        return "Done."
