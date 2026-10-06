"""
Credit cases: running the analysis pipeline for a borrower, building the case
record, and loading cases from memory, SQLite or legacy output files.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Callable
from uuid import uuid4

from src.application.company_service import CompanyService
from src.application.errors import ConflictError, NotFoundError
from src.application.serialization import repair_mojibake, repair_mojibake_text, to_jsonable
from src.application.state import AppState
from src.core.config_manager import config

log = logging.getLogger(__name__)

ProgressCallback = Callable[[dict], None]


def build_case_result(entity_id: str, company_data: dict, context: dict, pipeline_log: list) -> dict:
    """Flatten a pipeline context into the case record stored and served by the API."""
    results = context.get("results", {})
    narrative = results.get("narrative", {})
    policy = results.get("policy", {})
    validation = results.get("validation", {})
    rec = policy.get("recommendation")
    rs = policy.get("risk_score")
    b = company_data["borrower"]
    f = company_data["facility"]
    return {
        "run_id": uuid4().hex,
        "entity_id": entity_id,
        "company_name": b.company_name,
        "sector": b.sector.value,
        "case_type": f.case_type.value,
        "requested_amount_cr": f.amount_requested_cr,
        "facility_type": f.facility_type.value if hasattr(f.facility_type, "value") else str(f.facility_type),
        "recommendation": rec.recommendation.value if rec else "error",
        "risk_grade": rs.risk_grade if rs else "N/A",
        "composite_score": rs.composite_score if rs else 0,
        "financial_score": rs.financial_score if rs else 0,
        "conduct_score": rs.conduct_score if rs else 0,
        "governance_score": rs.governance_score if rs else 0,
        "market_score": rs.market_score if rs else 0,
        "conditions": rec.conditions if rec else [],
        "covenants_proposed": rec.covenants_proposed if rec else [],
        "rationale": rec.rationale if rec else "",
        "cam_text": narrative.get("cam_text", ""),
        "narrative_mode": narrative.get("narrative_mode", "template"),
        "data_provider": company_data.get("data_provider", "internal"),
        "fact_pack": narrative.get("fact_pack", {}),
        "pipeline_log": pipeline_log,
        "run_at": datetime.now().isoformat(),
        "tier1_decisions": to_jsonable(policy.get("tier1_decisions", [])),
        "exceptions": to_jsonable(validation.get("exceptions", [])),
    }


class CaseService:
    def __init__(self, state: AppState, persistence, companies: CompanyService,
                 output_dir: Path, pipeline_factory: Callable,
                 rerun_guard: Callable[[str], bool] | None = None):
        self.state = state
        # Returns True when a case must not be re-run (e.g. it is with an approver).
        self.rerun_guard = rerun_guard
        self.persistence = persistence
        self.companies = companies
        self.output_dir = output_dir
        self._pipeline_factory = pipeline_factory

    # ── Queries ──────────────────────────────────────────────────────────

    def get(self, entity_id: str) -> dict | None:
        """Latest case from memory, then SQLite, then legacy output files.

        Cases are text-repaired once when they enter memory (run, load), so a
        read does not walk the whole case — fact pack included — again.
        """
        if entity_id in self.state.cases:
            return self.state.cases[entity_id]
        stored = self.persistence.get_latest_case(entity_id)
        if stored:
            self.state.cases[entity_id] = repair_mojibake(stored)
            return self.state.cases[entity_id]
        return self._load_from_disk(entity_id)

    def require(self, entity_id: str, message: str = "Case not found") -> dict:
        case = self.get(entity_id)
        if not case:
            raise NotFoundError(message)
        return case

    def run_history(self, entity_id: str, limit: int = 20) -> list[dict]:
        """Every pipeline attempt for a company, including failed ones."""
        self.companies.require(entity_id)
        return self.persistence.list_pipeline_runs(entity_id, limit)

    def summaries(self) -> list[dict]:
        keys = ("entity_id", "company_name", "sector", "case_type", "facility_type",
                "requested_amount_cr", "recommendation", "risk_grade", "data_provider",
                "composite_score", "financial_score", "conduct_score", "governance_score",
                "market_score", "narrative_mode", "run_at")
        return [{**{k: c[k] for k in keys if k in c}, **self._review_indicators(c)}
                for c in self.state.cases.values()]

    @staticmethod
    def _review_indicators(case: dict) -> dict:
        """Small review indicators so list views need not fetch the full case."""
        exceptions = case.get("exceptions") or []
        top = exceptions[0] if exceptions and isinstance(exceptions[0], dict) else {}
        key_risks = (case.get("fact_pack") or {}).get("key_risks")
        return {
            "exception_count": len(exceptions),
            "top_exception": top.get("message") or top.get("exception_code"),
            "key_risk_count": len(key_risks) if isinstance(key_risks, list) else 0,
            "documents_changed": bool(case.get("_documents_changed")),
        }

    def dashboard(self) -> dict:
        cases = list(self.state.cases.values())
        grade_dist: dict[str, int] = {}
        for c in cases:
            grade = c.get("risk_grade", "N/A")
            grade_dist[grade] = grade_dist.get(grade, 0) + 1
        recent = sorted(cases, key=lambda x: x.get("run_at", ""), reverse=True)[:5]

        # Human decisions on each company's latest run (metrics above are system recommendations).
        current_runs = {c.get("entity_id"): c.get("run_id") for c in cases}
        workflow_status: dict[str, int] = {}
        decided = set()
        for wf in self.persistence.list_workflows():
            if current_runs.get(wf["entity_id"]) == wf["case_run_id"]:
                workflow_status[wf["status"]] = workflow_status.get(wf["status"], 0) + 1
                decided.add(wf["entity_id"])
        undecided_drafts = sum(1 for eid in current_runs if eid not in decided)
        if undecided_drafts:
            workflow_status["draft"] = workflow_status.get("draft", 0) + undecided_drafts

        return {
            "workflow_status": workflow_status,
            "metrics": {
                "total_cases": len(cases),
                "approved": sum(1 for c in cases if c.get("recommendation") in ("approve", "conditional_approve")),
                "declined": sum(1 for c in cases if c.get("recommendation") == "decline"),
                "referred": sum(1 for c in cases if c.get("recommendation") == "refer"),
            },
            "grade_distribution": grade_dist,
            "recent_cases": [
                {k: c[k] for k in ("entity_id", "company_name", "recommendation",
                                   "risk_grade", "composite_score", "run_at")}
                for c in recent
            ],
        }

    # ── Pipeline execution ───────────────────────────────────────────────

    def run(self, entity_id: str, on_progress: ProgressCallback | None = None,
            enrich: bool = True) -> tuple[dict, list]:
        """Run the full analysis pipeline and persist the resulting case.

        Returns ``(case_record, pipeline_log)``. Raises if a critical agent fails.
        """
        if not self.companies.exists(entity_id):
            raise NotFoundError(f"Company {entity_id} not found")
        if self.rerun_guard and self.rerun_guard(entity_id):
            raise ConflictError("Case is with the approving authority — recall it before re-running")

        tracking_id = uuid4().hex
        self.persistence.start_pipeline_run(tracking_id, entity_id,
                                            llm_provider=config.get("llm_providers", "active_provider"))
        try:
            company = self.companies.ensure_enriched(entity_id) if enrich else self.companies.get(entity_id)
            pipeline = self._pipeline_factory()
            context = pipeline.execute_pipeline(company, on_progress=on_progress,
                                                stores=self.state.pipeline_stores())
            # Text repair happens once, here and on load, not on every read.
            case = repair_mojibake(build_case_result(entity_id, company, context, pipeline.pipeline_log))
            self.state.cases[entity_id] = case
            self.persistence.save_case_run(case)
        except Exception as e:
            self.persistence.finish_pipeline_run(tracking_id, "failed", error=str(e))
            raise
        self.persistence.finish_pipeline_run(tracking_id, "completed", case_run_id=case["run_id"])
        self.persistence.reset_workflow(entity_id, case["run_id"])
        return case, pipeline.pipeline_log

    # ── Legacy output-file cases ─────────────────────────────────────────

    def load_all_from_disk(self) -> None:
        """Populate the cache from ``*_fact_pack.json`` files of earlier versions."""
        if not self.output_dir.exists():
            return
        for fp_file in self.output_dir.glob("*_fact_pack.json"):
            eid = fp_file.stem.replace("_fact_pack", "")
            if eid in self.state.companies and eid not in self.state.cases:
                self._load_from_disk(eid)

    def _read_json(self, path: Path) -> dict:
        if not path.exists():
            return {}
        try:
            return repair_mojibake(json.loads(path.read_text(encoding="utf-8")))
        except Exception:
            return {}

    def _load_from_disk(self, entity_id: str) -> dict | None:
        fact_pack_file = self.output_dir / f"{entity_id}_fact_pack.json"
        if not fact_pack_file.exists():
            return None

        fp = self._read_json(fact_pack_file)
        pr = self._read_json(self.output_dir / f"{entity_id}_pipeline_result.json")
        cam_text = ""
        cam_md_file = self.output_dir / f"{entity_id}_CAM.md"
        if cam_md_file.exists():
            try:
                cam_text = repair_mojibake_text(cam_md_file.read_text(encoding="utf-8"))
            except Exception:
                pass

        company = self.state.companies.get(entity_id)
        company_name = company["borrower"].company_name if company else ""
        if not company_name:
            company_name = fp.get("company_name") or fp.get("borrower_name", entity_id)

        policy = fp.get("policy_decisions", {})
        risk_scores = policy.get("tier2_risk_scores", {})
        recommendation = policy.get("tier3_recommendation", {})
        case_summary = fp.get("case_summary", {})
        facility_details = fp.get("facility_details", {})
        borrower_profile = fp.get("borrower_profile", {})

        case = {
            "run_id": pr.get("run_id") or f"legacy-{entity_id}",
            "entity_id": entity_id,
            "company_name": company_name or borrower_profile.get("company_name", entity_id),
            "sector": pr.get("sector") or case_summary.get("sector", ""),
            "case_type": pr.get("case_type") or case_summary.get("case_type", ""),
            "requested_amount_cr": (pr.get("requested_amount_cr") or case_summary.get("amount_requested_cr")
                                    or facility_details.get("amount_requested_cr")),
            "facility_type": (pr.get("facility_type") or case_summary.get("facility_type")
                              or facility_details.get("facility_type")),
            "recommendation": pr.get("recommendation") or recommendation.get("recommendation", "pending"),
            "risk_grade": (pr.get("risk_grade") or recommendation.get("risk_grade")
                           or risk_scores.get("risk_grade", "N/A")),
            "composite_score": (pr.get("composite_score") or recommendation.get("composite_score")
                                or risk_scores.get("composite_score", 0) or 0),
            "financial_score": pr.get("financial_score") or risk_scores.get("financial_score", 0) or 0,
            "conduct_score": pr.get("conduct_score") or risk_scores.get("conduct_score", 0) or 0,
            "governance_score": pr.get("governance_score") or risk_scores.get("governance_score", 0) or 0,
            "market_score": pr.get("market_score") or risk_scores.get("market_score", 0) or 0,
            "cam_text": cam_text,
            "narrative_mode": pr.get("narrative_mode", "template"),
            "data_provider": company.get("data_provider", "internal") if company else "internal",
            "fact_pack": fp,
            "pipeline_log": pr.get("pipeline_log", []),
            "run_at": pr.get("run_at", ""),
            "conditions": pr.get("conditions") or recommendation.get("conditions", []),
            "covenants_proposed": pr.get("covenants_proposed") or recommendation.get("covenants_proposed", []),
            "rationale": pr.get("rationale") or recommendation.get("rationale", ""),
            "_loaded_from_disk": True,
        }
        self.state.cases[entity_id] = case
        self.persistence.save_case_run(case)
        return case
