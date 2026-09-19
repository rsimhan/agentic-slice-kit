# contracts/state_machine.py
# STATE MACHINE LOGIC — Imported by agent_runtime and api

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Literal
from contracts.schemas import RunState, ReviewStatus, MAX_TEST_GENERATION_RETRIES


# Valid forward transitions
VALID_TRANSITIONS: dict[RunState, list[RunState]] = {
    RunState.TEACHER_SETUP: [RunState.TAG_CONFIRMATION],
    RunState.TAG_CONFIRMATION: [RunState.TEST_GENERATING, RunState.TEACHER_SETUP],  # teacher confirms -> generating, rejects -> back to setup
    RunState.TEST_GENERATING: [RunState.TEST_READY, RunState.TEST_GENERATING, RunState.FAILED],  # success, retry, permanent failure
    RunState.TEST_READY: [RunState.AWAITING_STUDENT],
    RunState.AWAITING_STUDENT: [RunState.ATTEMPT_RECEIVED],
    RunState.ATTEMPT_RECEIVED: [RunState.DIAGNOSING],
    RunState.DIAGNOSING: [RunState.TAILORING],
    RunState.TAILORING: [RunState.REVIEWING],
    RunState.REVIEWING: [RunState.NOTE_SAVED, RunState.TAILORING],
    RunState.NOTE_SAVED: [RunState.ANALYSING],
    RunState.ANALYSING: [RunState.AGGREGATING],
    RunState.AGGREGATING: [RunState.COMPLETE],
    RunState.COMPLETE: [RunState.AWAITING_STUDENT],  # New run for same concept
    RunState.FAILED: [],  # Terminal state - no forward transitions
}


@dataclass(frozen=True)
class TransitionRule:
    from_state: RunState
    to_state: RunState
    trigger: Literal["code", "model", "human", "timeout", "human_or_timeout"]
    description: str
    max_retries: int = 3


TRANSITION_RULES: list[TransitionRule] = [
    TransitionRule(RunState.TEACHER_SETUP, RunState.TAG_CONFIRMATION, "code", "Canonical note structured into concepts"),
    TransitionRule(RunState.TAG_CONFIRMATION, RunState.TEST_GENERATING, "code", "Teacher confirms/tags — test generation starts"),
    TransitionRule(RunState.TAG_CONFIRMATION, RunState.TEACHER_SETUP, "human", "Teacher rejects concepts — re-extraction needed"),
    TransitionRule(RunState.TEST_GENERATING, RunState.TEST_READY, "model", "Test generation succeeds"),
    TransitionRule(RunState.TEST_GENERATING, RunState.TEST_GENERATING, "model", "Test generation retry (bounded)"),
    TransitionRule(RunState.TEST_GENERATING, RunState.FAILED, "model", "Test generation failed permanently after max retries"),
    TransitionRule(RunState.TEST_READY, RunState.AWAITING_STUDENT, "code", "Test passes schema validation"),
    TransitionRule(RunState.AWAITING_STUDENT, RunState.ATTEMPT_RECEIVED, "code", "Student submits attempt"),
    TransitionRule(RunState.ATTEMPT_RECEIVED, RunState.DIAGNOSING, "code", "Auto-transition to diagnosis"),
    TransitionRule(RunState.DIAGNOSING, RunState.TAILORING, "model", "LLM produces diagnosis"),
    TransitionRule(RunState.TAILORING, RunState.REVIEWING, "code", "Candidate note produced"),
    TransitionRule(RunState.REVIEWING, RunState.NOTE_SAVED, "model", "Review passes"),
    TransitionRule(RunState.REVIEWING, RunState.TAILORING, "model", "Review fails → revision"),
    TransitionRule(RunState.NOTE_SAVED, RunState.ANALYSING, "code", "Note persisted"),
    TransitionRule(RunState.ANALYSING, RunState.AGGREGATING, "model", "Mastery/trend calculated"),
    TransitionRule(RunState.AGGREGATING, RunState.COMPLETE, "code", "Class summary updated"),
    TransitionRule(RunState.COMPLETE, RunState.AWAITING_STUDENT, "code", "New test cycle begins"),
]


# Failure → retry state (bounded by max_retries)
FAILURE_RETRY_STATE: dict[RunState, RunState] = {
    RunState.DIAGNOSING: RunState.DIAGNOSING,
    RunState.TAILORING: RunState.TAILORING,
    RunState.REVIEWING: RunState.TAILORING,  # Revision, not retry
    RunState.ANALYSING: RunState.ANALYSING,
    RunState.AGGREGATING: RunState.AGGREGATING,
    RunState.TEST_GENERATING: RunState.TEST_GENERATING,  # Retry test generation
}


def can_transition(from_state: RunState, to_state: RunState) -> bool:
    return to_state in VALID_TRANSITIONS.get(from_state, [])


def get_transition_rule(from_state: RunState, to_state: RunState) -> Optional[TransitionRule]:
    for rule in TRANSITION_RULES:
        if rule.from_state == from_state and rule.to_state == to_state:
            return rule
    return None


def can_revise(current_revisions: int, max_revisions: int = 3) -> bool:
    from contracts.schemas import MAX_REVISIONS_PER_CYCLE
    return current_revisions < max_revisions


def can_retry_test_generation(current_retries: int, max_retries: int = MAX_TEST_GENERATION_RETRIES) -> bool:
    return current_retries < max_retries