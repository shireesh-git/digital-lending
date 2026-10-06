"""Data ingestion: DMS fetch, document extraction, authenticity checks, ETB analytics, cached public records."""

import logging

from src.agents.base_agent import BaseAgent
from src.agents.financial_overrides import apply_uploaded_financial_overrides
from src.core.runtime_paths import DOCUMENTS_ROOT, REFERENCE_ROOT

log = logging.getLogger(__name__)


class DataIngestionAgent(BaseAgent):
    name = "data_ingestion"
    description = "Fetch docs from DMS, OCR extract, verify authenticity, fetch APIs"

    def run(self, context):
        cd = context["company_data"]
        entity_id = cd["borrower"].entity_id
        stores = context.get("_stores", {})
        extraction_store = stores.get("extraction", {})
        etb_store = stores.get("etb", {})
        progress = self.emitter(context)

        def emit(msg):
            log.debug("[DIA] %s", msg)
            progress(msg)

        self._fetch_from_dms(entity_id, cd, emit)
        downloaded_reports = self._ingest_downloaded_reports(entity_id, emit)
        self._extract_documents(entity_id, cd, extraction_store, downloaded_reports, emit)
        self._verify_authenticity(entity_id, cd, emit)
        self._run_etb_analytics(entity_id, cd, extraction_store, etb_store, emit)

        emit("Web-crawl enrichment skipped — only verified public records and uploaded documents are used.")
        emit("Social-media screening skipped — only verified data sources are used.")
        external = self._external_data(cd, emit)
        log.debug("DataIngestionAgent complete for %s", entity_id)
        return {
            **external,
            "web_crawl_news": {"articles": [], "sentiment_summary": {}, "crawl_date": ""},
            "swot_signals": {},
            "social_media": {},
            "downloaded_reports": downloaded_reports,
        }

    # ── Steps ────────────────────────────────────────────────────────────

    @staticmethod
    def _fetch_from_dms(entity_id, cd, emit):
        from src.services.dms_service import dms_service
        emit("Fetching documents from DMS (Document Management System)...")
        result = dms_service.fetch_documents(entity_id, company_data=cd, on_progress=emit)
        log.debug("DIA dms: %d documents, categories=%s", result.get("total_documents", 0),
                  [c["category"] for c in result.get("categories_populated", [])])

    @staticmethod
    def _ingest_downloaded_reports(entity_id, emit) -> dict:
        """Annual reports downloaded into the reference folder (real PDFs, if any)."""
        try:
            from src.engines.document_ocr_engine import ingest_downloaded_documents
            if not REFERENCE_ROOT.exists():
                return {}
            emit("Processing downloaded annual reports (PyMuPDF OCR)...")
            reports = ingest_downloaded_documents(REFERENCE_ROOT, DOCUMENTS_ROOT,
                                                  entity_id=entity_id, on_progress=emit)
            if reports.get("processed"):
                emit(f"Verified & extracted {len(reports['processed'])} annual report(s)")
            return reports
        except Exception as e:
            log.warning("Downloaded doc processing: %s", e)
            return {}

    @staticmethod
    def _extract_documents(entity_id, cd, extraction_store, downloaded_reports, emit):
        from src.services.document_extractor import extract_all_documents

        cached = extraction_store.get(entity_id)
        # Re-extract when the cache predates newer keys such as extraction_engine.
        stale = cached is None or "extraction_engine" not in cached
        if stale and (DOCUMENTS_ROOT / entity_id).exists():
            try:
                emit("Extracting documents (PyMuPDF OCR engine)...")
                extraction_store[entity_id] = extract_all_documents(entity_id, DOCUMENTS_ROOT)
            except Exception as e:
                emit(f"Skipping OCR extraction: {e}")
                extraction_store.setdefault(entity_id, {"document_count": 0, "documents": [], "warning": str(e)})

        ext_data = extraction_store.get(entity_id, {})
        reports_for_entity = downloaded_reports.get("entity_extractions", {}).get(entity_id)
        if reports_for_entity:
            ext_data["downloaded_annual_reports"] = reports_for_entity
        cd["extraction"] = ext_data
        apply_uploaded_financial_overrides(cd, ext_data, emit=emit)

    @staticmethod
    def _verify_authenticity(entity_id, cd, emit):
        try:
            from src.engines.document_ocr_engine import verify_batch
            entity_dir = DOCUMENTS_ROOT / entity_id
            if not entity_dir.exists():
                return
            pdfs = list(entity_dir.rglob("*.pdf"))
            if not pdfs:
                return
            emit(f"Verifying document authenticity ({len(pdfs)} files, SHA-256)...")
            verification = verify_batch(pdfs)
            cd["document_verification"] = {
                "verified_count": verification["verified_count"],
                "total_documents": verification["total_documents"],
                "total_size_mb": verification["total_size_mb"],
            }
        except Exception as e:
            log.warning("Doc verification error: %s", e)

    @staticmethod
    def _run_etb_analytics(entity_id, cd, extraction_store, etb_store, emit):
        ext = extraction_store.get(entity_id)
        if ext and ext.get("etb_conduct") and entity_id not in etb_store:
            emit("Running ETB conduct analytics...")
            from src.engines.etb_analytics_engine import etb_analysis_to_dict, run_etb_analytics
            etb_store[entity_id] = etb_analysis_to_dict(run_etb_analytics(ext["etb_conduct"], entity_id))
        cd["etb_analysis_data"] = etb_store.get(entity_id)

    @staticmethod
    def _external_data(cd, emit) -> dict:
        """Cached verified public-record bundle (Probe42). No synthetic fallback."""
        cached = cd.get("external_data") or {}
        if cached:
            emit("Using cached Probe42 external data for validation and CAM context...")
        else:
            emit("No cached verified public-record bundle found. Skipping synthetic fallbacks.")
        return {key: cached.get(key, {}) for key in
                ("mca_data", "bureau_data", "market_data", "gst_data", "rating_data")}
