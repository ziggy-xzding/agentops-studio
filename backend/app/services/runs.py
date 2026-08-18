from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.agents.registry import AgentRegistry, get_default_registry
from app.domain.runs import RunAction, RunState, transition_run
from app.models import AuditEvent, RunTask, WorkflowRun, WorkOrder


class RunNotFound(LookupError):
    pass


class WorkOrderNotFound(LookupError):
    pass


class RunService:
    def __init__(self, session: Session, registry: AgentRegistry | None = None) -> None:
        self.session = session
        self.registry = registry or get_default_registry()

    def create_run(
        self,
        prompt: str,
        title: str | None = None,
        agent_key: str = "incident_response",
    ) -> WorkflowRun:
        self.registry.get(agent_key)
        run = WorkflowRun(
            agent_key=agent_key,
            title=title or self._title_from_prompt(prompt),
            prompt=prompt,
            state=RunState.DRAFT.value,
        )
        run.audit_events.append(AuditEvent(action="run.created", actor="user"))
        self.session.add(run)
        self._commit()
        return self.get_run(run.id)

    def list_runs(self) -> list[WorkflowRun]:
        statement = (
            select(WorkflowRun)
            .options(selectinload(WorkflowRun.tasks), selectinload(WorkflowRun.audit_events))
            .order_by(WorkflowRun.created_at.desc())
        )
        return list(self.session.scalars(statement).all())

    def get_run(self, run_id: str) -> WorkflowRun:
        statement = (
            select(WorkflowRun)
            .where(WorkflowRun.id == run_id)
            .options(selectinload(WorkflowRun.tasks), selectinload(WorkflowRun.audit_events))
        )
        run = self.session.scalar(statement)
        if run is None:
            raise RunNotFound(run_id)
        return run

    def list_work_orders(self) -> list[WorkOrder]:
        statement = select(WorkOrder).order_by(WorkOrder.created_at.desc())
        return list(self.session.scalars(statement).all())

    def get_work_order(self, work_order_id: str) -> WorkOrder:
        work_order = self.session.get(WorkOrder, work_order_id)
        if work_order is None:
            raise WorkOrderNotFound(work_order_id)
        return work_order

    def execute(self, run_id: str, *, simulate_failure: bool = False) -> WorkflowRun:
        run = self.get_run(run_id)
        run.state = transition_run(RunState(run.state), RunAction.START).value
        run.attempt += 1
        self._audit(run, "run.started", details={"attempt": run.attempt})
        self._execute_attempt(run, simulate_failure=simulate_failure)
        self._commit()
        return self.get_run(run_id)

    def approve(self, run_id: str, *, actor: str, note: str) -> WorkflowRun:
        run = self.get_run(run_id)
        run.state = transition_run(RunState(run.state), RunAction.APPROVE).value
        approval = self._waiting_approval_task(run)
        approval.status = "completed"
        approval.completed_at = datetime.now(UTC)
        approval.output = {"decision": "approved", "note": note}
        self._audit(run, "approval.approved", actor=actor, details={"note": note})
        agent = self.registry.get(run.agent_key)
        source_output = next(
            task.output for task in reversed(run.tasks) if task.name != "human_approval"
        )
        follow_up = agent.on_approved(run.prompt, source_output)
        if follow_up is not None:
            follow_up_output = dict(follow_up.output)
            if follow_up.work_order is not None:
                draft = follow_up.work_order
                work_order = WorkOrder(
                    run_id=run.id,
                    priority=draft.priority,
                    crew=draft.crew,
                    location=draft.location,
                    defect_type=draft.defect_type,
                )
                self.session.add(work_order)
                self.session.flush()
                follow_up_output.update(
                    {"work_order_id": work_order.id, "status": work_order.status}
                )
            run.tasks.append(
                RunTask(
                    name=follow_up.task_name,
                    status="completed",
                    attempt=run.attempt,
                    output=follow_up_output,
                    completed_at=datetime.now(UTC),
                )
            )
            self._audit(
                run,
                follow_up.audit_action,
                actor="system",
                details=follow_up_output,
            )
        self._commit()
        return self.get_run(run_id)

    def reject(self, run_id: str, *, actor: str, note: str) -> WorkflowRun:
        run = self.get_run(run_id)
        run.state = transition_run(RunState(run.state), RunAction.REJECT).value
        approval = self._waiting_approval_task(run)
        approval.status = "rejected"
        approval.completed_at = datetime.now(UTC)
        approval.output = {"decision": "rejected", "note": note}
        self._audit(run, "approval.rejected", actor=actor, details={"note": note})
        self._commit()
        return self.get_run(run_id)

    def retry(self, run_id: str) -> WorkflowRun:
        run = self.get_run(run_id)
        run.state = transition_run(RunState(run.state), RunAction.RETRY).value
        run.attempt += 1
        self._audit(run, "run.retried", details={"attempt": run.attempt})
        self._execute_attempt(run, simulate_failure=False)
        self._commit()
        return self.get_run(run_id)

    def _execute_attempt(self, run: WorkflowRun, *, simulate_failure: bool) -> None:
        agent = self.registry.get(run.agent_key)
        plan_task = RunTask(
            name=agent.task_name,
            status="running",
            attempt=run.attempt,
        )
        run.tasks.append(plan_task)

        if simulate_failure:
            plan_task.status = "failed"
            plan_task.completed_at = datetime.now(UTC)
            plan_task.output = {"error": "Simulated provider timeout"}
            run.state = transition_run(RunState(run.state), RunAction.FAIL).value
            self._audit(run, "task.failed", details={"task": plan_task.name})
            return

        result = agent.invoke(run.prompt)
        plan_task.status = "completed"
        plan_task.completed_at = datetime.now(UTC)
        plan_task.output = result.output
        plan_task.token_count = result.token_count
        plan_task.cost_usd = Decimal(result.cost_usd)
        run.total_tokens += plan_task.token_count
        run.total_cost_usd += plan_task.cost_usd
        self._audit(
            run,
            "task.completed",
            details={"task": plan_task.name, "tokens": plan_task.token_count},
        )

        run.tasks.append(
            RunTask(name="human_approval", status="waiting", attempt=run.attempt)
        )
        run.state = transition_run(RunState(run.state), RunAction.REQUEST_APPROVAL).value
        self._audit(run, "approval.requested", details={"task": "human_approval"})

    @staticmethod
    def _waiting_approval_task(run: WorkflowRun) -> RunTask:
        return next(task for task in reversed(run.tasks) if task.status == "waiting")

    @staticmethod
    def _audit(
        run: WorkflowRun,
        action: str,
        *,
        actor: str = "system",
        details: dict | None = None,
    ) -> None:
        run.audit_events.append(
            AuditEvent(action=action, actor=actor, details=details or {})
        )

    def _commit(self) -> None:
        self.session.commit()

    @staticmethod
    def _title_from_prompt(prompt: str) -> str:
        compact = " ".join(prompt.split())
        return compact[:80] if compact else "Untitled run"
