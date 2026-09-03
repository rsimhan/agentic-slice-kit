"""Orchestration is code. These tests are about control flow, not models."""
from types import SimpleNamespace

from slice import runner
from slice.budget import BudgetExceeded
from slice.config import Settings
from slice.records import RunState
from slice.store import Store

S = Settings(api_key="x", model="m", fallback_model="f", escalation_model="e",
             max_tokens=100, max_tokens_per_run=1000, max_attempts_per_step=2,
             expert_timeout_minutes=45, langfuse_public="", langfuse_secret="",
             langfuse_host="")


def flow(handlers):
    return SimpleNamespace(name="test", handlers=handlers)


def test_runs_to_completion_and_records_each_step(tmp_path):
    s = Store(tmp_path / "r.db")
    run = s.create_run("test")

    def draft(ctx):
        ctx.append("thesis", {"v": 1}, "spot"); return RunState.PROBING

    def probe(ctx):
        ctx.append("evidence", {"n": 3}, "probe"); return RunState.COMPLETE

    assert runner.advance(s, run, flow({RunState.DRAFTING: draft,
                                        RunState.PROBING: probe}), S) is RunState.COMPLETE
    assert [v.kind for v in s.replay(run)] == ["thesis", "evidence"]


def test_a_suspended_run_stops_without_spinning(tmp_path):
    s = Store(tmp_path / "r.db")
    run = s.create_run("test")
    calls = []

    def draft(ctx):
        calls.append(1); return RunState.AWAITING_EXPERT

    assert runner.advance(s, run, flow({RunState.DRAFTING: draft}), S) is RunState.AWAITING_EXPERT
    assert len(calls) == 1
    # resuming while still suspended must do nothing at all
    assert runner.advance(s, run, flow({RunState.DRAFTING: draft}), S) is RunState.AWAITING_EXPERT
    assert len(calls) == 1


def test_resume_continues_from_where_it_stopped(tmp_path):
    s = Store(tmp_path / "r.db")
    run = s.create_run("test")

    def draft(ctx): return RunState.AWAITING_EXPERT
    def probe(ctx): ctx.append("evidence", {"ok": True}, "probe"); return RunState.COMPLETE
    f = flow({RunState.DRAFTING: draft, RunState.PROBING: probe})

    runner.advance(s, run, f, S)
    s.set_state(run, RunState.PROBING)          # as an expert answer would
    assert runner.advance(s, run, f, S) is RunState.COMPLETE


def test_budget_failure_is_recorded_not_raised(tmp_path):
    """A run that dies without leaving a reason is the one you cannot debug."""
    s = Store(tmp_path / "r.db")
    run = s.create_run("test")

    def greedy(ctx):
        raise BudgetExceeded("token", 1001, 1000)

    assert runner.advance(s, run, flow({RunState.DRAFTING: greedy}), S) is RunState.FAILED
    f = s.latest(run, "failure")
    assert f["kind"] == "budget" and "1001" in f["detail"]


def test_a_handler_that_makes_no_progress_is_caught(tmp_path):
    s = Store(tmp_path / "r.db")
    run = s.create_run("test")
    assert runner.advance(s, run, flow({RunState.DRAFTING: lambda c: RunState.DRAFTING}),
                          S) is RunState.FAILED
    assert s.latest(run, "failure")["kind"] == "no_progress"


def test_missing_handler_fails_loudly(tmp_path):
    s = Store(tmp_path / "r.db")
    run = s.create_run("test")
    assert runner.advance(s, run, flow({}), S) is RunState.FAILED
    assert s.latest(run, "failure")["kind"] == "no_handler"
