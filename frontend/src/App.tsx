import { FormEvent, useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Activity,
  AlertCircle,
  BookOpen,
  Check,
  CheckCircle2,
  ChevronRight,
  CircleDollarSign,
  Clock3,
  GitBranch,
  ListChecks,
  LoaderCircle,
  MapPin,
  Play,
  Plus,
  RefreshCw,
  RotateCcw,
  ShieldCheck,
  Sparkles,
  Timer,
  Users,
  Wrench,
  X,
  XCircle,
  Zap,
} from "lucide-react";

import { AgentDescriptor, api, RunState, WorkflowRun } from "./api";
import "./styles.css";


const stateLabel: Record<RunState, string> = {
  draft: "Draft",
  running: "Running",
  waiting_approval: "Approval required",
  completed: "Completed",
  rejected: "Rejected",
  failed: "Failed",
};


interface ComplaintOutput extends Record<string, unknown> {
  summary: string;
  location: string;
  defect_type: string;
  priority: string;
  response_target: string;
  rule: { id: string; title: string; citation: string };
  dispatch: { crew: string; materials: string[]; actions: string[] };
  needs_clarification?: boolean;
  clarification_reason?: string | null;
}


function isComplaintOutput(output: Record<string, unknown>): output is ComplaintOutput {
  const rule = output.rule;
  const dispatch = output.dispatch;
  return (
    typeof output.summary === "string" &&
    typeof output.location === "string" &&
    typeof output.defect_type === "string" &&
    typeof output.priority === "string" &&
    typeof output.response_target === "string" &&
    typeof rule === "object" &&
    rule !== null &&
    typeof (rule as Record<string, unknown>).id === "string" &&
    typeof (rule as Record<string, unknown>).title === "string" &&
    typeof (rule as Record<string, unknown>).citation === "string" &&
    typeof dispatch === "object" &&
    dispatch !== null &&
    typeof (dispatch as Record<string, unknown>).crew === "string" &&
    Array.isArray((dispatch as Record<string, unknown>).materials) &&
    ((dispatch as Record<string, unknown>).materials as unknown[]).every(
      (item) => typeof item === "string",
    ) &&
    Array.isArray((dispatch as Record<string, unknown>).actions) &&
    ((dispatch as Record<string, unknown>).actions as unknown[]).every(
      (item) => typeof item === "string",
    ) &&
    (output.needs_clarification === undefined ||
      typeof output.needs_clarification === "boolean") &&
    (output.clarification_reason === undefined ||
      output.clarification_reason === null ||
      typeof output.clarification_reason === "string")
  );
}


function formatTime(value: string) {
  return new Intl.DateTimeFormat("en", {
    hour: "2-digit",
    minute: "2-digit",
    month: "short",
    day: "numeric",
  }).format(new Date(value));
}


function StatusIcon({ state }: { state: RunState }) {
  if (state === "completed") return <CheckCircle2 size={16} />;
  if (state === "failed" || state === "rejected") return <XCircle size={16} />;
  if (state === "running") return <LoaderCircle className="spin" size={16} />;
  if (state === "waiting_approval") return <ShieldCheck size={16} />;
  return <Clock3 size={16} />;
}


function App() {
  const queryClient = useQueryClient();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [reviewNote, setReviewNote] = useState("");
  const [error, setError] = useState<string | null>(null);

  const runsQuery = useQuery({ queryKey: ["runs"], queryFn: api.listRuns });
  const agentsQuery = useQuery({ queryKey: ["agents"], queryFn: api.listAgents });
  const runs = runsQuery.data ?? [];
  const selected = runs.find((run) => run.id === selectedId) ?? runs[0] ?? null;

  useEffect(() => {
    if (!selected || typeof EventSource === "undefined") return;
    const stream = new EventSource(`/api/runs/${selected.id}/events`);
    stream.addEventListener("audit", () => queryClient.invalidateQueries({ queryKey: ["runs"] }));
    return () => stream.close();
  }, [queryClient, selected?.id]);

  const updateRun = (run: WorkflowRun) => {
    queryClient.setQueryData<WorkflowRun[]>(["runs"], (current = []) =>
      current.map((item) => (item.id === run.id ? run : item)),
    );
    setError(null);
  };

  const runAction = useMutation({
    mutationFn: ({ action, run }: { action: string; run: WorkflowRun }) => {
      if (action === "execute") return api.executeRun(run.id);
      if (action === "fail") return api.executeRun(run.id, true);
      if (action === "retry") return api.retryRun(run.id);
      if (action === "approve") return api.approveRun(run.id, reviewNote);
      return api.rejectRun(run.id, reviewNote);
    },
    onSuccess: (run) => {
      updateRun(run);
      setReviewNote("");
    },
    onError: (cause: Error) => setError(cause.message),
  });

  const totals = useMemo(
    () => ({
      active: runs.filter((run) => ["running", "waiting_approval"].includes(run.state)).length,
      approvals: runs.filter((run) => run.state === "waiting_approval").length,
      tokens: runs.reduce((sum, run) => sum + run.total_tokens, 0),
      cost: runs.reduce((sum, run) => sum + Number(run.total_cost_usd), 0),
    }),
    [runs],
  );

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand"><span className="brand-mark"><GitBranch size={18} /></span><span>AgentOps</span></div>
        <nav aria-label="Primary navigation">
          <button className="nav-item active"><Activity size={17} /><span>Runs</span></button>
          <button className="nav-item"><ListChecks size={17} /><span>Workflows</span></button>
          <button className="nav-item"><CircleDollarSign size={17} /><span>Usage</span></button>
        </nav>
        <div className="environment"><span className="live-dot" />Local environment</div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <div>
            <p className="eyebrow">OPERATIONS / WORKFLOW RUNS</p>
            <h1>Run control</h1>
          </div>
          <div className="header-actions">
            <button className="icon-button" title="Refresh runs" aria-label="Refresh runs" onClick={() => runsQuery.refetch()}><RefreshCw size={17} /></button>
            <button className="primary-button" onClick={() => setShowCreate(true)}><Plus size={17} />Create run</button>
          </div>
        </header>

        <section className="metrics" aria-label="Run metrics">
          <Metric label="Active runs" value={totals.active.toString()} icon={<Zap size={17} />} />
          <Metric label="Awaiting review" value={totals.approvals.toString()} icon={<ShieldCheck size={17} />} warn={totals.approvals > 0} />
          <Metric label="Tokens used" value={totals.tokens.toLocaleString()} icon={<Sparkles size={17} />} />
          <Metric label="Total cost" value={`$${totals.cost.toFixed(4)}`} icon={<CircleDollarSign size={17} />} />
        </section>

        {error && <div className="error-banner"><AlertCircle size={16} />{error}<button aria-label="Dismiss error" onClick={() => setError(null)}><X size={15} /></button></div>}

        {runsQuery.isLoading ? (
          <div className="loading-state"><LoaderCircle className="spin" size={22} />Loading runs</div>
        ) : runs.length === 0 ? (
          <EmptyState onCreate={() => setShowCreate(true)} />
        ) : (
          <div className="workspace-grid">
            <section className="run-list-panel">
              <div className="panel-heading"><div><h2>Recent runs</h2><span>{runs.length} total</span></div></div>
              <div className="run-list">
                {runs.map((run) => (
                  <button key={run.id} className={`run-row ${selected?.id === run.id ? "selected" : ""}`} onClick={() => setSelectedId(run.id)}>
                    <span className={`status-icon status-${run.state}`}><StatusIcon state={run.state} /></span>
                    <span className="run-row-content"><strong>{run.title}</strong><small>{formatTime(run.created_at)} · Attempt {run.attempt || 0}</small></span>
                    <span className={`state-pill state-${run.state}`}>{stateLabel[run.state]}</span>
                    <ChevronRight size={16} className="chevron" />
                  </button>
                ))}
              </div>
            </section>

            {selected && <RunDetail run={selected} note={reviewNote} setNote={setReviewNote} pending={runAction.isPending} act={(action) => runAction.mutate({ action, run: selected })} />}
          </div>
        )}
      </main>

      {showCreate && <CreateDialog agents={agentsQuery.data ?? []} onClose={() => setShowCreate(false)} onCreated={(run) => { queryClient.setQueryData<WorkflowRun[]>(["runs"], (old = []) => [run, ...old]); setSelectedId(run.id); setShowCreate(false); }} />}
    </div>
  );
}


function Metric({ label, value, icon, warn = false }: { label: string; value: string; icon: React.ReactNode; warn?: boolean }) {
  return <div className={`metric ${warn ? "metric-warn" : ""}`}><div className="metric-label"><span>{icon}</span>{label}</div><strong>{value}</strong></div>;
}


function EmptyState({ onCreate }: { onCreate: () => void }) {
  return <section className="empty-state"><div className="empty-icon"><GitBranch size={26} /></div><h2>No workflow runs yet</h2><p>Create a run to inspect task execution, approval gates, retries, and token cost.</p><button className="primary-button" onClick={onCreate}><Plus size={17} />Create run</button></section>;
}


function RunDetail({ run, note, setNote, pending, act }: { run: WorkflowRun; note: string; setNote: (value: string) => void; pending: boolean; act: (action: string) => void }) {
  const complaintTask = run.tasks.find((task) => task.name === "complaint_triage");
  const complaint = complaintTask && isComplaintOutput(complaintTask.output)
    ? complaintTask.output
    : null;
  const workOrder = run.tasks.find((task) => task.name === "work_order_created");
  const needsClarification = complaint?.needs_clarification === true;

  return (
    <section className="detail-panel">
      <div className="detail-header">
        <div><span className={`state-pill state-${run.state}`}><StatusIcon state={run.state} />{stateLabel[run.state]}</span><h2>{run.title}</h2><p>{run.prompt}</p></div>
        {run.state === "draft" && <div className="detail-actions"><button className="secondary-button" disabled={pending} onClick={() => act("fail")}><AlertCircle size={16} />Simulate failure</button><button className="primary-button" disabled={pending} onClick={() => act("execute")}><Play size={16} />Run workflow</button></div>}
        {run.state === "failed" && <button className="primary-button" disabled={pending} onClick={() => act("retry")}><RotateCcw size={16} />Retry run</button>}
      </div>

      <div className="detail-stats"><span><strong>{run.attempt}</strong>Attempts</span><span><strong>{run.total_tokens.toLocaleString()}</strong>Tokens</span><span><strong>${Number(run.total_cost_usd).toFixed(4)}</strong>Cost</span></div>

      {complaint && <ComplaintAnalysis output={complaint} />}
      {workOrder && <WorkOrderResult output={workOrder.output} />}

      {run.state === "waiting_approval" && (
        <section className="approval-box">
          <div className="approval-title"><span><ShieldCheck size={18} /></span><div><h3>{needsClarification ? "Review clarification request" : "Approval required"}</h3><p>{needsClarification ? "Confirm that the complaint should return for missing information." : "Review the generated plan before the workflow can complete."}</p></div></div>
          <label htmlFor="review-note">Review note</label>
          <textarea id="review-note" value={note} onChange={(event) => setNote(event.target.value)} placeholder="Record the reason for this decision" />
          <div className="approval-actions"><button className="secondary-button danger" disabled={pending || note.trim().length < 2} onClick={() => act("reject")}><X size={16} />Reject run</button><button className="primary-button" disabled={pending || note.trim().length < 2} onClick={() => act("approve")}><Check size={16} />{needsClarification ? "Request information" : "Approve run"}</button></div>
        </section>
      )}

      <section className="detail-section"><div className="section-title"><h3>Execution</h3><span>{run.tasks.length} tasks</span></div>{run.tasks.length === 0 ? <p className="muted">This run has not started.</p> : <div className="task-list">{run.tasks.map((task, index) => <div className="task-row" key={task.id}><div className={`task-node task-${task.status}`}>{task.status === "completed" ? <Check size={14} /> : task.status === "failed" ? <X size={14} /> : <span>{index + 1}</span>}</div><div><strong>{task.name.replaceAll("_", " ")}</strong><small>Attempt {task.attempt} · {task.token_count.toLocaleString()} tokens · ${Number(task.cost_usd).toFixed(4)}</small>{typeof task.output.summary === "string" && <p>{task.output.summary}</p>}</div><span className={`task-status task-${task.status}`}>{task.status}</span></div>)}</div>}</section>

      <section className="detail-section"><div className="section-title"><h3>Audit log</h3><span>Immutable history</span></div><div className="audit-list">{[...run.audit_events].reverse().map((event) => <div className="audit-row" key={event.id}><span className="audit-dot" /><div><strong>{event.action.replaceAll(".", " ")}</strong><small>{event.actor} · {formatTime(event.created_at)}</small></div></div>)}</div></section>
    </section>
  );
}


function ComplaintAnalysis({ output }: { output: ComplaintOutput }) {
  return (
    <section className="complaint-analysis">
      <div className="section-title">
        <div><p className="eyebrow">ROAD OPERATIONS</p><h3>Complaint analysis</h3></div>
        <span className={`priority-badge priority-${output.priority.toLowerCase()}`}>{output.priority}</span>
      </div>
      <div className="complaint-facts">
        <div><MapPin size={16} /><span><small>Location</small><strong>{output.location}</strong></span></div>
        <div><AlertCircle size={16} /><span><small>Defect</small><strong>{output.defect_type}</strong></span></div>
        <div><Timer size={16} /><span><small>Response target</small><strong>{output.response_target}</strong></span></div>
        <div><Users size={16} /><span><small>Assigned crew</small><strong>{output.dispatch.crew}</strong></span></div>
      </div>
      {output.needs_clarification && (
        <div className="clarification-notice">
          <AlertCircle size={17} />
          <div><h4>More information required</h4><p>{output.clarification_reason}</p></div>
        </div>
      )}
      <div className="rule-evidence">
        <BookOpen size={17} />
        <div><div className="rule-heading"><strong>{output.rule.title}</strong><code>{output.rule.id}</code></div><p>{output.rule.citation}</p></div>
      </div>
      <div className="dispatch-details">
        <div><h4><Wrench size={15} />Materials</h4><div className="material-list">{output.dispatch.materials.map((material) => <span key={material}>{material}</span>)}</div></div>
        <div><h4><ListChecks size={15} />Recommended actions</h4><ol>{output.dispatch.actions.map((action) => <li key={action}>{action}</li>)}</ol></div>
      </div>
    </section>
  );
}


function WorkOrderResult({ output }: { output: Record<string, unknown> }) {
  return (
    <section className="work-order-result">
      <CheckCircle2 size={18} />
      <div><p className="eyebrow">WORK ORDER CREATED</p><strong>{String(output.work_order_id)}</strong><span>{String(output.crew)} · {String(output.status)}</span></div>
    </section>
  );
}


function CreateDialog({ agents, onClose, onCreated }: { agents: AgentDescriptor[]; onClose: () => void; onCreated: (run: WorkflowRun) => void }) {
  const [title, setTitle] = useState("");
  const [prompt, setPrompt] = useState("");
  const [agentKey, setAgentKey] = useState("incident_response");
  const selectedAgent = agents.find((agent) => agent.key === agentKey);
  const mutation = useMutation({ mutationFn: api.createRun, onSuccess: onCreated });
  const submit = (event: FormEvent) => { event.preventDefault(); mutation.mutate({ title: title.trim() || undefined, prompt, agent_key: agentKey }); };
  return <div className="dialog-backdrop" role="presentation"><section className="dialog" role="dialog" aria-modal="true" aria-labelledby="create-title"><div className="dialog-header"><div><p className="eyebrow">NEW EXECUTION</p><h2 id="create-title">Create workflow run</h2></div><button className="icon-button" aria-label="Close dialog" onClick={onClose}><X size={18} /></button></div><form onSubmit={submit}><label htmlFor="agent-key">Agent</label><select id="agent-key" value={agentKey} onChange={(event) => setAgentKey(event.target.value)}>{agents.map((agent) => <option key={agent.key} value={agent.key}>{agent.label}</option>)}</select>{selectedAgent && <p className="agent-description">{selectedAgent.description}</p>}<label htmlFor="run-title">Run title</label><input id="run-title" value={title} onChange={(event) => setTitle(event.target.value)} placeholder="Incident response review" /><label htmlFor="run-prompt">Agent request</label><textarea id="run-prompt" required minLength={3} value={prompt} onChange={(event) => setPrompt(event.target.value)} placeholder={agentKey === "road_complaint" ? "Describe the road location, defect, size, and traffic impact." : "Assess the incident, prepare a response plan, and request human approval."} />{mutation.error && <p className="form-error">{mutation.error.message}</p>}<div className="dialog-actions"><button type="button" className="secondary-button" onClick={onClose}>Cancel</button><button className="primary-button" disabled={mutation.isPending || prompt.trim().length < 3}><Plus size={16} />Create run</button></div></form></section></div>;
}

export default App;
