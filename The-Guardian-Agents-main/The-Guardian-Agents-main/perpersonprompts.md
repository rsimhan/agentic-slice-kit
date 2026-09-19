SECTION D — Five Copy-Paste-Ready Prompts
PROMPT 1 — Person 1: Agent Runtime + Persistence
# ROLE: Agent Runtime Engineer (Person 1)

## Project Context
You are building the **Agent Runtime + Persistence** layer for Synapse Cycle, a hackathon MVP that helps teachers diagnose student misconceptions and generate tailored private notes. The system uses a persistent state machine with SQLite storage, bounded retries/revisions, and human-in-the-loop checkpoints.

**Key Documents:** 
- AgentSpec-Synapse-Cycle.md (sections 6, 7, 10, 12)
- Synapse_Cycle_Per_Person_Build_Split.md (Person 1 section)

## Your Exact Responsibilities
Build the reusable agent runtime that orchestrates the Synapse state machine. You own:
- State machine execution engine
- SQLite persistence for runs, steps, and domain records
- Run IDs, revision counting, model call budgeting
- Pause/resume and restart-from-persistence
- Human-in-the-loop callback mechanism (teacher tag confirmation)
- Mock handlers for other teammates' development

## Files to Create/Modify
agent_runtime/
├── init.py
├── runner.py              # Main orchestrator
├── state_machine.py       # Transition logic (imports contracts.state_machine)
├── store.py               # SQLite persistence
├── records.py             # RunRecord, StepRecord (imports contracts.schemas)
├── budget.py              # Model call + revision budgets
├── callbacks.py           # Human-in-the-loop hooks
├── mocks.py               # Fake implementations for other teammates
└── tests/
    ├── test_state_machine.py
    ├── test_persistence.py
    ├── test_restart_resume.py
    ├── test_retry_limits.py
    ├── test_revision_limits.py
    └── test_callbacks.py

## Shared Contracts (Import Only — Do Not Modify)
```python
from contracts.schemas import (
    RunState, RunRecord, StepRecord, Diagnosis, NoteVersion,
    ReviewResult, AnalysisPayload, Attempt, Test, ConceptNode,
    MAX_REVISIONS_PER_CYCLE, MAX_MODEL_CALL_RETRIES, TAG_CONFIRMATION_TIMEOUT_SECONDS
)
from contracts.state_machine import (
    VALID_TRANSITIONS, TRANSITION_RULES, FAILURE_RETRY_STATE,
    can_transition, get_transition_rule, can_revise
)
Implementation Requirements
1. runner.py — Run Orchestrator
class AgentRunner:
    def __init__(self, store: Store, callbacks: CallbackRegistry, budget: BudgetTracker):
        ...
    
    async def start_run(self, concept_id: str, teacher_id: str) -> RunRecord:
        """Create new run in TEACHER_SETUP state."""
    
    async def resume_run(self, run_id: str) -> RunRecord:
        """Load run from DB, continue from persisted state."""
    
    async def transition(self, run_id: str, to_state: RunState, 
                         input_data: dict, output_data: dict | None = None) -> RunRecord:
        """Execute validated state transition, persist step record."""
    
    async def handle_human_callback(self, run_id: str, response: TeacherConfirmation) -> RunRecord:
        """Called when teacher confirms/tags or timeout fires."""
2. store.py — SQLite Persistence
- Single SQLite file: synapse.db
- Tables: runs, steps, concepts, tests, attempts, diagnoses, notes, reviews, analyses, teacher_summaries, teacher_answers
- Use WAL mode for concurrency
- Methods: save_run, load_run, save_step, get_steps, save_domain_record, load_domain_records
3. budget.py — Budget Tracking
class BudgetTracker:
    def __init__(self, max_model_calls: int = 50, max_revisions: int = 3):
        ...
    
    def can_call_model(self, run: RunRecord) -> bool:
        return run.model_call_count < self.max_model_calls
    
    def can_revise(self, run: RunRecord) -> bool:
        return run.revision_count < self.max_revisions
    
    def record_model_call(self, run: RunRecord) -> RunRecord:
        run.model_call_count += 1
        return run
    
    def record_revision(self, run: RunRecord) -> RunRecord:
        run.revision_count += 1
        return run
4. callbacks.py — Human-in-the-Loop
class CallbackRegistry:
    def __init__(self):
        self._waiting: dict[str, asyncio.Future] = {}
    
    async def wait_for_teacher(self, run_id: str, timeout: int) -> TeacherConfirmation:
        """Register waiter, return when teacher responds or timeout."""
    
    def resolve_teacher(self, run_id: str, confirmation: TeacherConfirmation):
        """Called by API when teacher POSTs confirmation."""
5. mocks.py — Fake Handlers for Other Teammates
class MockDiagnosisHandler:
    async def diagnose(self, attempt: Attempt, history: StudentHistory) -> Diagnosis:
        return load_fixture("diagnosis_fixture.json")

class MockTailoringHandler:
    async def tailor(self, diagnosis: Diagnosis, prev_note: NoteVersion | None) -> NoteVersion:
        return load_fixture("note_fixture.json")

class MockReviewHandler:
    async def review(self, note: NoteVersion, diagnosis: Diagnosis, canonical: CanonicalNote) -> ReviewResult:
        return load_fixture("review_pass.json")

class MockAnalyticsHandler:
    async def analyse(self, diagnosis: Diagnosis, note: NoteVersion) -> AnalysisPayload:
        return load_fixture("analysis_fixture.json")

class MockAggregationHandler:
    async def aggregate(self, payloads: list[AnalysisPayload]) -> ClassAnalytics:
        return load_fixture("analytics_fixture.json")
Unit Tests (Must Pass Before Merge)
Run: pytest agent_runtime/tests/ -v
Test	What It Verifies
test_state_machine.py	All valid transitions work; invalid transitions rejected
test_persistence.py	RunRecord/StepRecord round-trip; domain records persisted
test_restart_resume.py	Kill process mid-run → resume from correct state
test_retry_limits.py	DIAGNOSING/TAILORING/REVIEWING retry max 3 times
test_revision_limits.py	REVIEWING→TAILORING max 3 revisions per cycle
test_callbacks.py	Teacher confirmation resolves; timeout transitions to TEST_READY
Mock Strategy
- All external handlers (diagnosis, tailoring, review, analytics) are protocols injected via runner.py constructor
- mocks.py provides MockHandler implementations loading JSON fixtures from agent_runtime/fixtures/
- Unit tests use mocks; integration tests swap in real handlers
Acceptance Criteria
- pytest agent_runtime/tests/ passes (100%)
- Can run full state machine with mock handlers: TEACHER_SETUP → COMPLETE
- Process kill + resume works at every state
- Revision limit enforced (3 max) — run terminates with REVISION_LIMIT_REACHED
- Model call budget enforced (configurable, default 50)
- Teacher confirmation timeout transitions to TEST_READY with timed_out=true
- No imports from agents/, curriculum/, analytics/, api/
Integration Handoff
Person 5 (API) will import:
from agent_runtime.runner import AgentRunner
from agent_runtime.store import Store
from agent_runtime.callbacks import CallbackRegistry
from agent_runtime.budget import BudgetTracker
Person 5 provides real handler implementations that satisfy the protocols.
What NOT to Build
- ❌ Diagnosis, tailoring, review logic (Person 2)
- ❌ Curriculum/test generation (Person 3)
- ❌ Analytics/mastery/graph (Person 4)
- ❌ FastAPI routes, auth, frontend (Person 5)
- ❌ Schema definitions (in contracts/)

---

## PROMPT 2 — Person 2: Diagnosis + Tailoring + Review Agents

ROLE: AI Agent Engineer (Person 2)
Project Context
You are building the Student Intelligence pipeline — the core AI brain of Synapse Cycle. This module takes a student's test attempt and private history, produces a structured diagnosis, generates/updates a private markdown note, and validates it through a review loop.
Key Documents:
- AgentSpec-Synapse-Cycle.md (sections 3, 4, 5, 7, 8, 9)
- Synapse_Cycle_Per_Person_Build_Split.md (Person 2 section)
Your Exact Responsibilities
Build three LLM-powered agents with a revision loop:
1. Diagnosis Agent — Classify mistakes, estimate mastery, detect trends
2. Tailoring Agent — Create/update private markdown note with mistake patterns and [[Concept]] links
3. Review Agent — Validate note against diagnosis, canonical coverage, and link existence
Critical: The Review → Tailoring back-edge (revision loop) must work. Max 3 revisions per cycle.
Files to Create/Modify
agents/
├── __init__.py
├── diagnosis.py
├── tailoring.py
├── review.py
├── nim_adapter.py           # NVIDIA NIM client (with mock)
├── prompts/
│   ├── diagnosis.md
│   ├── tailoring.md
│   └── review.md
├── fixtures/
│   ├── attempt.json
│   ├── previous_note.json
│   ├── canonical_note.json
│   ├── diagnosis_responses.json
│   ├── tailored_notes.json
│   └── review_responses.json
└── tests/
    ├── test_diagnosis.py
    ├── test_tailoring.py
    ├── test_review.py
    └── test_revision_loop.py
Shared Contracts (Import Only)
from contracts.schemas import (
    Attempt, StudentHistory, Diagnosis, DiagnosisItem,
    MistakeClassification, TrendLabel, NoteVersion,
    CanonicalNote, ReviewResult, ReviewStatus,
    ConceptNode, MAX_REVISIONS_PER_CYCLE
)
Implementation Requirements
1. nim_adapter.py — NVIDIA NIM Client
class NIMAdapter:
    def __init__(self, api_key: str, base_url: str, model: str = "nemotron-3-ultra"):
        ...
    
    async def structured_completion(self, prompt: str, response_model: type[BaseModel]) -> BaseModel:
        """Call NIM with JSON schema enforcement, return parsed Pydantic model."""
    
    async def raw_completion(self, prompt: str) -> str:
        """Raw text completion for prompts not needing structured output."""

class MockNIMAdapter:
    """Deterministic fake for unit tests — loads from fixtures."""
    def __init__(self, fixture_dir: Path):
        self.fixtures = load_all_fixtures(fixture_dir)
        self.call_count = 0
    
    async def structured_completion(self, prompt: str, response_model: type[BaseModel]) -> BaseModel:
        self.call_count += 1
        fixture_key = self._match_fixture(prompt)
        return response_model.model_validate(self.fixtures[fixture_key])
    
    async def raw_completion(self, prompt: str) -> str:
        self.call_count += 1
        return self.fixtures["default_response"]
2. diagnosis.py — Diagnosis Agent
async def diagnose(
    attempt: Attempt,
    history: StudentHistory,
    nim: NIMAdapter,
    canonical_note: CanonicalNote
) -> Diagnosis:
    """
    Input: student attempt + full private history + canonical concept
    Output: Diagnosis with items, mastery_estimate, trend
    
    Classifications: conceptual_gap, careless_mistake, contradictory, unrelated, empty
    Trend logic: 
      - No history → "new"
      - Mastery improved >0.15 → "improving"
      - Mastery declined >0.15 → "declining"
      - Mastery <0.5 and not improving → "still_weak"
      - Else → "stable"
    """
    # 1. Build prompt with attempt, history, canonical note
    # 2. Call nim.structured_completion(Diagnosis)
    # 3. Validate: every wrong answer has item; mastery 0-1; trend valid enum
    # 4. Return Diagnosis
3. tailoring.py — Tailoring Agent
async def tailor_note(
    diagnosis: Diagnosis,
    previous_note: NoteVersion | None,
    existing_concepts: set[str],
    nim: NIMAdapter,
    canonical_note: CanonicalNote
) -> NoteVersion:
    """
    Input: diagnosis + previous note (or None) + student's existing concept names
    Output: NoteVersion with markdown containing:
      - Explanation addressing diagnosed gaps
      - Mistake pattern table (Question | Your Answer | Correct Idea | What Happened)
      - [[Concept]] links ONLY for concepts in existing_concepts
    
    Link validation: deterministic check in review step, not here
    """
    # 1. Build prompt with diagnosis, previous note, canonical note, existing concepts
    # 2. Call nim.raw_completion() → markdown string
    # 3. Parse version: previous_note.version + 1 if exists else 1
    # 4. Return NoteVersion
4. review.py — Review Agent
async def review_note(
    note: NoteVersion,
    diagnosis: Diagnosis,
    canonical_note: CanonicalNote,
    existing_concepts: set[str],
    nim: NIMAdapter
) -> ReviewResult:
    """
    Deterministic checks (code, not LLM):
    - canonical_coverage: note covers all canonical concept points
    - diagnosis_addressed: every diagnosis item reflected in note
    - links_valid: every [[Concept]] in note exists in existing_concepts
    
    LLM check (model judgment):
    - Overall quality: does note actually help the student?
    
    Returns ReviewResult with passed=True/False and objections list.
    """
    # 1. Run deterministic checks first
    # 2. If any fail → return ReviewResult(passed=False, objections=...)
    # 3. Else call LLM for quality judgment
    # 4. Return ReviewResult
5. Prompts (in prompts/*.md)
- diagnosis.md: System + user prompt template with {attempt}, {history}, {canonical}
- tailoring.md: System + user prompt with {diagnosis}, {previous_note}, {canonical}, {existing_concepts}
- review.md: System + user prompt with {note}, {diagnosis}, {canonical}
Unit Tests (Must Pass Before Merge)
Run: pytest agents/tests/ -v
Test	Fixture	What It Verifies
test_diagnosis.py	attempt.json, history.json	Conceptual gap, careless, multiple, perfect, empty, contradictory
test_tailoring.py	diagnosis.json, prev_note.json	New note, update note, link inclusion, link rejection
test_review.py	note.json, diagnosis.json	Pass, fail coverage, fail diagnosis, fail links, fail quality
test_revision_loop.py	Sequence of fixtures	Review FAIL → Tailoring → Review PASS (max 3)
Fixtures: Save real NIM responses in fixtures/ for deterministic tests. Commit fixtures.
Mock Strategy
- MockNIMAdapter in nim_adapter.py returns pre-recorded fixtures
- Unit tests inject MockNIMAdapter — zero live NIM calls
- diagnose(), tailor_note(), review_note() are pure async functions — easy to test
Acceptance Criteria
- pytest agents/tests/ passes (100%)
- diagnose() returns valid Diagnosis for all 6 fixture cases
- tailor_note() produces markdown with mistake table + valid [[links]]
- review_note() catches: missing coverage, unaddressed diagnosis, invalid links, poor quality
- Revision loop: Review FAIL → tailor again → Review PASS (tested in test_revision_loop.py)
- No imports from agent_runtime/, curriculum/, analytics/, api/
- All LLM calls go through NIMAdapter protocol (swappable)
Integration Handoff
Person 1 (Runtime) and Person 5 (API) will call:
from agents.diagnosis import diagnose
from agents.tailoring import tailor_note
from agents.review import review_note
from agents.nim_adapter import NIMAdapter, MockNIMAdapter
They provide real NIMAdapter at integration time.
What NOT to Build
- ❌ State machine, persistence, run orchestration (Person 1)
- ❌ Curriculum parsing, test generation, teacher confirmation (Person 3)
- ❌ Analytics, mastery calc, graph, dashboard (Person 4)
- ❌ FastAPI, auth, frontend (Person 5)
- ❌ Schema definitions (in contracts/)

---

## PROMPT 3 — Person 3: Curriculum + Test Generation

ROLE: Curriculum & Test Generation Engineer (Person 3)
Project Context
You own the teacher-facing curriculum pipeline: transforming a teacher's canonical markdown note into structured concepts, getting teacher confirmation on tags, and generating a validated MCQ test.
Key Documents:
- AgentSpec-Synapse-Cycle.md (sections 4, 5, 7, 8, 10)
- Synapse_Cycle_Per_Person_Build_Split.md (Person 3 section)
Your Exact Responsibilities
Build the end-to-end curriculum pipeline:
1. Curriculum Agent — Parse canonical markdown → extract ConceptNode[]
2. Tag Confirmation — Present inferred tags to teacher, handle confirmation/timeout
3. Test Generator — Generate MCQ test from confirmed concept (4-option, tied to concept)
Files to Create/Modify
curriculum/
├── __init__.py
├── curriculum_agent.py
├── test_generator.py
├── tag_confirmation.py
├── nim_adapter.py
├── prompts/
│   ├── concept_extraction.md
│   ├── test_generation.md
│   └── tag_confirmation.md
├── fixtures/
│   ├── canonical_note.md
│   ├── concept_nodes.json
│   ├── teacher_confirmations.json
│   └── test_outputs.json
└── tests/
    ├── test_concept_extraction.py
    ├── test_tag_confirmation.py
    └── test_generation.py
Shared Contracts (Import Only)
from contracts.schemas import (
    ConceptNode, CanonicalNote, Test, Question,
    TeacherConfirmation, MistakeClassification
)
from contracts.state_machine import (
    RunState, TAG_CONFIRMATION_TIMEOUT_SECONDS
)
Implementation Requirements
1. curriculum_agent.py — Concept Extraction
async def extract_concepts(
    canonical_note: CanonicalNote,
    nim: NIMAdapter
) -> list[ConceptNode]:
    """
    Input: CanonicalNote with raw markdown
    Output: List of ConceptNode with stable IDs, names, summaries
    
    Each concept must have:
    - Unique name (e.g., "Recursion", "Base Case", "Recursive Case")
    - Summary capturing the key idea
    - Stable UUID (persisted)
    """
    # 1. Prompt LLM to structure markdown into discrete concepts
    # 2. Validate: no duplicate names, each has summary
    # 3. Return ConceptNode[]
2. tag_confirmation.py — Teacher Confirmation
class TagConfirmationService:
    def __init__(self, timeout_seconds: int = TAG_CONFIRMATION_TIMEOUT_SECONDS):
        self.pending: dict[str, asyncio.Future] = {}
        self.timeout_seconds = timeout_seconds
    
    async def request_confirmation(
        self, run_id: str, concepts: list[ConceptNode]
    ) -> TeacherConfirmation:
        """Store concepts, return future that resolves on teacher POST or timeout."""
    
    async def submit_confirmation(
        self, run_id: str, confirmed: bool, edited_concepts: list[ConceptNode] | None
    ) -> TeacherConfirmation:
        """Called by API when teacher responds."""
    
    def _on_timeout(self, run_id: str):
        """Auto-resolve with timed_out=true, use inferred concepts."""
3. test_generator.py — MCQ Generation
async def generate_test(
    concept: ConceptNode,
    canonical_note: CanonicalNote,
    nim: NIMAdapter,
    num_questions: int = 3
) -> Test:
    """
    Input: Confirmed ConceptNode + canonical note
    Output: Test with questions:
      - Exactly 4 options each
      - Correct answer present in options
      - No duplicate options
      - Each question tied to concept_id
      - Questions test distinct aspects (base case, recursive case, termination)
    
    Validation (deterministic, not LLM):
    - Schema valid
    - 4 unique options per question
    - Correct answer in options
    - Question text non-empty
    """
    # 1. Prompt LLM for questions
    # 2. Validate each question deterministically
    # 3. Retry up to 3 times if validation fails
    # 4. Return Test
4. Prompts
- concept_extraction.md: "Break this canonical note into discrete, testable concepts..."
- test_generation.md: "Generate 3 MCQs testing distinct aspects of Concept..."
- tag_confirmation.md: (Not an LLM prompt — UI text for teacher)
Unit Tests (Must Pass Before Merge)
Run: pytest curriculum/tests/ -v
Test	What It Verifies
test_concept_extraction.py	Canonical markdown → valid ConceptNode[]; stable IDs; no duplicates
test_tag_confirmation.py	Teacher confirms → returns confirmed; Teacher edits → returns edited; Timeout → timed_out=true with inferred
test_generation.py	Test schema valid; 4 options; correct in options; no duplicates; concept-linked
Mock Strategy
- MockNIMAdapter in nim_adapter.py returns fixtures from fixtures/
- tag_confirmation.py tested with fake asyncio.Future resolution
- No live NIM calls in unit tests
Acceptance Criteria
- pytest curriculum/tests/ passes (100%)
- extract_concepts() produces stable ConceptNodes from canonical markdown
- generate_test() produces valid Test with 3 questions, 4 unique options each
- Tag confirmation: teacher confirm/edit/timeout all work
- Timeout uses inferred concepts, marks timed_out=true
- No imports from agent_runtime/, agents/, analytics/, api/
Integration Handoff
Person 5 (API) will call:
from curriculum.curriculum_agent import extract_concepts
from curriculum.test_generator import generate_test
from curriculum.tag_confirmation import TagConfirmationService
Person 1 (Runtime) manages the run state transitions around these calls.
What NOT to Build
- ❌ Diagnosis, tailoring, review (Person 2)
- ❌ State machine, persistence (Person 1)
- ❌ Analytics, mastery, graph, dashboard (Person 4)
- ❌ FastAPI, auth, frontend (Person 5)
- ❌ Schema definitions (in contracts/)

---

## PROMPT 4 — Person 4: Analytics + Mastery + Graph + Dashboard

ROLE: Analytics & Visualization Engineer (Person 4)
Project Context
You own both teacher analytics and student concept graph — combined because both are derived-data visualization logic. You build the aggregation pipeline, mastery/trend calculations, concept graph parsing, and the React dashboards for teacher and student.
Key Documents:
- AgentSpec-Synapse-Cycle.md (sections 3, 4, 7, 8, 9)
- Synapse_Cycle_Per_Person_Build_Split.md (Person 4 section)
Your Exact Responsibilities
Backend (Python)
1. Aggregation — Collect AnalysisPayload[] → ClassAnalytics
2. Mastery Calculation — Heuristic from diagnosis items → 0.0-1.0
3. Trend Calculation — Compare cycles → TrendLabel
4. Graph Parsing — Extract [[Concept]] links from student notes → DAG
Frontend (React + TypeScript)
5. Teacher Dashboard — Concept cards: mastery %, trend arrow, class distribution
6. Student Graph — Interactive DAG of student's concepts with [[links]]
Files to Create/Modify
analytics/
├── __init__.py
├── aggregation.py
├── mastery.py
├── trends.py
├── graph.py
├── fixtures/
│   ├── analysis_payloads.json
│   └── student_notes/
│       ├── student_A/
│       │   ├── Recursion.md
│       │   └── Functions.md
│       └── student_B/
│           └── Recursion.md
└── tests/
    ├── test_aggregation.py
    ├── test_mastery.py
    ├── test_trends.py
    └── test_graph.py

dashboard/
├── teacher/
│   ├── components/
│   │   ├── ConceptCard.tsx
│   │   ├── MasteryTrendChart.tsx
│   │   └── ClassDistribution.tsx
│   ├── pages/
│   │   └── TeacherDashboard.tsx
│   └── hooks/
│       └── useTeacherAnalytics.ts
├── student/
│   ├── components/
│   │   ├── ConceptGraph.tsx
│   │   ├── NoteViewer.tsx
│   │   └── MistakePatternTable.tsx
│   ├── pages/
│   │   └── StudentDashboard.tsx
│   └── hooks/
│       └── useStudentData.ts
├── shared/
│   ├── graph/
│   │   └── ConceptGraphRenderer.tsx  # React Flow / Cytoscape wrapper
│   └── ui/
│       ├── Card.tsx
│       ├── Badge.tsx
│       └── TrendArrow.tsx
└── tests/
    ├── teacher.test.tsx
    ├── student.test.tsx
    └── graph.test.tsx
Shared Contracts (Import Only)
# Python
from contracts.schemas import (
    AnalysisPayload, ClassAnalytics, ConceptNode, NoteVersion,
    TrendLabel, Diagnosis, DiagnosisItem, MistakeClassification
)

# TypeScript (from contracts/types.ts)
import type {
  AnalysisPayload, ClassAnalytics, ConceptNode, NoteVersion,
  TrendLabel, StudentGraphResponse
} from '@/contracts/types';
Implementation Requirements
Backend — analytics/
mastery.py — Mastery Heuristic (Document as Domain Opinion)
def calculate_mastery(diagnosis: Diagnosis) -> float:
    """
    Heuristic (domain opinion, not architecture):
    - Start at 1.0
    - Each conceptual_gap: -0.25
    - Each careless_mistake: -0.10
    - Each contradictory: -0.15
    - Each unrelated/empty: -0.05
    - Floor at 0.0, ceiling at 1.0
    """
    penalties = {
        MistakeClassification.CONCEPTUAL_GAP: 0.25,
        MistakeClassification.CARELESS_MISTAKE: 0.10,
        MistakeClassification.CONTRADICTORY: 0.15,
        MistakeClassification.UNRELATED: 0.05,
        MistakeClassification.EMPTY: 0.05,
    }
    mastery = 1.0 - sum(penalties.get(item.classification, 0) for item in diagnosis.items)
    return max(0.0, min(1.0, mastery))
trends.py — Trend Calculation
def calculate_trend(
    current_mastery: float,
    history: list[tuple[int, float]]  # [(cycle, mastery)]
) -> TrendLabel:
    if not history:
        return TrendLabel.NEW
    prev_mastery = history[-1][1]
    delta = current_mastery - prev_mastery
    if delta > 0.15:
        return TrendLabel.IMPROVING
    elif delta < -0.15:
        return TrendLabel.DECLINING
    elif current_mastery < 0.5:
        return TrendLabel.STILL_WEAK
    else:
        return TrendLabel.STABLE
aggregation.py — Class Analytics
def aggregate(payloads: list[AnalysisPayload]) -> ClassAnalytics:
    """Group by concept_id, compute average mastery, trend distribution."""
    # Group payloads by concept_id
    # For each concept: avg mastery, count trends, identify weak students (<0.5)
    # Return ClassAnalytics
graph.py — Concept Link Parsing
import re

CONCEPT_LINK_PATTERN = re.compile(r'\[\[([^\]]+)\]\]')

def parse_concept_links(markdown: str) -> list[str]:
    """Extract all [[Concept]] references from markdown."""
    return CONCEPT_LINK_PATTERN.findall(markdown)

def build_student_graph(
    student_id: str,
    notes: list[NoteVersion],
    all_concepts: list[ConceptNode]
) -> tuple[list[ConceptNode], list[tuple[str, str]]]:
    """
    Returns (nodes, edges) for student's concept graph.
    - Nodes: concepts the student has notes for
    - Edges: (from_concept, to_concept) from [[links]] in notes
    - Only include edges where target concept exists in student's notes
    """
    # 1. Get latest note per concept
    # 2. Parse links from each note
    # 3. Filter to links where target exists in student's concepts
    # 4. Return nodes + edges
Frontend — dashboard/
Teacher Dashboard
- ConceptCard: Shows concept name, mastery % (large), trend arrow (↑/↓/→), student count
- MasteryTrendChart: Simple line chart (Recharts or similar) — cycles on X, mastery on Y
- ClassDistribution: Bar chart of trend distribution
Student Dashboard
- ConceptGraphRenderer: React Flow or Cytoscape.js wrapper
- Nodes: student's concepts (click → show note)
- Edges: [[links]] from notes
- Visual: DAG layout, colored by mastery (green/yellow/red)
- NoteViewer: Renders markdown with highlighted mistake table
- MistakePatternTable: Re-renders the diagnosis table from note
API Client (Shared)
// dashboard/shared/api/client.ts
export async function fetchTeacherAnalytics(conceptId: string): Promise<TeacherAnalyticsResponse>
export async function fetchTeacherTrends(conceptId: string): Promise<TeacherTrendsResponse>
export async function fetchStudentNotes(conceptId: string): Promise<StudentNotesResponse>
export async function fetchStudentGraph(): Promise<StudentGraphResponse>
Use MSW (Mock Service Worker) for all frontend tests.
Unit Tests (Must Pass Before Merge)
Run: pytest analytics/tests/ -v and npm run test --prefix dashboard/
Backend Test	What It Verifies
test_mastery.py	Heuristic matches spec cases (conceptual_gap=-0.25, careless=-0.10, etc.)
test_trends.py	NEW, IMPROVING, STABLE, STILL_WEAK, DECLINING with fixture histories
test_aggregation.py	3 students → correct avg, trend dist, weak list
test_graph.py	Valid links → edges; invalid links → dropped; isolated nodes included
Frontend Test	What It Verifies
teacher.test.tsx	ConceptCard renders mastery/trend; chart updates on data change
student.test.tsx	Graph renders nodes/edges; click node shows note
graph.test.tsx	Invalid link filtered; isolated node shown
Mock Strategy
- Backend: Pure functions — test with fixture JSON in analytics/fixtures/
- Frontend: MSW handlers mock all API endpoints with fixture data
- No backend dependency for frontend development
Acceptance Criteria
- pytest analytics/tests/ passes (100%)
- npm run test --prefix dashboard/ passes (100%)
- Mastery heuristic documented and tested against 5+ cases
- Trend labels match spec: new/improving/stable/still_weak/declining
- Graph parsing: valid [[Links]] → edges; invalid → silently dropped
- Teacher dashboard shows only concept-level data (NO private notes)
- Student graph shows only their own concepts + valid links
- No imports from agent_runtime/, agents/, curriculum/, api/
Integration Handoff
Person 5 (API) will call:
from analytics.aggregation import aggregate
from analytics.mastery import calculate_mastery
from analytics.trends import calculate_trend
from analytics.graph import build_student_graph
Frontend consumes API endpoints Person 5 exposes.
What NOT to Build
- ❌ Diagnosis, tailoring, review (Person 2)
- ❌ State machine, persistence (Person 1)
- ❌ Curriculum, test generation (Person 3)
- ❌ FastAPI, auth, API routes (Person 5)
- ❌ Schema definitions (in contracts/)

---

## PROMPT 5 — Person 5: API + Auth + Application Integration

ROLE: Full-Stack Integration Engineer (Person 5)
Project Context
You build the application shell: FastAPI backend with auth, all HTTP endpoints, React frontend for student/teacher, and the integration wiring that connects all four teammates' modules. You work against mocks until integration.
Key Documents:
- AgentSpec-Synapse-Cycle.md (sections 5, 7, 8, 10, 11, 12)
- Synapse_Cycle_Per_Person_Build_Split.md (Person 5 section)
Your Exact Responsibilities
1. FastAPI Application — App factory, middleware, lifespan
2. Authentication — JWT/session, role-based access (student vs teacher)
3. HTTP Endpoints — All 8 endpoints per contracts/api_contracts.py
4. Dependency Injection — Wire real/mock services
5. React Frontend — Student + Teacher UIs consuming API
6. Integration Testing — End-to-end with mocks, then real modules
Files to Create/Modify
api/
├── __init__.py
├── main.py                  # FastAPI app factory
├── auth.py                  # JWT auth, role guards
├── student_routes.py        # POST /student/attempts, GET /student/*
├── teacher_routes.py        # POST /teacher/*, GET /teacher/*
├── schemas.py               # Re-exports contracts.api_contracts
├── dependencies.py          # DI container (real vs mock services)
├── mocks.py                 # Mock service implementations
└── tests/
    ├── test_auth.py
    ├── test_student_routes.py
    ├── test_teacher_routes.py
    └── test_integration.py

frontend/
├── src/
│   ├── student/
│   │   ├── components/
│   │   ├── pages/
│   │   └── api.ts
│   ├── teacher/
│   │   ├── components/
│   │   ├── pages/
│   │   └── api.ts
│   ├── api_client/
│   │   ├── client.ts        # Axios/Fetch wrapper with auth
│   │   └── endpoints.ts
│   ├── shared/
│   │   ├── auth/
│   │   └── ui/
│   └── main.tsx
├── package.json
├── vite.config.ts
├── vitest.config.ts
└── tests/
Shared Contracts (Import Only)
# Python
from contracts.schemas import RunState
from contracts.api_contracts import (
    CreateConceptRequest, CreateConceptResponse,
    ConfirmTagsRequest, ConfirmTagsResponse,
    SubmitAttemptRequest, SubmitAttemptResponse,
    TeacherAnalyticsResponse, TeacherTrendsResponse,
    StudentNotesResponse, StudentGraphResponse,
    RunStatusResponse, ErrorResponse
)

# TypeScript (frontend)
import type {
  CreateConceptRequest, CreateConceptResponse,
  SubmitAttemptRequest, SubmitAttemptResponse,
  TeacherAnalyticsResponse, StudentNotesResponse,
  StudentGraphResponse, RunStatusResponse, ErrorResponse
} from '@/contracts/types';
Implementation Requirements
1. auth.py — Authentication
# Simple JWT for hackathon (no OAuth complexity)
SECRET_KEY = "dev-secret-change-in-prod"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 480  # 8 hours

def create_token(subject: str, role: Literal["student", "teacher"]) -> str:
    ...

def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    ...

def require_teacher(user: User = Depends(get_current_user)) -> User:
    if user.role != "teacher": raise HTTPException(403, "Teacher only")
    return user

def require_student(user: User = Depends(get_current_user)) -> User:
    if user.role != "student": raise HTTPException(403, "Student only")
    return user

class User(BaseModel):
    id: str
    role: Literal["student", "teacher"]
    name: str
2. dependencies.py — DI Container
class ServiceContainer:
    def __init__(self, use_mocks: bool = False):
        self.use_mocks = use_mocks
        self._init_services()
    
    def _init_services(self):
        if self.use_mocks:
            from api.mocks import (
                MockCurriculumService, MockAgentRuntime,
                MockDiagnosisService, MockAnalyticsService
            )
            self.curriculum = MockCurriculumService()
            self.runtime = MockAgentRuntime()
            self.diagnosis = MockDiagnosisService()
            self.analytics = MockAnalyticsService()
        else:
            # Real imports — ONLY at integration time
            from curriculum.curriculum_agent import extract_concepts
            from curriculum.test_generator import generate_test
            from curriculum.tag_confirmation import TagConfirmationService
            from agent_runtime.runner import AgentRunner
            from agent_runtime.store import Store
            from agents.diagnosis import diagnose
            from agents.tailoring import tailor_note
            from agents.review import review_note
            from agents.nim_adapter import NIMAdapter
            from analytics.aggregation import aggregate
            from analytics.mastery import calculate_mastery
            from analytics.trends import calculate_trend
            from analytics.graph import build_student_graph
            # ... wire them up
    
    # Service accessors
    def get_curriculum_service(self): ...
    def get_runtime(self): ...
    def get_diagnosis_service(self): ...
    def get_analytics_service(self): ...

# Global container (set at startup)
container: ServiceContainer
3. mocks.py — Mock Services for Independent Development
class MockCurriculumService:
    async def create_concept(self, markdown: str, name: str) -> tuple[ConceptNode, str]:
        return load_fixture("concept.json"), "run-123"
    
    async def confirm_tags(self, run_id: str, confirmed: bool, edited: list[ConceptNode] | None) -> Test:
        return load_fixture("test.json")
    
    async def get_test(self, run_id: str) -> Test:
        return load_fixture("test.json")

class MockAgentRuntime:
    async def start_run(self, concept_id: str, teacher_id: str) -> RunRecord:
        return RunRecord(run_id="run-123", concept_id=concept_id, teacher_id=teacher_id)
    
    async def submit_attempt(self, run_id: str, attempt: Attempt) -> SubmitAttemptResponse:
        return load_fixture("submit_response.json")
    
    async def get_run_status(self, run_id: str) -> RunStatusResponse:
        return RunStatusResponse(run_id=run_id, state=RunState.COMPLETE, ...)

class MockDiagnosisService:
    async def diagnose(self, attempt: Attempt, history: StudentHistory) -> Diagnosis:
        return load_fixture("diagnosis.json")

class MockAnalyticsService:
    async def get_teacher_analytics(self, concept_id: str) -> TeacherAnalyticsResponse:
        return load_fixture("teacher_analytics.json")
    
    async def get_student_notes(self, student_id: str, concept_id: str) -> StudentNotesResponse:
        return load_fixture("student_notes.json")
    
    async def get_student_graph(self, student_id: str) -> StudentGraphResponse:
        return load_fixture("student_graph.json")
4. Routes — Privacy Enforcement Critical
# student_routes.py
@router.post("/attempts", response_model=SubmitAttemptResponse)
async def submit_attempt(
    request: SubmitAttemptRequest,
    student: User = Depends(require_student),
    runtime: AgentRuntime = Depends(get_runtime)
):
    # 1. Load test, validate student owns it
    # 2. Score attempt
    # 3. Call runtime → triggers diagnosis → tailoring → review → analysis
    # 4. Return SubmitAttemptResponse (includes note — PRIVATE to this student)

@router.get("/notes/{concept_id}", response_model=StudentNotesResponse)
async def get_notes(
    concept_id: str,
    student: User = Depends(require_student),
    analytics: AnalyticsService = Depends(get_analytics)
):
    # ONLY return notes for THIS student
    return await analytics.get_student_notes(student.id, concept_id)

@router.get("/graph", response_model=StudentGraphResponse)
async def get_graph(
    student: User = Depends(require_student),
    analytics: AnalyticsService = Depends(get_analytics)
):
    return await analytics.get_student_graph(student.id)

# teacher_routes.py
@router.get("/analytics/{concept_id}", response_model=TeacherAnalyticsResponse)
async def get_analytics(
    concept_id: str,
    teacher: User = Depends(require_teacher),
    analytics: AnalyticsService = Depends(get_analytics)
):
    # AGGREGATE ONLY — no student note content
    return await analytics.get_teacher_analytics(concept_id)
5. Frontend — React + Vite + TypeScript
- Student Flow: Login → Test List → Take Test → View Result → View Note → View Graph
- Teacher Flow: Login → Create Concept → Confirm Tags → View Analytics → View Trends
- API Client: Axios instance with JWT interceptor, typed endpoints
- State: React Query or SWR for server state
- UI: Minimal — shadcn/ui or raw CSS; focus on functionality
Unit Tests (Must Pass Before Merge)
Run: pytest api/tests/ -v and npm run test --prefix frontend/
Backend Test	What It Verifies
test_auth.py	Student/teacher tokens; role guards reject wrong roles
test_student_routes.py	Submit attempt → response shape; Notes/graph privacy (student A ≠ student B)
test_teacher_routes.py	Create concept → run; Confirm tags → test; Analytics shape
test_integration.py	Full flow with mocks: Teacher → Test → Student → Attempt → Response
Frontend Test	What It Verifies
student.test.tsx	Test page renders, submit calls API, note displays
teacher.test.tsx	Concept creation, tag confirmation, analytics display
auth.test.tsx	Login redirects, role-based routing
Mock Strategy
- api/mocks.py provides complete fake service implementations
- dependencies.py switches via USE_MOCKS env var
- Frontend uses MSW with same fixture data
- Develop frontend against mock API — no backend needed until integration
Acceptance Criteria
- pytest api/tests/ passes (100%)
- npm run test --prefix frontend/ passes (100%)
- All 8 endpoints implemented with correct request/response schemas
- Auth: Student cannot access teacher endpoints; Teacher cannot access student notes
- Privacy: /student/notes only returns requesting student's notes
- Mock mode: Full flow works with USE_MOCKS=true
- No imports of internal modules from other teammates (only contracts.* and service protocols)
Integration Handoff
Integration Order (Person 5 drives):
1. Start with USE_MOCKS=true — verify all endpoints work
2. Replace MockCurriculumService → Real curriculum module
3. Replace MockAgentRuntime → Real agent_runtime + agents
4. Replace MockAnalyticsService → Real analytics
5. Run full E2E: Teacher → Concept → Test → Student → Attempt → Note → Analytics
What NOT to Build
- ❌ State machine, persistence (Person 1)
- ❌ Diagnosis, tailoring, review logic (Person 2)
- ❌ Curriculum extraction, test generation (Person 3)
- ❌ Mastery/trend/graph algorithms (Person 4)
- ❌ Schema definitions (in contracts/)

---

# SECTION E — Integration Checklist

## Pre-Integration (Each Teammate Completes Independently)

| Module | Checklist |
|--------|-----------|
| **Agent Runtime (P1)** | ☐ All 6 unit tests pass<br>☐ State machine runs `START → COMPLETE` with mocks<br>☐ Process kill + resume works at every state<br>☐ Revision limit (3) enforced<br>☐ Model call budget enforced<br>☐ Teacher timeout transitions correctly |
| **Agents (P2)** | ☐ All 4 test suites pass<br>☐ 6 diagnosis fixtures covered<br>☐ Tailoring produces valid markdown + links<br>☐ Review catches all 4 failure modes<br>☐ Revision loop (fail → tailor → pass) works |
| **Curriculum (P3)** | ☐ All 3 test suites pass<br>☐ Concept extraction stable IDs<br>☐ Test generation: 3 Qs, 4 opts, correct in opts, no dupes<br>☐ Tag confirmation: confirm/edit/timeout |
| **Analytics (P4)** | ☐ All 4 backend tests pass<br>☐ Mastery heuristic documented + tested<br>☐ All 5 trend labels verified<br>☐ Graph parsing: valid links kept, invalid dropped<br>☐ Frontend tests pass (MSW mocks) |
| **API (P5)** | ☐ All 4 backend tests pass<br>☐ Auth: role guards work<br>☐ Privacy: student A ≠ student B notes<br>☐ All 8 endpoints return correct schemas<br>☐ Frontend tests pass against MSW |

---

## Integration Stage 1 — Skeleton (Day 1 Morning)
**Goal:** `Frontend → API → Fake Agent → Fake DB` works end-to-end

| Step | Action | Verification |
|------|--------|--------------|
| 1 | Merge `contracts/` to `main` | CI passes (type sync) |
| 2 | Person 5 sets `USE_MOCKS=true` | `docker compose up` starts API + frontend |
| 3 | Teacher creates concept → sees test | UI shows test questions |
| 4 | Student takes test → sees result | UI shows diagnosis + note + graph |
| 5 | Teacher views analytics | Dashboard shows class mastery/trend |
| 6 | **Check:** No real LLM calls, no real DB writes (all mocks) | Logs confirm mock handlers hit |

**Merge Conflicts to Check:** `contracts/types.ts` drift; `pyproject.toml` dependency versions.

---

## Integration Stage 2 — Real Agents (Day 1 Afternoon → Day 2 Morning)
**Replace mocks one at a time; verify each before next.**

| Replacement | Person | Verification |
|-------------|--------|--------------|
| `MockCurriculumService` → Real `curriculum` | P3 + P5 | Teacher creates concept → real concepts extracted → test generated |
| `MockAgentRuntime` → Real `agent_runtime` | P1 + P5 | Run persists to SQLite; restart resumes |
| `MockDiagnosisService` → Real `agents.diagnosis` | P2 + P5 | Student attempt → real diagnosis (fixture NIM) |
| `MockTailoring/Review` → Real `agents.tailoring/review` | P2 + P5 | Note generated → reviewed → saved (revision loop tested) |
| `MockAnalyticsService` → Real `analytics` | P4 + P5 | Analysis payload → class analytics → dashboard updates |

**After Each Replacement:** Run `pytest api/tests/test_integration.py` + relevant module tests.

---

## Integration Stage 3 — Real End-to-End (Day 2 Afternoon)
**Full cycle with real NIM calls (or recorded fallbacks).**

| Scenario | Test |
|----------|------|
| First encounter | Teacher → Concept → Test → Student → Attempt → Diagnosis → Note v1 → Analytics |
| Second encounter | Same student, new test → Note v2 → Trend "improving" → Teacher sees trend |
| Adversarial | Malicious input in canonical/attempt → No private note leak, no instruction following |
| Failure | NIM timeout → Retry (max 3) → Graceful error |
| Failure | Review rejects 3x → `REVISION_LIMIT_REACHED` → Run completes with last note |

**Demo Rehearsal:** Run full demo script (AgentSpec §13) twice — once live, once recorded.

---

## Final Merge Checklist

- [ ] All `pytest` pass (backend)
- [ ] All `npm run test` pass (frontend)
- [ ] `scripts/sync_types.py` — no TS/Python drift
- [ ] `docker compose up` starts full stack
- [ ] Demo script runs end-to-end
- [ ] Adversarial tests pass
- [ ] Privacy audit: Teacher endpoints never return `NoteVersion.markdown`
- [ ] README updated with run instructions
- [ ] All 5 teammates approve final PR

---

# SECTION F — Risks and Unresolved Decisions

## F.1 High-Risk Items (Decide Before Coding)

| # | Decision | Options | Recommendation |
|---|----------|---------|----------------|
| 1 | **NIM Model Selection** | `nemotron-3-ultra` vs `llama-3.1-70b` vs `mistral-large` | Test all 3 with diagnosis prompt; pick most consistent structured output |
| 2 | **Teacher Timeout Duration** | 10 min (spec) vs 30 min vs 1 hour | Configurable env var; default 10 min; document that demo may need longer |
| 3 | **Mastery Heuristic Weights** | Spec: conceptual_gap=0.25, careless=0.10, etc. | Implement as specified; add unit tests; **document as domain opinion** |
| 4 | **Trend Thresholds** | Spec: ±0.15 for improving/declining | Implement as specified; test with 2-cycle fixture |
| 5 | **Student Auth Method** | JWT (stateless) vs Session (server-side) | JWT — simpler for hackathon; store in httpOnly cookie |
| 6 | **Concept Link Validation** | Strict (must exist in student's notes) vs Lenient (warn only) | **Strict** — spec says "only accepted if exists" |
| 7 | **Revision Loop Trigger** | Review FAIL → Tailoring (spec) vs Review FAIL → Diagnosing | **Spec: Review FAIL → Tailoring** (keeps diagnosis fixed) |

## F.2 Technical Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| NIM API latency > 30s | Medium | Demo fails | Pre-record all NIM responses; use fixtures for demo |
| NIM structured output fails schema | Medium | Diagnosis invalid | `nim_adapter` validates + retries (max 3); fallback to mock |
| SQLite lock contention | Low | Runtime errors | WAL mode; single writer; short transactions |
| React Flow bundle size | Low | Slow frontend load | Dynamic import; or use lighter Cytoscape.js |
| Schema drift Python↔TypeScript | High | Runtime errors | CI step: `python scripts/sync_types.py && git diff --exit-code` |

## F.3 Unresolved from Spec (Need Team Decision)

1. **Student Identification** — Spec uses `student_A` string. Real auth needs persistent student IDs. → Use UUIDs from auth system; map to spec's `student_id` field.

2. **Teacher Identification** — Spec doesn't detail teacher auth. → Simple email/password → JWT with `role: "teacher"`.

3. **Multiple Concepts per Test** — Spec shows single concept. → MVP: **one concept per test**. Multi-concept = future.

4. **Note Version Storage** — SQLite vs Markdown files. → **SQLite for metadata + Markdown files for content** (spec says "Student Notes: Markdown").

5. **Concept Graph Persistence** — Computed on-demand vs stored. → **Computed on-demand** from note versions (simpler, consistent).

6. **Demo Data Seeding** — How to reset between demo runs? → `scripts/seed_demo.py` that creates teacher, students, concepts, runs.

## F.4 Scope Boundaries (Explicitly NOT in MVP)

Per AgentSpec §11 — Do not build:
- ❌ Embeddings / vector search / semantic retrieval
- ❌ Multi-class / multi-teacher / multi-subject
- ❌ Scheduler / recurring tests
- ❌ Real citation verification (web search)
- ❌ Student note exposure to teacher
- ❌ Model-invented concept links
- ❌ Complex ML mastery models (heuristic only)

---

## Final Note to Team

> **This architecture is designed for a 2-day hackathon build.** Every decision optimizes for:
> 1. **Parallel independent development** (contracts-first, mocks)
> 2. **Deterministic testing** (fixtures, no live LLM in unit tests)
> 3. **Minimal integration friction** (DI container, single schema source)
> 4. **Demo reliability** (recorded fallbacks, bounded retries)
>
> **If something feels over-engineered, it probably is.** Cut scope to hit the demo beats in AgentSpec §13. The "argument beat" is **Beat 9** — the same student's note visibly evolves after a second test because the system remembered the first encounter.
>
> **Ship the loop. Polish later.**