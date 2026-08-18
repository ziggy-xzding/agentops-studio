import json
import time
from collections.abc import Iterator
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.db import get_session
from app.schemas import AuditEventRead, ReviewDecision, RunCreate, RunRead
from app.services.runs import RunService

router = APIRouter(prefix="/runs", tags=["runs"])
LOCAL_DEMO_REVIEWER = "local-demo-reviewer"


SessionDependency = Annotated[Session, Depends(get_session)]


def get_service(session: SessionDependency) -> RunService:
    return RunService(session)


ServiceDependency = Annotated[RunService, Depends(get_service)]


@router.get("", response_model=list[RunRead])
def list_runs(service: ServiceDependency):
    return service.list_runs()


@router.post("", response_model=RunRead, status_code=201)
def create_run(payload: RunCreate, service: ServiceDependency):
    return service.create_run(
        payload.prompt,
        title=payload.title,
        agent_key=payload.agent_key,
    )


@router.get("/{run_id}", response_model=RunRead)
def get_run(run_id: str, service: ServiceDependency):
    return service.get_run(run_id)


@router.post("/{run_id}/execute", response_model=RunRead)
def execute_run(
    run_id: str,
    service: ServiceDependency,
    simulate_failure: Annotated[bool, Query()] = False,
):
    return service.execute(run_id, simulate_failure=simulate_failure)


@router.post("/{run_id}/approve", response_model=RunRead)
def approve_run(
    run_id: str,
    payload: ReviewDecision,
    service: ServiceDependency,
):
    return service.approve(run_id, actor=LOCAL_DEMO_REVIEWER, note=payload.note)


@router.post("/{run_id}/reject", response_model=RunRead)
def reject_run(
    run_id: str,
    payload: ReviewDecision,
    service: ServiceDependency,
):
    return service.reject(run_id, actor=LOCAL_DEMO_REVIEWER, note=payload.note)


@router.post("/{run_id}/retry", response_model=RunRead)
def retry_run(run_id: str, service: ServiceDependency):
    return service.retry(run_id)


@router.get("/{run_id}/events")
def stream_events(
    run_id: str,
    service: ServiceDependency,
    follow: Annotated[bool, Query()] = True,
) -> StreamingResponse:
    service.get_run(run_id)

    def generate() -> Iterator[str]:
        sent_ids: set[int] = set()
        while True:
            run = service.get_run(run_id)
            for event in run.audit_events:
                if event.id not in sent_ids:
                    payload = AuditEventRead.model_validate(event).model_dump(mode="json")
                    yield f"event: audit\ndata: {json.dumps(payload)}\n\n"
                    sent_ids.add(event.id)
            if not follow:
                return
            yield ": heartbeat\n\n"
            time.sleep(2)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
