import os
import tempfile

# FIX: the old tests wrote student_state.json into the working directory as a
# side effect. Point the store at a throwaway dir before importing anything.
_TMP = tempfile.mkdtemp(prefix="cognix-test-")
os.environ["COGNIX_STATE_DIR"] = _TMP

from state_machine import DiagnosticAgent, MAX_ATTEMPTS  # noqa: E402
from models import DiagnosticCheck, StudentState  # noqa: E402
import store  # noqa: E402


def _agent(sid):
    return DiagnosticAgent(sid)


def test_contradiction_revises():
    a = _agent("T1")
    h = a.choose_hypothesis("base_case", "test")
    q = a.ask(h, "base case?")
    a.evaluate(q, "n=0", "contradicts", "base case understood")
    assert h.status == "rejected"
    assert a.run.state == "FORM_HYPOTHESIS"
    assert a.run.revisions_used == 1


def test_support_requires_confirmation():
    a = _agent("T2")
    h = a.choose_hypothesis("call_stack", "test")
    q = a.ask(h, "trace")
    a.evaluate(q, "can't", "supports", "weak trace")
    assert a.run.state == "CONFIRM"
    a.confirm("yes")
    assert a.state.confirmation_status == "confirmed"


def test_invalid_evidence_rejected():
    a = _agent("T3")
    h = a.choose_hypothesis("base_case", "test")
    q = a.ask(h, "base case?")
    try:
        a.evaluate(q, "answer", "certain", "bad")
        raise AssertionError("invalid result should raise")
    except ValueError:
        pass


def test_rejected_hypothesis_not_reproposed():
    a = _agent("T4")
    h = a.choose_hypothesis("base_case", "test")
    a.evaluate(a.ask(h, "?"), "n=0", "contradicts", "understood")
    assert a.choose_hypothesis("base_case", "again") is None
    assert len(a.state.hypotheses) == 1


def test_uncertain_does_not_name_a_gap():
    a = _agent("T5")
    h = a.choose_hypothesis("base_case", "test")
    a.evaluate(a.ask(h, "?"), "maybe", "uncertain", "ambiguous")
    assert a.state.current_gap is None
    assert a.state.confidence == "low"
    assert h.status == "uncertain"


def test_attempt_limit_stops_safely():
    a = _agent("T6")
    for i in range(MAX_ATTEMPTS):
        h = a.choose_hypothesis(f"cause_{i}", "probe")
        a.evaluate(a.ask(h, "?"), "unclear", "uncertain", "ambiguous")
    assert a.run.attempts_used == MAX_ATTEMPTS
    assert a.choose_hypothesis("cause_x", "probe") is None
    assert a.run.outcome == "stopped:attempt_limit"
    assert a.run.state == "STORE"


def test_evaluate_rejects_none_check():
    a = _agent("T7")
    try:
        a.evaluate(None, "r", "supports", "n")
        raise AssertionError("None check should raise")
    except ValueError:
        pass


def test_evaluate_rejects_orphan_check():
    a = _agent("T8")
    try:
        a.evaluate(DiagnosticCheck("Q9", "H99", "?"), "r", "supports", "n")
        raise AssertionError("orphan check should raise")
    except ValueError:
        pass


def test_double_evaluation_rejected():
    a = _agent("T9")
    h = a.choose_hypothesis("base_case", "test")
    q = a.ask(h, "?")
    a.evaluate(q, "n=0", "contradicts", "understood")
    try:
        a.evaluate(q, "n=0", "supports", "flip")
        raise AssertionError("re-scoring should raise")
    except ValueError:
        pass
    assert a.run.revisions_used == 1


def test_rejection_clears_gap():
    a = _agent("T10")
    h = a.choose_hypothesis("call_stack", "test")
    a.evaluate(a.ask(h, "?"), "fine", "supports", "n")
    a.confirm("no")
    assert a.state.confirmation_status == "rejected"
    assert a.state.current_gap is None
    assert h.status == "rejected"


def test_safe_stop_preserves_confirmation():
    a = _agent("T11")
    h = a.choose_hypothesis("call_stack", "test")
    a.evaluate(a.ask(h, "?"), "can't", "supports", "n")
    a.confirm("yes")
    a.safe_stop("late_stop")
    assert a.state.confirmation_status == "confirmed"


def test_state_is_per_student():
    a = _agent("T12")
    h = a.choose_hypothesis("base_case", "test")
    a.evaluate(a.ask(h, "?"), "n=0", "contradicts", "understood")
    assert len(store.load("T12").hypotheses) == 1
    assert store.load("T13").hypotheses == []  # not clobbered


def test_load_rejects_mismatched_student():
    a = _agent("T14")
    try:
        a.load(StudentState(student_id="someone_else", topic="recursion"))
        raise AssertionError("mismatched state should raise")
    except ValueError:
        pass


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"  ok  {t.__name__}")
    print(f"\nAll {len(tests)} tests passed.")
