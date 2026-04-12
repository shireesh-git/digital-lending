from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from dataclasses import is_dataclass
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from threading import RLock
from typing import Any

from src.core.runtime_paths import RUNTIME_DB_PATH, RUNTIME_DB_ROOT, ensure_runtime_dirs
from src.models.canonical_model import (
    Borrower,
    BorrowerType,
    CaseType,
    Collateral,
    ConductRecord,
    CovenantRecord,
    DirectorPromoter,
    ExistingExposure,
    FacilityRequest,
    FacilityType,
    FinancialStatement,
    GroupEntity,
    MarketSignal,
    RiskSeverity,
    Sector,
)


def _plain(value: Any) -> Any:
    if is_dataclass(value):
        return {field: _plain(getattr(value, field)) for field in value.__dataclass_fields__}
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    return value


def _parse_date(value: Any, default: date | None = None) -> date | None:
    if not value:
        return default
    if isinstance(value, date):
        return value
    text = str(value).strip()
    if not text:
        return default
    try:
        return date.fromisoformat(text[:10])
    except Exception:
        return default


def _enum_value(enum_cls, value, default):
    try:
        return enum_cls(value)
    except Exception:
        return default


def _deserialize_financial_statement(payload: dict[str, Any] | None) -> FinancialStatement | None:
    if not isinstance(payload, dict):
        return None
    return FinancialStatement(
        entity_id=str(payload.get("entity_id") or ""),
        period=str(payload.get("period") or "FY2025"),
        statement_type=str(payload.get("statement_type") or "standalone"),
        source=str(payload.get("source") or "unknown"),
        as_of_date=_parse_date(payload.get("as_of_date"), date(2025, 3, 31)) or date(2025, 3, 31),
        line_items=dict(payload.get("line_items") or {}),
    )


def deserialize_company_payload(payload: dict[str, Any]) -> dict[str, Any]:
    borrower_payload = payload.get("borrower") or {}
    facility_payload = payload.get("facility") or {}

    borrower = Borrower(
        entity_id=str(borrower_payload.get("entity_id") or payload.get("entity_id") or ""),
        company_name=str(borrower_payload.get("company_name") or payload.get("company_name") or ""),
        cin=str(borrower_payload.get("cin") or ""),
        pan=str(borrower_payload.get("pan") or ""),
        borrower_type=_enum_value(BorrowerType, borrower_payload.get("borrower_type"), BorrowerType.LISTED),
        sector=_enum_value(Sector, borrower_payload.get("sector"), Sector.MANUFACTURING),
        subsector=str(borrower_payload.get("subsector") or "General"),
        date_of_incorporation=_parse_date(borrower_payload.get("date_of_incorporation"), date(2000, 1, 1)) or date(2000, 1, 1),
        registered_state=str(borrower_payload.get("registered_state") or "Unknown"),
        registered_address=str(borrower_payload.get("registered_address") or "Unknown"),
        authorized_capital=float(borrower_payload.get("authorized_capital") or 0.0),
        paid_up_capital=float(borrower_payload.get("paid_up_capital") or 0.0),
        listed_exchange=borrower_payload.get("listed_exchange"),
        isin=borrower_payload.get("isin"),
        bse_code=borrower_payload.get("bse_code"),
        nse_symbol=borrower_payload.get("nse_symbol"),
        credit_rating=borrower_payload.get("credit_rating"),
        rating_agency=borrower_payload.get("rating_agency"),
        employee_count=borrower_payload.get("employee_count"),
        website=borrower_payload.get("website"),
    )

    group_payload = payload.get("group")
    group = None
    if isinstance(group_payload, dict):
        group = GroupEntity(
            group_id=str(group_payload.get("group_id") or f"GRP-{borrower.entity_id}"),
            group_name=str(group_payload.get("group_name") or borrower.company_name),
            parent_entity_id=str(group_payload.get("parent_entity_id") or borrower.entity_id),
            entities=list(group_payload.get("entities") or []),
            promoter_holding_pct=float(group_payload.get("promoter_holding_pct") or 0.0),
            institutional_holding_pct=float(group_payload.get("institutional_holding_pct") or 0.0),
            public_holding_pct=float(group_payload.get("public_holding_pct") or 0.0),
            hierarchy=group_payload.get("hierarchy"),
            ultimate_parent=group_payload.get("ultimate_parent"),
            group_revenue_cr=group_payload.get("group_revenue_cr"),
            group_net_worth_cr=group_payload.get("group_net_worth_cr"),
            group_total_debt_cr=group_payload.get("group_total_debt_cr"),
        )

    directors = [
        DirectorPromoter(
            din=str(item.get("din") or "00000000"),
            name=str(item.get("name") or "Unknown Director"),
            designation=str(item.get("designation") or "Director"),
            entity_id=str(item.get("entity_id") or borrower.entity_id),
            pan=item.get("pan"),
            date_of_appointment=_parse_date(item.get("date_of_appointment")),
            other_directorships=list(item.get("other_directorships") or []),
            net_worth_cr=item.get("net_worth_cr"),
            is_promoter=bool(item.get("is_promoter", False)),
        )
        for item in (payload.get("directors") or [])
        if isinstance(item, dict)
    ]

    financials = {
        period: statement
        for period, statement in (
            (period, _deserialize_financial_statement(statement_payload))
            for period, statement_payload in (payload.get("financials") or {}).items()
        )
        if statement is not None
    }

    provisional = _deserialize_financial_statement(payload.get("provisional"))

    facility = FacilityRequest(
        facility_id=str(facility_payload.get("facility_id") or f"FAC-{borrower.entity_id}"),
        entity_id=str(facility_payload.get("entity_id") or borrower.entity_id),
        case_type=_enum_value(CaseType, facility_payload.get("case_type"), CaseType.NTB),
        facility_type=_enum_value(FacilityType, facility_payload.get("facility_type"), FacilityType.WORKING_CAPITAL),
        amount_requested_cr=float(facility_payload.get("amount_requested_cr") or 0.0),
        purpose=str(facility_payload.get("purpose") or "To be captured during onboarding"),
        tenor_months=facility_payload.get("tenor_months"),
        collateral_type=facility_payload.get("collateral_type"),
        collateral_value_cr=facility_payload.get("collateral_value_cr"),
        existing_limit_cr=facility_payload.get("existing_limit_cr"),
        proposed_limit_cr=facility_payload.get("proposed_limit_cr"),
    )

    collateral = [
        Collateral(
            collateral_id=str(item.get("collateral_id") or f"COL-{borrower.entity_id}"),
            entity_id=str(item.get("entity_id") or borrower.entity_id),
            collateral_type=str(item.get("collateral_type") or "general"),
            description=str(item.get("description") or ""),
            market_value_cr=float(item.get("market_value_cr") or 0.0),
            forced_sale_value_cr=float(item.get("forced_sale_value_cr") or 0.0),
            valuation_date=_parse_date(item.get("valuation_date"), date.today()) or date.today(),
            encumbrance_status=str(item.get("encumbrance_status") or "clear"),
        )
        for item in (payload.get("collateral") or [])
        if isinstance(item, dict)
    ]

    market_signals = [
        MarketSignal(
            entity_id=str(item.get("entity_id") or borrower.entity_id),
            signal_type=str(item.get("signal_type") or "news"),
            headline=str(item.get("headline") or ""),
            sentiment=str(item.get("sentiment") or "neutral"),
            severity=_enum_value(RiskSeverity, item.get("severity"), RiskSeverity.LOW),
            source_name=str(item.get("source_name") or "Unknown"),
            signal_date=_parse_date(item.get("signal_date"), date.today()) or date.today(),
            details=str(item.get("details") or ""),
        )
        for item in (payload.get("market_signals") or [])
        if isinstance(item, dict)
    ]

    existing_exposure = [
        ExistingExposure(
            facility_id=str(item.get("facility_id") or f"EXP-{borrower.entity_id}"),
            entity_id=str(item.get("entity_id") or borrower.entity_id),
            facility_type=str(item.get("facility_type") or "facility"),
            sanctioned_limit_cr=float(item.get("sanctioned_limit_cr") or 0.0),
            outstanding_cr=float(item.get("outstanding_cr") or 0.0),
            utilization_pct=float(item.get("utilization_pct") or 0.0),
            overdue_days=int(item.get("overdue_days") or 0),
            classification=str(item.get("classification") or "Standard"),
        )
        for item in (payload.get("existing_exposure") or [])
        if isinstance(item, dict)
    ]

    conduct = [
        ConductRecord(
            entity_id=str(item.get("entity_id") or borrower.entity_id),
            period=str(item.get("period") or ""),
            avg_bank_balance_cr=float(item.get("avg_bank_balance_cr") or 0.0),
            credit_turnover_cr=float(item.get("credit_turnover_cr") or 0.0),
            debit_turnover_cr=float(item.get("debit_turnover_cr") or 0.0),
            cheque_returns=int(item.get("cheque_returns") or 0),
            limit_utilization_pct=float(item.get("limit_utilization_pct") or 0.0),
            overdue_instances=int(item.get("overdue_instances") or 0),
            max_overdue_days=int(item.get("max_overdue_days") or 0),
            dpd_30_count=int(item.get("dpd_30_count") or 0),
            dpd_60_count=int(item.get("dpd_60_count") or 0),
            dpd_90_count=int(item.get("dpd_90_count") or 0),
        )
        for item in (payload.get("conduct") or [])
        if isinstance(item, dict)
    ]

    covenants = [
        CovenantRecord(
            entity_id=str(item.get("entity_id") or borrower.entity_id),
            covenant_type=str(item.get("covenant_type") or ""),
            required_value=str(item.get("required_value") or ""),
            actual_value=str(item.get("actual_value") or ""),
            compliance_status=str(item.get("compliance_status") or "compliant"),
            period=str(item.get("period") or ""),
            breach_details=str(item.get("breach_details") or ""),
        )
        for item in (payload.get("covenants") or [])
        if isinstance(item, dict)
    ]

    restored = dict(payload)
    restored.update(
        {
            "borrower": borrower,
            "group": group,
            "directors": directors,
            "financials": financials,
            "provisional": provisional,
            "facility": facility,
            "collateral": collateral,
            "market_signals": market_signals,
            "existing_exposure": existing_exposure,
            "conduct": conduct,
            "covenants": covenants,
        }
    )
    return restored


class PersistenceService:
    def __init__(self, db_path: Path | None = None):
        ensure_runtime_dirs()
        self.db_path = db_path or RUNTIME_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()
        self._init_db()

    @contextmanager
    def _connect(self):
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            try:
                yield conn
                conn.commit()
            finally:
                conn.close()

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                PRAGMA journal_mode=WAL;

                CREATE TABLE IF NOT EXISTS app_users (
                    user_id TEXT PRIMARY KEY,
                    email TEXT,
                    display_name TEXT,
                    role TEXT,
                    status TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS companies (
                    entity_id TEXT PRIMARY KEY,
                    company_name TEXT NOT NULL,
                    catalog_source TEXT,
                    is_seeded INTEGER NOT NULL DEFAULT 0,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS case_runs (
                    run_id TEXT PRIMARY KEY,
                    entity_id TEXT NOT NULL,
                    company_name TEXT NOT NULL,
                    recommendation TEXT,
                    risk_grade TEXT,
                    composite_score REAL,
                    run_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_case_runs_entity_run_at
                ON case_runs(entity_id, run_at DESC);

                CREATE TABLE IF NOT EXISTS case_comments (
                    run_id TEXT NOT NULL,
                    section_id TEXT NOT NULL,
                    comment_text TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (run_id, section_id)
                );

                CREATE TABLE IF NOT EXISTS cam_section_edits (
                    entity_id TEXT NOT NULL,
                    section_key TEXT NOT NULL,
                    edited_html TEXT NOT NULL,
                    edited_by TEXT NOT NULL DEFAULT 'RM',
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (entity_id, section_key)
                );
                """
            )
            now = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
            conn.execute(
                """
                INSERT OR IGNORE INTO app_users(user_id, email, display_name, role, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                ("system", "future-login@local", "System Placeholder", "admin", "active", now, now),
            )

    def upsert_company(self, entity_id: str, company_data: dict[str, Any], *, is_seeded: bool = False, catalog_source: str | None = None) -> None:
        payload = json.dumps(_plain(company_data), ensure_ascii=False)
        company_name = (
            getattr(company_data.get("borrower"), "company_name", None)
            or company_data.get("company_name")
            or entity_id
        )
        now = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO companies(entity_id, company_name, catalog_source, is_seeded, payload_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(entity_id) DO UPDATE SET
                    company_name=excluded.company_name,
                    catalog_source=excluded.catalog_source,
                    is_seeded=excluded.is_seeded,
                    payload_json=excluded.payload_json,
                    updated_at=excluded.updated_at
                """,
                (entity_id, str(company_name), catalog_source or company_data.get("catalog_source"), 1 if is_seeded else 0, payload, now, now),
            )

    def load_companies(self) -> dict[str, dict[str, Any]]:
        results: dict[str, dict[str, Any]] = {}
        with self._connect() as conn:
            rows = conn.execute("SELECT entity_id, payload_json FROM companies").fetchall()
        for row in rows:
            try:
                payload = json.loads(row["payload_json"])
                results[row["entity_id"]] = deserialize_company_payload(payload)
            except Exception:
                continue
        return results

    def delete_company(self, entity_id: str) -> None:
        with self._connect() as conn:
            run_rows = conn.execute("SELECT run_id FROM case_runs WHERE entity_id = ?", (entity_id,)).fetchall()
            run_ids = [row["run_id"] for row in run_rows]
            conn.execute("DELETE FROM companies WHERE entity_id = ?", (entity_id,))
            conn.execute("DELETE FROM case_runs WHERE entity_id = ?", (entity_id,))
            for run_id in run_ids:
                conn.execute("DELETE FROM case_comments WHERE run_id = ?", (run_id,))

    def save_case_run(self, case_result: dict[str, Any]) -> None:
        payload = json.dumps(_plain(case_result), ensure_ascii=False)
        now = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
        run_id = str(case_result.get("run_id") or "")
        if not run_id:
            return
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO case_runs(
                    run_id, entity_id, company_name, recommendation, risk_grade, composite_score, run_at, payload_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    case_result.get("entity_id"),
                    case_result.get("company_name") or case_result.get("entity_id"),
                    case_result.get("recommendation"),
                    case_result.get("risk_grade"),
                    case_result.get("composite_score"),
                    case_result.get("run_at") or now,
                    payload,
                    now,
                ),
            )

    def get_latest_case(self, entity_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT payload_json
                FROM case_runs
                WHERE entity_id = ?
                ORDER BY run_at DESC, created_at DESC
                LIMIT 1
                """,
                (entity_id,),
            ).fetchone()
        if not row:
            return None
        try:
            return json.loads(row["payload_json"])
        except Exception:
            return None

    def load_latest_cases(self) -> dict[str, dict[str, Any]]:
        latest: dict[str, dict[str, Any]] = {}
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT entity_id, payload_json
                FROM case_runs
                ORDER BY run_at DESC, created_at DESC
                """
            ).fetchall()
        for row in rows:
            entity_id = row["entity_id"]
            if entity_id in latest:
                continue
            try:
                latest[entity_id] = json.loads(row["payload_json"])
            except Exception:
                continue
        return latest

    def load_case_comments(self, run_id: str | None) -> dict[str, str]:
        if not run_id:
            return {}
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT section_id, comment_text FROM case_comments WHERE run_id = ? ORDER BY section_id",
                (run_id,),
            ).fetchall()
        return {row["section_id"]: row["comment_text"] for row in rows}

    def save_case_comments(self, run_id: str | None, comments: dict[str, str]) -> dict[str, str]:
        if not run_id:
            return {}
        clean = {str(key): str(value or "").strip() for key, value in comments.items() if str(value or "").strip()}
        now = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
        with self._connect() as conn:
            conn.execute("DELETE FROM case_comments WHERE run_id = ?", (run_id,))
            for section_id, comment_text in clean.items():
                conn.execute(
                    "INSERT INTO case_comments(run_id, section_id, comment_text, updated_at) VALUES (?, ?, ?, ?)",
                    (run_id, section_id, comment_text, now),
                )
        return clean

    def load_cam_section_edits(self, entity_id: str) -> dict[str, dict[str, str]]:
        """Load all RM-edited CAM section overrides for a given entity."""
        if not entity_id:
            return {}
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT section_key, edited_html, edited_by, updated_at FROM cam_section_edits WHERE entity_id = ? ORDER BY section_key",
                (entity_id,),
            ).fetchall()
        return {
            row["section_key"]: {
                "html": row["edited_html"],
                "edited_by": row["edited_by"],
                "updated_at": row["updated_at"],
            }
            for row in rows
        }

    def save_cam_section_edit(self, entity_id: str, section_key: str, edited_html: str, edited_by: str = "RM") -> None:
        """Save or update a single RM-edited CAM section."""
        if not entity_id or not section_key:
            return
        now = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
        with self._connect() as conn:
            if edited_html.strip():
                conn.execute(
                    """
                    INSERT INTO cam_section_edits(entity_id, section_key, edited_html, edited_by, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(entity_id, section_key) DO UPDATE SET
                        edited_html=excluded.edited_html,
                        edited_by=excluded.edited_by,
                        updated_at=excluded.updated_at
                    """,
                    (entity_id, section_key, edited_html.strip(), edited_by, now),
                )
            else:
                conn.execute(
                    "DELETE FROM cam_section_edits WHERE entity_id = ? AND section_key = ?",
                    (entity_id, section_key),
                )

    def delete_cam_section_edits(self, entity_id: str) -> None:
        """Delete all RM section edits for a given entity."""
        if not entity_id:
            return
        with self._connect() as conn:
            conn.execute("DELETE FROM cam_section_edits WHERE entity_id = ?", (entity_id,))

    def describe(self) -> dict[str, Any]:
        return {
            "engine": "sqlite",
            "db_path": str(self.db_path),
            "db_root": str(RUNTIME_DB_ROOT),
        }


persistence = PersistenceService()
