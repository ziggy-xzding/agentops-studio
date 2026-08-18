from typing import TypedDict

from langgraph.graph import END, START, StateGraph


class AgentState(TypedDict, total=False):
    prompt: str
    risk: str
    summary: str
    steps: list[str]
    requires_approval: bool
    token_count: int


def analyze_request(state: AgentState) -> AgentState:
    prompt = state["prompt"].lower()
    elevated_terms = ("production", "database", "incident", "customer")
    return {"risk": "elevated" if any(term in prompt for term in elevated_terms) else "standard"}


def prepare_plan(state: AgentState) -> AgentState:
    return {
        "summary": "A deterministic execution plan is ready for human review.",
        "steps": ["Inspect request", "Assess risk", "Prepare response"],
        "requires_approval": True,
        "token_count": 840,
    }


class AgentGraph:
    def __init__(self) -> None:
        builder = StateGraph(AgentState)
        builder.add_node("analyze_request", analyze_request)
        builder.add_node("prepare_plan", prepare_plan)
        builder.add_edge(START, "analyze_request")
        builder.add_edge("analyze_request", "prepare_plan")
        builder.add_edge("prepare_plan", END)
        self._graph = builder.compile()

    def invoke(self, prompt: str) -> AgentState:
        return self._graph.invoke({"prompt": prompt})
