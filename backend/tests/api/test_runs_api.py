import json

from fastapi.testclient import TestClient


def test_health(client: TestClient) -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_run_lifecycle(client: TestClient) -> None:
    created = client.post(
        "/api/runs",
        json={"title": "Incident response", "prompt": "Assess a production incident"},
    )
    assert created.status_code == 201
    run_id = created.json()["id"]
    assert created.json()["state"] == "draft"
    assert created.json()["created_at"].endswith("Z")
    assert created.json()["audit_events"][0]["created_at"].endswith("Z")

    executed = client.post(f"/api/runs/{run_id}/execute")
    assert executed.status_code == 200
    assert executed.json()["state"] == "waiting_approval"
    assert executed.json()["total_tokens"] == 840
    assert all(event["created_at"].endswith("Z") for event in executed.json()["audit_events"])

    approved = client.post(
        f"/api/runs/{run_id}/approve",
        json={"actor": "reviewer@example.com", "note": "Approved for demo"},
    )
    assert approved.status_code == 200
    assert approved.json()["state"] == "completed"
    assert approved.json()["audit_events"][-1]["action"] == "approval.approved"
    assert approved.json()["audit_events"][-1]["actor"] == "local-demo-reviewer"


def test_reject_requires_review_note(client: TestClient) -> None:
    run_id = client.post("/api/runs", json={"prompt": "Review this"}).json()["id"]
    client.post(f"/api/runs/{run_id}/execute")

    response = client.post(
        f"/api/runs/{run_id}/reject",
        json={"actor": "reviewer", "note": ""},
    )

    assert response.status_code == 422


def test_invalid_transition_returns_conflict(client: TestClient) -> None:
    run_id = client.post("/api/runs", json={"prompt": "Draft run"}).json()["id"]

    response = client.post(
        f"/api/runs/{run_id}/approve",
        json={"actor": "reviewer", "note": "Too early"},
    )

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "invalid_transition"


def test_missing_run_returns_not_found(client: TestClient) -> None:
    response = client.get("/api/runs/missing")

    assert response.status_code == 404


def test_failed_run_can_retry_via_api(client: TestClient) -> None:
    run_id = client.post("/api/runs", json={"prompt": "Retry demo"}).json()["id"]
    failed = client.post(f"/api/runs/{run_id}/execute?simulate_failure=true")
    assert failed.json()["state"] == "failed"

    retried = client.post(f"/api/runs/{run_id}/retry")

    assert retried.status_code == 200
    assert retried.json()["state"] == "waiting_approval"
    assert retried.json()["attempt"] == 2


def test_event_stream_serializes_audit_history(client: TestClient) -> None:
    run_id = client.post("/api/runs", json={"prompt": "Stream demo"}).json()["id"]
    client.post(f"/api/runs/{run_id}/execute")

    response = client.get(f"/api/runs/{run_id}/events?follow=false")

    assert response.status_code == 200
    events = [
        json.loads(line.removeprefix("data: "))
        for line in response.text.splitlines()
        if line.startswith("data: ")
    ]
    assert events[-1]["action"] == "approval.requested"


def test_agent_catalog_lists_available_agents(client: TestClient) -> None:
    response = client.get("/api/agents")

    assert response.status_code == 200
    assert [agent["key"] for agent in response.json()] == [
        "incident_response",
        "road_complaint",
    ]


def test_road_complaint_lifecycle_via_api(client: TestClient) -> None:
    created = client.post(
        "/api/runs",
        json={
            "title": "元朗大型坑洞投诉",
            "agent_key": "road_complaint",
            "prompt": "元朗青山公路近朗屏站发现一米宽大型坑洞，车辆需要绕行。",
        },
    )
    assert created.status_code == 201
    assert created.json()["agent_key"] == "road_complaint"

    run_id = created.json()["id"]
    executed = client.post(f"/api/runs/{run_id}/execute")

    assert executed.status_code == 200
    assert executed.json()["tasks"][0]["name"] == "complaint_triage"
    assert executed.json()["tasks"][0]["output"]["priority"] == "P1"
    assert executed.json()["total_tokens"] == 0
    assert executed.json()["total_cost_usd"] == "0.0000"

    approved = client.post(
        f"/api/runs/{run_id}/approve",
        json={"actor": "dispatcher", "note": "派工方案已核实"},
    )
    assert approved.status_code == 200
    assert approved.json()["tasks"][-1]["name"] == "work_order_created"
    assert approved.json()["audit_events"][-2]["actor"] == "local-demo-reviewer"

    work_order_id = approved.json()["tasks"][-1]["output"]["work_order_id"]
    listed = client.get("/api/work-orders")
    detail = client.get(f"/api/work-orders/{work_order_id}")

    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [work_order_id]
    assert detail.status_code == 200
    assert detail.json()["run_id"] == run_id
    assert detail.json()["status"] == "created"


def test_missing_work_order_returns_not_found(client: TestClient) -> None:
    response = client.get("/api/work-orders/WO-missing")

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "work_order_not_found"


def test_create_run_rejects_unknown_agent_key(client: TestClient) -> None:
    response = client.post(
        "/api/runs",
        json={"agent_key": "missing", "prompt": "Handle this"},
    )

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "agent_not_found"
