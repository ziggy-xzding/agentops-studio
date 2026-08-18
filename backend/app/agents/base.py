from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Protocol


@dataclass(frozen=True)
class AgentResult:
    task_name: str
    output: dict[str, Any]
    token_count: int
    cost_usd: Decimal | str


@dataclass(frozen=True)
class WorkOrderDraft:
    priority: str
    crew: str
    location: str
    defect_type: str


@dataclass(frozen=True)
class ApprovalResult:
    task_name: str
    output: dict[str, Any]
    audit_action: str
    work_order: WorkOrderDraft | None = None


class AgentAdapter(Protocol):
    key: str
    label: str
    description: str
    task_name: str

    def invoke(self, prompt: str) -> AgentResult: ...

    def on_approved(self, prompt: str, output: dict[str, Any]) -> ApprovalResult | None: ...
