import pytest

from app.domain.runs import InvalidTransition, RunAction, RunState, transition_run


@pytest.mark.parametrize(
    ("current", "action", "expected"),
    [
        (RunState.DRAFT, RunAction.START, RunState.RUNNING),
        (RunState.RUNNING, RunAction.REQUEST_APPROVAL, RunState.WAITING_APPROVAL),
        (RunState.WAITING_APPROVAL, RunAction.APPROVE, RunState.COMPLETED),
        (RunState.WAITING_APPROVAL, RunAction.REJECT, RunState.REJECTED),
        (RunState.RUNNING, RunAction.FAIL, RunState.FAILED),
        (RunState.FAILED, RunAction.RETRY, RunState.RUNNING),
    ],
)
def test_valid_transition(current: RunState, action: RunAction, expected: RunState) -> None:
    assert transition_run(current, action) is expected


@pytest.mark.parametrize("state", [RunState.COMPLETED, RunState.REJECTED])
def test_terminal_states_cannot_transition(state: RunState) -> None:
    with pytest.raises(InvalidTransition, match="cannot apply"):
        transition_run(state, RunAction.START)


def test_approval_requires_waiting_state() -> None:
    with pytest.raises(InvalidTransition):
        transition_run(RunState.RUNNING, RunAction.APPROVE)
