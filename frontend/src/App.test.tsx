import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, test, vi } from "vitest";

import App from "./App";
import type { AgentDescriptor, WorkflowRun } from "./api";


const agents: AgentDescriptor[] = [
  {
    key: "incident_response",
    label: "Incident response planner",
    description: "Prepares a deterministic plan for review.",
  },
  {
    key: "road_complaint",
    label: "Road complaint triage",
    description: "Extracts defects, retrieves rules, and proposes dispatch.",
  },
];

const waitingRun: WorkflowRun = {
  id: "run-1",
  agent_key: "incident_response",
  title: "Incident response",
  prompt: "Assess a production incident",
  state: "waiting_approval",
  attempt: 1,
  total_tokens: 840,
  total_cost_usd: "0.0017",
  created_at: "2026-08-12T08:00:00Z",
  updated_at: "2026-08-12T08:01:00Z",
  tasks: [
    {
      id: 1,
      name: "plan_response",
      status: "completed",
      attempt: 1,
      output: { summary: "Plan is ready" },
      token_count: 840,
      cost_usd: "0.0017",
      started_at: "2026-08-12T08:00:00Z",
      completed_at: "2026-08-12T08:00:10Z",
    },
    {
      id: 2,
      name: "human_approval",
      status: "waiting",
      attempt: 1,
      output: {},
      token_count: 0,
      cost_usd: "0.0000",
      started_at: "2026-08-12T08:00:10Z",
      completed_at: null,
    },
  ],
  audit_events: [
    {
      id: 1,
      action: "approval.requested",
      actor: "system",
      details: {},
      created_at: "2026-08-12T08:00:10Z",
    },
  ],
};


const complaintRun: WorkflowRun = {
  ...waitingRun,
  id: "run-complaint",
  agent_key: "road_complaint",
  title: "元朗大型坑洞投诉",
  prompt: "元朗青山公路近朗屏站发现一米宽大型坑洞，车辆需要绕行。",
  total_tokens: 1260,
  total_cost_usd: "0.0024",
  tasks: [
    {
      ...waitingRun.tasks[0],
      id: 10,
      name: "complaint_triage",
      token_count: 1260,
      cost_usd: "0.0024",
      output: {
        summary: "已识别大型坑洞并生成派工建议。",
        location: "元朗青山公路近朗屏站",
        defect_type: "道路坑洞",
        priority: "P1",
        response_target: "4 小时内到场",
        rule: {
          id: "RM-POTHOLE-01",
          title: "大型坑洞应急处置规则",
          citation: "合成演示规则：影响车辆正常通行的大型坑洞，应在 4 小时内围封并修补。",
        },
        dispatch: {
          crew: "路面维修班组 A",
          materials: ["热拌沥青", "碎石", "交通锥", "临时警示牌"],
          actions: ["现场围封", "清理坑洞", "分层填补压实", "完工拍照验收"],
        },
      },
    },
    { ...waitingRun.tasks[1], id: 11 },
  ],
};


const clarificationRun: WorkflowRun = {
  ...complaintRun,
  id: "run-clarification",
  title: "地点不完整的投诉",
  prompt: "九龙某道路有一米宽大型坑洞，车辆需要绕行。",
  tasks: complaintRun.tasks.map((task) =>
    task.name === "complaint_triage"
      ? {
          ...task,
          output: {
            ...task.output,
            location: "位置待现场确认",
            needs_clarification: true,
            clarification_reason: "缺少可派工的准确地点",
          },
        }
      : task,
  ),
};


function renderApp() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>,
  );
}


beforeEach(() => {
  vi.restoreAllMocks();
});


function mockApi(runs: WorkflowRun[], createdRun: WorkflowRun = waitingRun) {
  return vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
    const url = String(input);
    if (url === "/api/agents") {
      return new Response(JSON.stringify(agents), { status: 200 });
    }
    if (url === "/api/runs" && init?.method === "POST") {
      return new Response(JSON.stringify(createdRun), { status: 201 });
    }
    if (url === "/api/runs") {
      return new Response(JSON.stringify(runs), { status: 200 });
    }
    return new Response(JSON.stringify(runs[0] ?? createdRun), { status: 200 });
  });
}


test("shows a useful empty state", async () => {
  mockApi([]);

  renderApp();

  expect(await screen.findByText("No workflow runs yet")).toBeInTheDocument();
  expect(screen.getAllByRole("button", { name: "Create run" })).not.toHaveLength(0);
});


test("shows approval controls and submits a decision", async () => {
  const fetchMock = mockApi([waitingRun]);
  const user = userEvent.setup();

  renderApp();

  expect(
    await screen.findByRole("heading", { name: "Approval required" }),
  ).toBeInTheDocument();
  await user.type(screen.getByLabelText("Review note"), "Verified output");
  await user.click(screen.getByRole("button", { name: "Approve run" }));

  expect(fetchMock).toHaveBeenLastCalledWith(
    "/api/runs/run-1/approve",
    expect.objectContaining({ method: "POST" }),
  );
  const approveCall = fetchMock.mock.calls.at(-1);
  expect(JSON.parse(String(approveCall?.[1]?.body))).toEqual({ note: "Verified output" });
});


test("creates a run with the selected road complaint agent", async () => {
  const fetchMock = mockApi([], complaintRun);
  const user = userEvent.setup();
  renderApp();

  await screen.findByText("No workflow runs yet");
  await user.click(screen.getAllByRole("button", { name: "Create run" })[0]);
  const dialog = screen.getByRole("dialog", { name: "Create workflow run" });

  await user.selectOptions(within(dialog).getByLabelText("Agent"), "road_complaint");
  await user.type(within(dialog).getByLabelText("Run title"), "元朗大型坑洞投诉");
  await user.type(
    within(dialog).getByLabelText("Agent request"),
    "元朗青山公路近朗屏站发现一米宽大型坑洞，车辆需要绕行。",
  );
  await user.click(within(dialog).getByRole("button", { name: "Create run" }));

  const createCall = fetchMock.mock.calls.find(
    ([url, init]) => url === "/api/runs" && init?.method === "POST",
  );
  expect(JSON.parse(String(createCall?.[1]?.body))).toMatchObject({
    agent_key: "road_complaint",
  });
});


test("shows structured complaint analysis and dispatch evidence", async () => {
  mockApi([complaintRun]);
  renderApp();

  expect(await screen.findByRole("heading", { name: "Complaint analysis" })).toBeVisible();
  expect(screen.getByText("元朗青山公路近朗屏站")).toBeVisible();
  expect(screen.getByText("P1")).toBeVisible();
  expect(screen.getByText("RM-POTHOLE-01")).toBeVisible();
  expect(screen.getByText("路面维修班组 A")).toBeVisible();
  expect(screen.getByText("热拌沥青")).toBeVisible();
});


test("warns the reviewer when complaint information is insufficient", async () => {
  mockApi([clarificationRun]);
  renderApp();

  expect(await screen.findByRole("heading", { name: "More information required" })).toBeVisible();
  expect(screen.getByText("缺少可派工的准确地点")).toBeVisible();
  expect(screen.getByRole("button", { name: "Request information" })).toBeVisible();
  expect(screen.queryByText("WORK ORDER CREATED")).not.toBeInTheDocument();
});


test("falls back to generic task output when complaint evidence is malformed", async () => {
  const malformedRun: WorkflowRun = {
    ...complaintRun,
    id: "run-malformed",
    tasks: complaintRun.tasks.map((task) =>
      task.name === "complaint_triage"
        ? {
            ...task,
            output: {
              ...task.output,
              dispatch: { crew: "道路维修班组", materials: "invalid", actions: [] },
            },
          }
        : task,
    ),
  };
  mockApi([malformedRun]);
  const view = renderApp();

  expect(await within(view.container).findByRole("heading", { name: "Execution" })).toBeVisible();
  expect(
    within(view.container).queryByRole("heading", { name: "Complaint analysis" }),
  ).not.toBeInTheDocument();
});
