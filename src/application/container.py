"""
Composition root: builds the application state and wires the services.

Startup order matches the original monolith: seeded catalog, then persisted
companies, then persisted cases (dropping orphans), then reference documents,
then legacy output-file cases.
"""

from dataclasses import dataclass

from src.application.approval_service import ApprovalService
from src.application.cam_service import CamService
from src.application.case_service import CaseService
from src.application.company_service import CompanyService
from src.application.document_workspace import DocumentWorkspaceService
from src.application.state import AppState


@dataclass
class ServiceContainer:
    state: AppState
    persistence: object
    workspace: DocumentWorkspaceService
    companies: CompanyService
    cases: CaseService
    cam: CamService
    approvals: ApprovalService


def load_authority_matrix():
    from src.core.config_manager import config
    from src.engines.approval_policy import AuthorityMatrix

    config.reload()
    return AuthorityMatrix.from_config(config.get("approval", default={}) or {})


def default_pipeline_factory():
    from functools import partial

    from src.agents.pipeline import SuperAgent
    from src.core.config_manager import config
    from src.core.llm_provider import create_llm_provider
    from src.services.cam_checkpoints import PersistentSectionCheckpoints
    from src.services.persistence import persistence

    return SuperAgent(
        llm_provider=create_llm_provider(config.get_active_llm_provider()),
        checkpoint_factory=partial(PersistentSectionCheckpoints, persistence),
    )


def build_container(pipeline_factory=default_pipeline_factory) -> ServiceContainer:
    from src.core.runtime_paths import DOCUMENTS_ROOT, OUTPUT_ROOT, REFERENCE_CAM_ROOT
    from src.data.company_catalog import bootstrap_reference_documents, seed_company_store
    from src.services.company_onboarding import onboard_company
    from src.services.document_store import doc_store
    from src.services.persistence import persistence
    from src.services.probe_service import clear_probe_cache
    from src.application.serialization import repair_mojibake

    cases = persistence.load_latest_cases()
    companies = seed_company_store()
    companies.update(persistence.load_companies())
    state = AppState(
        companies=companies,
        # Repaired once here; CaseService.get no longer repairs on every read.
        cases={eid: repair_mojibake(case) for eid, case in cases.items() if eid in companies},
    )
    bootstrap_reference_documents()

    workspace = DocumentWorkspaceService(DOCUMENTS_ROOT, REFERENCE_CAM_ROOT)
    company_service = CompanyService(state, persistence, doc_store, workspace,
                                     onboard_fn=onboard_company, clear_probe_cache_fn=clear_probe_cache)
    case_service = CaseService(state, persistence, company_service, OUTPUT_ROOT, pipeline_factory)
    case_service.load_all_from_disk()
    cam_service = CamService(state, persistence, case_service, company_service)
    approval_service = ApprovalService(persistence, case_service, matrix_loader=load_authority_matrix)
    case_service.rerun_guard = approval_service.is_locked_for_rerun

    return ServiceContainer(
        state=state,
        persistence=persistence,
        workspace=workspace,
        companies=company_service,
        cases=case_service,
        cam=cam_service,
        approvals=approval_service,
    )
