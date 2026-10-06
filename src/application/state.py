"""In-process application state shared by the services."""

from dataclasses import dataclass, field


@dataclass
class AppState:
    """Working set of the running application.

    ``companies`` and ``cases`` are write-through caches over SQLite (see
    ``PersistenceService``). The other three are per-process caches that are
    rebuilt on demand and invalidated when a company's documents change.
    """

    companies: dict[str, dict] = field(default_factory=dict)
    cases: dict[str, dict] = field(default_factory=dict)
    extractions: dict[str, dict] = field(default_factory=dict)
    etb_analytics: dict[str, dict] = field(default_factory=dict)
    fraud_reports: dict[str, dict] = field(default_factory=dict)

    def pipeline_stores(self) -> dict:
        """Caches the pipeline's ingestion agent reads and fills."""
        return {"extraction": self.extractions, "etb": self.etb_analytics}

    def invalidate_derived(self, entity_id: str) -> None:
        """Drop results derived from a company's documents after they change."""
        self.extractions.pop(entity_id, None)
        self.cases.pop(entity_id, None)
