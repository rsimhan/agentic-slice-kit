"""
Does the spine actually work against a real model?

Everything else in this suite tests one piece in isolation. This runs a whole
tiny flow end to end - config, budget, llm, store, runner - against the live
API, with a real schema the model has to satisfy.

It costs a fraction of a cent and it is the only test here that can catch
"all the parts work and the assembly does not".

Skipped automatically when there is no key, so `pytest` stays green for someone
who has not been to the key desk yet:

    python -m pytest tests/test_integration.py -v
"""
from types import SimpleNamespace

import pytest
from pydantic import BaseModel, Field

from slice.budget import Budget
from slice.config import settings
from slice.llm import complete
from slice.records import RunState
from slice.runner import advance
from slice.store import Store

S = settings()
needs_key = pytest.mark.skipif(
    not S.api_key, reason="no OPENROUTER_API_KEY - copy .env.example to .env")


class Verdict(BaseModel):
    """A deliberately strict contract. If the model drifts, this catches it."""
    status: str = Field(description="PASS or BLOCK")
    reasons: list[str] = Field(min_length=1)


PROMPT = [
    {"role": "system", "content":
        'Return ONLY JSON: {"status":"PASS"|"BLOCK","reasons":[string,...]}. '
        'BLOCK anything whose customer is a category rather than a specific person. '
        'reasons must never be empty.'},
    {"role": "user", "content":
        "Problem: students struggle with time management. Who: university students."},
]


@needs_key
def test_a_real_call_returns_a_parsed_schema(tmp_path):
    s = Store(tmp_path / "i.db")
    run = s.create_run("integration")
    v = complete(settings=S, budget=Budget(s, run, S), messages=PROMPT,
                 schema=Verdict, step="gate")

    assert isinstance(v, Verdict)
    assert v.status in ("PASS", "BLOCK")
    assert v.reasons, "the schema requires at least one reason"
    assert v.status == "BLOCK", "'university students' is a category, not a person"


@needs_key
def test_tokens_are_recorded_against_the_run(tmp_path):
    """The fence only works if spend is actually counted."""
    s = Store(tmp_path / "i.db")
    run = s.create_run("integration")
    b = Budget(s, run, S)
    assert b.tokens_used() == 0
    complete(settings=S, budget=b, messages=PROMPT, schema=Verdict, step="gate")
    assert b.tokens_used() > 0

    s2 = Store(tmp_path / "i.db")          # and survives a reopen
    assert Budget(s2, run, S).tokens_used() == b.tokens_used()


@needs_key
def test_a_whole_flow_runs_through_the_state_machine(tmp_path):
    """Two states, a real model call in each, ending COMPLETE - with the
    history showing every step in order."""
    s = Store(tmp_path / "i.db")
    run = s.create_run("integration")

    def draft(ctx):
        v = complete(settings=S, budget=ctx.budget, messages=PROMPT,
                     schema=Verdict, step="draft")
        ctx.append("verdict", v.model_dump(), "gate")
        return RunState.PROBING

    def probe(ctx):
        prior = ctx.latest("verdict")
        assert prior is not None, "state did not survive the transition"
        ctx.append("evidence", {"checked": len(prior["reasons"])}, "probe")
        return RunState.COMPLETE

    final = advance(s, run, SimpleNamespace(
        name="integration",
        handlers={RunState.DRAFTING: draft, RunState.PROBING: probe}), S)

    assert final is RunState.COMPLETE, s.latest(run, "failure")
    assert [v.kind for v in s.replay(run)] == ["verdict", "evidence"]
