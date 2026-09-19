from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime, timezone


@dataclass
class Hypothesis:
    id: str
    label: str
    rationale: str
    status: str = "active"  # active/passed/rejected/uncertain
    evidence_ids: list[str] = field(default_factory=list)


@dataclass
class DiagnosticCheck:
    id: str
    hypothesis_id: str
    question: str
    response: Optional[str] = None
    result: Optional[str] = None  # supports/contradicts/uncertain
    evidence_note: str = ""


@dataclass
class StudentState:
    student_id: str
    topic: str
    checks: list[DiagnosticCheck] = field(default_factory=list)
    hypotheses: list[Hypothesis] = field(default_factory=list)
    current_gap: Optional[str] = None
    confidence: str = "low"
    confirmation_status: str = "none"
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class DiagnosticRun:
    run_id: str
    student_id: str
    state: str = "START"
    attempts_used: int = 0
    revisions_used: int = 0
    outcome: Optional[str] = None
