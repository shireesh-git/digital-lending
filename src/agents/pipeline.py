"""
Pipeline orchestrator: runs the agents in order, records a log entry per
agent, streams progress events, and stops on a critical failure.
"""

import logging

from src.agents.analysis_agents import BenchmarkAgent, FinancialAnalysisAgent, PolicyAgent, ValidationAgent
from src.agents.base_agent import AgentResult, BaseAgent
from src.agents.ingestion_agent import DataIngestionAgent
from src.agents.narrative_agent import NarrativeAgent
from src.agents.screening_agent import PEPScreeningAgent

log = logging.getLogger(__name__)


def default_agents(llm_provider=None, checkpoint_factory=None) -> list[BaseAgent]:
    return [
        DataIngestionAgent(),
        PEPScreeningAgent(),
        FinancialAnalysisAgent(),
        ValidationAgent(),
        BenchmarkAgent(),
        PolicyAgent(),
        NarrativeAgent(llm_provider=llm_provider, checkpoint_factory=checkpoint_factory),
    ]


class SuperAgent:
    """Orchestrates the full CAM pipeline by delegating to sub-agents."""

    def __init__(self, llm_provider=None, agents: list[BaseAgent] | None = None, checkpoint_factory=None):
        self.llm_provider = llm_provider
        self.agents: list[BaseAgent] = (agents if agents is not None
                                        else default_agents(llm_provider, checkpoint_factory))
        self.pipeline_log: list[dict] = []

    @staticmethod
    def _trace(message: str) -> None:
        log.info("[PIPELINE] %s", message)

    @staticmethod
    def _missing_requirements(agent: BaseAgent, results: dict) -> list[str]:
        return [name for name in agent.requires if name not in results]

    def execute_pipeline(self, company_data: dict, on_progress=None, stores=None) -> dict:
        context = {"company_data": company_data, "results": {}}
        if on_progress:
            context["_on_progress"] = on_progress
        if stores:
            context["_stores"] = stores
        self.pipeline_log = []
        total = len(self.agents)

        for step, agent in enumerate(self.agents, start=1):
            self._trace(f">>> Starting agent {step}/{total}: {agent.name}")
            if on_progress:
                on_progress({"type": "agent_start", "agent": agent.name, "description": agent.description,
                             "step": step, "total": total})

            missing = self._missing_requirements(agent, context["results"])
            if missing:
                result = AgentResult(agent_name=agent.name, status="failed",
                                     error=f"Missing results from required agent(s): {', '.join(missing)}")
            else:
                result = agent.execute(context)

            self._trace(f"<<< Agent {agent.name}: {result.status} ({result.duration_ms}ms)")
            self.pipeline_log.append(result.to_dict())
            if on_progress:
                on_progress({"type": "agent_complete", "agent": agent.name, "status": result.status,
                             "duration_ms": result.duration_ms, "error": result.error,
                             "step": step, "total": total})

            if result.status == "completed" and result.data:
                context["results"][agent.name] = result.data
            elif result.status == "failed" and agent.critical:
                raise RuntimeError(f"Critical agent '{agent.name}' failed: {result.error}")

        return context

    def get_agent_list(self) -> list[dict]:
        return [agent.describe() for agent in self.agents]
