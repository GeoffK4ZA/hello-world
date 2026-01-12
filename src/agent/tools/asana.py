"""
Asana Integration for Digital Geoff.

Provides comprehensive task and project management:
- Task creation, updates, completion
- Project management
- Due date tracking
- Assignment and collaboration
"""

from datetime import datetime, timedelta
from typing import Any, Optional, List
from .base import BaseTool, ToolResult


class AsanaTool(BaseTool):
    """
    Asana task management integration.

    Actions:
    - get_tasks: Get tasks from a project or assignee
    - get_task: Get a specific task by ID
    - create_task: Create a new task
    - update_task: Update an existing task
    - complete_task: Mark a task as complete
    - get_due_soon: Get tasks due within N hours
    - check_due_soon: Check for tasks due soon (for triggers)
    - find_stale_tasks: Find tasks not updated in N days
    - get_projects: List all projects
    - add_comment: Add a comment to a task
    """

    name = "asana"
    description = "Manage Asana tasks and projects - create, update, track, and complete tasks"

    def __init__(self, personal_access_token: str, workspace_id: Optional[str] = None):
        self.token = personal_access_token
        self.workspace_id = workspace_id
        self.base_url = "https://app.asana.com/api/1.0"
        # Production: Initialize httpx client with auth headers

    async def execute(self, action: str, parameters: dict) -> ToolResult:
        try:
            actions = {
                "get_tasks": self._get_tasks,
                "get_task": self._get_task,
                "create_task": self._create_task,
                "update_task": self._update_task,
                "complete_task": self._complete_task,
                "get_due_soon": self._get_due_soon,
                "check_due_soon": self._check_due_soon,
                "find_stale_tasks": self._find_stale_tasks,
                "get_projects": self._get_projects,
                "add_comment": self._add_comment
            }

            if action not in actions:
                return ToolResult(success=False, error=f"Unknown action: {action}")

            return await actions[action](parameters)
        except Exception as e:
            return ToolResult(success=False, error=str(e))

    async def _get_tasks(self, params: dict) -> ToolResult:
        """Get tasks, optionally filtered by project or assignee."""
        project_id = params.get("project_id")
        assignee = params.get("assignee", "me")
        completed = params.get("completed", False)

        # Production Asana API:
        # url = f"{self.base_url}/tasks"
        # query = {"assignee": assignee, "workspace": self.workspace_id, "completed_since": "now" if not completed else None}
        # response = await self._request("GET", url, params=query)

        return ToolResult(
            success=True,
            data={
                "tasks": [
                    {
                        "id": "task_1",
                        "name": "Review architecture proposal",
                        "due_on": "2026-01-13",
                        "assignee": {"name": "Me"},
                        "completed": False,
                        "projects": [{"name": "Data Platform Migration"}],
                        "tags": ["high-priority"]
                    },
                    {
                        "id": "task_2",
                        "name": "Prepare stakeholder presentation",
                        "due_on": "2026-01-15",
                        "assignee": {"name": "Me"},
                        "completed": False,
                        "projects": [{"name": "Q1 Planning"}]
                    }
                ]
            }
        )

    async def _get_task(self, params: dict) -> ToolResult:
        """Get a specific task by ID."""
        task_id = params.get("task_id")
        if not task_id:
            return ToolResult(success=False, error="task_id is required")

        # Production: GET /tasks/{task_id}
        return ToolResult(
            success=True,
            data={
                "task": {
                    "id": task_id,
                    "name": "Example Task",
                    "notes": "Task description here",
                    "due_on": "2026-01-14",
                    "completed": False
                }
            }
        )

    async def _create_task(self, params: dict) -> ToolResult:
        """Create a new task."""
        name = params.get("name")
        if not name:
            return ToolResult(success=False, error="name is required")

        # Production Asana API:
        # body = {
        #     "data": {
        #         "name": name,
        #         "notes": params.get("notes", ""),
        #         "due_on": params.get("due_on"),
        #         "assignee": params.get("assignee", "me"),
        #         "projects": params.get("projects", [])
        #     }
        # }
        # response = await self._request("POST", f"{self.base_url}/tasks", json=body)

        return ToolResult(
            success=True,
            data={
                "task": {
                    "id": "new_task_456",
                    "name": name,
                    "created": True
                }
            }
        )

    async def _update_task(self, params: dict) -> ToolResult:
        """Update an existing task."""
        task_id = params.get("task_id")
        if not task_id:
            return ToolResult(success=False, error="task_id is required")

        # Production: PUT /tasks/{task_id}
        return ToolResult(
            success=True,
            data={"task_id": task_id, "updated": True}
        )

    async def _complete_task(self, params: dict) -> ToolResult:
        """Mark a task as complete."""
        task_id = params.get("task_id")
        if not task_id:
            return ToolResult(success=False, error="task_id is required")

        # Production: PUT /tasks/{task_id} with completed=true
        return ToolResult(
            success=True,
            data={"task_id": task_id, "completed": True}
        )

    async def _get_due_soon(self, params: dict) -> ToolResult:
        """Get tasks due within N hours."""
        hours = params.get("hours", 24)
        due_before = datetime.utcnow() + timedelta(hours=hours)

        # Production: Filter tasks by due_on
        return ToolResult(
            success=True,
            data={
                "tasks": [
                    {
                        "id": "task_urgent",
                        "name": "Submit weekly report",
                        "due_on": "2026-01-12",
                        "hours_until_due": 4
                    }
                ],
                "count": 1
            }
        )

    async def _check_due_soon(self, params: dict) -> ToolResult:
        """Check for tasks due soon (used by trigger system)."""
        hours = params.get("hours", 24)
        result = await self._get_due_soon({"hours": hours})

        if result.success and result.data.get("tasks"):
            return ToolResult(
                success=True,
                data=result.data["tasks"]  # Return just the list for trigger processing
            )
        return ToolResult(success=True, data=[])

    async def _find_stale_tasks(self, params: dict) -> ToolResult:
        """Find tasks not updated in N days."""
        days = params.get("days", 7)

        # Production: Query tasks and filter by modified_at
        return ToolResult(
            success=True,
            data={
                "stale_tasks": [
                    {
                        "id": "task_stale_1",
                        "name": "Review vendor proposals",
                        "last_modified": "2026-01-05",
                        "days_stale": 7
                    }
                ]
            }
        )

    async def _get_projects(self, params: dict) -> ToolResult:
        """List all projects."""
        # Production: GET /projects
        return ToolResult(
            success=True,
            data={
                "projects": [
                    {"id": "proj_1", "name": "Data Platform Migration", "status": "active"},
                    {"id": "proj_2", "name": "Q1 Planning", "status": "active"},
                    {"id": "proj_3", "name": "Client Delivery - Acme Corp", "status": "active"}
                ]
            }
        )

    async def _add_comment(self, params: dict) -> ToolResult:
        """Add a comment to a task."""
        task_id = params.get("task_id")
        text = params.get("text")

        if not task_id or not text:
            return ToolResult(success=False, error="task_id and text are required")

        # Production: POST /tasks/{task_id}/stories
        return ToolResult(
            success=True,
            data={"comment_id": "comment_789", "added": True}
        )

    def get_actions(self) -> list[dict]:
        return [
            {"name": "get_tasks", "description": "Get tasks from a project or assignee"},
            {"name": "get_task", "description": "Get a specific task by ID"},
            {"name": "create_task", "description": "Create a new task"},
            {"name": "update_task", "description": "Update an existing task"},
            {"name": "complete_task", "description": "Mark a task as complete"},
            {"name": "get_due_soon", "description": "Get tasks due within N hours"},
            {"name": "check_due_soon", "description": "Check for tasks due soon"},
            {"name": "find_stale_tasks", "description": "Find tasks not updated in N days"},
            {"name": "get_projects", "description": "List all projects"},
            {"name": "add_comment", "description": "Add a comment to a task"}
        ]
