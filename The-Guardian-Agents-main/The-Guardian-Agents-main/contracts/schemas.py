# contracts/schemas.py
# SOURCE OF TRUTH — All teammates import from here
# DO NOT MODIFY without team consensus and PR approval

from __future__ import annotations
from enum import Enum
from typing import Optional, Literal, Annotated
from pydantic import BaseModel, Field, field_validator, ConfigDict
from datetime import datetime
import uuid


# ════════════════════════════════════════════════════════════════════════════
# ENUMS
# ════════════════════════════════════════════════════════════════════════════

class RunState(str, Enum):
    TEACHER_SETUP = "teacher_setup"
    TAG_CONFIRMATION = "tag_confirmation"
    TEST_GENERATING = "test_generating"
    TEST_READY = "test_ready"
    AWAITING_STUDENT = "awaiting_student"
    ATTEMPT_RECEIVED = "attempt_received"
    DIAGNOSING = "diagnosing"
    TAILORING = "tailoring"
    REVIEWING = "reviewing"
    NOTE_SAVED = "note_saved"
    ANALYSING = "analysing"
    AGGREGATING = "aggregating"
    COMPLETE = "complete"
    FAILED = "failed"


class MistakeClassification(str, Enum):
    CONCEPTUAL_GAP = "conceptual_gap"
    CARELESS_MISTAKE = "careless_mistake"
    CONTRADICTORY = "contradictory"
    UNRELATED = "unrelated"
    EMPTY = "empty"


class TrendLabel(str, Enum):
    NEW = "new"
    IMPROVING = "improving"
    STABLE = "stable"
    STILL_WEAK = "still_weak"
    DECLINING = "declining"


class ReviewStatus(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    REVISION_LIMIT_REACHED = "revision_limit_reached"


# ════════════════════════════════════════════════════════════════════════════
# CORE DOMAIN MODELS
# ════════════════════════════════════════════════════════════════════════════

class ConceptNode(BaseModel):
    model_config = ConfigDict(frozen=False)

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(min_length=1, max_length=100)
    summary: str = Field(min_length=1, max_length=500)
    prerequisites: list[str] = Field(default_factory=list)  # concept IDs
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class CanonicalNote(BaseModel):
    model_config = ConfigDict(frozen=False)

    concept_id: str
    markdown: str = Field(min_length=1)
    extracted_concepts: list[ConceptNode] = Field(default_factory=list)
    teacher_confirmed: bool = False
    confirmed_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Question(BaseModel):
    model_config = ConfigDict(frozen=False)

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    text: str = Field(min_length=1, max_length=500)
    correct_answer: str = Field(min_length=1, max_length=200)
    options: list[str] = Field(min_length=4, max_length=4)
    concept_id: str

    @field_validator('options')
    @classmethod
    def unique_options(cls, v: list[str]) -> list[str]:
        if len(set(v)) != len(v):
            raise ValueError('Options must be unique')
        return v


class Test(BaseModel):
    model_config = ConfigDict(frozen=False)

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    concept_id: str
    concept_name: str
    questions: list[Question] = Field(min_length=1)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Attempt(BaseModel):
    model_config = ConfigDict(frozen=False)

    student_id: str = Field(min_length=1)
    test_id: str
    concept_id: str
    answers: dict[str, str] = Field(default_factory=dict)  # question_id -> answer
    # score and total are SERVER-OWNED: computed by backend, never trusted from client
    score: int = Field(default=0, ge=0)
    total: int = Field(default=0, ge=0)
    submitted_at: datetime = Field(default_factory=datetime.utcnow)


class DiagnosisItem(BaseModel):
    model_config = ConfigDict(frozen=False)

    question_id: str
    classification: MistakeClassification
    reason: str = Field(min_length=1, max_length=300)


class Diagnosis(BaseModel):
    model_config = ConfigDict(frozen=False)

    student_id: str
    concept_id: str
    items: list[DiagnosisItem] = Field(default_factory=list)
    mastery_estimate: float = Field(ge=0.0, le=1.0)
    trend: TrendLabel
    created_at: datetime = Field(default_factory=datetime.utcnow)


class NoteVersion(BaseModel):
    model_config = ConfigDict(frozen=False)

    student_id: str
    concept_id: str
    version: int = Field(ge=1)
    markdown: str = Field(min_length=1)
    diagnosis_id: Optional[str] = None
    review_id: Optional[str] = None
    run_id: Optional[str] = None  # links to RunRecord for traceability
    created_at: datetime = Field(default_factory=datetime.utcnow)


# Teacher-facing view of NoteVersion — excludes private markdown
class TeacherNoteVersion(BaseModel):
    model_config = ConfigDict(frozen=False)

    student_id: str
    concept_id: str
    version: int
    diagnosis_id: Optional[str] = None
    review_id: Optional[str] = None
    run_id: Optional[str] = None
    created_at: datetime


class ReviewResult(BaseModel):
    model_config = ConfigDict(frozen=False)

    passed: bool
    canonical_coverage: bool
    diagnosis_addressed: bool
    links_valid: bool
    objections: list[str] = Field(default_factory=list)
    status: ReviewStatus
    created_at: datetime = Field(default_factory=datetime.utcnow)


class AnalysisPayload(BaseModel):
    model_config = ConfigDict(frozen=False)

    student_id: str
    concept_id: str
    mastery_estimate: float = Field(ge=0.0, le=1.0)
    trend: TrendLabel
    cycle_number: int = Field(ge=1)
    run_id: Optional[str] = None  # links to RunRecord
    created_at: datetime = Field(default_factory=datetime.utcnow)


class TeacherConfirmation(BaseModel):
    model_config = ConfigDict(frozen=False)

    concept_id: str
    teacher_id: str
    confirmed: bool
    edited_concepts: Optional[list[ConceptNode]] = None
    confirmed_at: Optional[datetime] = None
    timed_out: bool = False


# ════════════════════════════════════════════════════════════════════════════
# AGGREGATE / HISTORY MODELS
# ════════════════════════════════════════════════════════════════════════════

class StudentHistory(BaseModel):
    model_config = ConfigDict(frozen=False, arbitrary_types_allowed=True)

    student_id: str
    concept_id: str
    previous_diagnoses: list[Diagnosis] = Field(default_factory=list)
    previous_notes: list[NoteVersion] = Field(default_factory=list)
    mastery_history: list[tuple[int, float]] = Field(default_factory=list)  # [(cycle, mastery)]
    existing_concept_names: set[str] = Field(default_factory=set)


class ClassAnalytics(BaseModel):
    model_config = ConfigDict(frozen=False)

    concept_id: str
    concept_name: str
    student_count: int = Field(ge=0)
    average_mastery: float = Field(ge=0.0, le=1.0)
    trend_distribution: dict[TrendLabel, int] = Field(default_factory=dict)
    weak_students: list[str] = Field(default_factory=list)  # student_ids below MASTERY_WEAK_THRESHOLD
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# ════════════════════════════════════════════════════════════════════════════
# AGENT RUNTIME RECORDS
# ════════════════════════════════════════════════════════════════════════════

class RunRecord(BaseModel):
    model_config = ConfigDict(frozen=False)

    run_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    concept_id: str
    student_id: Optional[str] = None
    teacher_id: Optional[str] = None
    state: RunState = RunState.TEACHER_SETUP
    current_cycle: int = Field(default=1, ge=1)
    revision_count: int = Field(default=0, ge=0)
    model_call_count: int = Field(default=0, ge=0)
    test_generation_retry_count: int = Field(default=0, ge=0)
    test_generation_error: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    error: Optional[str] = None


class StepRecord(BaseModel):
    model_config = ConfigDict(frozen=False)

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    run_id: str
    step_name: str
    input_data: dict
    output_data: Optional[dict] = None
    state_before: RunState
    state_after: Optional[RunState] = None
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    retry_count: int = Field(default=0, ge=0)


# ════════════════════════════════════════════════════════════════════════════
# GRAPH MODELS (for student concept graph)
# ════════════════════════════════════════════════════════════════════════════

class GraphEdge(BaseModel):
    model_config = ConfigDict(frozen=False)

    from_concept_id: str
    to_concept_id: str
    edge_type: str = Field(default="prerequisite")  # prerequisite, related, etc.

    @field_validator('to_concept_id')
    @classmethod
    def no_self_reference(cls, v: str, info) -> str:
        from_id = info.data.get('from_concept_id')
        if from_id and v == from_id:
            raise ValueError('GraphEdge cannot reference the same concept (self-reference)')
        return v


class ConceptGraph(BaseModel):
    model_config = ConfigDict(frozen=False)

    nodes: list[ConceptNode]
    edges: list[GraphEdge]

    @field_validator('edges')
    @classmethod
    def validate_edges_reference_existing_nodes(cls, edges: list[GraphEdge], info) -> list[GraphEdge]:
        nodes = info.data.get('nodes', [])
        node_ids = {n.id for n in nodes}
        for edge in edges:
            if edge.from_concept_id not in node_ids:
                raise ValueError(f'Edge references unknown from_concept_id: {edge.from_concept_id}')
            if edge.to_concept_id not in node_ids:
                raise ValueError(f'Edge references unknown to_concept_id: {edge.to_concept_id}')
        return edges


# ════════════════════════════════════════════════════════════════════════════
# CONSTANTS (Architecture-level, not domain opinions)
# ════════════════════════════════════════════════════════════════════════════

MAX_REVISIONS_PER_CYCLE: int = 3
MAX_MODEL_CALL_RETRIES: int = 3
MAX_TEST_GENERATION_RETRIES: int = 3
TAG_CONFIRMATION_TIMEOUT_SECONDS: int = 600
MASTERY_WEAK_THRESHOLD: float = 0.5
DEFAULT_MASTERY_ESTIMATE: float = 0.5
SCHEMA_VERSION: int = 3