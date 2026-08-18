from app.graph import AgentGraph


def test_graph_builds_reviewable_plan() -> None:
    result = AgentGraph().invoke("Assess an elevated API error rate")

    assert result["summary"] == "A deterministic execution plan is ready for human review."
    assert result["steps"] == ["Inspect request", "Assess risk", "Prepare response"]
    assert result["requires_approval"] is True
    assert result["token_count"] == 840
