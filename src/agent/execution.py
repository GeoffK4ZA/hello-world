"""
Durable Execution Layer for Digital Geoff.

Provides:
- State checkpointing after each step
- Recovery from failures
- Human-in-the-loop approval gates
- Workflow persistence

Based on patterns from LangGraph and similar frameworks.
"""

import asyncio
import json
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod
import hashlib


class ExecutionState(Enum):
    """States for durable execution."""
    PENDING = "pending"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Checkpoint:
    """A saved state checkpoint."""
    id: str
    execution_id: str
    step_index: int
    state: dict
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "execution_id": self.execution_id,
            "step_index": self.step_index,
            "state": self.state,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Checkpoint":
        return cls(
            id=data["id"],
            execution_id=data["execution_id"],
            step_index=data["step_index"],
            state=data["state"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            metadata=data.get("metadata", {})
        )


@dataclass
class ExecutionStep:
    """A single step in an execution plan."""
    id: str
    name: str
    action: str
    parameters: dict
    requires_approval: bool = False
    timeout_seconds: int = 300
    retries: int = 3
    result: Optional[Any] = None
    error: Optional[str] = None
    state: ExecutionState = ExecutionState.PENDING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


@dataclass
class Execution:
    """A complete execution with multiple steps."""
    id: str
    name: str
    steps: List[ExecutionStep]
    state: ExecutionState = ExecutionState.PENDING
    current_step: int = 0
    context: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    checkpoints: List[Checkpoint] = field(default_factory=list)


class CheckpointStore(ABC):
    """Abstract base for checkpoint storage."""

    @abstractmethod
    async def save(self, checkpoint: Checkpoint) -> str:
        pass

    @abstractmethod
    async def load(self, checkpoint_id: str) -> Optional[Checkpoint]:
        pass

    @abstractmethod
    async def get_latest(self, execution_id: str) -> Optional[Checkpoint]:
        pass

    @abstractmethod
    async def list_checkpoints(self, execution_id: str) -> List[Checkpoint]:
        pass


class InMemoryCheckpointStore(CheckpointStore):
    """In-memory checkpoint store for development."""

    def __init__(self):
        self._checkpoints: Dict[str, Checkpoint] = {}
        self._by_execution: Dict[str, List[str]] = {}

    async def save(self, checkpoint: Checkpoint) -> str:
        self._checkpoints[checkpoint.id] = checkpoint

        if checkpoint.execution_id not in self._by_execution:
            self._by_execution[checkpoint.execution_id] = []
        self._by_execution[checkpoint.execution_id].append(checkpoint.id)

        return checkpoint.id

    async def load(self, checkpoint_id: str) -> Optional[Checkpoint]:
        return self._checkpoints.get(checkpoint_id)

    async def get_latest(self, execution_id: str) -> Optional[Checkpoint]:
        checkpoint_ids = self._by_execution.get(execution_id, [])
        if not checkpoint_ids:
            return None

        latest_id = checkpoint_ids[-1]
        return self._checkpoints.get(latest_id)

    async def list_checkpoints(self, execution_id: str) -> List[Checkpoint]:
        checkpoint_ids = self._by_execution.get(execution_id, [])
        return [self._checkpoints[cid] for cid in checkpoint_ids if cid in self._checkpoints]


class RedisCheckpointStore(CheckpointStore):
    """Production checkpoint store using Redis."""

    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        # Production: import redis.asyncio as redis
        # self.client = redis.from_url(redis_url)
        self._fallback = InMemoryCheckpointStore()

    async def save(self, checkpoint: Checkpoint) -> str:
        # Production:
        # await self.client.hset(f"checkpoint:{checkpoint.id}", mapping=checkpoint.to_dict())
        # await self.client.rpush(f"execution:{checkpoint.execution_id}:checkpoints", checkpoint.id)
        return await self._fallback.save(checkpoint)

    async def load(self, checkpoint_id: str) -> Optional[Checkpoint]:
        return await self._fallback.load(checkpoint_id)

    async def get_latest(self, execution_id: str) -> Optional[Checkpoint]:
        return await self._fallback.get_latest(execution_id)

    async def list_checkpoints(self, execution_id: str) -> List[Checkpoint]:
        return await self._fallback.list_checkpoints(execution_id)


class DurableExecutor:
    """
    Executes plans with checkpointing and recovery.

    Key features:
    - Saves state after each step
    - Can resume from any checkpoint
    - Handles approval gates
    - Retries failed steps
    """

    def __init__(
        self,
        checkpoint_store: CheckpointStore,
        step_executor: Callable[[ExecutionStep], Any],
        approval_handler: Optional[Callable[[ExecutionStep], bool]] = None
    ):
        self.checkpoint_store = checkpoint_store
        self.step_executor = step_executor
        self.approval_handler = approval_handler
        self._executions: Dict[str, Execution] = {}

    async def execute(self, execution: Execution) -> Execution:
        """Execute a plan with checkpointing."""
        self._executions[execution.id] = execution
        execution.state = ExecutionState.RUNNING

        try:
            # Resume from checkpoint if exists
            latest_checkpoint = await self.checkpoint_store.get_latest(execution.id)
            if latest_checkpoint:
                execution.current_step = latest_checkpoint.step_index + 1
                execution.context = latest_checkpoint.state.get("context", {})

            # Execute remaining steps
            while execution.current_step < len(execution.steps):
                step = execution.steps[execution.current_step]

                # Handle approval gate
                if step.requires_approval:
                    execution.state = ExecutionState.WAITING_APPROVAL
                    if self.approval_handler:
                        approved = await self.approval_handler(step)
                        if not approved:
                            execution.current_step += 1
                            continue
                    execution.state = ExecutionState.RUNNING

                # Execute step with retries
                step.state = ExecutionState.RUNNING
                step.started_at = datetime.utcnow()

                for attempt in range(step.retries):
                    try:
                        result = await asyncio.wait_for(
                            self.step_executor(step),
                            timeout=step.timeout_seconds
                        )
                        step.result = result
                        step.state = ExecutionState.COMPLETED
                        step.completed_at = datetime.utcnow()
                        break
                    except asyncio.TimeoutError:
                        step.error = f"Step timed out after {step.timeout_seconds}s"
                        if attempt == step.retries - 1:
                            step.state = ExecutionState.FAILED
                    except Exception as e:
                        step.error = str(e)
                        if attempt == step.retries - 1:
                            step.state = ExecutionState.FAILED

                # Checkpoint after each step
                await self._checkpoint(execution)

                # Stop if step failed
                if step.state == ExecutionState.FAILED:
                    execution.state = ExecutionState.FAILED
                    return execution

                execution.current_step += 1

            execution.state = ExecutionState.COMPLETED
            return execution

        except Exception as e:
            execution.state = ExecutionState.FAILED
            return execution

    async def resume(self, execution_id: str) -> Optional[Execution]:
        """Resume an execution from its last checkpoint."""
        execution = self._executions.get(execution_id)
        if not execution:
            return None

        if execution.state in (ExecutionState.COMPLETED, ExecutionState.CANCELLED):
            return execution

        return await self.execute(execution)

    async def cancel(self, execution_id: str) -> bool:
        """Cancel an execution."""
        execution = self._executions.get(execution_id)
        if not execution:
            return False

        execution.state = ExecutionState.CANCELLED
        return True

    async def _checkpoint(self, execution: Execution):
        """Save a checkpoint of the current state."""
        checkpoint = Checkpoint(
            id=self._generate_checkpoint_id(execution),
            execution_id=execution.id,
            step_index=execution.current_step,
            state={
                "context": execution.context,
                "steps": [
                    {
                        "id": s.id,
                        "state": s.state.value,
                        "result": s.result,
                        "error": s.error
                    }
                    for s in execution.steps
                ]
            }
        )
        await self.checkpoint_store.save(checkpoint)
        execution.checkpoints.append(checkpoint)

    def _generate_checkpoint_id(self, execution: Execution) -> str:
        """Generate a unique checkpoint ID."""
        timestamp = datetime.utcnow().isoformat()
        return hashlib.sha256(
            f"{execution.id}{execution.current_step}{timestamp}".encode()
        ).hexdigest()[:16]


# --- Workflow Definitions ---

def create_execution(
    name: str,
    steps: List[dict],
    context: Optional[dict] = None
) -> Execution:
    """
    Create an execution from a list of step definitions.

    Example:
        execution = create_execution(
            name="meeting_prep",
            steps=[
                {"name": "fetch_calendar", "action": "calendar.get_next_meeting", "parameters": {}},
                {"name": "get_attendees", "action": "knowledge.get_person_context", "parameters": {}},
                {"name": "generate_prep", "action": "agent.generate_prep", "parameters": {}},
                {"name": "send_notification", "action": "slack.send_message", "requires_approval": True}
            ]
        )
    """
    execution_id = hashlib.sha256(f"{name}{datetime.utcnow().isoformat()}".encode()).hexdigest()[:16]

    execution_steps = []
    for i, step_def in enumerate(steps):
        step = ExecutionStep(
            id=f"{execution_id}_step_{i}",
            name=step_def.get("name", f"step_{i}"),
            action=step_def["action"],
            parameters=step_def.get("parameters", {}),
            requires_approval=step_def.get("requires_approval", False),
            timeout_seconds=step_def.get("timeout", 300),
            retries=step_def.get("retries", 3)
        )
        execution_steps.append(step)

    return Execution(
        id=execution_id,
        name=name,
        steps=execution_steps,
        context=context or {}
    )
