"""
core/state.py

Responsible for:
    - Representing the application's in-memory runtime state.

This module defines *structure only* — no persistence, no database,
no memory-manager logic. Sprint 5 (Memory) will read/write this shape
to a real store (SQLite first, PostgreSQL later) without needing to
change these definitions; persistence sits on top of this structure
rather than replacing it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class TaskStatus(Enum):
    """Lifecycle states for a unit of work moving through the system."""

    IDLE = "idle"
    ROUTING = "routing"
    RUNNING = "running"
    WAITING_ON_HUMAN = "waiting_on_human"  # MAFS Ch.2: Human Control
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Session:
    """A single conversational session between a user and the system."""

    session_id: str
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    is_active: bool = True


@dataclass
class AppState:
    """
    Mutable runtime state for the current process.

    Attributes:
        current_user: Identifier for the active user, if any.
        current_session: The active Session, if any.
        selected_agent: agent_id of the agent currently handling the
            task (per MAFS Ch.4 agent_id convention). Stays None until
            a real Agent Layer exists (Sprint 3+).
        selected_skill: Name of the skill currently in use, if any.
        selected_model: Name/label of the model or provider currently
            selected. Just a string in Sprint 2 — the Provider Layer
            (Sprint 4) will validate it against real providers.
        task_status: Current TaskStatus of the active task.
    """

    current_user: Optional[str] = None
    current_session: Optional[Session] = None
    selected_agent: Optional[str] = None
    selected_skill: Optional[str] = None
    selected_model: Optional[str] = None
    task_status: TaskStatus = TaskStatus.IDLE

    def start_session(self, session_id: str, user: Optional[str] = None) -> None:
        """Begin a new session, replacing any previous one."""
        self.current_session = Session(session_id=session_id)
        self.current_user = user
        self.task_status = TaskStatus.IDLE

    def end_session(self) -> None:
        """Mark the current session inactive."""
        if self.current_session is not None:
            self.current_session.is_active = False
        self.task_status = TaskStatus.IDLE

    def reset_task(self) -> None:
        """
        Reset per-task selections without ending the session.

        Resets agent, skill, AND model selection: all three are
        per-task routing decisions, so leaving any one of them behind
        after a reset would let a stale model silently carry over into
        the next task.
        """
        self.selected_agent = None
        self.selected_skill = None
        self.selected_model = None
        self.task_status = TaskStatus.IDLE
