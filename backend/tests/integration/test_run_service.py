from decimal import Decimal

import pytest
from sqlalchemy import inspect

from app.agents.registry import AgentNotFound
from app.domain.runs import InvalidTransition, RunState
from app.services.runs import RunService


def test_execute_pauses_for_approval_and_records_usage(session) -> None:
    service = RunService(session)
    run = service.create_run("Assess a production incident")

    run = service.execute(run.id)

    assert run.state == RunState.WAITING_APPROVAL
    assert [task.name for task in run.tasks] == ["plan_response", "human_approval"]
    assert [task.status for task in run.tasks] == ["completed", "waiting"]
    assert run.total_tokens == 840
    assert run.total_cost_usd == Decimal("0.0017")
    assert [event.action for event in run.audit_events] == [
        "run.created",
        "run.started",
        "task.completed",
        "approval.requested",
    ]


def test_approve_completes_waiting_run(session) -> None:
    service = RunService(session)
    run = service.create_run("Prepare a customer response")
    service.execute(run.id)

    run = service.approve(run.id, actor="reviewer@example.com", note="Looks good")

    assert run.state == RunState.COMPLETED
    assert run.tasks[-1].status == "completed"
    assert run.audit_events[-1].actor == "reviewer@example.com"
    assert run.audit_events[-1].details["note"] == "Looks good"


def test_reject_stores_review_note(session) -> None:
    service = RunService(session)
    run = service.create_run("Draft a risky database migration")
    service.execute(run.id)

    run = service.reject(run.id, actor="on-call", note="Missing rollback steps")

    assert run.state == RunState.REJECTED
    assert run.tasks[-1].status == "rejected"
    assert run.audit_events[-1].details["note"] == "Missing rollback steps"


def test_failed_run_can_retry(session) -> None:
    service = RunService(session)
    run = service.create_run("Demonstrate retry behavior")
    service.execute(run.id, simulate_failure=True)

    assert run.state == RunState.FAILED
    assert run.attempt == 1
    assert run.tasks[-1].status == "failed"

    run = service.retry(run.id)

    assert run.state == RunState.WAITING_APPROVAL
    assert run.attempt == 2
    assert run.tasks[-1].status == "waiting"
    assert any(event.action == "run.retried" for event in run.audit_events)


def test_invalid_service_transition_is_rejected(session) -> None:
    service = RunService(session)
    run = service.create_run("Cannot approve a draft")

    with pytest.raises(InvalidTransition):
        service.approve(run.id, actor="reviewer", note="Too early")


def test_road_complaint_agent_creates_work_order_after_approval(session) -> None:
    service = RunService(session)
    run = service.create_run(
        "元朗青山公路近朗屏站发现一米宽大型坑洞，车辆需要绕行。",
        agent_key="road_complaint",
    )

    run = service.execute(run.id)

    assert run.agent_key == "road_complaint"
    assert [task.name for task in run.tasks] == ["complaint_triage", "human_approval"]
    assert run.tasks[0].output["priority"] == "P1"
    assert run.tasks[0].output["rule"]["id"] == "RM-POTHOLE-01"
    assert run.total_tokens == 0
    assert run.total_cost_usd == Decimal("0")

    run = service.approve(run.id, actor="dispatcher", note="派工方案已核实")

    assert run.state == RunState.COMPLETED
    assert run.tasks[-1].name == "work_order_created"
    assert run.tasks[-1].output["status"] == "created"
    assert run.tasks[-1].output["work_order_id"].startswith("WO-")
    assert run.audit_events[-1].action == "work_order.created"


def test_identical_complaints_create_distinct_persisted_work_orders(session) -> None:
    service = RunService(session)
    prompt = "元朗青山公路近朗屏站发现一米宽大型坑洞，车辆需要绕行。"

    work_order_ids = []
    for title in ("首次投诉", "后续投诉"):
        run = service.create_run(prompt, title=title, agent_key="road_complaint")
        service.execute(run.id)
        approved = service.approve(run.id, actor="dispatcher", note="派工方案已核实")
        work_order_ids.append(approved.tasks[-1].output["work_order_id"])

    assert "work_orders" in inspect(session.get_bind()).get_table_names()
    assert len(set(work_order_ids)) == 2
    assert [item.id for item in service.list_work_orders()] == list(reversed(work_order_ids))


def test_clarification_request_does_not_persist_work_order(session) -> None:
    service = RunService(session)
    run = service.create_run(
        "九龙某道路有一米宽大型坑洞，车辆需要绕行。",
        agent_key="road_complaint",
    )
    service.execute(run.id)

    approved = service.approve(run.id, actor="dispatcher", note="请补充准确位置")

    assert approved.tasks[-1].name == "clarification_requested"
    assert service.list_work_orders() == []


def test_rejected_complaint_does_not_create_work_order(session) -> None:
    service = RunService(session)
    run = service.create_run("元朗大马路发现坑洞。", agent_key="road_complaint")
    service.execute(run.id)

    run = service.reject(run.id, actor="dispatcher", note="需要补充现场照片")

    assert run.state == RunState.REJECTED
    assert all(task.name != "work_order_created" for task in run.tasks)


def test_create_run_rejects_unknown_agent(session) -> None:
    service = RunService(session)

    with pytest.raises(AgentNotFound, match="missing"):
        service.create_run("Handle this", agent_key="missing")
