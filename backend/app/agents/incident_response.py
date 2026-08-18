from decimal import Decimal
from typing import Any

from app.agents.base import AgentResult, ApprovalResult
from app.graph import AgentGraph


class IncidentResponseAgent:
    key = "incident_response"
    label = "Incident response planner"
    description = "Analyzes a request and prepares a deterministic plan for review."
    task_name = "plan_response"

    def __init__(self) -> None:
        self._graph = AgentGraph()

    def invoke(self, prompt: str) -> AgentResult:
        result = self._graph.invoke(prompt)
        return AgentResult(
            task_name=self.task_name,
            output={
                "summary": result["summary"],
                "steps": result["steps"],
                "risk": result["risk"],
            },
            token_count=result["token_count"],
            cost_usd=Decimal("0.0017"),
        )

    def on_approved(self, prompt: str, output: dict[str, Any]) -> ApprovalResult | None:
        return None
