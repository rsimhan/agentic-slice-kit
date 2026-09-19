"""Synapse domain flow: State machine handlers and business logic.

Integrates directly with the Agentic Slice Kit spine (slice.runner, slice.store, slice.budget, slice.llm).
Enforces the explicit backward edge:
DRAFTING -> GATING -> PASS -> COMPLETE
                   -> BLOCK -> DRAFTING (revisions addressing reviewer objections, bounded at MAX_REVISIONS).
"""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Callable

from slice.llm import complete
from slice.records import RunState

from .schema import TailoredNoteRecord, ReviewVerdict

# --------------------------------------------------------------- domain rules

MAX_REVISIONS = 3
"""How many revisions a student remediation note gets before stopping.

This is a domain pedagogical decision, NOT a spend limit.
It is counted from the store's record history, deliberately NOT from budget.attempt(),
ensuring that spend fences and domain revision boundaries do not conflate.
"""

_PROMPTS = Path(__file__).parent / "prompts"


def _prompt(name: str) -> str:
    path = _PROMPTS / f"{name}.md"
    if path.exists():
        return path.read_text(encoding="utf-8")
    return f"You are the Synapse {name} agent."


# ------------------------------------------------------------------ messages

def build_tailoring_messages(
    canonical: dict,
    attempt: dict,
    diagnosis: dict,
    prior_note: dict | None,
    verdict: dict | None
) -> list[dict]:
    user_parts = [
        f"### Canonical Concept Notes:\n{json.dumps(canonical, indent=2)}",
        f"### Student Attempt:\n{json.dumps(attempt, indent=2)}",
        f"### Diagnostic Analysis:\n{json.dumps(diagnosis, indent=2)}"
    ]

    if prior_note and verdict and verdict.get("status") == "BLOCK":
        user_parts.append(
            f"### Previous Draft (v{prior_note.get('version', 1)}):\n"
            + json.dumps(prior_note, indent=2)
        )
        objections = verdict.get("objections", [])
        objections_text = "\n".join(
            f"- [{o.get('field', 'general')}]: {o.get('problem', '')}" for o in objections
        )
        user_parts.append(
            "### Reviewer Objections (You MUST fix each of these in this revision):\n"
            + objections_text
        )

    return [
        {"role": "system", "content": _prompt("tailor")},
        {"role": "user", "content": "\n\n---\n\n".join(user_parts)},
    ]


def build_review_messages(
    canonical: dict,
    diagnosis: dict,
    tailored_note: dict
) -> list[dict]:
    user_content = (
        f"### Canonical Subject Matter:\n{json.dumps(canonical, indent=2)}\n\n"
        f"### Diagnosed Student Gaps:\n{json.dumps(diagnosis, indent=2)}\n\n"
        f"### Candidate Tailored Note for Review:\n{json.dumps(tailored_note, indent=2)}"
    )
    return [
        {"role": "system", "content": _prompt("review")},
        {"role": "user", "content": user_content},
    ]


# ------------------------------------------------------------------ handlers

def build_flow(call: Callable = complete):
    """Build the Synapse Flow protocol object for slice.runner.advance.
    
    `call` is injected so the flow can run against live OpenRouter models
    or deterministic offline stubs (see demo/stub.py).
    """

    def handle_drafting(ctx) -> RunState:
        # Fences: check token and attempt limits
        ctx.budget.check_tokens()
        ctx.budget.attempt("tailoring")

        canonical = ctx.latest("canonical_note") or {}
        attempt = ctx.latest("attempt") or {}
        diagnosis = ctx.latest("diagnosis") or {}
        prior_note = ctx.latest("tailored_note")
        verdict = ctx.latest("verdict")

        # Determine version count from history
        prior_drafts = ctx.history("tailored_note")
        next_version = len(prior_drafts) + 1

        messages = build_tailoring_messages(canonical, attempt, diagnosis, prior_note, verdict)
        record = call(
            settings=ctx.settings,
            budget=ctx.budget,
            messages=messages,
            schema=TailoredNoteRecord,
            step=f"tailor:{next_version}"
        )

        ctx.append("tailored_note", record.model_dump(), produced_by="agent:tailor")
        ctx.budget.reset_attempts("tailoring")
        return RunState.GATING

    def handle_gating(ctx) -> RunState:
        # Fences: check token and attempt limits
        ctx.budget.check_tokens()
        ctx.budget.attempt("review")

        canonical = ctx.latest("canonical_note") or {}
        diagnosis = ctx.latest("diagnosis") or {}
        note = ctx.latest("tailored_note") or {}

        revisions = len(ctx.history("tailored_note"))

        messages = build_review_messages(canonical, diagnosis, note)
        verdict = call(
            settings=ctx.settings,
            budget=ctx.budget,
            messages=messages,
            schema=ReviewVerdict,
            step=f"review:{revisions}"
        )

        ctx.append("verdict", verdict.model_dump(), produced_by="agent:review")
        ctx.budget.reset_attempts("review")

        if verdict.status == "PASS":
            return RunState.COMPLETE

        # Verdict is BLOCK: check if we reached the maximum revisions limit
        if revisions >= MAX_REVISIONS:
            ctx.append(
                "failure",
                {
                    "kind": "revision_limit",
                    "detail": f"Reached maximum allowed revisions ({MAX_REVISIONS}) without passing review."
                },
                produced_by="domain"
            )
            return RunState.COMPLETE

        # EXPLICIT AGENTIC BACKWARD EDGE:
        # Review failed, so work is sent BACKWARDS to DRAFTING to write a revision
        return RunState.DRAFTING

    return SimpleNamespace(
        name="synapse",
        handlers={
            RunState.DRAFTING: handle_drafting,
            RunState.GATING: handle_gating,
        }
    )
