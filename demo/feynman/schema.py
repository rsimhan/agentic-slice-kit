"""
Pydantic contracts and data models for Socratic Feynman Check & Batch Gap Ping.

Defines schemas for:
- Critic evaluation verdicts
- Socratic counter-example probes
- Student session persistence records
- Batch misconception clusters
- Professor escalation reports
- Ground-truth concept invariants
"""
from __future__ import annotations

from typing import List, Optional, Literal
from pydantic import BaseModel, Field, field_validator


class ConceptInvariant(BaseModel):
    """Ground truth invariant for a lecture concept."""

    concept_id: str
    invariant_statement: str
    common_fallacy_patterns: List[str] = Field(default_factory=list)


class CriticVerdict(BaseModel):
    """
    Structured outcome of the Critic evaluating a student's explanation.

    verdict:
      - MASTERED: accurately explains the invariant without conflations.
      - MISCONCEPTION: commits a clear conceptual fallacy / violates invariant.
      - AMBIGUOUS: vague, circular, or incomplete explanation.
    """

    verdict: Literal["MASTERED", "MISCONCEPTION", "AMBIGUOUS"]
    detected_flaw_tag: Optional[str] = None
    flaw_explanation: Optional[str] = None
    violates_invariant: bool = False
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)

    @field_validator("verdict", mode="before")
    @classmethod
    def normalize_verdict(cls, v: str) -> str:
        if isinstance(v, str):
            v_upper = v.strip().upper()
            if v_upper in ("FALLACY_DETECTED", "FALLACY", "FLAW"):
                return "MISCONCEPTION"
            return v_upper
        return v


class ProbeMessage(BaseModel):
    """
    Diagnostic Socratic counter-example probe issued to the student.
    Forces cognitive dissonance without giving away the invariant answer.
    """

    probe_id: str
    counter_example_scenario: str
    target_invariant: str


class StudentSessionRecord(BaseModel):
    """
    Full audit record of a single student's Feynman Check session,
    serialized to data/students/{student_id}.json.
    """

    student_id: str
    concept_id: str
    iteration_count: int = Field(default=0, ge=0, le=2)
    initial_text: str
    probes_issued: List[str] = Field(default_factory=list, max_length=2)
    student_revisions: List[str] = Field(default_factory=list, max_length=2)
    final_verdict: Literal["MASTERED", "UNRESOLVED_ESCALATE", "ABANDONED"]
    tagged_fallacy: Optional[str] = None

    @field_validator("final_verdict", mode="before")
    @classmethod
    def normalize_final_verdict(cls, v: str) -> str:
        if isinstance(v, str):
            v_upper = v.strip().upper()
            if v_upper in ("RESOLVED", "PASS", "PASSED"):
                return "MASTERED"
            return v_upper
        return v


class BatchMisconceptionCluster(BaseModel):
    """
    Aggregated telemetry for a specific fallacy tag detected across the cohort.
    Triggers professor escalation when occurrence_count >= 3.
    """

    fallacy_tag: str
    occurrence_count: int = Field(default=1, ge=1)
    affected_student_ids: List[str] = Field(default_factory=list)
    sample_student_quotes: List[str] = Field(min_length=1, max_length=5)
    remediation_suggestion: str


class ProfessorEscalationReport(BaseModel):
    """
    High-priority gap report surfaced to the instructor when the alert threshold
    is reached (>= 3 students exhibiting the same fallacy).
    """

    report_id: str
    concept_id: str
    timestamp: str
    cluster: BatchMisconceptionCluster
    status: Literal["WAITING_ACK", "ACKNOWLEDGED", "DISMISSED"] = "WAITING_ACK"


class StudentSubmission(BaseModel):
    """Free-text submission from a student (initial or revision)."""

    student_id: str
    concept_id: str
    text: str
    iteration: int = Field(default=0, ge=0, le=2)
