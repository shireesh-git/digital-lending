"""
Base Agent Framework
Common interface and result contract for all pipeline agents.
"""

from datetime import datetime
from typing import Any, Callable


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
    """All pipeline agents inherit from this.

    Contract:
      * ``requires`` — agents that must finish *successfully* first: their results
        (``context["results"]``) or their changes to ``company_data`` are needed.
        The orchestrator starts an agent only after these finish, and fails it
        if one of them produced no result, so a broken order fails loudly.
      * ``waits_for`` — agents to wait for whose results are optional: the agent
        starts after them and uses their result when present, but runs anyway if
        they failed (e.g. reuse a non-critical agent's output instead of
        recomputing it).
      * ``critical`` — when True, a failure stops the pipeline.
      * ``run(context)`` returns this agent's result payload, stored under
        ``context["results"][name]``.

    Agents without a dependency between them may run at the same time (see
    ``src/agents/pipeline.py``), so an agent must not write to ``company_data``
    keys that another independent agent reads.
    """

    name: str = "base"
    description: str = ""
    critical: bool = True
    requires: tuple[str, ...] = ()
    waits_for: tuple[str, ...] = ()

    def execute(self, context: dict) -> AgentResult:
        start = datetime.now()
        try:
            data = self.run(context)
            status, error = "completed", None
        except Exception as e:
            data, status, error = None, "failed", str(e)
        end = datetime.now()
        return AgentResult(
            agent_name=self.name, status=status, data=data, error=error,
            started_at=start.isoformat(), completed_at=end.isoformat(),
            duration_ms=round((end - start).total_seconds() * 1000, 1),
        )

    def run(self, context: dict) -> Any:
        raise NotImplementedError

    @staticmethod
    def emitter(context: dict) -> Callable[[str], None]:
        """Progress callback that forwards info messages to the pipeline listener."""
        on_progress = context.get("_on_progress")

        def emit(message: str) -> None:
            if on_progress:
                on_progress({"type": "info", "message": message})

        return emit

    def describe(self) -> dict:
        return {"name": self.name, "description": self.description,
                "critical": self.critical, "requires": list(self.requires),
                "waits_for": list(self.waits_for)}
