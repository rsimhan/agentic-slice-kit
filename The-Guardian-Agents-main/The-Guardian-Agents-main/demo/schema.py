"""Domain schemas for the Synapse adaptive learning cycle.

Records passed between steps in the Synapse agentic slice.
Nothing crosses a step boundary as unvalidated prose.
"""
from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field


class CanonicalNoteInput(BaseModel):
    """The canonical note provided by the teacher."""
    concept_id: str = Field(description="Unique identifier for the primary concept")
    title: str = Field(description="Title of the topic/concept")
    markdown: str = Field(description="Canonical explanation written by the teacher")
    key_terms: list[str] = Field(default_factory=list, description="Key terms and prerequisite concepts")


class AttemptInput(BaseModel):
    """The student's submitted assessment attempt."""
    student_id: str = Field(description="Unique student identifier")
    test_id: str = Field(description="Test/assessment identifier")
    concept_id: str = Field(description="Concept being tested")
    answers: dict[str, str] = Field(description="Map of question_id -> chosen answer")


class DiagnosisItem(BaseModel):
    """One diagnostic finding for a student mistake."""
    question_id: str = Field(description="Question where mistake occurred")
    concept: str = Field(description="Concept or prerequisite involved")
    classification: Literal[
        "conceptual_gap", "careless_mistake", "contradictory", "unrelated", "empty"
    ] = Field(description="Nature of the mistake")
    reason: str = Field(description="Explanation of what the student misunderstood")


class DiagnosisRecord(BaseModel):
    """AI diagnostic analysis of the student's attempt."""
    student_id: str
    concept_id: str
    items: list[DiagnosisItem] = Field(default_factory=list)
    summary: str = Field(description="Brief summary of learning gaps to address")


class TailoredNoteRecord(BaseModel):
    """Personalized tailored remediation note generated for the student."""
    version: int = Field(default=1, description="Iteration number (v1, v2, etc.)")
    student_id: str
    concept_id: str
    markdown: str = Field(description="Personalized pedagogical remediation note")
    addressed_gaps: list[str] = Field(
        default_factory=list, description="List of mistake concepts addressed"
    )
    prerequisite_links: list[str] = Field(
        default_factory=list, description="Referenced concept links in [[concept]] format"
    )


class Objection(BaseModel):
    """One specific defect in a candidate tailored note identified by the reviewer."""
    field: str = Field(description="Which section or property is flawed (e.g. 'coverage', 'prerequisite')")
    problem: str = Field(description="Specific defect quoting the problem or missing concept")


class ReviewVerdict(BaseModel):
    """Reviewer judgement on the tailored note. The only record that moves the run."""
    status: Literal["PASS", "BLOCK"] = Field(description="Review verdict")
    canonical_coverage: bool = Field(default=True, description="Whether canonical facts are accurately preserved")
    objections: list[Objection] = Field(
        default_factory=list, description="List of actionable objections if blocked"
    )
    verdict_note: str = Field(default="", description="Summary explanation of the verdict")
