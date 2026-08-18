from enum import StrEnum


class RunState(StrEnum):
    DRAFT = "draft"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    REJECTED = "rejected"
    FAILED = "failed"


class RunAction(StrEnum):
    START = "start"
    REQUEST_APPROVAL = "request_approval"
    APPROVE = "approve"
    REJECT = "reject"
    FAIL = "fail"
    RETRY = "retry"


class InvalidTransition(ValueError):
    pass


_TRANSITIONS = {
    (RunState.DRAFT, RunAction.START): RunState.RUNNING,
    (RunState.RUNNING, RunAction.REQUEST_APPROVAL): RunState.WAITING_APPROVAL,
    (RunState.WAITING_APPROVAL, RunAction.APPROVE): RunState.COMPLETED,
    (RunState.WAITING_APPROVAL, RunAction.REJECT): RunState.REJECTED,
    (RunState.RUNNING, RunAction.FAIL): RunState.FAILED,
    (RunState.FAILED, RunAction.RETRY): RunState.RUNNING,
}


def transition_run(current: RunState, action: RunAction) -> RunState:
    try:
        return _TRANSITIONS[(current, action)]
    except KeyError as exc:
        message = f"cannot apply {action.value} while run is {current.value}"
        raise InvalidTransition(message) from exc
