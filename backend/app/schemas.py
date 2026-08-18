from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_serializer


class ApiModel(BaseModel):
    @field_serializer("*", when_used="json", check_fields=False)
    def serialize_utc(self, value):
        if isinstance(value, datetime):
            normalized = (
                value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
            )
            return normalized.isoformat().replace("+00:00", "Z")
        return value


class RunCreate(ApiModel):
    prompt: str = Field(min_length=3, max_length=4000)
    title: str | None = Field(default=None, min_length=3, max_length=160)
    agent_key: str = Field(default="incident_response", min_length=2, max_length=64)


class AgentRead(ApiModel):
    key: str
    label: str
    description: str


class ReviewDecision(ApiModel):
    note: str = Field(min_length=2, max_length=1000)


class TaskRead(ApiModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    status: str
    attempt: int
    output: dict[str, Any]
    token_count: int
    cost_usd: Decimal
    started_at: datetime
    completed_at: datetime | None


class AuditEventRead(ApiModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    action: str
    actor: str
    details: dict[str, Any]
    created_at: datetime


class WorkOrderRead(ApiModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    run_id: str
    status: str
    priority: str
    crew: str
    location: str
    defect_type: str
    created_at: datetime
    updated_at: datetime


class RunRead(ApiModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    agent_key: str
    title: str
    prompt: str
    state: str
    attempt: int
    total_tokens: int
    total_cost_usd: Decimal
    created_at: datetime
    updated_at: datetime
    tasks: list[TaskRead]
    audit_events: list[AuditEventRead]
