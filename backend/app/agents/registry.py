from collections.abc import Iterable
from functools import lru_cache

from app.agents.base import AgentAdapter


class AgentNotFound(LookupError):
    pass


class AgentRegistry:
    def __init__(self, agents: Iterable[AgentAdapter]) -> None:
        self._agents: dict[str, AgentAdapter] = {}
        for agent in agents:
            if agent.key in self._agents:
                raise ValueError(f"duplicate agent key: {agent.key}")
            self._agents[agent.key] = agent

    def get(self, key: str) -> AgentAdapter:
        try:
            return self._agents[key]
        except KeyError as exc:
            raise AgentNotFound(f"unknown agent: {key}") from exc

    def list(self) -> list[AgentAdapter]:
        return list(self._agents.values())


@lru_cache
def get_default_registry() -> AgentRegistry:
    from app.agents.incident_response import IncidentResponseAgent
    from app.agents.road_complaint import RoadComplaintAgent

    return AgentRegistry([IncidentResponseAgent(), RoadComplaintAgent()])
