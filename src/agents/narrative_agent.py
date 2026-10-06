"""CAM narrative: build the approved fact pack and render the CAM (LLM or template)."""

import logging

from src.agents.base_agent import BaseAgent

log = logging.getLogger(__name__)


class NarrativeAgent(BaseAgent):
    name = "narrative"
    description = "Build fact-pack and render CAM narrative"
    critical = True
    requires = ("financial_analysis", "validation", "benchmark", "policy")

    def __init__(self, llm_provider=None, checkpoint_factory=None):
        """``checkpoint_factory(entity_id, llm_provider)`` returns a section
        checkpoint store, or None to generate every section from scratch."""
        self.llm = llm_provider
        self.checkpoint_factory = checkpoint_factory

    def _template_mode(self) -> bool:
        from src.core.config_manager import config

        is_mock = not self.llm or getattr(self.llm, "name", None) == "mock"
        narrative_cfg = config.get("llm_providers", "narrative", default={}) or {}
        return is_mock or narrative_cfg.get("mode") == "template"

    @staticmethod
    def _assessment(context):
        """The credit assessment already made by the analysis agents."""
        from src.engines.credit_assessment import CreditAssessment

        r = context["results"]
        return CreditAssessment(
            exceptions=r["validation"]["exceptions"],
            benchmarks=r["benchmark"]["view"],
            latest_ratios=r["financial_analysis"]["latest_ratios"],
            policy=r["policy"]["outcome"],
        )

    def run(self, context):
        from src.core.config_manager import config
        from src.engines.cam_fact_builder import build_cam_fact_pack
        from src.engines.cam_llm_renderer import render_cam_template_only, render_cam_with_llm

        fact_pack = build_cam_fact_pack(context["company_data"], assessment=self._assessment(context))
        section_cb = context.get("_on_progress")

        if self._template_mode():
            cam_text = render_cam_template_only(fact_pack, on_section_progress=section_cb)
            return {"fact_pack": fact_pack, "cam_text": cam_text, "narrative_mode": "template"}

        settings = config.get_narrative_settings()  # raises if mode != 'llm'
        entity_id = context["company_data"]["borrower"].entity_id
        checkpoints = self.checkpoint_factory(entity_id, self.llm) if self.checkpoint_factory else None
        cam_text = render_cam_with_llm(
            fact_pack=fact_pack,
            llm_provider=self.llm,
            temperature=settings.get("temperature", 0.1),
            max_tokens_per_section=settings.get("max_tokens_per_section", 1500),
            on_section_progress=section_cb,
            checkpoints=checkpoints,
        )
        if not cam_text or len(cam_text.strip()) < 100:
            raise RuntimeError("LLM narrative generation produced empty or insufficient output")
        return {"fact_pack": fact_pack, "cam_text": cam_text, "narrative_mode": "llm"}
