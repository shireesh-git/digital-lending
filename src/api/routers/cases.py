"""Credit cases: list, fetch, and run the analysis pipeline (blocking or streamed)."""

import asyncio
import json
import logging
import queue
import threading
import traceback

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from src.api.dependencies import get_container
from src.application.container import ServiceContainer
from src.application.errors import ApplicationError

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["cases"])


def _run_summary(case: dict) -> dict:
    return {
        "recommendation": case["recommendation"],
        "risk_grade": case["risk_grade"],
        "composite_score": case["composite_score"],
        "narrative_mode": case.get("narrative_mode", "template"),
    }


@router.get("/cases")
async def list_cases(svc: ServiceContainer = Depends(get_container)):
    return {"cases": svc.cases.summaries()}


@router.get("/cases/{entity_id}")
async def get_case(entity_id: str, svc: ServiceContainer = Depends(get_container)):
    return svc.cases.require(entity_id, "Case not found — run the pipeline first.")


@router.get("/cases/{entity_id}/runs")
async def list_runs(entity_id: str, limit: int = 20, svc: ServiceContainer = Depends(get_container)):
    """Pipeline attempts for a company (running / completed / failed, with errors)."""
    return {"entity_id": entity_id, "runs": svc.cases.run_history(entity_id, limit)}


@router.post("/cases/{entity_id}/run")
async def run_case(entity_id: str, svc: ServiceContainer = Depends(get_container)):
    svc.companies.require(entity_id)
    try:
        case, pipeline_log = await asyncio.to_thread(svc.cases.run, entity_id)
    except ApplicationError:
        raise
    except Exception as e:
        log.error("Pipeline failed for %s: %s", entity_id, e)
        traceback.print_exc()
        raise HTTPException(500, f"Pipeline failed: {str(e)}")
    return {"status": "completed", "entity_id": entity_id, **_run_summary(case),
            "pipeline_log": pipeline_log}


@router.get("/cases/{entity_id}/run-stream")
async def run_case_stream(entity_id: str, svc: ServiceContainer = Depends(get_container)):
    """Server-sent events: run the pipeline and stream agent/section progress."""
    svc.companies.require(entity_id)
    events: queue.Queue = queue.Queue()

    def _pipeline_thread():
        try:
            case, _ = svc.cases.run(entity_id, on_progress=events.put)
            events.put({"type": "done", "entity_id": entity_id, **_run_summary(case)})
        except Exception as e:
            events.put({"type": "error", "message": str(e)})

    threading.Thread(target=_pipeline_thread, daemon=True).start()

    async def _event_generator():
        while True:
            try:
                event = events.get_nowait()
            except queue.Empty:
                yield ": keepalive\n\n"
                await asyncio.sleep(0.3)
                continue
            yield f"data: {json.dumps(event)}\n\n"
            if event.get("type") in ("done", "error"):
                break

    return StreamingResponse(_event_generator(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@router.post("/pipeline/run-all")
async def run_all(svc: ServiceContainer = Depends(get_container)):
    results = []
    for entity_id in list(svc.state.companies):
        if svc.approvals.is_locked_for_rerun(entity_id):
            results.append({"entity_id": entity_id, "skipped": "with approving authority"})
            continue
        case, _ = svc.cases.run(entity_id)
        results.append({"entity_id": entity_id, "recommendation": case["recommendation"],
                        "risk_grade": case["risk_grade"]})
    return {"status": "completed", "results": results}
