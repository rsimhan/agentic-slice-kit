# contracts/api_contracts.py
# API REQUEST/RESPONSE MODELS — Used by Person 5 (API) and frontend

from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field
from datetime import datetime
from contracts.schemas import (
    ConceptNode, Test, Question, Attempt, Diagnosis,
    NoteVersion, TeacherNoteVersion, ReviewResult, AnalysisPayload,
    ClassAnalytics, TeacherConfirmation, RunState, GraphEdge, ConceptGraph,
    RunRecord
)


# ─── Teacher Endpoints ────────────────────────────────────────────────────

class CreateConceptRequest(BaseModel):
    markdown: str = Field(min_length=1, max_length=10000)
    concept_name: str = Field(min_length=1, max_length=100)


class CreateConceptResponse(BaseModel):
    concept: ConceptNode
    run_id: str


class ConfirmTagsRequest(BaseModel):
    run_id: str
    confirmed: bool
    edited_concepts: Optional[list[ConceptNode]] = None


class ConfirmTagsResponse(BaseModel):
    # Test generation is async — returns run_id for polling /runs/{run_id}/status
    # 202 Accepted if generation started, 200 if already complete
    run_id: str
    state: RunState
    test: Optional[Test] = None  # Present only if state == TEST_READY
    error: Optional[str] = None  # Present if state == FAILED


class TeacherAnalyticsResponse(BaseModel):
    concept_id: str
    concept_name: str
    analytics: ClassAnalytics


class TeacherTrendsResponse(BaseModel):
    concept_id: str
    trends: list[AnalysisPayload]


# ─── Student Endpoints ────────────────────────────────────────────────────

class SubmitAttemptRequest(BaseModel):
    # ONLY answers accepted from client — score/total are SERVER-OWNED
    test_id: str
    answers: dict[str, str] = Field(default_factory=dict)  # question_id -> answer


class SubmitAttemptResponse(BaseModel):
    # Server-computed attempt with authoritative score/total
    attempt: Attempt
    diagnosis: Diagnosis
    note: NoteVersion
    review: ReviewResult
    analysis: AnalysisPayload


class StudentNotesResponse(BaseModel):
    notes: list[NoteVersion]


class StudentGraphResponse(BaseModel):
    nodes: list[ConceptNode]
    edges: list[GraphEdge]


# ─── Teacher-Facing Student Data (Privacy-Safe) ───────────────────────────

class TeacherStudentNotesResponse(BaseModel):
    """Teacher view of student notes — excludes private markdown"""
    notes: list[TeacherNoteVersion]


# ─── Runtime / Shared ─────────────────────────────────────────────────────

class RunStatusResponse(BaseModel):
    run_id: str
    state: RunState
    current_cycle: int
    revision_count: int
    model_call_count: int
    test_generation_retry_count: int = 0
    test_generation_error: Optional[str] = None
    error: Optional[str] = None


class ErrorResponse(BaseModel):
    error: str
    message: str
    details: dict = Field(default_factory=dict)


# ─── HTTP Status Code Mapping (Documentation) ─────────────────────────────
# These are not runtime models but document expected behavior:
#
# 200 OK — Successful GET, PUT, PATCH
# 201 Created — Successful POST (CreateConcept, SubmitAttempt)
# 202 Accepted — Async operation started (ConfirmTags → test generation)
# 400 Bad Request — Validation error (pydantic)
# 401 Unauthorized — Missing/invalid auth
# 403 Forbidden — Authz failure (e.g., teacher accessing student notes)
# 404 Not Found — Resource not found
# 409 Conflict — State machine transition invalid
# 422 Unprocessable Entity — Semantic validation error
# 429 Too Many Requests — Rate limit exceeded
# 500 Internal Server Error — Unexpected failure
# 503 Service Unavailable — LLM service down


# ─── TypeScript Generation Hint ───────────────────────────────────────────
# Run `python scripts/sync_types.py` to generate contracts/types.ts
# This file is the single source of truth for all API shapes.