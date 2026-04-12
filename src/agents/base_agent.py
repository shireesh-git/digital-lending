"""
Base Agent Framework
Common interface for all pipeline agents.
"""

from datetime import datetime
from typing import Any


class AgentResult:
    """Standardized result from an agent execution."""

    __slots__ = ("agent_name", "status", "data", "error",
                 "started_at", "completed_at", "duration_ms")

    def __init__(self, agent_name: str, status: str, data: Any = None,
                 error: str = None, started_at: str = None,
                 completed_at: str = None, duration_ms: float = 0):
        self.agent_name = agent_name
        self.status = status
        self.data = data
        self.error = error
        self.started_at = started_at
        self.completed_at = completed_at
        self.duration_ms = duration_ms

    def to_dict(self) -> dict:
        return {
            "agent_name": self.agent_name,
            "status": self.status,
            "error": self.error,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration_ms": self.duration_ms,
        }


class BaseAgent:
    """All pipeline agents inherit from this."""

    name: str = "base"
    description: str = ""
    critical: bool = True  # pipeline halts on failure if True

    def execute(self, context: dict) -> AgentResult:
        start = datetime.now()
        try:
            data = self.run(context)
            end = datetime.now()
            return AgentResult(
                agent_name=self.name, status="completed", data=data,
                started_at=start.isoformat(), completed_at=end.isoformat(),
                duration_ms=round((end - start).total_seconds() * 1000, 1),
            )
        except Exception as e:
            end = datetime.now()
            return AgentResult(
                agent_name=self.name, status="failed", error=str(e),
                started_at=start.isoformat(), completed_at=end.isoformat(),
                duration_ms=round((end - start).total_seconds() * 1000, 1),
            )

    def run(self, context: dict) -> Any:
        raise NotImplementedError
