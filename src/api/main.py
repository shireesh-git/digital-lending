"""
CAM Intelligence Platform — FastAPI Backend
REST API + static-file serving for the dashboard SPA.
"""

import sys
import json
import re
from pathlib import Path
from datetime import datetime, date
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request, UploadFile, File, Form, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, Response, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

# Ensure project root importable
_root = str(Path(__file__).parent.parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

from src.core.env_loader import load_local_env

load_local_env()

from src.core.config_manager import config
from src.core.engine_registry import registry, register_default_engines
from src.core.llm_provider import create_llm_provider
from src.core.runtime_paths import DOCUMENTS_ROOT, OUTPUT_ROOT, REFERENCE_CAM_ROOT
from src.agents.super_agent import SuperAgent
from src.agents.dashboard_360_agent import generate_360_view
from src.data.company_catalog import bootstrap_reference_documents, seed_company_store
from src.services.company_onboarding import onboard_company
from src.services.document_store import doc_store
from src.services.document_operations import document_operations
from src.services.external_systems import (
    resolve_company, mca_company_master, mca_directors, mca_charges,
    gstin_details, gstin_turnover, bureau_commercial_report,
    rating_action, market_intelligence, crilc_report,
    epfo_compliance, itr_filing_status,
    exchange_financial_results, exchange_governance_filings,
    social_reputation_signals,
)
from src.services.document_extractor import extract_all_documents
from src.services.analyst_chat import (
    chat as analyst_chat_fn, get_or_create_session, clear_session,
    get_session_history, list_sessions as chat_list_sessions,
)
from src.services.probe_service import (
    get_probe_status, resolve_company_with_probe,
    company_probe_snapshot, probe_context_text, clear_probe_cache,
)
# synthetic_optional_inputs removed — all data via Probe42
from src.services.document_classifier import requirement_is_satisfied
from src.engines.etb_analytics_engine import run_etb_analytics, etb_analysis_to_dict
from src.engines.fraud_detection_engine import run_fraud_scan
from src.services.ocr_service import extract_document as ocr_extract, analyze_document_metadata
from src.engines.cam_one_pager import generate_one_pager_html
from src.services.corporate_hierarchy import (
    enrich_group_with_hierarchy, hierarchy_to_dict, build_corporate_hierarchy,
)
from src.services.persistence import persistence
from src.models.canonical_model import (
    Borrower, GroupEntity, DirectorPromoter, FinancialStatement,
    FacilityRequest, Collateral, ExistingExposure, MarketSignal,
    CaseType, BorrowerType, FacilityType, Sector,
)

# ─── Bootstrap ───────────────────────────────────────────────────────────────

config.load()
register_default_engines()

app = FastAPI(title="CAM Intelligence Platform", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)

# In-memory case store (latest run per entity, backed by SQLite)
case_store: dict[str, dict] = persistence.load_latest_cases()

# Dynamic company store — pre-loaded with reference-backed catalog + persisted updates
company_store: dict[str, dict] = seed_company_store()
company_store.update(persistence.load_companies())
case_store = {eid: case for eid, case in case_store.items() if eid in company_store}
ALL_COMPANIES = company_store
bootstrap_reference_documents()

# Extraction / ETB analytics / fraud caches
extraction_store: dict[str, dict] = {}
etb_store: dict[str, dict] = {}
fraud_store: dict[str, dict] = {}

# Static / SPA paths
_ui = Path(__file__).parent.parent / "ui"
app.mount("/static", StaticFiles(directory=str(_ui / "static")), name="static")


@app.get("/", response_class=HTMLResponse)
async def serve_spa():
    return (_ui / "templates" / "index.html").read_text(encoding="utf-8")


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return Response(status_code=204)


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════════

_output_dir = OUTPUT_ROOT
_reference_root = REFERENCE_CAM_ROOT
_reference_stop_words = {
    "and", "co", "company", "corp", "corporation", "inc", "india", "industries",
    "limited", "ltd", "pvt", "private", "services", "solutions",
}
_rm_upload_requirements = [
    {
        "type": "audited_financial_statements",
        "description": "Audited financial statements for latest 3 years",
        "category": "financials",
        "role": "audited_financial_statements",
    },
    {
        "type": "provisional_financials",
        "description": "Latest provisional or management financials",
        "category": "financials",
        "role": "provisional_financials",
    },
    {
        "type": "debt_schedule",
        "description": "Detailed debt schedule and lender-wise exposure",
        "category": "financials",
        "role": "debt_schedule",
    },
    {
        "type": "board_resolution",
        "description": "Board resolution / borrowing approval",
        "category": "kyc",
        "role": "board_resolution",
    },
    {
        "type": "cma_or_projection",
        "description": "CMA data / projections / repayment assumptions",
        "category": "request",
        "role": "cma_or_projection",
    },
]
_probe_source_requirements = [
    {
        "category": "mca",
        "filename": "probe42_base_details.json",
        "description": "Probe42 company master profile",
    },
    {
        "category": "mca",
        "filename": "probe42_open_charges.json",
        "description": "Probe42 open charges profile",
    },
    {
        "category": "kyc",
        "filename": "probe42_kyc_details.json",
        "description": "Probe42 KYC profile",
    },
    {
        "category": "legal",
        "filename": "probe42_legal_history.json",
        "description": "Probe42 legal history",
    },
    {
        "category": "ratings",
        "filename": "probe42_credit_ratings.json",
        "description": "Probe42 credit ratings snapshot",
    },
    {
        "category": "gst",
        "filename": "probe42_gst_details.json",
        "description": "Probe42 GST profile",
    },
    {
        "category": "legal",
        "filename": "probe42_epfo_details.json",
        "description": "Probe42 EPFO profile",
    },
    {
        "category": "legal",
        "filename": "probe42_suit_filed_cases.json",
        "description": "Probe42 suit-filed cases",
    },
    {
        "category": "mca",
        "filename": "probe42_director_network.json",
        "description": "Probe42 director network",
    },
    {
        "category": "misc",
        "filename": "probe42_data_status.json",
        "description": "Probe42 data status and freshness",
    },
]


def _load_cam_comments(entity_id: str) -> dict[str, str]:
    cr = case_store.get(entity_id)
    run_id = (cr or {}).get("run_id")
    if not run_id:
        return {}
    return persistence.load_case_comments(run_id)


def _normalize_lookup_text(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(text or "").lower()).strip()


def _significant_tokens(text: str) -> set[str]:
    return {
        token for token in _normalize_lookup_text(text).split()
        if len(token) >= 3 and token not in _reference_stop_words
    }


def _workspace_provider(company_data: dict | None, workspace: dict) -> str:
    provider = (company_data or {}).get("data_provider")
    if provider:
        return provider
    active_sources = set(workspace.get("active_sources") or [])
    if "probe42_mcp_v2" in active_sources:
        return "probe42_mcp_v2"
    return "internal"


def _visible_stems_for_category(workspace: dict, category: str) -> set[str]:
    info = (workspace.get("categories") or {}).get(category) or {}
    return {Path(name).stem for name in info.get("files") or []}


def _required_missing_documents(workspace: dict) -> list[dict]:
    missing: list[dict] = []
    for requirement in _rm_upload_requirements:
        category_info = (workspace.get("categories") or {}).get(requirement["category"]) or {}
        visible_files = category_info.get("files") or []
        if requirement_is_satisfied(requirement["category"], visible_files, requirement["role"]):
            continue
        # Also check if any item has the role assigned (e.g. via manual upload tagging)
        items = category_info.get("items") or []
        if any(item.get("document_role") == requirement["role"] for item in items):
            continue
        missing.append({
            "type": requirement["type"],
            "description": requirement["description"],
            "category": requirement["category"],
            "source": "rm_upload",
        })
    return missing


def _rm_upload_requirement_map() -> dict[str, list[dict]]:
    mapping: dict[str, list[dict]] = {}
    for requirement in _rm_upload_requirements:
        mapping.setdefault(requirement["category"], []).append(requirement)
    return mapping


def _source_gaps(company_data: dict | None, workspace: dict) -> list[dict]:
    provider = _workspace_provider(company_data, workspace)
    if provider != "probe42_mcp_v2":
        return []

    missing: list[dict] = []
    categories = workspace.get("categories") or {}
    for requirement in _probe_source_requirements:
        category_info = categories.get(requirement["category"]) or {}
        files = set(category_info.get("raw_files") or [])
        if requirement["filename"] in files:
            continue
        missing.append({
            "type": requirement["filename"].replace(".json", ""),
            "description": requirement["description"],
            "category": requirement["category"],
            "source": "probe42_mcp_v2",
        })
    return missing


def _augment_document_workspace(entity_id: str, company_data: dict | None, workspace: dict) -> dict:
    if not workspace.get("exists"):
        return workspace

    required_missing = _required_missing_documents(workspace)
    source_gaps = _source_gaps(company_data, workspace)
    requirement_map = _rm_upload_requirement_map()
    total_required = len(_rm_upload_requirements)
    matched_required = total_required - len(required_missing)

    for category, info in (workspace.get("categories") or {}).items():
        visible_files = info.get("files") or []
        requirements = requirement_map.get(category, [])
        matched = 0
        missing_descriptions: list[str] = []
        for requirement in requirements:
            if requirement_is_satisfied(category, visible_files, requirement["role"]):
                matched += 1
            else:
                missing_descriptions.append(requirement["description"])
        info["upload_required_count"] = len(requirements)
        info["upload_matched_count"] = matched
        info["upload_missing_descriptions"] = missing_descriptions
        info["upload_coverage_pct"] = round(matched / len(requirements) * 100, 1) if requirements else None
        info["has_archived_reference"] = bool((info.get("hidden_legacy_count") or 0) + (info.get("hidden_system_count") or 0))

    workspace["provider"] = _workspace_provider(company_data, workspace)
    workspace["required_missing_documents"] = required_missing
    workspace["source_gaps"] = source_gaps
    workspace["upload_required_count"] = total_required
    workspace["upload_matched_count"] = matched_required
    workspace["upload_coverage_pct"] = round(matched_required / total_required * 100, 1) if total_required else 100.0
    workspace["hidden_artifact_count"] = int(workspace.get("hidden_legacy_files", 0)) + int(workspace.get("hidden_system_files", 0))
    workspace["summary_note"] = (
        f"Showing {workspace.get('total_files', 0)} borrower/reference files with "
        f"{workspace.get('hidden_artifact_count', 0)} additional source/system files available."
    )
    workspace["public_record_note"] = (
        "Verified public records are retained locally and reused automatically. "
        "Borrower, RM, and internal bank files must still be uploaded into the workspace."
    )
    return workspace


def _company_probe_identifiers(entity_id: str, company_data: dict | None) -> list[str]:
    identifiers: set[str] = {entity_id}
    borrower = (company_data or {}).get("borrower")
    for value in (
        getattr(borrower, "cin", None),
        getattr(borrower, "pan", None),
        getattr(borrower, "gstin", None),
        (company_data or {}).get("preferred_identifier"),
    ):
        if value:
            identifiers.add(str(value))

    summary = (company_data or {}).get("probe_summary") or {}
    resolved = ((company_data or {}).get("probe_bundle") or {}).get("resolved") or {}
    bundle = (company_data or {}).get("probe_bundle") or {}
    for source in (summary, resolved):
        if not isinstance(source, dict):
            continue
        for key in ("cin", "pan", "gstin", "company_name"):
            value = source.get(key)
            if value:
                identifiers.add(str(value))
    if bundle.get("resolved_identifier"):
        identifiers.add(str(bundle.get("resolved_identifier")))
    return sorted(identifiers)


def _clear_stored_probe_documents(entity_id: str) -> list[str]:
    entity_root = DOCUMENTS_ROOT / entity_id
    deleted: list[str] = []
    if not entity_root.exists():
        return deleted

    for path in entity_root.rglob("probe42_*.json"):
        if not path.is_file():
            continue
        try:
            path.unlink()
            deleted.append(str(path.relative_to(entity_root)))
        except Exception:
            continue

    metadata_path = entity_root / "metadata.json"
    if metadata_path.exists():
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            doc_index = metadata.get("document_index") or {}
            metadata["document_index"] = {
                key: value
                for key, value in doc_index.items()
                if "probe42_" not in key
            }
            metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        except Exception:
            pass
    return deleted


def _reference_groups() -> dict[str, list[str]]:
    if not _reference_root.exists():
        return {}

    files = sorted(f.name for f in _reference_root.iterdir() if f.is_file())
    groups: dict[str, list[str]] = {}
    for filename in files:
        for sep in ("_AR_", "_Annual", "_Unaudited"):
            if sep in filename:
                prefix = filename.split(sep)[0]
                break
        else:
            prefix = filename.rsplit("_", 1)[0] if "_" in filename else filename
        groups.setdefault(prefix, []).append(filename)
    return groups


def _reference_aliases(entity_id: str, company_data: dict | None) -> list[str]:
    aliases: set[str] = set()
    normalized_entity = _normalize_lookup_text(entity_id).replace(" ", "")
    if normalized_entity:
        aliases.add(normalized_entity)
    if entity_id and len(entity_id) >= 4:
        aliases.add(_normalize_lookup_text(entity_id[:4]).replace(" ", ""))

    borrower = (company_data or {}).get("borrower")
    company_name = getattr(borrower, "company_name", "") if borrower else ""
    normalized_name = _normalize_lookup_text(company_name)
    compact_name = normalized_name.replace(" ", "")
    if compact_name:
        aliases.add(compact_name)
    aliases.update(_significant_tokens(company_name))
    return sorted(alias for alias in aliases if alias)


def _reference_match(group: str, aliases: list[str]) -> bool:
    normalized_group = _normalize_lookup_text(group)
    compact_group = normalized_group.replace(" ", "")
    group_tokens = _significant_tokens(group)
    for alias in aliases:
        compact_alias = alias.replace(" ", "")
        if not compact_alias:
            continue
        if compact_alias in compact_group or compact_group in compact_alias:
            return True
        if compact_alias in group_tokens:
            return True
    return False


def _save_cam_comments(entity_id: str, comments: dict[str, str]) -> None:
    clean: dict[str, str] = {}
    for key, value in comments.items():
        text = str(value or "").strip()
        if text:
            clean[str(key)] = text
    cr = case_store.get(entity_id)
    run_id = (cr or {}).get("run_id")
    persistence.save_case_comments(run_id, clean)


def _repair_mojibake_text(value: str) -> str:
    if not isinstance(value, str) or not any(ch in value for ch in ("â", "Ã", "Â")):
        return value
    try:
        repaired = value.encode("latin-1").decode("utf-8")
    except Exception:
        return value
    return repaired if repaired else value


def _repair_mojibake(obj):
    if isinstance(obj, str):
        return _repair_mojibake_text(obj)
    if isinstance(obj, list):
        return [_repair_mojibake(item) for item in obj]
    if isinstance(obj, dict):
        return {key: _repair_mojibake(value) for key, value in obj.items()}
    return obj


def _load_case_from_disk(entity_id: str) -> dict | None:
    """Load a case result from persisted output files when case_store is empty (e.g. after restart).
    Returns a populated case dict or None if no output files exist."""
    import json as _json

    fact_pack_file = _output_dir / f"{entity_id}_fact_pack.json"
    pipeline_file = _output_dir / f"{entity_id}_pipeline_result.json"
    cam_md_file = _output_dir / f"{entity_id}_CAM.md"

    if not fact_pack_file.exists():
        return None

    fp = {}
    try:
        fp = _repair_mojibake(_json.loads(fact_pack_file.read_text(encoding="utf-8")))
    except Exception:
        pass

    pr = {}
    if pipeline_file.exists():
        try:
            pr = _repair_mojibake(_json.loads(pipeline_file.read_text(encoding="utf-8")))
        except Exception:
            pass

    cam_text = ""
    if cam_md_file.exists():
        try:
            cam_text = _repair_mojibake_text(cam_md_file.read_text(encoding="utf-8"))
        except Exception:
            pass

    # Derive company name from company_store or fact pack
    company_name = ""
    if entity_id in company_store:
        company_name = company_store[entity_id]["borrower"].company_name
    if not company_name:
        company_name = fp.get("company_name") or fp.get("borrower_name", entity_id)

    policy = fp.get("policy_decisions", {})
    risk_scores = policy.get("tier2_risk_scores", {})
    recommendation = policy.get("tier3_recommendation", {})
    case_summary = fp.get("case_summary", {})
    facility_details = fp.get("facility_details", {})
    borrower_profile = fp.get("borrower_profile", {})

    cr = {
        "run_id": pr.get("run_id") or f"legacy-{entity_id}",
        "entity_id": entity_id,
        "company_name": company_name or borrower_profile.get("company_name", entity_id),
        "sector": pr.get("sector") or case_summary.get("sector", ""),
        "case_type": pr.get("case_type") or case_summary.get("case_type", ""),
        "requested_amount_cr": pr.get("requested_amount_cr") or case_summary.get("amount_requested_cr") or facility_details.get("amount_requested_cr"),
        "facility_type": pr.get("facility_type") or case_summary.get("facility_type") or facility_details.get("facility_type"),
        "recommendation": pr.get("recommendation") or recommendation.get("recommendation", "pending"),
        "risk_grade": pr.get("risk_grade") or recommendation.get("risk_grade") or risk_scores.get("risk_grade", "N/A"),
        "composite_score": pr.get("composite_score") or recommendation.get("composite_score") or risk_scores.get("composite_score", 0) or 0,
        "financial_score": pr.get("financial_score") or risk_scores.get("financial_score", 0) or 0,
        "conduct_score": pr.get("conduct_score") or risk_scores.get("conduct_score", 0) or 0,
        "governance_score": pr.get("governance_score") or risk_scores.get("governance_score", 0) or 0,
        "market_score": pr.get("market_score") or risk_scores.get("market_score", 0) or 0,
        "cam_text": cam_text,
        "narrative_mode": pr.get("narrative_mode", "template"),
        "data_provider": company_store.get(entity_id, {}).get("data_provider", "internal") if entity_id in company_store else "internal",
        "fact_pack": fp,
        "pipeline_log": pr.get("pipeline_log", []),
        "run_at": pr.get("run_at", ""),
        "conditions": pr.get("conditions") or recommendation.get("conditions", []),
        "covenants_proposed": pr.get("covenants_proposed") or recommendation.get("covenants_proposed", []),
        "rationale": pr.get("rationale") or recommendation.get("rationale", ""),
        "_loaded_from_disk": True,
    }
    case_store[entity_id] = cr
    persistence.save_case_run(cr)
    return cr


def _load_case_from_db(entity_id: str) -> dict | None:
    cr = persistence.get_latest_case(entity_id)
    if not cr:
        return None
    case_store[entity_id] = _repair_mojibake(cr)
    return case_store[entity_id]


def _get_case(entity_id: str) -> dict | None:
    """Get case from memory, SQLite, or legacy disk output."""
    if entity_id in case_store:
        case_store[entity_id] = _repair_mojibake(case_store[entity_id])
        return case_store[entity_id]
    cr = _load_case_from_db(entity_id)
    if cr:
        return cr
    return _load_case_from_disk(entity_id)


def _load_all_cases_from_disk():
    """On startup, pre-populate case_store from any persisted output files."""
    import json as _json
    if not _output_dir.exists():
        return
    for fp_file in _output_dir.glob("*_fact_pack.json"):
        eid = fp_file.stem.replace("_fact_pack", "")
        if eid not in company_store:
            continue
        if eid not in case_store:
            _load_case_from_disk(eid)


# Pre-load persisted cases on startup
_load_all_cases_from_disk()


def _regenerate_cam_text(entity_id: str) -> str:
    """Regenerate CAM text from fact_pack using template renderer when stored cam_text is empty."""
    from src.engines.cam_renderer_v2 import render_complete_cam
    from src.engines.cam_fact_builder import build_cam_fact_pack
    cr = case_store.get(entity_id, {})
    fp = cr.get("fact_pack")
    if not fp and entity_id in company_store:
        fp = build_cam_fact_pack(company_store[entity_id])
    if fp:
        try:
            cam_text = render_complete_cam(fp)
            cr["cam_text"] = cam_text
            cr["narrative_mode"] = "template"
            return cam_text
        except Exception:
            pass
    return "# CAM Report\n\nNarrative content could not be generated. Please re-run the case."


def _serialize(obj):
    """Recursively convert dataclass / enum objects to JSON-safe dicts."""
    if hasattr(obj, "__dataclass_fields__"):
        return {k: _serialize(getattr(obj, k)) for k in obj.__dataclass_fields__}
    if hasattr(obj, "value") and not isinstance(obj, (int, float, str, bool)):
        return obj.value
    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_serialize(i) for i in obj]
    if isinstance(obj, (datetime,)):
        return obj.isoformat()
    return obj


def _build_case_result(entity_id, company_data, context, pipeline_log):
    """Pack pipeline context into a flat case-store record."""
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
        "facility_type": f.facility_type.value if hasattr(f.facility_type, 'value') else str(f.facility_type),
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
        "tier1_decisions": _serialize(policy.get("tier1_decisions", [])),
        "exceptions": _serialize(validation.get("exceptions", [])),
    }


def _merge_overlay_company_data(base_company: dict, enriched_company: dict) -> dict:
    merged = dict(enriched_company or {})
    prior = base_company or {}

    for key in ("catalog_source", "preferred_identifier", "reference_prefix", "missing_documents", "source_summary", "probe_summary"):
        if key in prior and key not in merged:
            merged[key] = prior[key]

    if prior.get("core_banking"):
        merged["core_banking"] = prior["core_banking"]

    if prior.get("conduct"):
        merged["conduct"] = prior["conduct"]

    if prior.get("covenants"):
        merged["covenants"] = prior["covenants"]

    # Preserve rich seed data that the onboarding process cannot reconstruct.
    # Onboarding builds stub group/borrower/collateral from mock APIs which are
    # far less detailed than the curated seed data in real_companies.py.
    for key in ("group", "infra_metrics", "sector_kpis", "collateral",
                "market_signals", "directors", "borrower", "facility", "provisional"):
        prior_val = prior.get(key)
        if not prior_val:
            continue
        enriched_val = merged.get(key)
        # Always prefer seed for these structural keys — enriched is MCA-stub quality
        if key in ("group", "infra_metrics", "sector_kpis"):
            merged[key] = prior_val
        # For list/object keys, prefer seed when enriched is empty or trivial
        elif not enriched_val:
            merged[key] = prior_val
        elif isinstance(prior_val, list) and isinstance(enriched_val, list) and len(prior_val) > len(enriched_val):
            merged[key] = prior_val

    # Preserve seed financials when they are materially larger than enriched
    # (prevents probe-estimated / GSTN turnover from overwriting real seed data)
    prior_fin = prior.get("financials") or {}
    enriched_fin = merged.get("financials") or {}
    if prior_fin and enriched_fin:
        def _max_revenue(fin_dict):
            best = 0.0
            for fs in fin_dict.values():
                # Handle both FinancialStatement dataclass and plain dict
                if hasattr(fs, "line_items"):
                    val = (fs.line_items or {}).get("revenue_operating", 0) or 0
                elif hasattr(fs, "get"):
                    val = fs.get("revenue_operating", 0) or 0
                else:
                    continue
                if val > best:
                    best = val
            return best
        prior_max = _max_revenue(prior_fin)
        enriched_max = _max_revenue(enriched_fin)
        # Seed financials win if they have more periods OR materially higher revenue
        if prior_max > 0 and (enriched_max == 0 or prior_max > enriched_max * 1.5):
            merged["financials"] = prior_fin
        elif len(prior_fin) > len(enriched_fin):
            merged["financials"] = prior_fin
    elif prior_fin and not enriched_fin:
        merged["financials"] = prior_fin

    overlay_exposure = prior.get("existing_exposure") or []
    enriched_exposure = merged.get("existing_exposure") or []
    if overlay_exposure:
        existing_ids = {getattr(item, "facility_id", None) for item in enriched_exposure}
        merged["existing_exposure"] = list(enriched_exposure) + [
            item for item in overlay_exposure
            if getattr(item, "facility_id", None) not in existing_ids
        ]

    return merged


def _needs_company_enrichment(company_data: dict) -> bool:
    if not company_data:
        return False
    if company_data.get("data_provider") == "verified_public_records":
        return False
    if company_data.get("probe_bundle") and company_data.get("external_data"):
        return False
    borrower = company_data.get("borrower")
    if borrower and getattr(borrower, "cin", "") and getattr(borrower, "pan", "") and company_data.get("external_data"):
        return False
    return True


def _ensure_company_enriched(entity_id: str) -> dict:
    company_data = company_store.get(entity_id)
    if not company_data or not _needs_company_enrichment(company_data):
        return company_data

    borrower = company_data.get("borrower")
    facility = company_data.get("facility")
    identifier = (
        company_data.get("preferred_identifier")
        or getattr(borrower, "cin", None)
        or getattr(borrower, "pan", None)
        or getattr(borrower, "company_name", None)
        or entity_id
    )
    case_type = getattr(getattr(facility, "case_type", None), "value", getattr(facility, "case_type", "NTB"))
    facility_type = getattr(getattr(facility, "facility_type", None), "value", getattr(facility, "facility_type", "working_capital"))
    amount_requested = float(getattr(facility, "amount_requested_cr", 100.0) or 100.0)
    purpose = getattr(facility, "purpose", "General corporate purpose")
    tenor_months = getattr(facility, "tenor_months", None)

    result = onboard_company(
        identifier=identifier,
        case_type=str(case_type),
        facility_type=str(facility_type),
        amount_requested_cr=amount_requested,
        purpose=purpose,
        tenor_months=tenor_months,
    )
    if not result or result.get("status") == "not_found":
        return company_data

    enriched = _merge_overlay_company_data(company_data, result["company_data"])
    enriched["missing_documents"] = result.get("missing_documents", enriched.get("missing_documents", []))
    enriched["source_summary"] = result.get("source_summary", enriched.get("source_summary", {}))
    enriched["probe_summary"] = result.get("probe_summary", enriched.get("probe_summary"))
    if result.get("provider"):
        enriched["data_provider"] = result["provider"]

    company_store[entity_id] = enriched
    persistence.upsert_company(entity_id, enriched, is_seeded=False, catalog_source="run_autoload")
    return enriched


# ═══════════════════════════════════════════════════════════════════════════════
# DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/api/dashboard")
async def get_dashboard():
    total = len(case_store)
    approved = sum(1 for c in case_store.values()
                   if c.get("recommendation") in ("approve", "conditional_approve"))
    declined = sum(1 for c in case_store.values() if c.get("recommendation") == "decline")
    referred = sum(1 for c in case_store.values() if c.get("recommendation") == "refer")

    grade_dist = {}
    for c in case_store.values():
        g = c.get("risk_grade", "N/A")
        grade_dist[g] = grade_dist.get(g, 0) + 1

    recent = sorted(case_store.values(), key=lambda x: x.get("run_at", ""), reverse=True)[:5]

    return {
        "metrics": {
            "total_cases": total,
            "approved": approved,
            "declined": declined,
            "referred": referred,
        },
        "grade_distribution": grade_dist,
        "recent_cases": [
            {k: c[k] for k in ("entity_id", "company_name", "recommendation",
                                "risk_grade", "composite_score", "run_at")}
            for c in recent
        ],
    }


# ═══════════════════════════════════════════════════════════════════════════════
# COMPANIES / CASES
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/api/companies")
async def list_companies(executed_only: bool = False):
    items = company_store.items()
    if executed_only:
        items = [(eid, d) for eid, d in items if eid in case_store]
    return {
        "companies": [
            {
                "entity_id": eid,
                "company_name": d["borrower"].company_name,
                "sector": d["borrower"].sector.value,
                "borrower_type": d["borrower"].borrower_type.value,
                "case_type": d["facility"].case_type.value,
                "requested_amount_cr": d["facility"].amount_requested_cr,
                "data_provider": d.get("data_provider", "internal"),
                "has_result": eid in case_store,
            }
            for eid, d in items
        ]
    }


@app.post("/api/companies")
async def add_company(request: Request):
    """Add a new company for analysis. Builds canonical dataclass objects from JSON."""
    body = await request.json()

    # --- Validate required fields ---
    required = ["entity_id", "company_name", "sector", "case_type", "facility_type",
                 "amount_requested_cr"]
    missing = [f for f in required if not body.get(f)]
    if missing:
        raise HTTPException(400, f"Missing required fields: {', '.join(missing)}")

    eid = str(body["entity_id"]).strip()
    if eid in company_store:
        raise HTTPException(409, f"Company {eid} already exists")

    # --- Map enums safely ---
    try:
        sector = Sector(body["sector"])
    except ValueError:
        raise HTTPException(400, f"Invalid sector. Must be one of: {[s.value for s in Sector]}")
    try:
        case_type = CaseType(body["case_type"])
    except ValueError:
        raise HTTPException(400, f"Invalid case_type. Must be NTB or ETB")
    try:
        facility_type = FacilityType(body["facility_type"])
    except ValueError:
        raise HTTPException(400, f"Invalid facility_type. Must be one of: {[f.value for f in FacilityType]}")
    borrower_type = BorrowerType(body.get("borrower_type", "unlisted"))

    # --- Build Borrower ---
    borrower = Borrower(
        entity_id=eid,
        company_name=body["company_name"],
        cin=body.get("cin", f"U{eid}"),
        pan=body.get("pan", f"AADCP{eid[:4]}K"),
        borrower_type=borrower_type,
        sector=sector,
        subsector=body.get("subsector", sector.value),
        date_of_incorporation=date.fromisoformat(body["date_of_incorporation"]) if body.get("date_of_incorporation") else date(2010, 1, 1),
        registered_state=body.get("registered_state", "Maharashtra"),
        registered_address=body.get("registered_address", "Mumbai"),
        authorized_capital=body.get("authorized_capital", 100.0),
        paid_up_capital=body.get("paid_up_capital", 50.0),
        credit_rating=body.get("credit_rating"),
        rating_agency=body.get("rating_agency"),
        employee_count=body.get("employee_count"),
        website=body.get("website"),
    )

    # --- Build Financials ---
    financials_dict = {}
    for fin in body.get("financials", []):
        period = fin.get("period", "FY2024")
        fs = FinancialStatement(
            entity_id=eid, period=period,
            statement_type=fin.get("statement_type", "standalone"),
            source=fin.get("source", "borrower"),
            as_of_date=date.fromisoformat(fin["as_of_date"]) if fin.get("as_of_date") else date(2024, 3, 31),
            line_items=fin.get("line_items", {}),
        )
        financials_dict[period] = fs

    # If no financials provided, create a minimal FY2024 placeholder
    if not financials_dict:
        raw = body.get("line_items", {})
        # Map user-friendly names to canonical names used by ratio engine
        mapped = {}
        _alias = {
            "revenue": "revenue_operating", "net_worth": "total_equity",
            "interest_expense": "finance_cost",
            "cash_and_equivalents": "cash_equivalents",
        }
        for k, v in raw.items():
            mapped[_alias.get(k, k)] = v
        # Derive common computed fields if missing
        if "ebit" not in mapped and "ebitda" in mapped:
            mapped["ebit"] = mapped["ebitda"] - mapped.get("depreciation", 0)
        if "pbt" not in mapped and "ebit" in mapped:
            mapped["pbt"] = mapped["ebit"] - mapped.get("finance_cost", 0)
        if "total_income" not in mapped and "revenue_operating" in mapped:
            mapped["total_income"] = mapped["revenue_operating"] + mapped.get("other_income", 0)

        financials_dict["FY2024"] = FinancialStatement(
            entity_id=eid, period="FY2024",
            statement_type="standalone", source="borrower",
            as_of_date=date(2024, 3, 31),
            line_items=mapped,
        )

    # --- Build FacilityRequest ---
    facility = FacilityRequest(
        facility_id=body.get("facility_id", f"FAC-{eid}"),
        entity_id=eid,
        case_type=case_type,
        facility_type=facility_type,
        amount_requested_cr=float(body["amount_requested_cr"]),
        purpose=body.get("purpose", "General corporate purpose"),
        tenor_months=body.get("tenor_months"),
        existing_limit_cr=body.get("existing_limit_cr"),
        proposed_limit_cr=body.get("proposed_limit_cr"),
    )

    # --- Build optional objects ---
    group = None
    if body.get("group_name"):
        group = GroupEntity(
            group_id=body.get("group_id", f"GRP-{eid}"),
            group_name=body["group_name"],
            parent_entity_id=eid,
            entities=body.get("group_entities", []),
            promoter_holding_pct=body.get("promoter_holding_pct", 0),
        )

    directors = []
    for d in body.get("directors", []):
        directors.append(DirectorPromoter(
            din=d.get("din", "00000000"),
            name=d["name"],
            designation=d.get("designation", "Director"),
            entity_id=eid,
            is_promoter=d.get("is_promoter", False),
            net_worth_cr=d.get("net_worth_cr"),
        ))

    collateral = []
    for col in body.get("collateral", []):
        collateral.append(Collateral(
            collateral_id=col.get("collateral_id", f"COL-{eid}"),
            entity_id=eid,
            collateral_type=col.get("collateral_type", "property"),
            description=col.get("description", ""),
            market_value_cr=col.get("market_value_cr", 0),
            forced_sale_value_cr=col.get("forced_sale_value_cr", 0),
        ))

    # --- Store ---
    company_store[eid] = {
        "borrower": borrower,
        "group": group,
        "directors": directors,
        "financials": financials_dict,
        "provisional": None,
        "facility": facility,
        "collateral": collateral,
        "market_signals": [],
        "existing_exposure": [],
        "conduct": [],
        "covenants": [],
        "exchange_filing": None,
    }
    persistence.upsert_company(eid, company_store[eid], is_seeded=False, catalog_source="manual_entry")

    return {
        "status": "created",
        "entity_id": eid,
        "company_name": borrower.company_name,
        "sector": sector.value,
        "message": f"Company {borrower.company_name} added. Run the pipeline to analyse.",
    }


@app.delete("/api/companies/{entity_id}")
async def delete_company(entity_id: str):
    if entity_id not in company_store:
        raise HTTPException(404, f"Company {entity_id} not found")
    name = company_store[entity_id]["borrower"].company_name
    clear_probe_cache(*_company_probe_identifiers(entity_id, company_store.get(entity_id)))
    _clear_stored_probe_documents(entity_id)
    doc_store.delete_company(entity_id)
    del company_store[entity_id]
    case_store.pop(entity_id, None)
    persistence.delete_company(entity_id)
    return {"status": "deleted", "entity_id": entity_id, "company_name": name}


@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "version": "1.0.0",
        "companies": len(company_store),
        "cases_analysed": len(case_store),
        "active_llm": config.get_llm_config().get("active_provider", "mock"),
        "engines_enabled": sum(1 for e in registry.list_engines() if e["enabled"]),
        "probe42": get_probe_status(include_tools=False),
        "storage": {
            "documents_root": str(DOCUMENTS_ROOT),
            "output_root": str(OUTPUT_ROOT),
        },
        "database": persistence.describe(),
    }


@app.get("/api/probe/status")
async def probe_status():
    """Report Probe42 MCP integration readiness."""
    return get_probe_status(include_tools=True)


@app.get("/api/enums")
async def get_enums():
    """Return valid enum values for the Add Company form."""
    return {
        "sectors": [s.value for s in Sector],
        "case_types": [c.value for c in CaseType],
        "facility_types": [f.value for f in FacilityType],
        "borrower_types": [b.value for b in BorrowerType],
    }


@app.get("/api/cases")
async def list_cases():
    return {
        "cases": [
            {k: c[k] for k in ("entity_id", "company_name", "sector", "case_type",
                                "requested_amount_cr", "recommendation", "risk_grade",
                                "data_provider",
                                "composite_score", "narrative_mode", "run_at")
             if k in c}
            for c in case_store.values()
        ]
    }


@app.get("/api/cases/{entity_id}")
async def get_case(entity_id: str):
    cr = _get_case(entity_id)
    if not cr:
        raise HTTPException(404, "Case not found — run the pipeline first.")
    return cr


@app.get("/api/cases/{entity_id}/cam")
async def get_cam(entity_id: str):
    cr = _get_case(entity_id)
    if not cr:
        raise HTTPException(404, "Case not found")
    return {"cam_text": cr.get("cam_text", "")}


@app.get("/api/cases/{entity_id}/comments")
async def get_cam_comments(entity_id: str):
    cr = _get_case(entity_id)
    if not cr:
        raise HTTPException(404, "Case not found")
    return {"comments": _load_cam_comments(entity_id)}


@app.put("/api/cases/{entity_id}/comments")
async def update_cam_comments(entity_id: str, request: Request):
    cr = _get_case(entity_id)
    if not cr:
        raise HTTPException(404, "Case not found")
    body = await request.json()
    raw_comments = body.get("comments", {})
    if not isinstance(raw_comments, dict):
        raise HTTPException(400, "comments must be an object")
    comments = {str(key): str(value or "") for key, value in raw_comments.items()}
    _save_cam_comments(entity_id, comments)
    return {"status": "saved", "comments": _load_cam_comments(entity_id)}


@app.get("/api/cases/{entity_id}/cam-section-edits")
async def get_cam_section_edits(entity_id: str):
    """Return all RM-edited section overrides for a CAM report."""
    cr = _get_case(entity_id)
    if not cr:
        raise HTTPException(404, "Case not found")
    edits = persistence.load_cam_section_edits(entity_id)
    return {"edits": edits}


@app.put("/api/cases/{entity_id}/cam-section-edits")
async def save_cam_section_edit(entity_id: str, request: Request):
    """Save RM-edited section content for a specific CAM section."""
    cr = _get_case(entity_id)
    if not cr:
        raise HTTPException(404, "Case not found")
    body = await request.json()
    section_key = str(body.get("section_key", "")).strip()
    edited_html = str(body.get("edited_html", "")).strip()
    if not section_key:
        raise HTTPException(400, "section_key is required")
    persistence.save_cam_section_edit(entity_id, section_key, edited_html)
    edits = persistence.load_cam_section_edits(entity_id)
    return {"status": "saved", "edits": edits}


@app.get("/api/cases/{entity_id}/cam-html")
async def get_cam_html(entity_id: str):
    """Return the CAM text rendered as styled HTML for on-screen viewing."""
    from src.engines.cam_llm_renderer import _sanitize_llm_markdown
    cr = _get_case(entity_id)
    if not cr:
        raise HTTPException(404, "Case not found")
    md = cr.get("cam_text", "")
    # Regenerate if empty or if it's a short LLM-generated summary (template produces 20K+ chars)
    if not md.strip() or (len(md) < 10000 and cr.get("narrative_mode") != "template"):
        md = _regenerate_cam_text(entity_id)
    # Sanitize markdown to fix LLM rendering defects (broken tables, etc.)
    md = _sanitize_llm_markdown(md)
    html = _markdown_to_html(md, cr.get("company_name", entity_id))
    return Response(content=html, media_type="text/html")


@app.get("/api/cases/{entity_id}/cam-pdf")
async def get_cam_pdf(entity_id: str):
    """Generate and return a PDF version of the CAM report."""
    from src.engines.cam_llm_renderer import _sanitize_llm_markdown
    cr = _get_case(entity_id)
    if not cr:
        raise HTTPException(404, "Case not found")
    md = cr.get("cam_text", "")
    if not md.strip() or (len(md) < 10000 and cr.get("narrative_mode") != "template"):
        md = _regenerate_cam_text(entity_id)
    # Apply RM section edits so PDF reflects changed content
    section_edits = persistence.load_cam_section_edits(entity_id)
    if section_edits:
        md = _apply_section_edits_to_markdown(md, section_edits)
    # Sanitize markdown to fix LLM rendering defects (broken tables, etc.)
    md = _sanitize_llm_markdown(md)
    company_name = cr.get("company_name", entity_id)
    pdf_bytes = _generate_pdf(md, company_name, section_comments=_load_cam_comments(entity_id))
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{entity_id}_CAM.pdf"'},
    )


@app.get("/api/cases/{entity_id}/one-pager")
async def get_one_pager(entity_id: str):
    """Return the one-page graphical credit appraisal memo as HTML."""
    cr = _get_case(entity_id)
    if not cr:
        raise HTTPException(404, "Case not found")
    fp = cr.get("fact_pack", {})
    html = generate_one_pager_html(fp, cr)
    return Response(content=html, media_type="text/html")


@app.get("/api/companies/{entity_id}/hierarchy")
async def get_hierarchy(entity_id: str):
    """Return the corporate hierarchy for a company."""
    if entity_id not in company_store:
        raise HTTPException(404, f"Company {entity_id} not found")
    cd = company_store[entity_id]
    group = cd.get("group")
    if not group:
        return {"entity_id": entity_id, "hierarchy": [], "message": "No group structure"}
    borrower = cd.get("borrower")
    directors = cd.get("directors", [])
    tree, g_revenue, g_nw, g_debt = build_corporate_hierarchy(
        entity_id=entity_id,
        borrower=borrower,
        directors=directors,
        group=group,
    )
    from src.services.corporate_hierarchy import hierarchy_to_dict as _h2d
    return {
        "entity_id": entity_id,
        "group_name": group.group_name if hasattr(group, "group_name") else str(group),
        "group_revenue_cr": g_revenue,
        "group_net_worth_cr": g_nw,
        "group_total_debt_cr": g_debt,
        "hierarchy": _h2d(tree),
    }


@app.post("/api/cases/{entity_id}/run")
async def run_case(entity_id: str):
    if entity_id not in company_store:
        raise HTTPException(404, f"Company {entity_id} not found")

    cd = _ensure_company_enriched(entity_id)
    stores = {"extraction": extraction_store, "etb": etb_store}

    import asyncio
    try:
        llm = create_llm_provider(config.get_active_llm_provider())
        sa = SuperAgent(llm_provider=llm)
        ctx = await asyncio.to_thread(sa.execute_pipeline, cd, None, stores)
    except Exception as e:
        import logging, traceback
        logging.getLogger(__name__).error("Pipeline failed for %s: %s", entity_id, e)
        traceback.print_exc()
        raise HTTPException(500, f"Pipeline failed: {str(e)}")

    case_store[entity_id] = _build_case_result(
        entity_id, cd, ctx, sa.pipeline_log,
    )
    cr = case_store[entity_id]
    persistence.save_case_run(cr)
    cr["_extraction"] = extraction_store.get(entity_id)
    cr["_etb_analytics"] = etb_store.get(entity_id)
    return {
        "status": "completed",
        "entity_id": entity_id,
        "recommendation": cr["recommendation"],
        "risk_grade": cr["risk_grade"],
        "composite_score": cr["composite_score"],
        "narrative_mode": cr.get("narrative_mode", "template"),
        "pipeline_log": sa.pipeline_log,
    }


@app.get("/api/cases/{entity_id}/run-stream")
async def run_case_stream(entity_id: str):
    """SSE endpoint: run pipeline and stream agent progress events."""
    import json as _json, queue, threading

    if entity_id not in company_store:
        raise HTTPException(404, f"Company {entity_id} not found")

    q: queue.Queue = queue.Queue()

    def _pipeline_thread():
        try:
            cd = _ensure_company_enriched(entity_id)
            stores = {"extraction": extraction_store, "etb": etb_store}

            llm = create_llm_provider(config.get_active_llm_provider())
            sa = SuperAgent(llm_provider=llm)
            ctx = sa.execute_pipeline(cd, on_progress=lambda ev: q.put(ev), stores=stores)

            case_store[entity_id] = _build_case_result(entity_id, cd, ctx, sa.pipeline_log)
            cr = case_store[entity_id]
            persistence.save_case_run(cr)
            cr["_extraction"] = extraction_store.get(entity_id)
            cr["_etb_analytics"] = etb_store.get(entity_id)

            q.put({
                "type": "done",
                "entity_id": entity_id,
                "recommendation": cr["recommendation"],
                "risk_grade": cr["risk_grade"],
                "composite_score": cr["composite_score"],
                "narrative_mode": cr.get("narrative_mode", "template"),
            })
        except Exception as e:
            q.put({"type": "error", "message": str(e)})

    threading.Thread(target=_pipeline_thread, daemon=True).start()

    async def _event_generator():
        import asyncio
        while True:
            try:
                event = q.get_nowait()
            except queue.Empty:
                yield ": keepalive\n\n"
                await asyncio.sleep(0.3)
                continue
            yield f"data: {_json.dumps(event)}\n\n"
            if event.get("type") in ("done", "error"):
                break

    return StreamingResponse(_event_generator(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.post("/api/pipeline/run-all")
async def run_all():
    results = []
    stores = {"extraction": extraction_store, "etb": etb_store}
    for eid, cd in company_store.items():
        cd = _ensure_company_enriched(eid)
        llm = create_llm_provider(config.get_active_llm_provider())
        sa = SuperAgent(llm_provider=llm)
        ctx = sa.execute_pipeline(cd, stores=stores)
        case_store[eid] = _build_case_result(eid, cd, ctx, sa.pipeline_log)
        cr = case_store[eid]
        persistence.save_case_run(cr)
        cr["_extraction"] = extraction_store.get(eid)
        cr["_etb_analytics"] = etb_store.get(eid)
        results.append({
            "entity_id": eid,
            "recommendation": cr["recommendation"],
            "risk_grade": cr["risk_grade"],
        })
    return {"status": "completed", "results": results}


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/api/config")
async def get_all_config():
    config.reload()
    return config.all_configs()


@app.get("/api/config/{section}")
async def get_config_section(section: str):
    config.reload()
    data = config.get(section)
    if data is None:
        raise HTTPException(404, f"Config section '{section}' not found")
    return data


@app.put("/api/config/{section}")
async def update_config_section(section: str, request: Request):
    body = await request.json()
    config.update_config(section, body)
    return {"status": "updated", "section": section}


# ═══════════════════════════════════════════════════════════════════════════════
# ENGINE REGISTRY
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/api/engines")
async def list_engines():
    return {"engines": registry.list_engines()}


@app.put("/api/engines/{name}/toggle")
async def toggle_engine(name: str):
    engines = {e["name"]: e for e in registry.list_engines()}
    if name not in engines:
        raise HTTPException(404, f"Engine '{name}' not found")
    if engines[name]["enabled"]:
        registry.disable(name)
    else:
        registry.enable(name)
    return {"name": name, "enabled": registry.is_enabled(name)}


# ═══════════════════════════════════════════════════════════════════════════════
# LLM PROVIDERS
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/api/llm/providers")
async def llm_providers():
    lc = config.get_llm_config()
    active = lc.get("active_provider", "mock")
    return {
        "active_provider": active,
        "narrative_mode": lc.get("narrative", {}).get("mode", "template"),
        "providers": [
            {"id": k, "name": v.get("name", k), "type": v.get("type"), "active": k == active}
            for k, v in lc.get("providers", {}).items()
        ],
    }


@app.put("/api/llm/active")
async def set_active_llm(request: Request):
    body = await request.json()
    lc = config.get_llm_config()
    pid = body.get("provider")
    nm = body.get("narrative_mode")
    if pid:
        if pid not in lc.get("providers", {}):
            raise HTTPException(404, f"Provider '{pid}' not found")
        lc["active_provider"] = pid
    if nm:
        lc.setdefault("narrative", {})["mode"] = nm
    config.update_config("llm_providers", lc)
    return {"active_provider": lc["active_provider"],
            "narrative_mode": lc.get("narrative", {}).get("mode")}


@app.post("/api/llm/test")
async def test_llm():
    p = create_llm_provider(config.get_active_llm_provider())
    return p.test_connection()


# ═══════════════════════════════════════════════════════════════════════════════
# AGENTS
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/api/agents")
async def list_agents():
    return {"agents": SuperAgent().get_agent_list()}


# ═══════════════════════════════════════════════════════════════════════════════
# SMART ONBOARDING — PAN / GSTIN / Company Name only
# ═══════════════════════════════════════════════════════════════════════════════

@app.post("/api/onboard")
async def smart_onboard(request: Request):
    """
    Smart company onboarding — provide only one identifier.
    Accepts: { identifier, case_type?, facility_type?, amount_requested_cr?, purpose? }
    System auto-resolves identity, fetches all data from MCA/GSTIN/Bureau/Rating/Market.
    """
    body = await request.json()
    identifier = body.get("identifier", "").strip()
    if not identifier:
        raise HTTPException(400, "Provide 'identifier' — PAN, GSTIN, CIN, Entity ID, or Company Name")

    result = onboard_company(
        identifier=identifier,
        case_type=body.get("case_type", "NTB"),
        facility_type=body.get("facility_type", "working_capital"),
        amount_requested_cr=float(body.get("amount_requested_cr", 100.0)),
        purpose=body.get("purpose", "General corporate purpose"),
        tenor_months=body.get("tenor_months"),
    )

    if result["status"] == "not_found":
        raise HTTPException(404, result["message"])

    eid = result["entity_id"]
    # Allow re-onboarding: merge enriched data with existing seed data to preserve
    # rich seed financials, shareholding, infra_metrics, and sector_kpis.
    existing = company_store.get(eid)
    if existing:
        company_store[eid] = _merge_overlay_company_data(existing, result["company_data"])
    else:
        company_store[eid] = result["company_data"]
    company_store[eid]["missing_documents"] = result.get("missing_documents", [])
    company_store[eid]["source_summary"] = result.get("source_summary", {})
    company_store[eid]["probe_summary"] = result.get("probe_summary")
    if result.get("provider"):
        company_store[eid]["data_provider"] = result["provider"]

    # Store CRILC availability flag and ETB data if provided
    crilc_available = body.get("crilc_available", False)
    company_store[eid]["crilc_available"] = crilc_available
    etb_data = body.get("etb_data")
    if etb_data:
        company_store[eid]["etb_lookup"] = etb_data
    persistence.upsert_company(eid, company_store[eid], is_seeded=False, catalog_source="onboarding")

    return {
        "status": "onboarded",
        "entity_id": eid,
        "company_name": result["company_name"],
        "provider": result.get("provider", company_store[eid].get("data_provider", "internal")),
        "profile": result.get("profile"),
        "cache": result.get("cache", {}),
        "resolved_from": result["resolved"],
        "source_summary": result["source_summary"],
        "probe_summary": result.get("probe_summary"),
        "missing_documents": result.get("missing_documents", []),
        "documents_stored": result["documents_stored"],
        "crilc_available": crilc_available,
        "message": f"{result['company_name']} auto-onboarded. Run pipeline to analyse.",
    }


@app.post("/api/resolve")
async def resolve_identifier(request: Request):
    """Resolve a company identifier without onboarding — preview mode."""
    body = await request.json()
    identifier = body.get("identifier", "").strip()
    if not identifier:
        raise HTTPException(400, "Provide 'identifier'")
    result = resolve_company_with_probe(identifier)
    if not result:
        raise HTTPException(404, f"Could not resolve: {identifier}")
    return result


@app.get("/api/companies/{entity_id}/probe")
async def get_company_probe(entity_id: str):
    """Return the cached Probe42 snapshot for a company, if available."""
    company_data = company_store.get(entity_id)
    if not company_data:
        raise HTTPException(404, "Company not found")
    return {
        "entity_id": entity_id,
        **company_probe_snapshot(company_data),
    }


@app.delete("/api/companies/{entity_id}/verified-public-data")
async def delete_verified_public_data(entity_id: str):
    """Remove the retained public-record snapshot for a company."""
    company_data = company_store.get(entity_id)
    if not company_data:
        raise HTTPException(404, "Company not found")

    identifiers = _company_probe_identifiers(entity_id, company_data)
    deleted_cache = clear_probe_cache(*identifiers)
    deleted_documents = _clear_stored_probe_documents(entity_id)

    company_data.pop("probe_bundle", None)
    company_data.pop("probe_summary", None)
    company_data.pop("source_summary", None)
    if company_data.get("data_provider") == "probe42_mcp_v2":
        company_data["data_provider"] = "internal"

    persistence.upsert_company(
        entity_id,
        company_data,
        is_seeded=bool(company_data.get("seeded")),
        catalog_source=company_data.get("catalog_source", "manual_entry"),
    )

    return {
        "status": "deleted",
        "entity_id": entity_id,
        "deleted_cache_files": deleted_cache.get("deleted_files", []),
        "deleted_cache_count": deleted_cache.get("deleted_count", 0),
        "deleted_snapshot_documents": deleted_documents,
        "message": "Retained verified public data deleted for this borrower.",
    }


@app.post("/api/onboard/cin-lookup")
async def cin_lookup(request: Request):
    """
    CIN-based data lookup — RM enters CIN, system resolves via Probe42 MCP
    and returns a summary of what's available vs what RM must upload.
    """
    body = await request.json()
    cin = body.get("cin", "").strip()
    if not cin:
        raise HTTPException(400, "Provide 'cin' — Corporate Identification Number")

    # Resolve via local reference + Probe42
    resolved = resolve_company(cin)
    if not resolved:
        # Try Probe42 directly
        resolved = resolve_company_with_probe(cin)
    if not resolved:
        raise HTTPException(404, f"CIN {cin} not found")

    company_name = resolved.get("company_name", "")
    pan = resolved.get("pan", "")
    entity_id = resolved.get("entity_id")

    # Missing documents RM must upload
    missing_documents = [
        {"type": "audited_financial_fy2024", "description": "Audited Financial Statements FY2024 (PDF)", "source": "rm_upload", "ocr_required": True},
        {"type": "audited_financial_fy2023", "description": "Audited Financial Statements FY2023 (PDF)", "source": "rm_upload", "ocr_required": True},
        {"type": "provisional_fy2025", "description": "Provisional / Management Financials FY2025 (Excel/PDF)", "source": "rm_upload", "ocr_required": False},
        {"type": "board_resolution", "description": "Board Resolution for borrowing", "source": "rm_upload", "ocr_required": True},
        {"type": "cma_projection", "description": "CMA Data / Financial Projections", "source": "rm_upload", "ocr_required": False},
    ]

    return {
        "status": "found",
        "cin": cin,
        "entity_id": entity_id,
        "company_name": company_name,
        "pan": pan,
        "is_listed": resolved.get("probe_summary", {}).get("listing_status", "").lower() == "listed",
        "data_sources_fetched": {"probe42": resolved.get("provider", "")},
        "missing_documents": missing_documents,
        "rm_action_required": True,
        "next_steps": [
            "Upload missing documents (audited financials, provisionals, board resolution, CMA)",
            "System will run OCR on uploaded PDFs to extract financial data",
            f"Run pipeline: POST /api/cases/{entity_id or '{entity_id}'}/run",
        ],
        "message": (
            f"Company '{company_name}' identified via CIN. "
            f"Probe42 data will be fetched during onboarding. "
            f"RM needs to upload {len(missing_documents)} documents to complete the case."
        ),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# 360-DEGREE DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/api/companies/{entity_id}/360")
async def get_360_view(entity_id: str):
    """Full 360-degree view: overview, financials, credit risk, market intel, sell perspective."""
    company_data = company_store.get(entity_id)
    case_result = _get_case(entity_id)  # load from disk if needed
    view = generate_360_view(entity_id, company_data, case_result)
    return view


# ═══════════════════════════════════════════════════════════════════════════════
# DOCUMENT MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/api/companies/{entity_id}/documents")
async def list_documents(entity_id: str):
    """List all documents for a company with completeness tracking."""
    workspace = doc_store.list_company_documents(entity_id)
    return _augment_document_workspace(entity_id, company_store.get(entity_id), workspace)


@app.get("/api/document-operations")
async def list_document_operations(entity_id: str | None = Query(default=None), limit: int = Query(default=25, ge=1, le=100)):
    """List recent document generation operations, optionally filtered by company."""
    return {
        "operations": document_operations.list(entity_id=entity_id, limit=limit),
        "entity_id": entity_id,
        "limit": limit,
    }


@app.get("/api/companies/{entity_id}/document-operations")
async def list_company_document_operations(entity_id: str, limit: int = Query(default=10, ge=1, le=50)):
    """List recent document generation operations for a specific company."""
    return {
        "entity_id": entity_id,
        "operations": document_operations.list(entity_id=entity_id, limit=limit),
    }


# synthetic-inputs endpoints removed — all data sourced via Probe42 MCP


@app.get("/api/companies/{entity_id}/documents/{category}/{filename}")
async def get_document(entity_id: str, category: str, filename: str):
    """Retrieve a specific document. Returns file download for binary, JSON for text."""
    from fastapi.responses import Response
    content = doc_store.get_document(entity_id, category, filename)
    if content is None:
        raise HTTPException(404, f"Document not found: {category}/{filename}")

    # Determine MIME type by extension
    ext = Path(filename).suffix.lower()
    mime_map = {
        ".pdf": "application/pdf",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".xls": "application/vnd.ms-excel",
        ".csv": "text/csv",
        ".json": "application/json",
        ".txt": "text/plain",
    }
    mime = mime_map.get(ext, "application/octet-stream")

    # Binary files: return as downloadable response
    if ext in (".pdf", ".xlsx", ".xls"):
        return Response(
            content=content,
            media_type=mime,
            headers={"Content-Disposition": f'inline; filename="{filename}"'},
        )

    # Text files: try to decode and return as JSON
    try:
        text = content.decode("utf-8")
        return {"entity_id": entity_id, "category": category,
                "filename": filename, "content": text}
    except (UnicodeDecodeError, AttributeError):
        return Response(content=content, media_type=mime)


@app.post("/api/companies/{entity_id}/documents/{category}")
async def upload_document(entity_id: str, category: str, request: Request):
    """Upload a document to a category. Body: { filename, content }"""
    body = await request.json()
    filename = body.get("filename", "").strip()
    content = body.get("content", "")
    if not filename:
        raise HTTPException(400, "Provide 'filename'")
    doc_store.init_company_folder(entity_id)
    doc_store.store_document(entity_id, category, filename,
                             content.encode("utf-8") if isinstance(content, str) else content)
    extraction_store.pop(entity_id, None)
    case_store.pop(entity_id, None)
    return {"status": "stored", "entity_id": entity_id,
            "category": category, "filename": filename}


@app.post("/api/companies/{entity_id}/upload")
async def upload_file(entity_id: str, category: str = Form("misc"), file: UploadFile = File(...), document_role: str = Form(None)):
    """Upload a file via multipart form-data (used by the UI drag-drop / file picker)."""
    if not file.filename:
        raise HTTPException(400, "No file provided")
    content = await file.read()
    doc_store.init_company_folder(entity_id)
    result = doc_store.store_document(entity_id, category, file.filename, content, source="manual_upload", document_role=document_role or None)
    extraction_store.pop(entity_id, None)
    case_store.pop(entity_id, None)
    return {"status": "stored", **result}


@app.delete("/api/companies/{entity_id}/documents/{category}/{filename:path}")
async def delete_document_file(entity_id: str, category: str, filename: str):
    """Delete a single document from a category."""
    deleted = doc_store.delete_document(entity_id, category, filename)
    if not deleted:
        raise HTTPException(404, "Document not found")
    extraction_store.pop(entity_id, None)
    case_store.pop(entity_id, None)
    return {"status": "deleted", "entity_id": entity_id,
            "category": category, "filename": filename}


@app.get("/api/reference-documents")
async def list_reference_documents(entity_id: str | None = Query(default=None)):
    groups = _reference_groups()
    aliases: list[str] = []
    if entity_id:
        aliases = _reference_aliases(entity_id, company_store.get(entity_id))
        groups = {group: files for group, files in groups.items() if _reference_match(group, aliases)}

    files = sorted(filename for file_list in groups.values() for filename in file_list)
    return {
        "entity_id": entity_id,
        "aliases": aliases,
        "files": files,
        "groups": groups,
        "total": len(files),
        "purpose": "fact-check",
        "note": "Reference documents for manual verification only; filtered to the selected company when entity_id is provided",
    }
    """List downloaded reference documents (annual reports, filings) for manual fact-checking.
    These are NOT ingested into the pipeline — used only to verify web-crawled data accuracy."""
    dl_root = _reference_root
    if not dl_root.exists():
        return {"files": [], "groups": {}, "purpose": "fact-check"}
    files = sorted([f.name for f in dl_root.iterdir() if f.is_file()])
    groups: dict = {}
    for f in files:
        for sep in ("_AR_", "_Annual", "_Unaudited"):
            if sep in f:
                prefix = f.split(sep)[0]
                break
        else:
            prefix = f.rsplit("_", 1)[0] if "_" in f else f
        groups.setdefault(prefix, []).append(f)
    return {"files": files, "groups": groups, "total": len(files),
            "purpose": "fact-check",
            "note": "Reference documents for manual verification only — not part of automated pipeline"}


@app.get("/api/companies/{entity_id}/data-gaps")
async def check_data_gaps(entity_id: str):
    """Check data coverage for a company — how much the system found via APIs & web crawl."""
    company_data = company_store.get(entity_id)
    docs = _augment_document_workspace(entity_id, company_data, doc_store.list_company_documents(entity_id))
    cd = company_data
    web_crawl_available = False
    web_crawl_count = 0
    if cd:
        from src.services.web_crawl_service import crawl_company_news
        b = cd.get("borrower")
        name = b.company_name if b else entity_id
        sector = b.sector.value if b and hasattr(b.sector, "value") else "general"
        try:
            result = crawl_company_news(name, sector)
            web_crawl_count = len(result.get("articles", []))
            web_crawl_available = web_crawl_count > 0
        except Exception:
            pass

    categories_with_docs = {
        cat: info for cat, info in docs.get("categories", {}).items()
        if info.get("files")
    }
    categories_empty = {
        cat: info for cat, info in docs.get("categories", {}).items()
        if not info.get("files") and info.get("expected")
    }

    return {
        "entity_id": entity_id,
        "provider": docs.get("provider"),
        "total_files": docs.get("total_files", 0),
        "upload_coverage_pct": docs.get("upload_coverage_pct", 0),
        "hidden_legacy_files": docs.get("hidden_legacy_files", 0),
        "hidden_system_files": docs.get("hidden_system_files", 0),
        "categories_with_docs": list(categories_with_docs.keys()),
        "categories_empty": categories_empty,
        "required_missing_documents": docs.get("required_missing_documents", []),
        "source_gaps": docs.get("source_gaps", []),
        "web_crawl_available": web_crawl_available,
        "web_crawl_article_count": web_crawl_count,
        "data_sources": "APIs + Web Crawl (automated)",
    }


# ═══════════════════════════════════════════════════════════════════════════════
# DOCUMENT EXTRACTION
# ═══════════════════════════════════════════════════════════════════════════════

@app.post("/api/companies/{entity_id}/extract")
async def run_extraction(entity_id: str):
    """Run full document extraction pipeline for an entity."""
    storage_root = DOCUMENTS_ROOT
    entity_dir = storage_root / entity_id
    if not entity_dir.exists():
        raise HTTPException(404, f"No documents found for {entity_id}")
    try:
        result = extract_all_documents(entity_id, storage_root)
    except Exception as e:
        import traceback, logging
        logging.getLogger(__name__).error("Extraction failed for %s: %s\n%s", entity_id, e, traceback.format_exc())
        raise HTTPException(500, f"Extraction failed: {str(e)}")
    if result.get("error"):
        raise HTTPException(404, result["error"])
    extraction_store[entity_id] = result
    return {"status": "extracted", "entity_id": entity_id,
            "document_count": result.get("document_count", 0)}


@app.get("/api/companies/{entity_id}/extraction")
async def get_extraction(entity_id: str):
    """Get cached extraction results."""
    if entity_id not in extraction_store:
        return {
            "entity_id": entity_id,
            "status": "not_started",
            "document_count": 0,
            "financials": {},
            "documents": {},
            "message": "Run extraction first: POST /api/companies/{id}/extract",
        }
    return extraction_store[entity_id]


# ═══════════════════════════════════════════════════════════════════════════════
# ETB BEHAVIORAL ANALYTICS
# ═══════════════════════════════════════════════════════════════════════════════

@app.post("/api/companies/{entity_id}/etb-analytics")
async def run_etb_analytics_endpoint(entity_id: str):
    """Run ETB behavioral analytics on extracted conduct data."""
    ext = extraction_store.get(entity_id)
    if not ext or not ext.get("etb_conduct"):
        raise HTTPException(
            400,
            "No ETB conduct data. Run extraction first, and ensure entity has ETB CSVs.",
        )
    analysis = run_etb_analytics(ext["etb_conduct"], entity_id)
    result = etb_analysis_to_dict(analysis)
    etb_store[entity_id] = result
    return {"status": "analysed", "entity_id": entity_id,
            "composite_score": result.get("composite_score"),
            "risk_grade": result.get("risk_grade")}


@app.get("/api/companies/{entity_id}/etb-analytics")
async def get_etb_analytics(entity_id: str):
    """Get cached ETB analytics results."""
    if entity_id not in etb_store:
        raise HTTPException(404, "Run ETB analytics first: POST /api/companies/{id}/etb-analytics")
    return etb_store[entity_id]


# ═══════════════════════════════════════════════════════════════════════════════
# ANALYST CHAT
# ═══════════════════════════════════════════════════════════════════════════════

@app.post("/api/chat/{entity_id}")
async def chat_endpoint(entity_id: str, request: Request):
    """Send a message to the analyst chat for a specific entity."""
    body = await request.json()
    message = body.get("message", "").strip()
    if not message:
        raise HTTPException(400, "Provide 'message' in request body")

    case_data = _get_case(entity_id)
    extraction = extraction_store.get(entity_id)
    etb_analysis = etb_store.get(entity_id)
    company_data = company_store.get(entity_id) or {}
    probe_bundle = company_data.get("probe_bundle")

    result = await analyst_chat_fn(
        entity_id=entity_id,
        user_message=message,
        case_data=case_data,
        extraction=extraction,
        etb_analysis=etb_analysis,
        probe_context=probe_context_text(probe_bundle),
    )
    return result


@app.get("/api/chat/{entity_id}/history")
async def chat_history(entity_id: str):
    """Get chat conversation history for an entity."""
    history = get_session_history(entity_id)
    return {"entity_id": entity_id, "messages": history}


@app.delete("/api/chat/{entity_id}")
async def chat_clear(entity_id: str):
    """Clear chat session for an entity."""
    clear_session(entity_id)
    return {"status": "cleared", "entity_id": entity_id}


@app.get("/api/chat/sessions")
async def chat_sessions():
    """List all active chat sessions."""
    return {"sessions": chat_list_sessions()}


# ═══════════════════════════════════════════════════════════════════════════════
# EXTERNAL SYSTEMS MOCK APIs
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/api/external/mca/company/{cin}")
async def ext_mca_company(cin: str):
    return mca_company_master(cin)

@app.get("/api/external/mca/directors/{cin}")
async def ext_mca_directors(cin: str):
    return mca_directors(cin)

@app.get("/api/external/mca/charges/{cin}")
async def ext_mca_charges(cin: str):
    return mca_charges(cin)

@app.get("/api/external/gstin/{gstin}")
async def ext_gstin(gstin: str):
    return gstin_details(gstin)

@app.get("/api/external/gst-turnover/{pan}")
async def ext_gst_turnover(pan: str):
    return gstin_turnover(pan)

@app.get("/api/external/bureau/{pan}")
async def ext_bureau(pan: str):
    return bureau_commercial_report(pan)

@app.get("/api/external/rating/{entity_id}")
async def ext_rating(entity_id: str):
    return rating_action(entity_id)

@app.get("/api/external/market/{entity_id}")
async def ext_market(entity_id: str):
    return market_intelligence(entity_id)

@app.get("/api/external/crilc/{pan}")
async def ext_crilc(pan: str):
    return crilc_report(pan)

@app.get("/api/external/crilc/{pan}/pdf")
async def ext_crilc_pdf(pan: str):
    """Generate CRILC exposure report as PDF."""
    data = crilc_report(pan)
    payload = data.get("payload", {})
    entity_name = payload.get("entity_name", pan)

    from io import BytesIO
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib import colors
    from reportlab.lib.units import mm

    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=20*mm, rightMargin=20*mm,
                            topMargin=20*mm, bottomMargin=20*mm)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="RbiH1", fontSize=16, spaceAfter=12,
                              textColor=colors.HexColor("#00338d"), fontName="Helvetica-Bold",
                              alignment=1))
    styles.add(ParagraphStyle(name="RbiH2", fontSize=12, spaceAfter=8, spaceBefore=14,
                              textColor=colors.HexColor("#00338d"), fontName="Helvetica-Bold"))
    styles.add(ParagraphStyle(name="RbiBody", fontSize=10, spaceAfter=6, leading=14,
                              fontName="Helvetica"))
    styles.add(ParagraphStyle(name="RbiSmall", fontSize=8, spaceAfter=4, leading=10,
                              fontName="Helvetica", textColor=colors.grey))

    story = []
    # Header
    story.append(Paragraph("RESERVE BANK OF INDIA", styles["RbiH1"]))
    story.append(Paragraph("Central Repository of Information on Large Credits (CRILC)", styles["RbiH1"]))
    story.append(Spacer(1, 8*mm))
    story.append(Paragraph(f"<b>Entity:</b> {entity_name}", styles["RbiBody"]))
    story.append(Paragraph(f"<b>PAN:</b> {pan}", styles["RbiBody"]))
    story.append(Paragraph(f"<b>Report Date:</b> {data.get('as_of_date', 'N/A')}", styles["RbiBody"]))
    story.append(Spacer(1, 6*mm))

    # Exposure Summary Table
    story.append(Paragraph("1. Aggregate Exposure Summary", styles["RbiH2"]))
    exp_data = [
        ["Parameter", "Value"],
        ["Total Aggregate Exposure", f"₹ {payload.get('aggregate_exposure_cr', 0):.2f} Cr"],
        ["Fund-Based Exposure", f"₹ {payload.get('fund_based_cr', 0):.2f} Cr"],
        ["Non-Fund Based Exposure", f"₹ {payload.get('non_fund_based_cr', 0):.2f} Cr"],
        ["Number of Lending Institutions", str(payload.get("total_lenders", 0))],
        ["Asset Classification", payload.get("classification", "N/A")],
        ["SMA Status", payload.get("sma_status", "N/A")],
    ]
    t = Table(exp_data, colWidths=[200, 250])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#00338d")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f0f4fa")]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(t)
    story.append(Spacer(1, 6*mm))

    # Risk Flags
    story.append(Paragraph("2. Risk & Regulatory Flags", styles["RbiH2"]))
    flags_data = [
        ["Check", "Status", "Remark"],
        ["Restructured Account", "Yes" if payload.get("restructured") else "No",
         "Account has been restructured" if payload.get("restructured") else "No restructuring"],
        ["Wilful Defaulter", "Yes" if payload.get("wilful_defaulter") else "No",
         "Listed as wilful defaulter" if payload.get("wilful_defaulter") else "Not on wilful defaulter list"],
        ["SMA Classification", payload.get("sma_status", "N/A"),
         "Special Mention Account monitoring status"],
        ["Asset Classification", payload.get("classification", "N/A"),
         "Current asset classification under RBI norms"],
    ]
    t2 = Table(flags_data, colWidths=[130, 80, 240])
    t2.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#00338d")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f0f4fa")]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(t2)
    story.append(Spacer(1, 6*mm))

    # Lender-wise Exposure (synthetic breakdown)
    story.append(Paragraph("3. Lender-wise Exposure Breakdown", styles["RbiH2"]))
    total_fb = payload.get("fund_based_cr", 0)
    total_nfb = payload.get("non_fund_based_cr", 0)
    n_lenders = payload.get("total_lenders", 1) or 1
    lender_names = ["State Bank of India", "Bank of Baroda", "Punjab National Bank",
                    "HDFC Bank", "ICICI Bank", "Axis Bank", "Union Bank of India",
                    "Canara Bank"]
    lender_data = [["Lender", "Fund-Based (₹ Cr)", "Non-Fund (₹ Cr)", "Total (₹ Cr)", "Share %"]]
    for i in range(min(n_lenders, len(lender_names))):
        share = round(100.0 / n_lenders + (5 - i * 3 if i < 3 else -2), 1)
        share = max(5.0, min(share, 60.0))
        fb = round(total_fb * share / 100, 2)
        nfb = round(total_nfb * share / 100, 2)
        lender_data.append([
            lender_names[i], f"{fb:.2f}", f"{nfb:.2f}", f"{fb + nfb:.2f}", f"{share:.1f}%"
        ])
    t3 = Table(lender_data, colWidths=[140, 90, 90, 90, 60])
    t3.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#00338d")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f0f4fa")]),
        ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(t3)
    story.append(Spacer(1, 8*mm))

    # Disclaimer
    story.append(Paragraph("Disclaimer", styles["RbiH2"]))
    story.append(Paragraph(
        "This report is generated from the Central Repository of Information on Large Credits "
        "(CRILC) maintained by the Reserve Bank of India. The information is based on data "
        "reported by lending institutions and is for regulatory and credit assessment purposes. "
        "Report as on: " + payload.get("last_reported", "N/A"),
        styles["RbiSmall"]
    ))

    doc.build(story)
    return Response(
        content=buf.getvalue(),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="CRILC_{pan}.pdf"'},
    )

@app.get("/api/external/epfo/{pan}")
async def ext_epfo(pan: str):
    return epfo_compliance(pan)

@app.get("/api/external/itr/{pan}")
async def ext_itr(pan: str):
    return itr_filing_status(pan)

@app.get("/api/external/exchange/financial-results/{entity_id}")
async def ext_exchange_financials(entity_id: str):
    return exchange_financial_results(entity_id)

@app.get("/api/external/exchange/governance/{entity_id}")
async def ext_exchange_governance(entity_id: str):
    return exchange_governance_filings(entity_id)

@app.get("/api/external/social/reputation/{entity_id}")
async def ext_social_reputation(entity_id: str):
    return social_reputation_signals(entity_id)


@app.get("/api/external/web-crawl/{entity_id}")
async def ext_web_crawl(entity_id: str):
    """Crawl news & market intelligence for a company (NTB focus)."""
    from src.services.web_crawl_service import crawl_company_news
    cd = company_store.get(entity_id)
    if not cd:
        if entity_id in ALL_COMPANIES:
            cd = ALL_COMPANIES[entity_id]
        else:
            raise HTTPException(404, f"Company {entity_id} not found")
    b = cd.get("borrower")
    name = b.company_name if b else entity_id
    sector = b.sector.value if b and hasattr(b.sector, "value") else "general"
    is_ntb = cd.get("facility") and cd["facility"].case_type.value == "NTB"
    return crawl_company_news(name, sector, is_ntb=bool(is_ntb))


# ═══════════════════════════════════════════════════════════════════════════════
# DOCUMENT MANAGEMENT SYSTEM (DMS)
# ═══════════════════════════════════════════════════════════════════════════════

@app.post("/api/companies/{entity_id}/dms-fetch")
async def dms_fetch(entity_id: str):
    """Fetch all documents from DMS (Document Management System) for a company."""
    if entity_id not in company_store:
        raise HTTPException(404, f"Company {entity_id} not found")
    from src.services.dms_service import dms_service
    cd = company_store[entity_id]
    result = dms_service.fetch_documents(entity_id, company_data=cd)
    return {"entity_id": entity_id, **result}


@app.get("/api/companies/{entity_id}/dms-status")
async def dms_status(entity_id: str):
    """Get DMS document status for a company."""
    if entity_id not in company_store:
        raise HTTPException(404, f"Company {entity_id} not found")
    from src.services.dms_service import dms_service
    return dms_service.get_document_status(entity_id)


# ═══════════════════════════════════════════════════════════════════════════════
# DOCUMENT DOWNLOAD / CRILC PDF GENERATION
# ═══════════════════════════════════════════════════════════════════════════════

@app.post("/api/companies/fetch-documents/bulk")
async def fetch_documents_bulk(force_refresh: bool = False):
    """Bulk backfill synthetic real-company document packs for all supported listed companies."""
    from src.engines.document_downloader import populate_supported_company_documents
    return populate_supported_company_documents(force_refresh=force_refresh)

@app.post("/api/companies/{entity_id}/fetch-documents")
async def fetch_documents(entity_id: str):
    """Download/generate financial documents for a supported listed company profile."""
    from src.engines.document_downloader import download_company_documents, get_supported_companies
    supported = get_supported_companies()
    supported_ids = [c["entity_id"] for c in supported]
    if entity_id not in supported_ids:
        raise HTTPException(400, f"Document download not supported for {entity_id}. "
                            f"Supported: {supported_ids}")
    result = download_company_documents(entity_id)
    return {"entity_id": entity_id, **result}


@app.get("/api/companies/supported-downloads")
async def supported_downloads():
    """List companies that support real financial document download."""
    from src.engines.document_downloader import get_supported_companies
    return get_supported_companies()


@app.post("/api/companies/{entity_id}/crilc-pdf")
async def generate_crilc_pdf(entity_id: str):
    """Generate CRILC exposure report PDF for a company."""
    from src.engines.crilc_report_generator import generate_crilc_report
    result = generate_crilc_report(entity_id)
    if result["status"] == "error":
        raise HTTPException(400, result["message"])
    return result


@app.get("/api/companies/{entity_id}/crilc-pdf")
async def get_crilc_pdf(entity_id: str):
    """Download generated CRILC PDF file."""
    storage_root = DOCUMENTS_ROOT
    crilc_file = storage_root / entity_id / "bureau" / "crilc_report.pdf"
    if not crilc_file.exists():
        raise HTTPException(404, f"No CRILC report found for {entity_id}. Generate first via POST.")
    return Response(
        content=crilc_file.read_bytes(),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="crilc_report_{entity_id}.pdf"'},
    )


# ═══════════════════════════════════════════════════════════════════════════════
# PEP / SANCTIONS SCREENING
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/api/companies/{entity_id}/pep-screening")
async def pep_screening(entity_id: str):
    """Run PEP, sanctions and adverse media screening on directors/promoters."""
    from src.services.pep_service import screen_directors
    cd = company_store.get(entity_id)
    if not cd:
        if entity_id in ALL_COMPANIES:
            cd = ALL_COMPANIES[entity_id]
        else:
            raise HTTPException(404, f"Company {entity_id} not found")
    directors = cd.get("directors", [])
    if not directors:
        b = cd.get("borrower")
        return {"entity_id": entity_id, "company_name": b.company_name if b else entity_id,
                "pep_hits": [], "sanctions_hits": [], "adverse_media": [],
                "summary": "No directors on record for screening"}
    result = screen_directors(entity_id=entity_id, directors=directors)
    from dataclasses import asdict
    return {"entity_id": entity_id, **asdict(result)}


# ═══════════════════════════════════════════════════════════════════════════════
# CORE BANKING ANALYSIS (ETB)
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/api/companies/{entity_id}/core-banking")
async def core_banking_analysis(entity_id: str):
    """Analyse core banking data (LOAN, BCLC, LIABILITY, FEES) for ETB customers."""
    from src.engines.core_banking_engine import analyze_core_banking
    cd = company_store.get(entity_id)
    if not cd:
        if entity_id in ALL_COMPANIES:
            cd = ALL_COMPANIES[entity_id]
        else:
            raise HTTPException(404, f"Company {entity_id} not found")
    core_banking_data = cd.get("core_banking")
    case_type = cd["facility"].case_type.value if cd.get("facility") else "NTB"
    result = analyze_core_banking(entity_id, core_banking_data, case_type)
    return {"entity_id": entity_id, **result}


# ═══════════════════════════════════════════════════════════════════════════════
# SOCIAL MEDIA & DIGITAL INTELLIGENCE
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/api/companies/{entity_id}/social-media")
async def social_media_analysis(entity_id: str):
    """Social media sentiment, reputation risk and digital intelligence analysis."""
    from src.engines.social_media_engine import analyze_social_media
    cd = company_store.get(entity_id)
    if not cd:
        if entity_id in ALL_COMPANIES:
            cd = ALL_COMPANIES[entity_id]
        else:
            raise HTTPException(404, f"Company {entity_id} not found")
    b = cd.get("borrower")
    name = b.company_name if b else entity_id
    sector = b.sector.value if b and hasattr(b.sector, "value") else "general"
    result = analyze_social_media(entity_id, name, sector)
    return {"entity_id": entity_id, **result}


# ═══════════════════════════════════════════════════════════════════════════════
# FRAUD DETECTION
# ═══════════════════════════════════════════════════════════════════════════════

@app.post("/api/companies/{entity_id}/fraud-analysis")
async def run_fraud_analysis(entity_id: str):
    """Run multi-signal fraud detection on a company."""
    company_data = company_store.get(entity_id)
    if not company_data:
        # Try loading from ALL_COMPANIES for pre-seeded companies
        if entity_id in ALL_COMPANIES:
            company_data = ALL_COMPANIES[entity_id]
        else:
            raise HTTPException(404, f"Company {entity_id} not found. Onboard first.")

    extraction = extraction_store.get(entity_id)
    report = run_fraud_scan(company_data, extraction_data=extraction)

    # Serialize dataclass to dict
    result = {
        "entity_id": report.entity_id,
        "company_name": report.company_name,
        "composite_score": round(report.composite_score, 2),
        "risk_grade": report.risk_grade,
        "beneish_m_score": round(report.beneish_m_score, 4) if report.beneish_m_score else None,
        "beneish_probability": report.beneish_probability,
        "altman_z_score": round(report.altman_z_score, 4) if report.altman_z_score else None,
        "altman_zone": report.altman_zone,
        "benford_chi_sq": round(report.benford_chi_sq, 4) if report.benford_chi_sq else None,
        "benford_verdict": report.benford_verdict,
        "revenue_consistency": round(report.revenue_consistency, 2),
        "governance_score": round(report.governance_score, 2),
        "document_anomaly_score": round(report.document_anomaly_score, 2),
        "circular_txn_score": round(report.circular_txn_score, 2),
        "summary": report.summary,
        "flags": [
            {
                "category": f.category,
                "indicator": f.indicator,
                "severity": f.severity,
                "score": round(f.score, 2),
                "details": f.details,
                "evidence": f.evidence,
            }
            for f in report.flags
        ],
    }
    fraud_store[entity_id] = result
    return {"status": "analysed", "entity_id": entity_id, **result}


@app.get("/api/companies/{entity_id}/fraud-analysis")
async def get_fraud_analysis(entity_id: str):
    """Get cached fraud analysis results."""
    if entity_id not in fraud_store:
        raise HTTPException(404, "Run fraud analysis first: POST /api/companies/{id}/fraud-analysis")
    return fraud_store[entity_id]


# ═══════════════════════════════════════════════════════════════════════════════
# OCR / DOCUMENT INTELLIGENCE
# ═══════════════════════════════════════════════════════════════════════════════

@app.post("/api/companies/{entity_id}/ocr/{category}/{filename:path}")
async def run_ocr(entity_id: str, category: str, filename: str):
    """Extract text from a specific document using OCR/native extraction."""
    storage_root = DOCUMENTS_ROOT
    filepath = storage_root / entity_id / category / filename
    if not filepath.exists():
        raise HTTPException(404, f"Document not found: {category}/{filename}")
    if filepath.suffix.lower() != ".pdf":
        raise HTTPException(400, "OCR is only supported for PDF files")
    result = ocr_extract(filepath)
    if result.get("error"):
        raise HTTPException(500, result["error"])
    return {"entity_id": entity_id, "category": category,
            "filename": filename, **result}


@app.post("/api/companies/{entity_id}/ocr-metadata/{category}/{filename:path}")
async def run_ocr_metadata(entity_id: str, category: str, filename: str):
    """Analyze document metadata for fraud indicators."""
    storage_root = DOCUMENTS_ROOT
    filepath = storage_root / entity_id / category / filename
    if not filepath.exists():
        raise HTTPException(404, f"Document not found: {category}/{filename}")
    result = analyze_document_metadata(filepath)
    if result.get("error"):
        raise HTTPException(500, result["error"])
    return {"entity_id": entity_id, "category": category,
            "filename": filename, **result}


# ═══════════════════════════════════════════════════════════════════════════════
# CAM Rendering Helpers
# ═══════════════════════════════════════════════════════════════════════════════

import html as _html_mod
import re as _re


# ── Section edit helpers for PDF generation ──────────────────────────────────

def _html_to_simple_markdown(html_str: str) -> str:
    """Convert contenteditable HTML back to simplified markdown for PDF rendering."""
    text = html_str
    # Block elements
    text = _re.sub(r'<h2[^>]*>(.*?)</h2>', r'## \1\n', text, flags=_re.DOTALL)
    text = _re.sub(r'<h3[^>]*>(.*?)</h3>', r'### \1\n', text, flags=_re.DOTALL)
    text = _re.sub(r'<h4[^>]*>(.*?)</h4>', r'#### \1\n', text, flags=_re.DOTALL)
    text = _re.sub(r'<br\s*/?>', '\n', text)
    text = _re.sub(r'</p>\s*', '\n\n', text)
    text = _re.sub(r'<p[^>]*>', '', text)
    text = _re.sub(r'</div>\s*', '\n', text)
    text = _re.sub(r'<div[^>]*>', '', text)
    # Inline formatting
    text = _re.sub(r'<(?:strong|b)>(.*?)</(?:strong|b)>', r'**\1**', text, flags=_re.DOTALL)
    text = _re.sub(r'<(?:em|i)>(.*?)</(?:em|i)>', r'*\1*', text, flags=_re.DOTALL)
    # Lists
    text = _re.sub(r'<li[^>]*>(.*?)</li>', r'- \1\n', text, flags=_re.DOTALL)
    text = _re.sub(r'</?[uo]l[^>]*>\s*', '', text)
    # Tables
    def _table_to_md(m):
        table_html = m.group(0)
        rows = _re.findall(r'<tr[^>]*>(.*?)</tr>', table_html, _re.DOTALL)
        md_lines = []
        for i, row_html in enumerate(rows):
            cells = _re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', row_html, _re.DOTALL)
            cells = [_re.sub(r'<[^>]+>', '', c).strip() for c in cells]
            md_lines.append('| ' + ' | '.join(cells) + ' |')
            if i == 0:
                md_lines.append('| ' + ' | '.join('---' for _ in cells) + ' |')
        return '\n'.join(md_lines) + '\n'
    text = _re.sub(r'<table[^>]*>.*?</table>', _table_to_md, text, flags=_re.DOTALL)
    # Strip remaining HTML tags
    text = _re.sub(r'<[^>]+>', '', text)
    # Clean up HTML entities
    text = text.replace('&nbsp;', ' ').replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>').replace('&quot;', '"')
    # Clean up excessive whitespace
    text = _re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def _apply_section_edits_to_markdown(md: str, edits: dict) -> str:
    """Merge RM CAM section edits into the markdown text for PDF generation."""
    if not edits:
        return md
    # Find all ## heading positions
    pattern = _re.compile(r'^## (.+)$', _re.MULTILINE)
    matches = list(pattern.finditer(md))
    if not matches:
        return md

    result_parts = []
    # Add content before first ## heading
    result_parts.append(md[:matches[0].start()])

    for idx, match in enumerate(matches):
        title = match.group(1).strip()
        key = ' '.join(title.split())  # Normalize whitespace (same as UI camSectionKey)
        section_start = match.start()
        section_end = matches[idx + 1].start() if idx + 1 < len(matches) else len(md)

        if key in edits and edits[key].get('html', '').strip():
            edited_md = _html_to_simple_markdown(edits[key]['html'])
            # Remove heading from converted content if present (edit HTML includes heading)
            lines = edited_md.split('\n')
            body_start = 0
            for j, line in enumerate(lines):
                if line.strip().startswith('## '):
                    body_start = j + 1
                    break
            body_content = '\n'.join(lines[body_start:]).strip()
            result_parts.append(f'## {title}\n\n{body_content}\n\n')
        else:
            result_parts.append(md[section_start:section_end])

    return ''.join(result_parts)


def _render_markdown_fragment(md: str) -> str:
    body = _html_mod.escape(md)

    def _table_block(block):
        rows = block.strip().split("\n")
        if len(rows) < 2:
            return block
        # Filter out separator rows (including malformed long-dash ones)
        data_rows = []
        for row in rows:
            stripped = row.strip()
            if _re.match(r"^\|[\s\-:|]+\|?$", stripped):
                continue
            if len(stripped) > 200 and stripped.count("-") / len(stripped) > 0.5:
                continue
            data_rows.append(row)
        if len(data_rows) <= 1:
            return ""  # Header-only table — skip
        out = '<table class="cam-table">'
        for i, row in enumerate(data_rows):
            cells = row.split("|")[1:-1]
            tag = "th" if i == 0 else "td"
            out += "<tr>" + "".join(f"<{tag}>{c.strip()}</{tag}>" for c in cells) + "</tr>"
        return out + "</table>"

    body = _re.sub(r"((?:^\|.+\|$\n?)+)", lambda m: _table_block(m.group(0)), body, flags=_re.MULTILINE)
    body = _re.sub(r"^#### (.+)$", r"<h4>\1</h4>", body, flags=_re.MULTILINE)
    body = _re.sub(r"^### (.+)$", r"<h3>\1</h3>", body, flags=_re.MULTILINE)
    body = _re.sub(r"^## (.+)$", r"<h2>\1</h2>", body, flags=_re.MULTILINE)
    body = _re.sub(r"^# (.+)$", r"<h1>\1</h1>", body, flags=_re.MULTILINE)
    body = _re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", body)
    body = _re.sub(r"\*(.+?)\*", r"<em>\1</em>", body)
    body = _re.sub(r"^---+$", "<hr>", body, flags=_re.MULTILINE)
    body = _re.sub(r"^[\-\*] (.+)$", r"<li>\1</li>", body, flags=_re.MULTILINE)
    body = _re.sub(r"((?:<li>.+</li>\n?)+)", r"<ul>\1</ul>", body)
    body = _re.sub(r"\n{2,}", "</p><p>", body)
    body = "<p>" + body + "</p>"
    body = _re.sub(r"<p>\s*<(h[1-4]|table|ul|hr)", r"<\1", body)
    body = _re.sub(r"</(h[1-4]|table|ul|hr)>\s*</p>", r"</\1>", body)
    return body


def _markdown_to_html(md: str, title: str = "CAM Report") -> str:
    """Convert CAM Markdown to a styled HTML document for on-screen viewing."""
    body = _render_markdown_fragment(md)

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<title>{_html_mod.escape(title)} — CAM Report</title>
<style>
  :root {{
    --bg-primary: #0d0d1a;
    --bg-section: #111128;
    --bg-table-header: #1e3a5f;
    --bg-table-alt: rgba(30,58,95,0.15);
    --text-primary: #c8c8e0;
    --text-secondary: #9595b0;
    --accent-blue: #60a5fa;
    --accent-indigo: #818cf8;
    --accent-purple: #a78bfa;
    --border-color: #252550;
    --border-section: #1e3a5f;
  }}
  * {{ box-sizing: border-box; }}
  body {{ font-family:'Segoe UI',Tahoma,'Helvetica Neue',sans-serif;
         background:var(--bg-primary); color:var(--text-primary);
         max-width:960px; margin:0 auto; padding:2rem 2.5rem; line-height:1.75;
         font-size: 14px; }}
  h1 {{ color:var(--accent-blue); border-bottom:2px solid var(--border-section);
       padding-bottom:0.6rem; margin-top:2.5rem; font-size:1.6rem;
       letter-spacing: 0.03em; text-transform: uppercase; }}
  h2 {{ color:#3b82f6; margin-top:2.2rem; border-bottom:1px solid var(--border-color);
       padding-bottom:0.35rem; font-size:1.2rem; }}
  h3 {{ color:var(--accent-indigo); margin-top:1.5rem; font-size:1.05rem; }}
  h4 {{ color:var(--accent-purple); font-size:0.95rem; }}
  .cam-table {{ width:100%; border-collapse:collapse; margin:1rem 0; font-size:0.85rem;
               border-radius:6px; overflow:hidden; border:1px solid var(--border-color); }}
  .cam-table th {{ background:var(--bg-table-header); color:#fff; padding:10px 12px;
                  text-align:left; font-weight:600; font-size:0.82rem;
                  text-transform:uppercase; letter-spacing:0.04em; }}
  .cam-table td {{ padding:8px 12px; border-bottom:1px solid var(--border-color);
                  vertical-align:top; }}
  .cam-table tr:nth-child(even) td {{ background:var(--bg-table-alt); }}
  .cam-table tr:hover td {{ background:rgba(59,130,246,0.08); }}
  ul {{ padding-left:1.5rem; margin:0.6rem 0; }}
  li {{ margin:0.35rem 0; }}
  strong {{ color:#e0e0ff; }}
  em {{ color:var(--text-secondary); font-style:italic; }}
  hr {{ border:none; border-top:1px solid var(--border-color); margin:2.5rem 0; }}
  p {{ margin:0.5rem 0; }}
  /* Status badges */
  .cam-table td:nth-child(5) {{ font-size:0.82rem; }}
  /* Section containers for visual grouping */
  h1 + p, h1 + ul, h1 + .cam-table {{ margin-top:1rem; }}
  /* Print styles */
  @media print {{
    body {{ background:#fff; color:#111; font-size:11pt; max-width:100%; padding:1cm; }}
    h1 {{ color:#1e3a5f; border-bottom-color:#1e3a5f; page-break-before:always; }}
    h1:first-of-type {{ page-break-before:auto; }}
    h2 {{ color:#335577; border-bottom-color:#ccc; }}
    h3,h4 {{ color:#444; }}
    .cam-table th {{ background:#335577; -webkit-print-color-adjust:exact; print-color-adjust:exact; }}
    .cam-table {{ border-color:#ccc; }}
    .cam-table td {{ border-bottom-color:#ddd; color:#222; }}
    .cam-table tr:nth-child(even) td {{ background:#f8f8f8; -webkit-print-color-adjust:exact; }}
    strong {{ color:#111; }}
    hr {{ border-top-color:#ccc; }}
    a {{ color:#1e3a5f; }}
  }}
</style></head><body>
{body}
</body></html>"""


def _generate_pdf(md: str, company_name: str, section_comments: dict[str, str] | None = None) -> bytes:
    """Generate a professional CAM PDF with cover page, headers, footers, and page breaks."""
    from io import BytesIO
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                    TableStyle, PageBreak, KeepTogether)
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.lib.enums import TA_CENTER

    # ── Fix ₹ (U+20B9) which Helvetica cannot render (shows as ■) ──
    md = md.replace("\u20b9", "Rs.").replace("\u20a8", "Rs.")

    BANK_NAME = "INDIAN BANK"
    BANK_BLUE = colors.HexColor("#1e3a5f")
    HEADER_BLUE = colors.HexColor("#3b5998")
    ACCENT_GOLD = colors.HexColor("#c8a951")
    LIGHT_BG = colors.HexColor("#f0f4f8")
    SECTION_BG = colors.HexColor("#eaf0f7")
    SOURCE_GREY = colors.HexColor("#8899aa")

    buf = BytesIO()
    section_comments = section_comments or {}

    def _header_footer(canvas, doc):
        """Draw header and footer on each page."""
        canvas.saveState()
        w, h = A4
        # Header bar with bank blue background
        canvas.setFillColor(BANK_BLUE)
        canvas.rect(0, h - 13*mm, w, 13*mm, fill=1, stroke=0)
        canvas.setFont("Helvetica-Bold", 8)
        canvas.setFillColor(colors.white)
        canvas.drawString(15*mm, h - 9.5*mm, BANK_NAME)
        canvas.setFont("Helvetica", 7)
        canvas.drawRightString(w - 15*mm, h - 9.5*mm, "CREDIT APPRAISAL MEMORANDUM")
        # Gold accent line below header
        canvas.setStrokeColor(ACCENT_GOLD)
        canvas.setLineWidth(1.5)
        canvas.line(0, h - 13*mm, w, h - 13*mm)
        # Footer
        canvas.setStrokeColor(colors.HexColor("#cccccc"))
        canvas.setLineWidth(0.5)
        canvas.line(15*mm, 14*mm, w - 15*mm, 14*mm)
        canvas.setFont("Helvetica", 6.5)
        canvas.setFillColor(colors.HexColor("#888888"))
        canvas.drawString(15*mm, 9*mm, "STRICTLY CONFIDENTIAL  |  For Internal Use Only")
        canvas.drawRightString(w - 15*mm, 9*mm, f"Page {doc.page}")
        # Gold dot accent
        canvas.setFillColor(ACCENT_GOLD)
        canvas.circle(w / 2, 10.5*mm, 1.2, fill=1, stroke=0)
        canvas.restoreState()

    def _first_page(canvas, doc):
        """Cover page has no header/footer."""
        pass

    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=15*mm, rightMargin=15*mm,
                            topMargin=18*mm, bottomMargin=18*mm)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="CamH1", fontSize=13, spaceAfter=6, spaceBefore=14,
                              textColor=BANK_BLUE, fontName="Helvetica-Bold",
                              borderWidth=0, borderPadding=0))
    styles.add(ParagraphStyle(name="CamH2", fontSize=10.5, spaceAfter=5, spaceBefore=10,
                              textColor=HEADER_BLUE, fontName="Helvetica-Bold"))
    styles.add(ParagraphStyle(name="CamH3", fontSize=9.5, spaceAfter=3, spaceBefore=6,
                              textColor=colors.HexColor("#2c4a6e"), fontName="Helvetica-Bold"))
    styles.add(ParagraphStyle(name="CamBody", fontSize=8.5, spaceAfter=3, leading=12.5,
                              fontName="Helvetica", textColor=colors.HexColor("#222222")))
    styles.add(ParagraphStyle(name="CamBullet", fontSize=8.5, spaceAfter=2, leading=12,
                              bulletIndent=10, leftIndent=20, fontName="Helvetica",
                              textColor=colors.HexColor("#222222")))
    styles.add(ParagraphStyle(name="CamSource", fontSize=7, spaceAfter=6, leading=9.5,
                              fontName="Helvetica-Oblique", textColor=SOURCE_GREY))
    styles.add(ParagraphStyle(name="CoverBank", fontSize=26, leading=32, spaceAfter=2,
                              textColor=BANK_BLUE, fontName="Helvetica-Bold",
                              alignment=TA_CENTER))
    styles.add(ParagraphStyle(name="CoverDivision", fontSize=11, spaceAfter=6, spaceBefore=2,
                              textColor=colors.HexColor("#555"), fontName="Helvetica",
                              alignment=TA_CENTER))
    styles.add(ParagraphStyle(name="CoverTitle", fontSize=18, spaceAfter=6, spaceBefore=16,
                              textColor=BANK_BLUE, fontName="Helvetica-Bold",
                              alignment=TA_CENTER))
    styles.add(ParagraphStyle(name="CoverCompany", fontSize=20, spaceAfter=6, spaceBefore=8,
                              textColor=colors.HexColor("#111111"), fontName="Helvetica-Bold",
                              alignment=TA_CENTER))
    styles.add(ParagraphStyle(name="CoverDetail", fontSize=10, spaceAfter=3,
                              textColor=colors.HexColor("#444"), fontName="Helvetica",
                              alignment=TA_CENTER, leading=14))
    styles.add(ParagraphStyle(name="CoverConfidential", fontSize=7.5, spaceBefore=20,
                              textColor=colors.HexColor("#888"), fontName="Helvetica-Oblique",
                              alignment=TA_CENTER))
    styles.add(ParagraphStyle(name="CamComment", fontSize=8, spaceAfter=0, leading=11,
                              textColor=colors.HexColor("#4b5563"), fontName="Helvetica"))

    story = []
    lines = md.split("\n")
    table_buf = []
    in_cover = True    # Track when we are in the cover page section
    cover_done = False

    def _flush_table():
        if not table_buf:
            return
        data_rows = []
        for row in table_buf:
            # Skip separator rows: lines that are mostly dashes/colons/pipes/spaces
            stripped_row = row.strip()
            if _re.match(r"^\|[\s\-:|]+\|?$", stripped_row):
                continue
            # Also skip if > 60% dashes (LLM sometimes generates ultra-long separators)
            if len(stripped_row) > 0:
                dash_ratio = (stripped_row.count("-") + stripped_row.count(":")) / len(stripped_row)
                if dash_ratio > 0.6 and stripped_row.startswith("|"):
                    continue
            cells = [c.strip() for c in row.split("|")[1:-1]]
            if not cells:
                continue
            # Wrap cells in Paragraphs for word-wrapping
            wrapped = []
            for ci, c in enumerate(cells):
                c = _re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", c)
                style = styles["CamBody"]
                wrapped.append(Paragraph(c, style))
            data_rows.append(wrapped)
        # Skip header-only tables (1 row = header with no data)
        if len(data_rows) <= 1:
            table_buf.clear()
            return
        if data_rows:
            ncols = max(len(r) for r in data_rows)
            for r in data_rows:
                while len(r) < ncols:
                    r.append(Paragraph("", styles["CamBody"]))
            # ── Smart column widths based on content ──
            avail_w = A4[0] - 30*mm
            # Estimate character widths per column from all rows
            col_char_widths = [0] * ncols
            for r in data_rows:
                for ci, cell in enumerate(r):
                    txt = cell.text if hasattr(cell, 'text') else str(cell)
                    # Clean HTML tags for measuring
                    clean_txt = _re.sub(r"<[^>]+>", "", txt)
                    col_char_widths[ci] = max(col_char_widths[ci], len(clean_txt))
            total_chars = sum(col_char_widths) or 1
            # Ensure minimum width per column (at least 12% of avail)
            min_col_w = avail_w * 0.08
            col_widths = []
            for cw in col_char_widths:
                w = max((cw / total_chars) * avail_w, min_col_w)
                col_widths.append(w)
            # Normalize to fit available width
            total_w = sum(col_widths)
            if total_w > 0:
                col_widths = [(w / total_w) * avail_w for w in col_widths]

            t = Table(data_rows, repeatRows=1, colWidths=col_widths)
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), BANK_BLUE),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 7.5),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#d0d8e0")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_BG]),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                # Top rounding effect — thicker top border
                ("LINEABOVE", (0, 0), (-1, 0), 1.5, BANK_BLUE),
                # Bottom border accent
                ("LINEBELOW", (0, -1), (-1, -1), 0.8, BANK_BLUE),
            ]))
            story.append(t)
            story.append(Spacer(1, 4*mm))
        table_buf.clear()

    # ── Build cover page manually ──
    # Skip markdown cover page lines and build a proper ReportLab cover instead
    cover_lines_text = []
    body_start_idx = 0

    for i, line in enumerate(lines):
        stripped = line.strip()
        # Cover page ends at TABLE OF CONTENTS heading
        if stripped.startswith("## TABLE OF CONTENTS") or stripped.startswith("## 1."):
            body_start_idx = i
            break
        cover_lines_text.append(stripped)
        body_start_idx = i + 1

    # Build professional cover page
    story.append(Spacer(1, 35*mm))
    # Gold accent line
    cover_gold_line = Table([[""]], colWidths=[140*mm])
    cover_gold_line.setStyle(TableStyle([
        ("LINEBELOW", (0, 0), (-1, -1), 2.5, ACCENT_GOLD),
    ]))
    story.append(cover_gold_line)
    story.append(Spacer(1, 6*mm))
    story.append(Paragraph(BANK_NAME, styles["CoverBank"]))
    story.append(Spacer(1, 2*mm))
    story.append(Paragraph("Corporate Banking Division", styles["CoverDivision"]))
    story.append(Spacer(1, 4*mm))
    # Blue line under division
    cover_blue_line = Table([[""]], colWidths=[100*mm])
    cover_blue_line.setStyle(TableStyle([
        ("LINEBELOW", (0, 0), (-1, -1), 1, BANK_BLUE),
    ]))
    story.append(cover_blue_line)
    story.append(Spacer(1, 14*mm))
    story.append(Paragraph("CREDIT APPRAISAL MEMORANDUM", styles["CoverTitle"]))
    story.append(Paragraph("(CAM)", styles["CoverDivision"]))
    story.append(Spacer(1, 12*mm))
    # Borrower name in a highlighted box
    borrower_tbl = Table([[Paragraph(company_name.upper(), styles["CoverCompany"])]], colWidths=[150*mm])
    borrower_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), SECTION_BG),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LINEBEFORE", (0, 0), (0, -1), 3, ACCENT_GOLD),
        ("LINEAFTER", (-1, 0), (-1, -1), 3, ACCENT_GOLD),
    ]))
    story.append(borrower_tbl)

    # Extract key details from cover text
    for ct in cover_lines_text:
        if ct.startswith("**CIN") or ct.startswith("CIN:"):
            clean = ct.replace("**", "").strip().rstrip("  ")
            story.append(Paragraph(clean, styles["CoverDetail"]))
        elif ct.startswith("**PAN"):
            clean = ct.replace("**", "").strip().rstrip("  ")
            story.append(Paragraph(clean, styles["CoverDetail"]))
        elif "Case Type:" in ct:
            clean = ct.replace("**", "").strip().rstrip("  ")
            story.append(Spacer(1, 6*mm))
            story.append(Paragraph(clean, styles["CoverDetail"]))
        elif "Amount Requested:" in ct:
            clean = ct.replace("**", "").strip().rstrip("  ")
            story.append(Paragraph(clean, styles["CoverDetail"]))
        elif "Recommendation:" in ct:
            clean = ct.replace("**", "").strip().rstrip("  ")
            story.append(Paragraph(clean, styles["CoverDetail"]))
        elif "Risk Grade:" in ct:
            clean = ct.replace("**", "").strip().rstrip("  ")
            story.append(Paragraph(clean, styles["CoverDetail"]))
        elif "Date:" in ct:
            clean = ct.replace("**", "").strip().rstrip("  ")
            story.append(Paragraph(clean, styles["CoverDetail"]))
        elif "Sector:" in ct:
            clean = ct.replace("**", "").strip().rstrip("  ")
            story.append(Paragraph(clean, styles["CoverDetail"]))

    story.append(Spacer(1, 20*mm))
    cover_line_tbl3 = Table([[""]], colWidths=[140*mm])
    cover_line_tbl3.setStyle(TableStyle([
        ("LINEBELOW", (0, 0), (-1, -1), 1, ACCENT_GOLD),
    ]))
    story.append(cover_line_tbl3)
    story.append(Spacer(1, 2*mm))
    story.append(Paragraph("STRICTLY CONFIDENTIAL  |  For Internal Use Only  |  Credit Committee Circulation",
                            styles["CoverConfidential"]))
    story.append(PageBreak())

    # ── Process body content (from TOC onwards) ──
    prev_was_divider = False
    for idx, line in enumerate(lines[body_start_idx:], start=body_start_idx):
        stripped = line.strip()

        # Table row detection: starts with | (fix rows missing trailing |)
        if stripped.startswith("|"):
            if not stripped.endswith("|"):
                stripped = stripped + " |"
            # Skip absurdly long separator rows in the table buffer stage
            if len(stripped) > 200 and stripped.count("-") / len(stripped) > 0.5:
                pipes = stripped.count("|")
                ncols = max(pipes - 1, 2)
                stripped = "| " + " | ".join(["---"] * ncols) + " |"
            table_buf.append(stripped)
            continue
        elif table_buf:
            _flush_table()

        if not stripped:
            continue

        # Skip HTML div tags and emoji from markdown
        if stripped.startswith("<div") or stripped.startswith("</div"):
            continue

        # Collapse consecutive dividers
        if stripped.startswith("---"):
            if prev_was_divider:
                continue
            prev_was_divider = True
        else:
            prev_was_divider = False

        if stripped.startswith("# "):
            text = stripped[2:]
            # Page break before major numbered sections and annexures (not TOC or non-sections)
            if _re.match(r"^\d+\.", text) or text.upper().startswith("ANNEXURE") or text.upper().startswith("APPENDIX") or text.upper().startswith("DISCLAIMER"):
                story.append(PageBreak())
            # Skip "Generation Metadata" heading - render inline
            if text.strip().lower() == "generation metadata":
                story.append(Spacer(1, 4*mm))
                story.append(Paragraph(text, styles["CamH2"]))
                continue
            # Section heading with blue left bar
            h1_tbl = Table([[Paragraph(text, styles["CamH1"])]], colWidths=[A4[0] - 30*mm])
            h1_tbl.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), SECTION_BG),
                ("LINEBEFORE", (0, 0), (0, -1), 3, BANK_BLUE),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]))
            story.append(h1_tbl)
            story.append(Spacer(1, 3*mm))
        elif stripped.startswith("## "):
            section_text = stripped[3:]
            # Subsection heading with subtle bottom border
            story.append(Spacer(1, 2*mm))
            story.append(Paragraph(section_text, styles["CamH2"]))
            # Add subtle underline
            h2_line = Table([[""]], colWidths=[A4[0] - 30*mm])
            h2_line.setStyle(TableStyle([
                ("LINEBELOW", (0, 0), (-1, -1), 0.5, colors.HexColor("#b8c8dc")),
            ]))
            story.append(h2_line)
            story.append(Spacer(1, 1.5*mm))
            comment_text = section_comments.get(section_text.strip())
            if comment_text:
                comment_html = (
                    '<font name="Helvetica-Bold" color="#8b6d2f">RM Comment</font><br/>'
                    f'{_html_mod.escape(comment_text)}'
                )
                comment_tbl = Table([[Paragraph(comment_html, styles["CamComment"])]], colWidths=[A4[0] - 30*mm])
                comment_tbl.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fffbef")),
                    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#e6d7aa")),
                    ("LINEBEFORE", (0, 0), (0, -1), 3, ACCENT_GOLD),
                    ("LEFTPADDING", (0, 0), (-1, -1), 10),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]))
                story.append(comment_tbl)
                story.append(Spacer(1, 3*mm))
        elif stripped.startswith("### ") or stripped.startswith("#### "):
            text = _re.sub(r"^#{3,4}\s+", "", stripped)
            story.append(Spacer(1, 1.5*mm))
            story.append(Paragraph(text, styles["CamH3"]))
        elif stripped.startswith("---"):
            # Subtle section divider
            story.append(Spacer(1, 3*mm))
        elif stripped.startswith("- ") or stripped.startswith("* "):
            text = stripped[2:]
            text = _re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
            story.append(Paragraph(f"\u2022 {text}", styles["CamBullet"]))
        elif stripped.startswith("*Source:") and stripped.endswith("*"):
            # Source tags — render in distinctive italic grey style
            source_text = stripped[1:-1]  # Remove surrounding asterisks
            story.append(Paragraph(source_text, styles["CamSource"]))
        else:
            text = _re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", stripped)
            text = _re.sub(r"\*(.+?)\*", r"<i>\1</i>", text)
            story.append(Paragraph(text, styles["CamBody"]))

    _flush_table()
    doc.build(story, onFirstPage=_first_page, onLaterPages=_header_footer)
    return buf.getvalue()

