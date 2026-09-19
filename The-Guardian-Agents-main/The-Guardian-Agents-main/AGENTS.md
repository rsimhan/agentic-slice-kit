# Synapse — Architecture Document (Sections A–F)

## Section A: System Overview

Synapse is an AI-powered adaptive learning platform that creates personalized learning cycles for students. The system follows a five-person team architecture where each person owns a distinct, independently testable module connected by shared contracts.

### Core Flow

```
Teacher → Canonical Note → Curriculum Agent → ConceptNode[] → Teacher Confirmation → Test Generator → Test
                                                          ↓
Student → Attempt → Diagnosis → Tailored Note → Review → PASS/FAIL
                                                          ↓
                                                   AnalysisPayload → Teacher Analytics + Student Graph
```

### Key Principles

1. **Contract-First Development**: All modules communicate through shared Pydantic schemas; no internal imports across team boundaries.
2. **Independent Testability**: Each module must run with mock/fake data — no dependency on other modules' implementations.
3. **Typed Records**: Persistent state machine provides the common spine; typed records enable independent development.
4. **Three-Stage Integration**: Skeleton → Real Agents One-by-One → Full End-to-End.

---

## Section B: Shared Contracts

### Canonical Record Types (Locked in Contracts Session)

All types defined in `contracts/schemas.py` and mirrored to `contracts/types.ts`:

| Type | Purpose | Owned By |
|------|---------|----------|
| `ConceptNode` | Atomic concept with prerequisites | Person 3 |
| `Test` | Generated assessment (MCQ) | Person 3 |
| `Attempt` | Student's submitted answer | Person 1/5 |
| `Diagnosis` | AI analysis of attempt | Person 2 |
| `NoteVersion` | Iterative tailored note | Person 1/2 |
| `ReviewResult` | AI review verdict | Person 2 |
| `AnalysisPayload` | Aggregated cycle data | Person 4 |
| `TeacherConfirmation` | Human-in-loop tag approval | Person 3 |

### State Machine States (Person 1)

```
IDLE → CURRICULUM_GENERATION → TEACHER_REVIEW → TEST_DELIVERY
    → STUDENT_ATTEMPT → DIAGNOSIS → TAILORING → REVIEW
    → {PASS: COMPLETE, FAIL: TAILORING (max 3 revisions)}
```

---

## Section C: Module Specifications

### Person 1 — Agent Runtime + Persistence (`agent_runtime/`)

**Responsibility**: Reusable state machine, SQLite persistence, run lifecycle.

**Files**:
- `runner.py` — Entry point, orchestrates state transitions
- `state_machine.py` — State definitions, transitions, validation
- `store.py` — SQLite CRUD for runs, history, checkpoints
- `records.py` — Local record types + serialization
- `budget.py` — Token/cost tracking, limits enforcement
- `callbacks.py` — Human-in-loop hooks, pause/resume

**Interface**:
```python
class AgentRuntime:
    def start_run(self, canonical_note: str) -> RunId
    def transition(self, run_id: RunId, event: Event) -> State
    def get_history(self, run_id: RunId) -> list[StateRecord]
    def pause(self, run_id: RunId) -> None
    def resume(self, run_id: RunId) -> State
```

**Tests**: State transitions, persistence, restart/resume, retry limits, revision limits, backward transitions, waiting state.

---

### Person 2 — Student Intelligence / AI (`agents/`)

**Responsibility**: Diagnosis → Tailoring → Review pipeline.

**Files**:
- `diagnosis.py` — `diagnose(attempt, history) → Diagnosis`
- `tailoring.py` — `tailor(diagnosis, previous_note) → NoteVersion`
- `review.py` — `review(note, diagnosis, canonical) → ReviewResult`
- `prompts/` — System prompts for each stage

**Interface**:
```python
def diagnose(attempt: Attempt, history: StudentHistory) -> Diagnosis
def tailor(diagnosis: Diagnosis, previous_note: NoteVersion) -> NoteVersion
def review(note: NoteVersion, diagnosis: Diagnosis, canonical: str) -> ReviewResult
```

**Fixtures**: `attempt.json`, `previous_note.json`, `canonical_note.json`

**Tests**: Conceptual gap, careless mistake, multiple mistakes, perfect score, empty answer, contradictory answer, nonexistent `[[link]]`, bad tailored note, review rejection, revision loop.

---

### Person 3 — Curriculum + Test Generation (`curriculum/`)

**Responsibility**: Canonical note → Concepts → Teacher confirmation → Test.

**Files**:
- `curriculum_agent.py` — `extract_concepts(canonical_note) → list[ConceptNode]`
- `test_generator.py` — `generate_test(concepts, confirmation) → Test`
- `tag_confirmation.py` — Teacher confirmation flow
- `prompts/` — Extraction and generation prompts

**Interface**:
```python
def extract_concepts(canonical_note: str) -> list[ConceptNode]
def confirm_tags(concepts: list[ConceptNode], teacher_edits: dict) -> TeacherConfirmation
def generate_test(concepts: list[ConceptNode], confirmation: TeacherConfirmation) -> Test
```

**Tests**: Canonical → concepts, concept tags, MCQ schema, correct answer exists, 4 options, no duplicates, question tied to concept, teacher edits tag, teacher timeout, malformed canonical note.

---

### Person 4 — Teacher Analytics + Student Graph (`analytics/`, `dashboard/`)

**Responsibility**: Aggregation, mastery calculation, trends, concept graph visualization.

**Files**:
- `aggregation.py` — `aggregate(payloads) → ClassAnalytics`
- `mastery.py` — `calculate_mastery(history) → MasteryScore`
- `trends.py` — `calculate_trend(cycles) → Trend`
- `graph.py` — `parse_graph(note) → ConceptGraph`
- `dashboard/teacher/` — Teacher analytics UI
- `dashboard/student/` — Student concept graph UI

**Interface**:
```python
def aggregate(payloads: list[AnalysisPayload]) -> ClassAnalytics
def calculate_mastery(student_id: str, concept: str, history: list) -> MasteryScore
def calculate_trend(student_id: str, concept: str, cycles: list) -> Trend
def parse_graph(note_content: str) -> ConceptGraph
```

**Tests**: Aggregate 3 students, mastery calculation, trend calculation, cycle comparison, missing data, duplicate concept, graph parsing, invalid `[[link]]`, isolated node.

---

### Person 5 — API + Auth + Integration (`api/`, `frontend/`)

**Responsibility**: HTTP contracts, authentication, wiring, student/teacher UI.

**Files**:
- `main.py` — FastAPI app, routing, middleware
- `auth.py` — JWT auth, roles (student/teacher)
- `student_routes.py` — POST/GET student endpoints
- `teacher_routes.py` — POST/GET teacher endpoints
- `schemas.py` — FastAPI request/response models (extends contracts)
- `frontend/student/` — Student UI (React/Next.js)
- `frontend/teacher/` — Teacher UI (React/Next.js)
- `frontend/api_client/` — Typed API client

**Endpoints**:
```
POST /teacher/concepts          # Submit canonical note
POST /teacher/tests             # Generate test
POST /student/attempts          # Submit attempt
GET  /student/notes             # Get tailored notes
GET  /student/graph             # Get concept graph
GET  /teacher/analytics         # Class analytics
GET  /teacher/trends            # Trend data
```

**Tests**: Student/teacher auth, authorization isolation, valid/malformed attempts, analytics endpoints, note endpoint, graph endpoint.

---

## Section D: Integration Contract

### Service Layer (Exposed to Person 5)

```python
# synapse/services/__init__.py
from .diagnosis import diagnose
from .tailoring import tailor
from .review import review
from .curriculum import extract_concepts, generate_test
from .analytics import aggregate, calculate_mastery, calculate_trend, parse_graph
```

### Internal Imports Rule

**❌ Bad** (cross-person internal imports):
```python
from person2.diagnosis import diagnose  # DON'T
from person1.store import get_run       # DON'T
```

**✅ Good** (contract-only imports):
```python
from synapse.contracts import Diagnosis, Attempt
from synapse.services import diagnose, tailor, review
```

---

## Section E: Testing Standards

### Per-Module Deliverables

1. **Implementation** — Core logic
2. **Unit Tests** — `pytest module/tests/`
3. **Mock Input** — Fixtures in `module/fixtures/`
4. **Mock Output** — Expected results in fixtures
5. **README.md** — Interface documentation

### Test Command

```bash
# Each person runs their own tests
pytest agent_runtime/tests/
pytest agents/tests/
pytest curriculum/tests/
pytest analytics/tests/
pytest api/tests/
```

### Integration Stages

| Stage | Description | Command |
|-------|-------------|---------|
| 1 | Skeleton: Frontend → API → Fake Agents → Fake DB | `pytest integration/test_skeleton.py` |
| 2 | Real agents one at a time | `pytest integration/test_person2_real.py` |
| 3 | Full end-to-end | `pytest integration/test_e2e.py` |

---

## Section F: Development Workflow

### Getting Started

```bash
# 1. Install dependencies
pip install -r requirements.txt
npm install  # in frontend/

# 2. Generate TypeScript types
python scripts/sync_types.py

# 3. Run contract tests
pytest contracts/

# 4. Start development (each person in their module)
pytest agent_runtime/tests/ -w
pytest agents/tests/ -w
# etc.
```

### Directory Structure

```
Synapse/
├── AGENTS.md                    # This file
├── contracts/
│   ├── schemas.py               # Canonical Pydantic schemas
│   ├── state_machine.py         # State machine logic
│   ├── api_contracts.py         # FastAPI request/response models
│   └── types.ts                 # TypeScript types (generated)
├── scripts/
│   └── sync_types.py            # TypeScript generation script
├── prompts/
│   ├── person1_runtime.md
│   ├── person2_agents.md
│   ├── person3_curriculum.md
│   ├── person4_analytics.md
│   └── person5_api.md
├── agent_runtime/               # Person 1
├── agents/                      # Person 2
├── curriculum/                  # Person 3
├── analytics/                   # Person 4
├── dashboard/                   # Person 4 (UI)
├── api/                         # Person 5
└── frontend/                    # Person 5 (UI)
```

### The Golden Rule

> **If your module cannot be unit-tested without another teammate's unfinished module, the interface is not defined well enough yet.**

This prevents the classic hackathon failure mode: everything works individually, then nothing works together.