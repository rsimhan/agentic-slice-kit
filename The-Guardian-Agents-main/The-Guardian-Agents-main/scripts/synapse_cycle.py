#!/usr/bin/env python3
"""CLI runner for the Synapse Agentic Slice.

Usage:
    python scripts/synapse_cycle.py run --stub        # offline: zero tokens, zero key
    python scripts/synapse_cycle.py run               # live model calls via OpenRouter
    python scripts/synapse_cycle.py replay <run_id>   # view immutable audit history

Proves:
    1. Canonical notes and student attempts are ingested as typed records
    2. Drafting -> Gating -> Reviewer BLOCK -> Re-Drafting -> Gating -> Reviewer PASS
    3. Immutable append-only SQLite persistence with replay
    4. Bounded revision fences (MAX_REVISIONS = 3)
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Ensure repo root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from slice import runner
from slice.config import settings as load_settings
from slice.records import RunState
from slice.store import Store

from demo.flow import build_flow
from demo.stub import Stub

SAMPLE_CANONICAL = {
    "concept_id": "recursion_basics",
    "title": "Recursion in Python",
    "markdown": (
        "Recursion is a method of solving a problem where the solution depends on solutions "
        "to smaller instances of the same problem. Crucially, every recursive function must have:\n"
        "1. A base case (terminating condition)\n"
        "2. A recursive step moving toward the base case.\n"
        "Without a base case, frames accumulate on the [[call_stack]] until memory is exhausted."
    ),
    "key_terms": ["base_case", "call_stack", "recursive_step"]
}

SAMPLE_ATTEMPT = {
    "student_id": "student_42",
    "test_id": "quiz_recursion_1",
    "concept_id": "recursion_basics",
    "answers": {
        "q1": "A function that calls another function",
        "q2": "Infinite recursion causes a memory freeze without explanation"
    }
}

SAMPLE_DIAGNOSIS = {
    "student_id": "student_42",
    "concept_id": "recursion_basics",
    "items": [
        {
            "question_id": "q2",
            "concept": "call_stack",
            "classification": "conceptual_gap",
            "reason": "Student confuses memory freeze with call stack frame exhaustion."
        }
    ],
    "summary": "Student requires targeted explanation of base case termination and call stack memory mechanics."
}


def cmd_run(args):
    db_path = Path("synapse.db")
    store = Store(str(db_path))
    run_id = store.create_run("synapse", {"student_id": "student_42", "concept_id": "recursion_basics"})
    
    # Ingest initial records
    store.append(run_id, "canonical_note", SAMPLE_CANONICAL, produced_by="teacher")
    store.append(run_id, "attempt", SAMPLE_ATTEMPT, produced_by="student")
    store.append(run_id, "diagnosis", SAMPLE_DIAGNOSIS, produced_by="agent:diagnose")

    print(f"\nSynapse Learning Cycle [{run_id}] {'(STUB MODE)' if args.stub else '(LIVE MODE)'}")
    print("=" * 65)
    print(f"Concept: {SAMPLE_CANONICAL['title']}")
    print(f"Student: {SAMPLE_ATTEMPT['student_id']}")
    print("-" * 65)

    call_impl = Stub() if args.stub else runner.complete
    settings = load_settings()

    final = runner.advance(store, run_id, build_flow(call_impl), settings)

    # Print step progression
    for v in store.replay(run_id):
        if v.kind == "tailored_note":
            p = v.payload
            print(f"  [TAILOR] Note v{p.get('version', 1)} drafted | links: {p.get('prerequisite_links', [])}")
        elif v.kind == "verdict":
            p = v.payload
            status = p.get("status")
            objs = p.get("objections", [])
            print(f"  [GATE]   Review Verdict: {status} ({len(objs)} objection(s))")
            for obj in objs:
                print(f"           - [{obj.get('field')}]: {obj.get('problem')[:75]}...")

    tokens = store.counter(run_id, "tokens")
    drafts = len(store.history(run_id, "tailored_note"))
    print("-" * 65)
    print(f"Result: {final.value.upper()} | {drafts} draft revision(s) | {int(tokens)} tokens counted")
    if drafts > 1:
        print("=> SUCCESS: Agentic backward edge observed! Work looped backwards on BLOCK.")
    print(f"\nReplay with: python scripts/synapse_cycle.py replay {run_id}\n")


def cmd_replay(args):
    db_path = Path("synapse.db")
    if not db_path.exists():
        print("Database synapse.db not found.")
        return 1
    store = Store(str(db_path))
    print(f"\nAudit History for Run {args.run_id}:")
    print("-" * 65)
    for v in store.replay(args.run_id):
        print(f"seq={v.seq:<2} | kind={v.kind:<14} | author={v.produced_by:<14} | age={v.age_seconds:.1f}s")
        print(f"     payload: {str(v.payload)[:80]}...")
    print("-" * 65)


def main():
    parser = argparse.ArgumentParser(description="Synapse Agentic Slice CLI")
    subs = parser.add_subparsers(dest="command")

    run_p = subs.add_parser("run", help="Run a Synapse learning cycle")
    run_p.add_argument("--stub", action="store_true", help="Use deterministic canned stubs (no API key/tokens)")

    replay_p = subs.add_parser("replay", help="Replay a run's audit history")
    replay_p.add_argument("run_id", help="The run ID to replay")

    args = parser.parse_args()
    if args.command == "run":
        cmd_run(args)
    elif args.command == "replay":
        cmd_replay(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
