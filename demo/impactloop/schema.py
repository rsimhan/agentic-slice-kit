from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class StudentGoal(BaseModel):
    student_name: str
    goal: str
    current_skills: list[str]
    time_available: str
    desired_capability: str


class ProjectBrief(BaseModel):
    project_title: str
    problem_to_solve: str
    objective: str
    tasks: list[str]
    deliverables: list[str]
    required_capabilities: list[str]
    evidence_requirements: list[str]


class VerificationResult(BaseModel):
    status: Literal["PASS", "REVISION_REQUIRED"]
    reason: str
    missing_evidence: list[str] = Field(default_factory=list)


class ProofOfAbility(BaseModel):
    capability: str
    contribution: str
    evidence: list[str]
    verification_status: Literal["verified"]


class StudentMatch(BaseModel):
    student_name: str
    role: str
    reason: str
    matched_capabilities: list[str]


class TeamProposal(BaseModel):
    members: list[StudentMatch]
    unresolved_gaps: list[str] = Field(default_factory=list)


class TaskPlan(BaseModel):
    tasks: list[str]
    owners: dict[str, str]
    acceptance_conditions: dict[str, str]
    evidence_requirements: list[str]


class MentorDecision(BaseModel):
    question: str
    decision: str
    priority: str
    answered_by: str


class OpportunityRecommendation(BaseModel):
    opportunity_title: str
    explanation: str
    matched_evidence: list[str]
