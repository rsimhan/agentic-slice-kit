"""The two handlers, the domain rules, and the Flow object.

All the business rules in this slice live here, in code, not in the prompts. The
model returns a judgement; this file decides what that judgement means.

Nothing in slice/ changes for this to run.
"""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from slice.llm import complete
from slice.records import RunState

from .schema import OpportunityRecord, Verdict

# --------------------------------------------------------------- domain rules

MAX_REVISIONS = 3
"""How many rewrites a founder gets before the run stops.

This is a teaching decision, not a cost control. It is counted from the record
history below - deliberately NOT from budget.attempt(), which is a spend fence
and is also ticking for retries after a malformed response. Share one counter
between them and two bad replies silently buy a founder one revision instead of
three, which you find out on stage.
"""

_PROMPTS = Path(__file__).parent / "prompts"


def _prompt(name: str) -> str:
    return (_PROMPTS / f"{name}.md").read_text(encoding="utf-8")


# ------------------------------------------------------------------ messages
# Templates, not model calls. There are exactly two model calls in this build
# and no ambiguity about which they are.

def build_spot_messages(idea: str, prior: dict | None, verdict: dict | None) -> list[dict]:
    user = [f"The founder's paragraph:\n\n{idea}"]
    if prior and verdict and verdict.get("status") == "BLOCK":
        user.append("Your previous record:\n\n" + json.dumps(prior, indent=2))
        user.append(
            "It was blocked. Address each of these, in the field it names:\n\n"
            + "\n".join(f"- {o['field']}: {o['problem']}" for o in verdict["objections"])
        )
    return [
        {"role": "system", "content": _prompt("spot")},
        {"role": "user", "content": "\n\n---\n\n".join(user)},
    ]


def build_gate_messages(record: dict) -> list[dict]:
    return [
        {"role": "system", "content": _prompt("gate")},
        {"role": "user", "content": "Judge this record:\n\n" + json.dumps(record, indent=2)},
    ]


# ------------------------------------------------------------------ handlers

def build_flow(call=complete):
    """Return the Flow. `call` is injected so the whole state machine can be
    exercised with canned responses - no key, no network, no tokens. See
    demo/smoke/stub.py."""

    def handle_drafting(ctx) -> RunState:
        idea    = ctx.latest("input")["text"]
        prior   = ctx.latest("opportunity")     # None on the first pass
        verdict = ctx.latest("verdict")         # objections to address, if any

        record = call(
            settings=ctx.settings, budget=ctx.budget,
            messages=build_spot_messages(idea, prior, verdict),
            schema=OpportunityRecord, step="spot",
        )
        ctx.append("opportunity", record.model_dump(), produced_by="agent:spot")
        return RunState.GATING

    def handle_gating(ctx) -> RunState:
        verdict = call(
            settings=ctx.settings, budget=ctx.budget,
            messages=build_gate_messages(ctx.latest("opportunity")),
            schema=Verdict, step="gate",
        )
        ctx.append("verdict", verdict.model_dump(), produced_by="agent:gate")

        if verdict.status == "PASS":
            return RunState.COMPLETE

        # A revision that changed nothing will not change anything next time
        # either. Observed live: SPOT correctly reported "the founder did not
        # specify X", the gate objected "the founder did not specify X", and the
        # two of them repeated that exchange until the bound stopped the run -
        # eleven thousand tokens to learn nothing after the first round.
        #
        # This is the unresolved-versus-contradicted distinction from SPEC.md
        # 8.5, in miniature. A record that admits an absence is not wrong, it is
        # incomplete, and the remedy is not another revision - it is a question
        # for the founder. Stopping here says something useful; turning the loop
        # again says the same thing more expensively.
        drafts = ctx.history("opportunity")
        if len(drafts) >= 2 and drafts[-1].payload == drafts[-2].payload:
            missing = sorted({o["field"] for o in verdict.model_dump()["objections"]})
            ctx.append("failure",
                       {"kind": "needs_the_founder",
                        "detail": "The revision was identical to the draft before it. "
                                  "What the gate is asking for is not in the paragraph: "
                                  + ", ".join(missing) + ". Go back to the founder.",
                        "missing": missing},
                       produced_by="system")
            return RunState.FAILED

        # Counted from the record, not from the budget. See MAX_REVISIONS.
        blocks = sum(1 for v in ctx.history("verdict")
                     if v.payload["status"] == "BLOCK")
        if blocks >= MAX_REVISIONS:
            ctx.append("failure",
                       {"kind": "gate_exhausted",
                        "detail": f"Blocked {blocks} times; no revision passed."},
                       produced_by="system")
            return RunState.FAILED
        return RunState.DRAFTING

    return SimpleNamespace(
        name="smoke",
        handlers={
            RunState.DRAFTING: handle_drafting,
            RunState.GATING:   handle_gating,
        },
    )
