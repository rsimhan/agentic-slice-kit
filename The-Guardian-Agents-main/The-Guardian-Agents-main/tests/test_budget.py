"""The fences. If these do not hold, nothing stops a loop."""
import pytest

from slice.budget import Budget, BudgetExceeded
from slice.config import Settings
from slice.store import Store


def mk(tmp_path, **over):
    base = dict(api_key="x", model="m", fallback_model="f", escalation_model="e",
                max_tokens=100, max_tokens_per_run=1000, max_attempts_per_step=3,
                expert_timeout_minutes=45, langfuse_public="", langfuse_secret="",
                langfuse_host="")
    base.update(over)
    s = Store(tmp_path / "b.db")
    run = s.create_run("t")
    return s, run, Budget(s, run, Settings(**base))


def test_attempts_raise_after_the_allowance(tmp_path):
    _, _, b = mk(tmp_path)
    assert [b.attempt("gate") for _ in range(3)] == [1, 2, 3]
    with pytest.raises(BudgetExceeded) as e:
        b.attempt("gate")
    assert e.value.kind == "attempt" and "gate" in str(e.value)


def test_attempts_are_per_step(tmp_path):
    _, _, b = mk(tmp_path)
    for _ in range(3):
        b.attempt("gate")
    assert b.attempt("probe") == 1, "one step's allowance must not consume another's"


def test_reset_after_success(tmp_path):
    _, _, b = mk(tmp_path)
    b.attempt("gate"); b.attempt("gate")
    b.reset_attempts("gate")
    assert b.attempts("gate") == 0
    assert b.attempt("gate") == 1


def test_token_fence_checks_before_not_after(tmp_path):
    _, _, b = mk(tmp_path, max_tokens_per_run=500)
    b.check_tokens()
    b.record_tokens(499)
    b.check_tokens()               # still under: a request may start
    b.record_tokens(1)             # now exactly at the fence
    with pytest.raises(BudgetExceeded) as e:
        b.check_tokens()
    assert e.value.kind == "token"


def test_fences_survive_a_restart(tmp_path):
    """A fence held in a Python variable dies with the process. This one must not."""
    s, run, b = mk(tmp_path)
    b.attempt("gate"); b.attempt("gate"); b.record_tokens(700)
    s.close()

    s2 = Store(tmp_path / "b.db")
    from slice.config import Settings as S
    b2 = Budget(s2, run, S(api_key="x", model="m", fallback_model="f", escalation_model="e",
                           max_tokens=100, max_tokens_per_run=1000, max_attempts_per_step=3,
                           expert_timeout_minutes=45, langfuse_public="",
                           langfuse_secret="", langfuse_host=""))
    assert b2.attempts("gate") == 2 and b2.tokens_used() == 700
    b2.attempt("gate")
    with pytest.raises(BudgetExceeded):
        b2.attempt("gate")
