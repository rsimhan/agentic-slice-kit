"""
demo/feynman/flow.py - The Socratic State Machine & Feynman Check Flow.

Orchestrates the interactive Socratic dialogue for evaluating student conceptual
explanations against ground-truth lecture invariants.

Core State Transitions:
  AWAIT_EXPLANATION (DRAFTING)
        │
        ▼
  CRITIC_EVALUATE (GATING)
        │
        ├─▶ MISCONCEPTION / AMBIGUOUS (and revisions < 2)
        │     │
        │     ▼
        │   SOCRATIC_PROBE (PROBING)
        │     │
        │     └─▶ [THE BACK-EDGE] ──▶ AWAIT_EXPLANATION
        │
        └─▶ MASTERED or revisions >= 2
              │
              ▼
            LOG_STUDENT_STATE ──▶ COMPLETE

Architectural Guarantees:
1. Orchestration in Python, judgement in the model (Principle 7).
2. The Back-Edge: Work flows backward to generate counter-examples rather than giving answers.
3. Bounded loops: Revision count strictly derived from record history (`ctx.history("verdict")`),
   never from LLM spend retry counters (`budget.attempt()`) (Principle 3).
4. Full auditability: All student explanations, critic verdicts, probes, and session records
   are durably appended to SQLite (Principle 1) and persisted to data/students/{student_id}.json.
"""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable, Dict, List, Optional

from slice.llm import complete
from slice.records import RunState
from slice.runner import Context

from .schema import (
    CriticVerdict,
    ProbeMessage,
    StudentSessionRecord,
    StudentSubmission,
)
from .stub import get_canned_student, INVARIANT_VIRTUAL_MEMORY

# ---------------------------------------------------------------------------
# State Aliases matching AgentSpec & TEAM_TASKS
# ---------------------------------------------------------------------------
AWAIT_EXPLANATION = RunState.DRAFTING
CRITIC_EVALUATE   = RunState.GATING
SOCRATIC_PROBE    = RunState.PROBING
COMPLETE          = RunState.COMPLETE
FAILED            = RunState.FAILED

# ---------------------------------------------------------------------------
# Domain Bounds
# ---------------------------------------------------------------------------
MAX_REVISIONS = 2
"""
Maximum number of counter-example iterations allowed per student before escalation.
Derived strictly from len(ctx.history("verdict")) - NOT budget.attempt().
"""

# Path to ground truth invariants and prompt templates
_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "concepts"
_PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"


# ---------------------------------------------------------------------------
# Helpers: Ground Truth & Prompt Loading
# ---------------------------------------------------------------------------

def load_concept_ground_truth(concept_id: str = "virtual_memory") -> str:
    """Load the ground-truth markdown invariant file for a concept."""
    concept_file = _DATA_DIR / f"{concept_id}.md"
    if concept_file.exists():
        return concept_file.read_text(encoding="utf-8")
    # Fallback to in-memory stub invariant if file is missing
    return INVARIANT_VIRTUAL_MEMORY.invariant_statement


def load_prompt_template(name: str) -> str:
    """Load a markdown prompt template from demo/feynman/prompts/."""
    prompt_file = _PROMPTS_DIR / f"{name}.md"
    if prompt_file.exists():
        return prompt_file.read_text(encoding="utf-8")
    return ""


# ---------------------------------------------------------------------------
# Message Builders
# ---------------------------------------------------------------------------

def build_critic_messages(
    concept_ground_truth: str,
    student_text: str,
    prior_verdicts: Optional[List[Dict[str, Any]]] = None,
    prior_probes: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, str]]:
    """Builds prompt messages for the Critic evaluation step."""
    system_prompt = load_prompt_template("critic")

    user_sections = [
        f"### GROUND TRUTH CONCEPT INVARIANTS:\n{concept_ground_truth}",
    ]

    if prior_verdicts and prior_probes:
        history_lines = []
        for i, (v, p) in enumerate(zip(prior_verdicts, prior_probes)):
            history_lines.append(
                f"- Round {i+1}:\n"
                f"  Critic Verdict: {v.get('verdict')} (Flaw: {v.get('detected_flaw_tag')})\n"
                f"  Socratic Probe Issued: {p.get('counter_example_scenario')}"
            )
        user_sections.append("### PRIOR INTERACTION HISTORY:\n" + "\n".join(history_lines))

    user_sections.append(
        f"### STUDENT SUBMISSION TO EVALUATE:\n\"{student_text}\"\n\n"
        "Evaluate this submission against the ground truth invariants. "
        "Strictly catch semantic conflations (e.g. TLB miss directly causing disk access). "
        "Return a structured CriticVerdict."
    )

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "\n\n---\n\n".join(user_sections)},
    ]


def build_probe_messages(
    concept_ground_truth: str,
    student_text: str,
    verdict: Dict[str, Any],
) -> List[Dict[str, str]]:
    """Builds prompt messages for the Socratic counter-example generator."""
    system_prompt = load_prompt_template("probe")

    user_sections = [
        f"### GROUND TRUTH CONCEPT INVARIANTS:\n{concept_ground_truth}",
        f"### STUDENT SUBMISSION (CONTAINING MISCONCEPTION):\n\"{student_text}\"",
        f"### CRITIC DIAGNOSIS:\n"
        f"- Flaw Tag: {verdict.get('detected_flaw_tag')}\n"
        f"- Flaw Explanation: {verdict.get('flaw_explanation')}\n"
        f"- Confidence: {verdict.get('confidence')}",
        "Generate a concrete edge-case counter-example probe that forces the student "
        "to confront their faulty assumption without directly giving away the invariant. "
        "Return a structured ProbeMessage."
    ]

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "\n\n---\n\n".join(user_sections)},
    ]


# ---------------------------------------------------------------------------
# Telemetry Persistence: Log Student State
# ---------------------------------------------------------------------------

def log_student_session_state(
    ctx: Context,
    final_verdict: str,
) -> StudentSessionRecord:
    """
    Serializes completed session telemetry to the Store and to local JSON
    under data/students/{student_id}.json.
    """
    submissions = [s.payload for s in ctx.history("submission")]
    probes = [p.payload for p in ctx.history("probe")]
    verdicts = [v.payload for v in ctx.history("verdict")]

    initial_submission = submissions[0] if submissions else {}
    student_id = initial_submission.get("student_id") or ctx.store.meta(ctx.run_id).get("student_id", "anonymous")
    concept_id = initial_submission.get("concept_id", "virtual_memory")
    initial_text = initial_submission.get("text", "")

    student_revisions = [s.get("text", "") for s in submissions[1:]]
    probes_issued = [p.get("counter_example_scenario", "") for p in probes]

    # Tag initial fallacy detected, if any
    tagged_fallacy = None
    for v in verdicts:
        if v.get("detected_flaw_tag"):
            tagged_fallacy = v["detected_flaw_tag"]
            break

    session_record = StudentSessionRecord(
        student_id=str(student_id),
        concept_id=concept_id,
        iteration_count=len(probes_issued),
        initial_text=initial_text,
        probes_issued=probes_issued,
        student_revisions=student_revisions,
        final_verdict=final_verdict,  # type: ignore[arg-type]
        tagged_fallacy=tagged_fallacy,
    )

    # 1. Append to durable SQLite Store
    ctx.append("session_record", session_record.model_dump(), produced_by="agent:feynman_logger")

    # 2. Persist to local JSON file for Member 4 batch aggregator
    students_dir = Path("data/students")
    students_dir.mkdir(parents=True, exist_ok=True)
    out_file = students_dir / f"{student_id}.json"
    out_file.write_text(session_record.model_dump_json(indent=2), encoding="utf-8")

    # 3. Optional hook for batch aggregation check
    try:
        from .batch import check_and_escalate_batch  # type: ignore
        check_and_escalate_batch(ctx)
    except (ImportError, AttributeError):
        pass

    return session_record


# ---------------------------------------------------------------------------
# The Flow Factory
# ---------------------------------------------------------------------------

def build_flow(call: Callable = complete) -> SimpleNamespace:
    """
    Constructs the Feynman Check state machine flow.
    `call` is dependency-injected: defaults to live LLM `complete`,
    or accepts `stub_complete` for zero-token deterministic offline execution.
    """

    def handle_await_explanation(ctx: Context) -> RunState:
        """
        State: AWAIT_EXPLANATION (DRAFTING)
        Ingests the student's explanation (initial or revision) and routes to CRITIC_EVALUATE.
        """
        submissions = ctx.history("submission")
        probes = ctx.history("probe")
        meta = ctx.store.meta(ctx.run_id)

        # --------------------------------------------------------- Initial Submission
        if not submissions:
            # Check for initial input in store
            input_entry = ctx.latest("input")
            if input_entry:
                student_id = input_entry.get("student_id") or meta.get("student_id", "20231035053")
                concept_id = input_entry.get("concept_id") or meta.get("concept_id", "virtual_memory")
                text = input_entry.get("text", "")
            else:
                student_id = meta.get("student_id", "20231035053")
                concept_id = meta.get("concept_id", "virtual_memory")
                text = meta.get("text", "")

            ctx.append(
                "submission",
                {
                    "student_id": str(student_id),
                    "concept_id": concept_id,
                    "text": text,
                    "iteration": 0,
                },
                produced_by="student:initial",
            )
            return CRITIC_EVALUATE

        # --------------------------------------------------------- Back-Edge Revision
        # We returned to AWAIT_EXPLANATION because a SOCRATIC_PROBE was issued.
        # Check if a revision text was already supplied or if we can supply from canned/simulated profile.
        current_probe_count = len(probes)
        current_submission_count = len(submissions)

        if current_submission_count <= current_probe_count:
            # Need revision for the latest probe
            student_id = submissions[0].payload.get("student_id", "")
            student_name = meta.get("student_name") or student_id
            canned = get_canned_student(student_name)

            if canned and canned.get("revision_text"):
                revision_text = canned["revision_text"]
            else:
                # Check meta for a queued revision
                queued_revisions = meta.get("revisions", [])
                rev_idx = current_probe_count - 1
                if rev_idx < len(queued_revisions):
                    revision_text = queued_revisions[rev_idx]
                else:
                    # In simulated or headless runs without interactive input, fall back to canned or empty
                    revision_text = "Revised explanation acknowledging page table in RAM."

            ctx.append(
                "submission",
                {
                    "student_id": str(student_id),
                    "concept_id": submissions[0].payload.get("concept_id", "virtual_memory"),
                    "text": revision_text,
                    "iteration": current_probe_count,
                },
                produced_by="student:revision",
            )

        return CRITIC_EVALUATE

    def handle_critic_evaluate(ctx: Context) -> RunState:
        """
        State: CRITIC_EVALUATE (GATING)
        Evaluates the student explanation against ground truth invariants.
        Routes to SOCRATIC_PROBE (Back-Edge) if flawed, or LOG_STUDENT_STATE if mastered / bounded.
        """
        latest_sub = ctx.latest("submission")
        if not latest_sub:
            ctx.append("failure", {"kind": "missing_submission", "detail": "No student submission found"}, produced_by="runner")
            return FAILED

        concept_id = latest_sub.get("concept_id", "virtual_memory")
        ground_truth = load_concept_ground_truth(concept_id)

        prior_verdicts = [v.payload for v in ctx.history("verdict")]
        prior_probes = [p.payload for p in ctx.history("probe")]

        # Call Critic agent
        messages = build_critic_messages(
            concept_ground_truth=ground_truth,
            student_text=latest_sub.get("text", ""),
            prior_verdicts=prior_verdicts,
            prior_probes=prior_probes,
        )

        verdict: CriticVerdict = call(
            settings=ctx.settings,
            budget=ctx.budget,
            messages=messages,
            schema=CriticVerdict,
            step="critic",
        )

        ctx.append("verdict", verdict.model_dump(), produced_by="agent:critic")

        # --------------------------------------------------------- Mastered Case
        if verdict.verdict == "MASTERED":
            log_student_session_state(ctx, final_verdict="MASTERED")
            return COMPLETE

        # --------------------------------------------------------- Misconception / Ambiguous Case
        # Count revisions strictly from verdict history count
        # (prior_verdicts has verdicts BEFORE this one; so len(prior_verdicts) is the revision index)
        revision_attempts = len(prior_verdicts)

        if revision_attempts < MAX_REVISIONS:
            # Work goes backward: generate a Socratic probe!
            return SOCRATIC_PROBE

        # Reached revision bound (>= 2 iterations without mastering)
        # Escalates as unresolved
        log_student_session_state(ctx, final_verdict="UNRESOLVED_ESCALATE")
        return COMPLETE

    def handle_socratic_probe(ctx: Context) -> RunState:
        """
        State: SOCRATIC_PROBE (PROBING)
        Constructs a targeted counter-example scenario exposing the student's misconception.
        Transitions BACKWARD to AWAIT_EXPLANATION (The Back-Edge).
        """
        latest_sub = ctx.latest("submission")
        latest_verdict = ctx.latest("verdict")
        concept_id = latest_sub.get("concept_id", "virtual_memory") if latest_sub else "virtual_memory"
        ground_truth = load_concept_ground_truth(concept_id)

        messages = build_probe_messages(
            concept_ground_truth=ground_truth,
            student_text=latest_sub.get("text", "") if latest_sub else "",
            verdict=latest_verdict or {},
        )

        probe: ProbeMessage = call(
            settings=ctx.settings,
            budget=ctx.budget,
            messages=messages,
            schema=ProbeMessage,
            step="probe",
        )

        ctx.append("probe", probe.model_dump(), produced_by="agent:socratic_tutor")

        # The Back-Edge: Work transitions backward to AWAIT_EXPLANATION
        return AWAIT_EXPLANATION

    return SimpleNamespace(
        name="feynman",
        handlers={
            AWAIT_EXPLANATION: handle_await_explanation,
            CRITIC_EVALUATE:   handle_critic_evaluate,
            SOCRATIC_PROBE:    handle_socratic_probe,
        },
    )
