"""Tests for the Synapse agentic slice domain.

Runs entirely on deterministic stubs: zero tokens, zero key, zero network.
Proves the agentic back-edge:
Drafting -> Gating -> BLOCK -> Revision Addressing Objections -> Gating -> PASS -> COMPLETE.
"""
from __future__ import annotations

import pytest

from demo.flow import MAX_REVISIONS, build_flow
from demo.schema import CanonicalNoteInput, AttemptInput, DiagnosisRecord, DiagnosisItem
from demo.stub import Stub, BLOCK_VERDICT
from slice import runner
from slice.config import settings as load_settings
from slice.records import RunState
from slice.store import Store

CANONICAL = {
    "concept_id": "recursion_basics",
    "title": "Recursion in Python",
    "markdown": "Recursion requires two elements: a base case to terminate execution and a recursive step to divide work.",
    "key_terms": ["base_case", "call_stack", "recursive_step"]
}

ATTEMPT = {
    "student_id": "student_42",
    "test_id": "test_recursion_1",
    "concept_id": "recursion_basics",
    "answers": {
        "q1": "A function that calls another function",
        "q2": "Infinite recursion causes out of memory"
    }
}

DIAGNOSIS = {
    "student_id": "student_42",
    "concept_id": "recursion_basics",
    "items": [
        {
            "question_id": "q2",
            "concept": "call_stack",
            "classification": "conceptual_gap",
            "reason": "Student does not connect infinite recursion to call stack frame accumulation."
        }
    ],
    "summary": "Needs clarification on how the call stack manages recursion and the necessity of base case termination."
}


def _run_synapse(tmp_path, call):
    store = Store(str(tmp_path / "synapse_test.db"))
    run_id = store.create_run("synapse", {"student_id": "student_42", "concept_id": "recursion_basics"})
    
    # Store initial state / inputs
    store.append(run_id, "canonical_note", CANONICAL, produced_by="teacher")
    store.append(run_id, "attempt", ATTEMPT, produced_by="student")
    store.append(run_id, "diagnosis", DIAGNOSIS, produced_by="agent:diagnose")

    final = runner.advance(store, run_id, build_flow(call), load_settings())
    return store, run_id, final


# ------------------------------------------------------------- test cases

def test_the_synapse_loop_completes(tmp_path):
    """Proves the full flow settles on RunState.COMPLETE."""
    _, _, final = _run_synapse(tmp_path, Stub())
    assert final is RunState.COMPLETE


def test_synapse_work_goes_backwards(tmp_path):
    """The key test: proves this is an agent and not a linear pipeline.
    A BLOCK review verdict sends work BACKWARDS to DRAFTING to produce a second draft.
    """
    store, run_id, _ = _run_synapse(tmp_path, Stub())
    drafts = store.history(run_id, "tailored_note")
    assert len(drafts) == 2, f"Expected 2 drafts due to back-edge, got {len(drafts)}"
    assert drafts[0].payload != drafts[1].payload, "The second draft was identical to the first"
    assert drafts[0].payload["version"] == 1
    assert drafts[1].payload["version"] == 2


def test_the_revision_addresses_reviewer_objections(tmp_path):
    """Going backwards is not enough - it must go backwards *usefully*.
    The first draft omitted 'call_stack'. The gate objected. The second draft must fix it.
    """
    store, run_id, _ = _run_synapse(tmp_path, Stub())
    v1 = store.history(run_id, "tailored_note")[0].payload
    v2 = store.history(run_id, "tailored_note")[1].payload
    verdicts = store.history(run_id, "verdict")
    
    first_verdict = verdicts[0].payload
    assert first_verdict["status"] == "BLOCK"
    
    # Check that objection was about prerequisite_links
    objections = first_verdict["objections"]
    assert any(o["field"] == "prerequisite_links" for o in objections)
    
    # Check that v1 lacked 'call_stack' and v2 now includes it
    assert "call_stack" not in v1.get("prerequisite_links", [])
    assert "call_stack" in v2.get("prerequisite_links", [])


def test_verdicts_are_recorded_in_order(tmp_path):
    """Audit trail must show BLOCK followed by PASS."""
    store, run_id, _ = _run_synapse(tmp_path, Stub())
    verdicts = [v.payload["status"] for v in store.history(run_id, "verdict")]
    assert verdicts == ["BLOCK", "PASS"]


def test_revisions_are_bounded_at_three(tmp_path):
    """If the reviewer persistently blocks, the run must terminate at MAX_REVISIONS (3)
    rather than spinning forever or exhausting the token budget.
    """
    from demo.schema import TailoredNoteRecord, ReviewVerdict
    
    class PersistentBlockStub:
        def __init__(self):
            self._tailor_count = 0
            
        def __call__(self, *, settings, budget, messages, schema=None, model=None, step="call", timeout=120.0):
            base = step.split(":")[0]
            if base == "tailor":
                self._tailor_count += 1
                return TailoredNoteRecord(
                    version=self._tailor_count,
                    student_id="student_42",
                    concept_id="recursion_basics",
                    markdown=f"Draft version {self._tailor_count} with persistent flaws",
                    addressed_gaps=[],
                    prerequisite_links=[]
                )
            elif base == "review":
                return ReviewVerdict(
                    status="BLOCK",
                    canonical_coverage=False,
                    objections=[{"field": "general", "problem": "Still not acceptable"}]
                )
            raise AssertionError(f"Unexpected step: {step}")

    store, run_id, final = _run_synapse(tmp_path, PersistentBlockStub())
    assert final is RunState.COMPLETE
    drafts = store.history(run_id, "tailored_note")
    assert len(drafts) == MAX_REVISIONS, f"Should stop at exactly {MAX_REVISIONS} revisions"
    failures = store.history(run_id, "failure")
    assert len(failures) == 1
    assert failures[0].payload["kind"] == "revision_limit"


def test_budget_counters_updated_and_persist(tmp_path):
    """Proves that tokens and step attempts are tracked inside SQLite."""
    store, run_id, _ = _run_synapse(tmp_path, Stub())
    tokens = store.counter(run_id, "tokens")
    assert tokens > 0, "Tokens should have been recorded by the budget"
