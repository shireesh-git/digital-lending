"""HTTP routers, one per business area."""

from src.api.routers import (
    admin, analytics, approvals, cam, cases, chat, companies, documents, external, onboarding, system,
)

ALL_ROUTERS = [
    system.router,
    companies.router,
    onboarding.router,
    cases.router,
    cam.router,
    approvals.router,
    documents.router,
    analytics.router,
    external.router,
    chat.router,
    admin.router,
]
