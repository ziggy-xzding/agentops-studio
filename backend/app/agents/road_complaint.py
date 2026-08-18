from decimal import Decimal
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from app.agents.base import AgentResult, ApprovalResult, WorkOrderDraft


class ComplaintState(TypedDict, total=False):
    prompt: str
    location: str
    defect_type: str
    priority: str
    response_target: str
    rule: dict[str, str]
    dispatch: dict[str, Any]
    summary: str
    needs_clarification: bool
    clarification_reason: str | None


LOCATIONS = (
    "元朗青山公路近朗屏站",
    "屯门公路近市中心",
    "元朗大马路",
    "屯门青云路",
)


RULES = {
    "道路坑洞": {
        "id": "RM-POTHOLE-01",
        "title": "大型坑洞应急处置规则",
        "citation": "合成演示规则：影响车辆正常通行的大型坑洞，应在 4 小时内围封并修补。",
    },
    "倒树阻路": {
        "id": "RM-OBSTRUCTION-02",
        "title": "道路阻塞应急清障规则",
        "citation": "合成演示规则：完全阻断交通的倒树属于 P0 事件，应在 30 分钟内响应。",
    },
    "道路积水": {
        "id": "RM-DRAINAGE-03",
        "title": "道路积水处置规则",
        "citation": "合成演示规则：影响通行的道路积水应优先设置警示并检查排水设施。",
    },
    "其他道路缺陷": {
        "id": "RM-GENERAL-01",
        "title": "一般道路缺陷巡查规则",
        "citation": "合成演示规则：信息不完整的一般缺陷应在 24 小时内完成现场复核。",
    },
}


DISPATCH = {
    "道路坑洞": {
        "crew": "路面维修班组 A",
        "materials": ["热拌沥青", "碎石", "交通锥", "临时警示牌"],
        "actions": ["现场围封", "清理坑洞", "分层填补压实", "完工拍照验收"],
    },
    "倒树阻路": {
        "crew": "应急清障班组",
        "materials": ["链锯", "吊运车辆", "交通锥", "反光警示灯"],
        "actions": ["封闭受影响车道", "切割并移除倒树", "清理路面", "恢复交通"],
    },
    "道路积水": {
        "crew": "排水维护班组",
        "materials": ["抽水泵", "疏通工具", "交通锥", "警示牌"],
        "actions": ["设置积水警示", "检查雨水口", "抽排积水", "复核排水能力"],
    },
    "其他道路缺陷": {
        "crew": "道路巡查班组",
        "materials": ["交通锥", "测量工具", "现场记录设备"],
        "actions": ["现场复核", "补充照片和尺寸", "确认缺陷分类", "重新评估派工"],
    },
}


NEGATION_MARKERS = ("没有", "未", "并无", "不是", "不存在")


def contains_asserted_term(prompt: str, terms: tuple[str, ...]) -> bool:
    for term in terms:
        start = 0
        while (index := prompt.find(term, start)) >= 0:
            prefix = prompt[max(0, index - 4) : index]
            if not any(marker in prefix for marker in NEGATION_MARKERS):
                return True
            start = index + len(term)
    return False


def extract_complaint(state: ComplaintState) -> ComplaintState:
    prompt = state["prompt"]
    location = next((item for item in LOCATIONS if item in prompt), "位置待现场确认")

    if contains_asserted_term(prompt, ("倒树", "树木倒塌")):
        defect_type = "倒树阻路"
    elif contains_asserted_term(prompt, ("坑洞", "路坑", "pothole")):
        defect_type = "道路坑洞"
    elif contains_asserted_term(prompt, ("积水", "水浸", "排水")):
        defect_type = "道路积水"
    else:
        defect_type = "其他道路缺陷"

    traffic_blocked = contains_asserted_term(prompt, ("完全阻断", "无法通行", "封路"))
    traffic_affected = contains_asserted_term(
        prompt, ("车辆需要绕行", "影响通行", "大型", "一米")
    )
    if defect_type == "倒树阻路" and traffic_blocked:
        priority, response_target = "P0", "30 分钟内响应"
    elif defect_type in {"道路坑洞", "道路积水"} and traffic_affected:
        priority, response_target = "P1", "4 小时内到场"
    else:
        priority, response_target = "P2", "24 小时内现场复核"

    clarification_reason = None
    if location == "位置待现场确认":
        clarification_reason = "缺少可派工的准确地点"
    elif defect_type == "其他道路缺陷":
        clarification_reason = "未识别到明确的道路缺陷"

    return {
        "location": location,
        "defect_type": defect_type,
        "priority": priority,
        "response_target": response_target,
        "needs_clarification": clarification_reason is not None,
        "clarification_reason": clarification_reason,
    }


def retrieve_rule(state: ComplaintState) -> ComplaintState:
    return {"rule": RULES[state["defect_type"]]}


def propose_dispatch(state: ComplaintState) -> ComplaintState:
    if state["needs_clarification"]:
        return {
            "dispatch": {
                "crew": "待分配",
                "materials": [],
                "actions": ["补充准确地点和缺陷信息", "补充信息后重新评估派工"],
            },
            "summary": (
                f"已初步识别 {state['defect_type']}，但{state['clarification_reason']}；"
                "补充信息后重新评估派工。"
            ),
        }
    dispatch = DISPATCH[state["defect_type"]]
    summary = (
        f"已识别 {state['location']} 的{state['defect_type']}，等级 {state['priority']}；"
        f"建议由{dispatch['crew']} 在 {state['response_target']}处理。"
    )
    return {"dispatch": dispatch, "summary": summary}


class RoadComplaintAgent:
    key = "road_complaint"
    label = "Road complaint triage"
    description = "Extracts road defects, retrieves synthetic rules, and proposes dispatch."
    task_name = "complaint_triage"

    def __init__(self) -> None:
        builder = StateGraph(ComplaintState)
        builder.add_node("extract_complaint", extract_complaint)
        builder.add_node("retrieve_rule", retrieve_rule)
        builder.add_node("propose_dispatch", propose_dispatch)
        builder.add_edge(START, "extract_complaint")
        builder.add_edge("extract_complaint", "retrieve_rule")
        builder.add_edge("retrieve_rule", "propose_dispatch")
        builder.add_edge("propose_dispatch", END)
        self._graph = builder.compile()

    def invoke(self, prompt: str) -> AgentResult:
        state = self._graph.invoke({"prompt": prompt})
        output = {
            "summary": state["summary"],
            "location": state["location"],
            "defect_type": state["defect_type"],
            "priority": state["priority"],
            "response_target": state["response_target"],
            "rule": state["rule"],
            "dispatch": state["dispatch"],
            "needs_clarification": state["needs_clarification"],
            "clarification_reason": state["clarification_reason"],
            "steps": ["提取投诉信息", "匹配处置规则", "生成派工建议"],
            "risk": "critical" if state["priority"] == "P0" else "elevated",
            "execution_mode": "deterministic_rules",
        }
        return AgentResult(
            task_name=self.task_name,
            output=output,
            token_count=0,
            cost_usd=Decimal("0"),
        )

    def on_approved(self, prompt: str, output: dict[str, Any]) -> ApprovalResult:
        if output["needs_clarification"]:
            return ApprovalResult(
                task_name="clarification_requested",
                audit_action="complaint.clarification_requested",
                output={
                    "status": "awaiting_information",
                    "reason": output["clarification_reason"],
                    "location": output["location"],
                },
            )
        return ApprovalResult(
            task_name="work_order_created",
            audit_action="work_order.created",
            output={
                "priority": output["priority"],
                "crew": output["dispatch"]["crew"],
                "location": output["location"],
                "defect_type": output["defect_type"],
            },
            work_order=WorkOrderDraft(
                priority=output["priority"],
                crew=output["dispatch"]["crew"],
                location=output["location"],
                defect_type=output["defect_type"],
            ),
        )
