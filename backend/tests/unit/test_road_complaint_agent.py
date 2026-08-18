from app.agents.road_complaint import RoadComplaintAgent


def test_large_pothole_produces_priority_one_dispatch_plan() -> None:
    agent = RoadComplaintAgent()

    result = agent.invoke(
        "元朗青山公路近朗屏站发现一米宽大型坑洞，车辆需要绕行，已有市民投诉。"
    )

    assert result.task_name == "complaint_triage"
    assert result.output["location"] == "元朗青山公路近朗屏站"
    assert result.output["defect_type"] == "道路坑洞"
    assert result.output["priority"] == "P1"
    assert result.output["response_target"] == "4 小时内到场"
    assert result.output["rule"] == {
        "id": "RM-POTHOLE-01",
        "title": "大型坑洞应急处置规则",
        "citation": "合成演示规则：影响车辆正常通行的大型坑洞，应在 4 小时内围封并修补。",
    }
    assert result.output["dispatch"]["crew"] == "路面维修班组 A"
    assert "热拌沥青" in result.output["dispatch"]["materials"]
    assert result.output["summary"] == (
        "已识别 元朗青山公路近朗屏站 的道路坑洞，等级 P1；"
        "建议由路面维修班组 A 在 4 小时内到场处理。"
    )
    assert result.output["execution_mode"] == "deterministic_rules"
    assert result.token_count == 0
    assert result.cost_usd == 0


def test_fallen_tree_blocking_traffic_is_priority_zero() -> None:
    agent = RoadComplaintAgent()

    result = agent.invoke("屯门公路近市中心有倒树完全阻断交通，车辆无法通行。")

    assert result.output["defect_type"] == "倒树阻路"
    assert result.output["priority"] == "P0"
    assert result.output["response_target"] == "30 分钟内响应"
    assert result.output["rule"]["id"] == "RM-OBSTRUCTION-02"
    assert result.output["dispatch"]["crew"] == "应急清障班组"
    assert "链锯" in result.output["dispatch"]["materials"]


def test_negated_traffic_blockage_is_not_priority_zero() -> None:
    agent = RoadComplaintAgent()

    result = agent.invoke("屯门公路近市中心有倒树，但没有完全阻断交通，车辆仍可通行。")

    assert result.output["defect_type"] == "倒树阻路"
    assert result.output["priority"] == "P2"


def test_negated_defects_require_clarification() -> None:
    agent = RoadComplaintAgent()

    result = agent.invoke("元朗大马路路面完好，没有坑洞，也没有积水。")

    assert result.output["defect_type"] == "其他道路缺陷"
    assert result.output["needs_clarification"] is True
    assert result.output["clarification_reason"] == "未识别到明确的道路缺陷"


def test_unknown_location_requests_clarification_instead_of_work_order() -> None:
    agent = RoadComplaintAgent()
    result = agent.invoke("九龙某道路有一米宽大型坑洞，车辆需要绕行。")

    assert result.output["needs_clarification"] is True
    assert result.output["clarification_reason"] == "缺少可派工的准确地点"
    assert result.output["dispatch"]["crew"] == "待分配"
    assert result.output["dispatch"]["materials"] == []
    assert "补充信息后重新评估派工" in result.output["summary"]

    approval = agent.on_approved("original complaint", result.output)

    assert approval.task_name == "clarification_requested"
    assert approval.audit_action == "complaint.clarification_requested"
    assert approval.output["status"] == "awaiting_information"


def test_approval_creates_traceable_work_order() -> None:
    agent = RoadComplaintAgent()
    result = agent.invoke(
        "元朗青山公路近朗屏站发现一米宽大型坑洞，车辆需要绕行。"
    )

    approval = agent.on_approved("original complaint", result.output)

    assert approval is not None
    assert approval.task_name == "work_order_created"
    assert approval.audit_action == "work_order.created"
    assert approval.output["priority"] == "P1"
    assert approval.output["crew"] == "路面维修班组 A"
    assert approval.work_order is not None
    assert approval.work_order.location == "元朗青山公路近朗屏站"
    assert approval.work_order.defect_type == "道路坑洞"
