from dataclasses import dataclass

import pytest

from app.agents.base import AgentResult, ApprovalResult
from app.agents.registry import AgentNotFound, AgentRegistry


@dataclass
class StubAgent:
    key: str = "stub"
    label: str = "Stub agent"
    description: str = "Used to verify the registry contract."

    def invoke(self, prompt: str) -> AgentResult:
        return AgentResult(
            task_name="stub_task",
            output={"summary": prompt},
            token_count=10,
            cost_usd="0.0001",
        )

    def on_approved(self, prompt: str, output: dict) -> ApprovalResult | None:
        return None


def test_registry_lists_and_resolves_registered_agent() -> None:
    registry = AgentRegistry([StubAgent()])

    assert [agent.key for agent in registry.list()] == ["stub"]
    assert registry.get("stub").label == "Stub agent"


def test_registry_rejects_duplicate_keys() -> None:
    with pytest.raises(ValueError, match="duplicate agent key"):
        AgentRegistry([StubAgent(), StubAgent()])


def test_registry_reports_unknown_agent_key() -> None:
    registry = AgentRegistry([StubAgent()])

    with pytest.raises(AgentNotFound, match="missing"):
        registry.get("missing")
