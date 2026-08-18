export type RunState =
  | "draft"
  | "running"
  | "waiting_approval"
  | "completed"
  | "rejected"
  | "failed";

export interface AgentDescriptor {
  key: string;
  label: string;
  description: string;
}

export interface RunTask {
  id: number;
  name: string;
  status: string;
  attempt: number;
  output: Record<string, unknown>;
  token_count: number;
  cost_usd: string;
  started_at: string;
  completed_at: string | null;
}

export interface AuditEvent {
  id: number;
  action: string;
  actor: string;
  details: Record<string, unknown>;
  created_at: string;
}

export interface WorkflowRun {
  id: string;
  agent_key: string;
  title: string;
  prompt: string;
  state: RunState;
  attempt: number;
  total_tokens: number;
  total_cost_usd: string;
  created_at: string;
  updated_at: string;
  tasks: RunTask[];
  audit_events: AuditEvent[];
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail?.message ?? `Request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export const api = {
  listAgents: () => request<AgentDescriptor[]>("/api/agents"),
  listRuns: () => request<WorkflowRun[]>("/api/runs"),
  createRun: (input: { title?: string; prompt: string; agent_key: string }) =>
    request<WorkflowRun>("/api/runs", { method: "POST", body: JSON.stringify(input) }),
  executeRun: (id: string, simulateFailure = false) =>
    request<WorkflowRun>(`/api/runs/${id}/execute?simulate_failure=${simulateFailure}`, {
      method: "POST",
    }),
  approveRun: (id: string, note: string) =>
    request<WorkflowRun>(`/api/runs/${id}/approve`, {
      method: "POST",
      body: JSON.stringify({ note }),
    }),
  rejectRun: (id: string, note: string) =>
    request<WorkflowRun>(`/api/runs/${id}/reject`, {
      method: "POST",
      body: JSON.stringify({ note }),
    }),
  retryRun: (id: string) =>
    request<WorkflowRun>(`/api/runs/${id}/retry`, { method: "POST" }),
};
