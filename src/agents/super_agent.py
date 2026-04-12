"""
Super Agent & Specialized Sub-Agents
SuperAgent orchestrates the pipeline by delegating to sub-agents in order.
Each sub-agent wraps one or more deterministic engines.
"""

import json
import logging
from datetime import date

from src.agents.base_agent import BaseAgent, AgentResult
from src.core.runtime_paths import DOCUMENTS_ROOT, REFERENCE_ROOT
from src.models.canonical_model import ExistingExposure, FinancialStatement

log = logging.getLogger(__name__)


def _first_numeric(value):
    """Extract a numeric value from possibly-nested data.
    For lists, returns the *maximum* positive value — this picks the
    consolidated figure over standalone when regex captures both from
    an annual report that contains both sets of financial statements."""
    if isinstance(value, list):
        best = 0.0
        for item in value:
            numeric = _first_numeric(item)
            if numeric > best:
                best = numeric
        return best
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return 0.0


def _latest_financial_context(financials: dict[str, FinancialStatement]):
    if financials:
        ranked = sorted(
            financials.items(),
            key=lambda item: (
                getattr(item[1], "as_of_date", date.min),
                item[0],
            ),
        )
        period, statement = ranked[-1]
        return period, statement.as_of_date, statement

    today = date.today()
    latest_year = today.year - 1 if today.month <= 3 else today.year
    return f"FY{latest_year}", date(latest_year, 3, 31), None


def _statement_from_upload(
    entity_id: str,
    period: str,
    as_of_date: date,
    source: str,
    base_statement: FinancialStatement | None,
    overrides: dict[str, float],
) -> FinancialStatement:
    line_items = dict((base_statement.line_items if base_statement else {}) or {})
    for key, value in overrides.items():
        if value > 0:
            line_items[key] = round(value, 2)

    if line_items.get("revenue_operating", 0) > 0 and line_items.get("total_income", 0) <= 0:
        line_items["total_income"] = line_items["revenue_operating"]

    rhs = (
        line_items.get("total_equity", 0)
        + line_items.get("long_term_debt", 0)
        + line_items.get("current_liabilities", 0)
    )
    if rhs > 0 and line_items.get("total_assets", 0) < rhs:
        line_items["total_assets"] = round(rhs, 2)

    return FinancialStatement(
        entity_id=entity_id,
        period=period,
        statement_type=base_statement.statement_type if base_statement else "standalone",
        source=source,
        as_of_date=as_of_date,
        line_items=line_items,
    )


def _apply_uploaded_financial_overrides(company_data: dict, extraction: dict, emit=None) -> None:
    if not extraction:
        return

    borrower = company_data.get("borrower")
    if borrower is None:
        return

    financials = dict(company_data.get("financials") or {})
    latest_period, latest_as_of, latest_statement = _latest_financial_context(financials)
    selected_docs = extraction.get("selected_documents") or {}
    override_summary: dict[str, object] = {
        "public_baseline": company_data.get("data_provider", "internal"),
        "latest_period": latest_period,
        "latest_rm_documents_override": False,
    }

    audited_data = ((extraction.get("financials") or {}).get("audited")) or {}
    audited_values = {
        "revenue_operating": _first_numeric(audited_data.get("revenue")),
        "total_income": _first_numeric(audited_data.get("total_income")),
        "ebitda": _first_numeric(audited_data.get("ebitda")),
        "pat": _first_numeric(audited_data.get("pat")),
        "pbt": _first_numeric(audited_data.get("pbt")),
        "depreciation": _first_numeric(audited_data.get("depreciation")),
        "finance_cost": _first_numeric(audited_data.get("finance_cost")),
    }
    audited_values = {key: value for key, value in audited_values.items() if value > 0}
    if audited_values:
        financials[latest_period] = _statement_from_upload(
            borrower.entity_id,
            latest_period,
            latest_as_of,
            "rm_upload_audited",
            latest_statement,
            audited_values,
        )
        company_data["financials"] = financials
        override_summary["latest_rm_documents_override"] = True
        override_summary["audited_source_file"] = selected_docs.get("audited_financials")
        override_summary["audited_override_metrics"] = sorted(audited_values.keys())
        if emit:
            emit("Applying latest RM-uploaded audited financials over Probe baseline...")

    provisional_data = extraction.get("provisional") or {}
    provisional_values = {
        "revenue_operating": _first_numeric(provisional_data.get("provisional_revenue")),
        "ebitda": _first_numeric(provisional_data.get("provisional_ebitda")),
        "pat": _first_numeric(provisional_data.get("provisional_pat")),
        "pbt": _first_numeric(provisional_data.get("provisional_pbt")),
        "depreciation": _first_numeric(provisional_data.get("provisional_depreciation")),
        "finance_cost": _first_numeric(provisional_data.get("provisional_finance_cost")),
        "tax_expense": _first_numeric(provisional_data.get("provisional_tax")),
    }
    provisional_values = {key: value for key, value in provisional_values.items() if value > 0}
    if provisional_values:
        company_data["provisional"] = _statement_from_upload(
            borrower.entity_id,
            f"{latest_period} (P)",
            date.today(),
            "rm_upload_provisional",
            latest_statement,
            provisional_values,
        )
        override_summary["latest_rm_documents_override"] = True
        override_summary["provisional_source_file"] = selected_docs.get("provisional")
        override_summary["provisional_override_metrics"] = sorted(provisional_values.keys())
        if emit:
            emit("Using latest RM-uploaded provisional / management financials for current-period analysis...")

    exchange_data = extraction.get("exchange") or {}
    nine_month_revenue = _first_numeric(exchange_data.get("nine_month_revenue"))
    exchange_revenue = nine_month_revenue or _first_numeric(exchange_data.get("revenue"))
    if exchange_revenue > 0:
        annualized_revenue = round(exchange_revenue * (12 / 9), 2) if nine_month_revenue else exchange_revenue
        company_data["exchange_filing"] = FinancialStatement(
            entity_id=borrower.entity_id,
            period=f"9M {date.today().year}",
            statement_type="standalone",
            source="rm_upload_exchange",
            as_of_date=date.today(),
            line_items={
                "revenue_operating": annualized_revenue,
                "total_income": annualized_revenue,
            },
        )
        override_summary["latest_rm_documents_override"] = True
        override_summary["exchange_source_file"] = selected_docs.get("exchange")
        override_summary["exchange_annualized_revenue_cr"] = annualized_revenue

    debt_schedule = (extraction.get("debt_schedule") or {}).get("facilities") or []
    uploaded_exposure: list[ExistingExposure] = []
    for idx, facility in enumerate(debt_schedule, start=1):
        if not isinstance(facility, dict):
            continue
        sanctioned = _first_numeric(facility.get("sanctioned"))
        outstanding = _first_numeric(facility.get("outstanding"))
        utilization = round(outstanding / sanctioned * 100, 1) if sanctioned else 0.0
        uploaded_exposure.append(ExistingExposure(
            facility_id=f"UPL-EXP-{borrower.entity_id}-{idx}",
            entity_id=borrower.entity_id,
            facility_type=str(facility.get("facility_type") or "uploaded_facility"),
            sanctioned_limit_cr=sanctioned,
            outstanding_cr=outstanding,
            utilization_pct=utilization,
            classification="RM Uploaded",
        ))
    if uploaded_exposure:
        company_data["existing_exposure"] = uploaded_exposure
        total_uploaded_debt = round(sum(
            exposure.outstanding_cr or exposure.sanctioned_limit_cr for exposure in uploaded_exposure
        ), 2)
        latest_financials = dict(company_data.get("financials") or {})
        debt_period, debt_as_of, debt_statement = _latest_financial_context(latest_financials)
        latest_financials[debt_period] = _statement_from_upload(
            borrower.entity_id,
            debt_period,
            debt_as_of,
            debt_statement.source if debt_statement else "rm_upload_audited",
            debt_statement,
            {
                "total_debt": total_uploaded_debt,
                "long_term_debt": round(total_uploaded_debt * 0.65, 2),
            },
        )
        company_data["financials"] = latest_financials
        override_summary["latest_rm_documents_override"] = True
        override_summary["debt_schedule_source_file"] = selected_docs.get("debt_schedule")
        override_summary["uploaded_facilities"] = len(uploaded_exposure)
        if emit:
            emit("Replacing public debt placeholders with RM-uploaded debt schedule...")

    if override_summary["latest_rm_documents_override"]:
        company_data["financial_data_strategy"] = override_summary

    # ── Wire optional document data into company_data for fact pack ──
    site_visit = extraction.get("site_visit") or {}
    if site_visit and site_visit.get("full_text"):
        company_data["site_visit_extraction"] = site_visit
        if emit:
            emit("Site visit report extracted — observations will feed into CAM narrative...")

    valuation = extraction.get("valuation") or {}
    if valuation and (valuation.get("market_value") or valuation.get("full_text")):
        company_data["valuation_extraction"] = valuation
        if emit:
            emit("Valuation report extracted — collateral data will feed into CAM narrative...")

    bank_stmt = extraction.get("bank_statement") or {}
    if bank_stmt and (bank_stmt.get("account_number") or bank_stmt.get("full_text")):
        company_data["bank_statement_extraction"] = bank_stmt
        if emit:
            emit("Bank statement extracted — conduct data will feed into CAM narrative...")


# ═══════════════════════════════════════════════════════════════════════════════
# Specialized Sub-Agents
# ═══════════════════════════════════════════════════════════════════════════════

class DataIngestionAgent(BaseAgent):
    name = "data_ingestion"
    description = "Fetch docs from DMS, OCR extract, verify authenticity, fetch APIs"

    def run(self, context):
        from pathlib import Path
        cd = context["company_data"]
        b = cd["borrower"]
        entity_id = b.entity_id
        on_progress = context.get("_on_progress")
        stores = context.get("_stores", {})
        extraction_store = stores.get("extraction", {})
        etb_store = stores.get("etb", {})

        def emit(msg):
            log.debug("[DIA] %s", msg)
            if on_progress:
                on_progress({"type": "info", "message": msg})

        storage_root = DOCUMENTS_ROOT
        downloaded_root = REFERENCE_ROOT

        # ── Step 1: Fetch documents from DMS (replaces web crawling) ──
        from src.services.dms_service import dms_service
        emit("Fetching documents from DMS (Document Management System)...")
        dms_result = dms_service.fetch_documents(
            entity_id, company_data=cd, on_progress=lambda msg: emit(msg)
        )
        log.debug('DIA step1: DMS fetch — %d documents, categories=%s',
                   dms_result.get('total_documents', 0),
                   [c['category'] for c in dms_result.get('categories_populated', [])])

        # ── Step 2: Process downloaded annual reports (real PDFs if available) ──
        downloaded_reports = {}
        try:
            from src.engines.document_ocr_engine import ingest_downloaded_documents
            if downloaded_root.exists():
                emit("Processing downloaded annual reports (PyMuPDF OCR)...")
                downloaded_reports = ingest_downloaded_documents(
                    downloaded_root, storage_root,
                    entity_id=entity_id,
                    on_progress=lambda msg: emit(msg),
                )
                processed = downloaded_reports.get("processed", [])
                if processed:
                    emit(f"Verified & extracted {len(processed)} annual report(s)")
        except Exception as e:
            log.warning("Downloaded doc processing: %s", e)

        # ── Step 4: Extract all documents (PDF/Excel — PyMuPDF engine) ──
        from src.services.document_extractor import extract_all_documents
        # Re-extract if cache is stale (missing newer keys like extraction_engine)
        cached = extraction_store.get(entity_id)
        need_extract = cached is None or "extraction_engine" not in cached
        log.debug('DIA step4: cached=%s need_extract=%s dir_exists=%s', cached is not None, need_extract, (storage_root / entity_id).exists())
        if need_extract and (storage_root / entity_id).exists():
            try:
                emit("Extracting documents (PyMuPDF OCR engine)...")
                extraction_store[entity_id] = extract_all_documents(entity_id, storage_root)
            except Exception as e:
                emit(f"Skipping OCR extraction: {e}")
                extraction_store.setdefault(entity_id, {"document_count": 0, "documents": [], "warning": str(e)})
        ext_data = extraction_store.get(entity_id, {})
        log.debug('DIA step4: ext_data keys=%s extraction_engine=%s', list(ext_data.keys())[:5], ext_data.get('extraction_engine'))
        # Merge downloaded annual report data into extraction
        dr_for_entity = downloaded_reports.get("entity_extractions", {}).get(entity_id)
        log.debug('DIA step4: downloaded_reports entity=%s count=%s', dr_for_entity is not None, len(dr_for_entity) if dr_for_entity else 0)
        if dr_for_entity:
            ext_data["downloaded_annual_reports"] = dr_for_entity
        cd["extraction"] = ext_data
        _apply_uploaded_financial_overrides(cd, ext_data, emit=emit)
        log.debug('DIA step4: has downloaded_annual_reports=%s', 'downloaded_annual_reports' in ext_data)

        # ── Step 5: Document authenticity verification ──
        try:
            from src.engines.document_ocr_engine import verify_batch
            entity_dir = storage_root / entity_id
            if entity_dir.exists():
                all_pdfs = list(entity_dir.rglob("*.pdf"))
                log.debug('DIA step5: entity_dir=%s pdfs=%d', entity_dir, len(all_pdfs))
                if all_pdfs:
                    emit(f"Verifying document authenticity ({len(all_pdfs)} files, SHA-256)...")
                    verification = verify_batch(all_pdfs)
                    cd["document_verification"] = {
                        "verified_count": verification["verified_count"],
                        "total_documents": verification["total_documents"],
                        "total_size_mb": verification["total_size_mb"],
                    }
                    log.debug('DIA step5: verification=%s', cd['document_verification'])
        except Exception as e:
            log.warning('Doc verification error: %s', e)

        # ── Step 6: ETB analytics ──
        ext = extraction_store.get(entity_id)
        if ext and ext.get("etb_conduct") and entity_id not in etb_store:
            emit("Running ETB conduct analytics...")
            from src.engines.etb_analytics_engine import run_etb_analytics, etb_analysis_to_dict
            analysis = run_etb_analytics(ext["etb_conduct"], entity_id)
            etb_store[entity_id] = etb_analysis_to_dict(analysis)
        cd["etb_analysis_data"] = etb_store.get(entity_id)

        # ── Step 7: Web crawl — news & market intelligence ──
        news_data = {"articles": [], "sentiment_summary": {}, "crawl_date": ""}
        swot = {}
        emit("Web-crawl enrichment skipped — only verified public records and uploaded documents are used.")

        # ── Step 8: Social media screening ──
        social_data = {}
        emit("Social-media screening skipped — only verified data sources are used.")

        # ── Step 9: Fetch external API data ──
        cached_external = cd.get("external_data") or {}
        if cached_external:
            emit("Using cached Probe42 external data for validation and CAM context...")
            mca_data = cached_external.get("mca_data", {})
            bureau_data = cached_external.get("bureau_data", {})
            market_data = cached_external.get("market_data", {})
            gst_data = cached_external.get("gst_data", {})
            rating_data = cached_external.get("rating_data", {})
        else:
            emit("No cached verified public-record bundle found. Skipping synthetic fallbacks.")
            mca_data = {}
            bureau_data = {}
            market_data = {}
            gst_data = {}
            rating_data = {}
        log.debug('DataIngestionAgent complete for %s', entity_id)
        return {
            "mca_data": mca_data,
            "bureau_data": bureau_data,
            "market_data": market_data,
            "gst_data": gst_data,
            "rating_data": rating_data,
            "web_crawl_news": news_data,
            "swot_signals": swot,
            "social_media": social_data,
            "downloaded_reports": downloaded_reports,
        }


class PEPScreeningAgent(BaseAgent):
    name = "pep_screening"
    description = "Screen directors against PEP/sanctions databases & crawl adverse media"
    critical = False

    def run(self, context):
        on_progress = context.get("_on_progress")

        def emit(msg):
            if on_progress:
                on_progress({"type": "info", "message": msg})

        cd = context["company_data"]
        entity_id = cd["borrower"].entity_id
        directors = cd.get("directors", [])

        # Step 1: PEP database screening
        emit(f"Screening {len(directors)} directors against PEP/sanctions databases...")
        from src.services.pep_service import screen_directors
        result = screen_directors(entity_id=entity_id, directors=directors)

        company_name = cd["borrower"].company_name
        sector = cd["borrower"].sector
        sector_val = sector.value if hasattr(sector, "value") else str(sector)
        adverse_articles = []
        controversy_idx = 0.0
        emit("Enhanced media screening skipped — only verified data sources are used.")

        pep_summary = {
            "pep_result": result,
            "adverse_media_articles": len(adverse_articles),
            "adverse_headlines": [a.get("headline", "") for a in adverse_articles[:5]],
            "social_controversy_index": controversy_idx,
            "directors_screened": len(directors),
        }

        hits = getattr(result, 'total_hits', 0) if hasattr(result, 'total_hits') else 0
        emit(f"PEP screening complete: {hits} hit(s), {len(adverse_articles)} adverse media article(s)")
        return pep_summary


class FinancialAnalysisAgent(BaseAgent):
    name = "financial_analysis"
    description = "Compute financial ratios and growth metrics"

    def run(self, context):
        from src.engines.ratio_engine import compute_all_ratios, compute_multi_period_ratios
        financials = context["company_data"]["financials"]
        if not financials:
            raise ValueError(
                "No financial statements available. "
                "Re-onboard the company or upload audited financials first."
            )
        periods = sorted(financials.keys())
        latest_period = periods[-1]
        return {
            "multi_period_ratios": compute_multi_period_ratios(financials),
            "latest_ratios": compute_all_ratios(financials[latest_period]),
            "latest_period": latest_period,
        }


class ValidationAgent(BaseAgent):
    name = "validation"
    description = "Run structural, cross-source, and policy validations"

    def run(self, context):
        from src.engines.validation_engine import run_all_validations
        cd = context["company_data"]
        ingestion = context["results"].get("data_ingestion", {})
        return {
            "exceptions": run_all_validations(
                borrower=cd["borrower"],
                financials=cd["financials"],
                provisional=cd.get("provisional"),
                exchange_filing=cd.get("exchange_filing"),
                bureau_payload=ingestion.get("bureau_data"),
                gst_payload=ingestion.get("gst_data"),
                market_signals=cd.get("market_signals", []),
                conduct_records=cd.get("conduct", []),
                covenants=cd.get("covenants", []),
                case_type=cd["facility"].case_type,
                extraction=cd.get("extraction"),
                etb_analysis=cd.get("etb_analysis_data"),
            )
        }


class BenchmarkAgent(BaseAgent):
    name = "benchmark"
    description = "Compare borrower metrics against sector peer benchmarks"

    def run(self, context):
        from src.engines.benchmark_engine import benchmark_all_periods, get_worst_benchmarks
        cd = context["company_data"]
        b = cd["borrower"]
        benchmarks = benchmark_all_periods(b.entity_id, b.sector, cd["financials"])
        lp = context["results"]["financial_analysis"]["latest_period"]
        return {
            "benchmarks": benchmarks,
            "latest_benchmarks": benchmarks.get(lp, []),
            "worst_benchmarks": get_worst_benchmarks(benchmarks, lp),
        }


class PolicyAgent(BaseAgent):
    name = "policy"
    description = "Execute hard rules, risk scoring, and recommendation assembly"

    def run(self, context):
        from src.engines.policy_engine import tier1_hard_rules, tier2_scoring, tier3_recommendation
        cd = context["company_data"]
        r = context["results"]
        exceptions = r["validation"]["exceptions"]
        bureau = r.get("data_ingestion", {}).get("bureau_data")

        tier1 = tier1_hard_rules(cd["borrower"], cd["facility"], exceptions, bureau)

        risk_score = tier2_scoring(
            borrower=cd["borrower"],
            ratios=r["financial_analysis"]["latest_ratios"],
            benchmarks=r["benchmark"]["latest_benchmarks"],
            conduct=cd.get("conduct", []),
            covenants=cd.get("covenants", []),
            directors=cd["directors"],
            group_entities=len(cd.get("group").entities) if cd.get("group") else 0,
            market_signals=cd.get("market_signals", []),
        )

        coll_cov = (sum(c.market_value_cr for c in cd["collateral"])
                    / cd["facility"].amount_requested_cr
                    if cd["facility"].amount_requested_cr > 0 else 0)

        recommendation = tier3_recommendation(
            tier1, risk_score, exceptions, cd["facility"], coll_cov,
        )
        return {
            "tier1_decisions": tier1,
            "risk_score": risk_score,
            "recommendation": recommendation,
        }


class NarrativeAgent(BaseAgent):
    name = "narrative"
    description = "Build fact-pack and render CAM narrative"
    critical = True

    def __init__(self, llm_provider=None):
        self.llm = llm_provider

    def run(self, context):
        from src.engines.cam_fact_builder import build_cam_fact_pack
        from src.core.config_manager import config

        cd = context["company_data"]
        log.debug('NAR: extraction=%s doc_verification=%s', 'extraction' in cd, 'document_verification' in cd)

        fact_pack = build_cam_fact_pack(context["company_data"])

        is_mock = not self.llm or (hasattr(self.llm, "name") and self.llm.name == "mock")

        # Also check if narrative mode was explicitly set to template via config/API
        narrative_cfg = config.get("llm_providers", "narrative", default={}) or {}
        is_template_mode = narrative_cfg.get("mode") == "template"

        if is_mock or is_template_mode:
            # Template-based rendering — no LLM calls
            from src.engines.cam_llm_renderer import render_cam_template_only
            section_cb = context.get("_on_progress")
            cam_text = render_cam_template_only(fact_pack, on_section_progress=section_cb)
            return {"fact_pack": fact_pack, "cam_text": cam_text, "narrative_mode": "template"}

        ns = config.get_narrative_settings()  # raises if mode != 'llm'

        from src.engines.cam_llm_renderer import render_cam_with_llm
        section_cb = context.get("_on_progress")
        cam_text = render_cam_with_llm(
            fact_pack=fact_pack,
            llm_provider=self.llm,
            temperature=ns.get("temperature", 0.1),
            max_tokens_per_section=ns.get("max_tokens_per_section", 1500),
            on_section_progress=section_cb,
        )

        if not cam_text or len(cam_text.strip()) < 100:
            raise RuntimeError("LLM narrative generation produced empty or insufficient output")

        return {"fact_pack": fact_pack, "cam_text": cam_text, "narrative_mode": "llm"}


# ═══════════════════════════════════════════════════════════════════════════════
# Super Agent — Orchestrator
# ═══════════════════════════════════════════════════════════════════════════════

class SuperAgent:
    """Orchestrates the full CAM pipeline by delegating to sub-agents."""

    def __init__(self, llm_provider=None):
        self.agents: list[BaseAgent] = [
            DataIngestionAgent(),
            PEPScreeningAgent(),
            FinancialAnalysisAgent(),
            ValidationAgent(),
            BenchmarkAgent(),
            PolicyAgent(),
            NarrativeAgent(llm_provider=llm_provider),
        ]
        self.pipeline_log: list[dict] = []

    def execute_pipeline(self, company_data: dict, on_progress=None, stores=None) -> dict:
        import time as _time, sys as _sys
        def _plog(msg):
            print(f"[PIPELINE {_time.strftime('%H:%M:%S')}] {msg}", flush=True, file=_sys.stderr)
        context = {"company_data": company_data, "results": {}}
        if on_progress:
            context["_on_progress"] = on_progress
        if stores:
            context["_stores"] = stores
        self.pipeline_log = []
        total = len(self.agents)

        for idx, agent in enumerate(self.agents):
            _plog(f">>> Starting agent {idx+1}/{total}: {agent.name}")
            if on_progress:
                on_progress({
                    "type": "agent_start",
                    "agent": agent.name,
                    "description": agent.description,
                    "step": idx + 1,
                    "total": total,
                })
            result = agent.execute(context)
            _plog(f"<<< Agent {agent.name}: {result.status} ({result.duration_ms}ms)")
            self.pipeline_log.append(result.to_dict())
            if on_progress:
                on_progress({
                    "type": "agent_complete",
                    "agent": agent.name,
                    "status": result.status,
                    "duration_ms": result.duration_ms,
                    "error": result.error,
                    "step": idx + 1,
                    "total": total,
                })
            if result.status == "completed" and result.data:
                context["results"][agent.name] = result.data
            elif result.status == "failed" and agent.critical:
                raise RuntimeError(f"Critical agent '{agent.name}' failed: {result.error}")

        return context

    def get_agent_list(self) -> list[dict]:
        return [
            {"name": a.name, "description": a.description, "critical": a.critical}
            for a in self.agents
        ]
