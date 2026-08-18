from fastapi import APIRouter

from app.agents.registry import get_default_registry
from app.schemas import AgentRead

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("", response_model=list[AgentRead])
def list_agents() -> list[AgentRead]:
    return [
        AgentRead(key=agent.key, label=agent.label, description=agent.description)
        for agent in get_default_registry().list()
    ]
