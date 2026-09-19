# The Guardian Agents — Synapse Cycle

An adaptive learning platform built on the **Agentic Slice Kit** for CEG ASTRA Agent-a-thon (Sep 2026).

Synapse creates personalized, verified learning cycles for students. It diagnoses student quiz attempts into root-cause misconception classifications, tailors targeted private remediation notes, and subjects them to an autonomous AI review gate.

> **Status: Integrated Spine & Domain Complete.**  
> 100+ tests passing out of the box with zero key and zero network.  
> Offline deterministic stubs prove the **agentic backward loop**: `DRAFTING` &rarr; `GATING` &rarr; `BLOCK` &rarr; `DRAFTING` (revision with objections) &rarr; `GATING` &rarr; `PASS` &rarr; `COMPLETE`.

---

## Quickstart for Teammates

Open the repository in GitHub Codespaces or clone it locally:

```bash
# 1. Setup environment configuration
cp .env.example .env      # Paste your OPENROUTER_API_KEY from the desk

# 2. Run tests (all green with no key and no network)
python -m pytest

# 3. Check environment health
python scripts/doctor.py

# 4. Run the Synapse agentic slice with deterministic stubs
python scripts/synapse_cycle.py run --stub

# 5. Replay an execution's immutable SQLite audit trail
python scripts/synapse_cycle.py replay <run_id>
```

---

## Architecture: Synapse on Agentic Slice Kit

Synapse strictly adheres to the Agentic Slice Kit architecture, treating `slice/` as the underlying agentic infrastructure and `demo/` as the domain-specific application:

```
Synapse UI / API
      │
      ▼
demo/flow.py (Domain Rules & Handlers)
      │
      ▼
slice.runner (advance() State Machine)
      │
      ▼
slice.store / slice.llm / slice.budget / slice.callback / slice.retrieve
      │
      ▼
Synapse Services (Diagnosis, Tailoring, Review, Curriculum, Analytics)
```

### Directory Layout

```
slice/             THE PROTECTED SPINE — core agentic machinery
  records.py         Immutable run records and version types (stdlib)
  store.py           Durable SQLite append-only state with trigger protection
  config.py          Single point of truth for .env and settings
  budget.py          Dual-scoped fences: attempt counts and token limits
  llm.py             Single choke point for model calls, schemas, and repairs
  retrieve.py        Local vector search and chunking (sqlite-vec + fastembed)
  callback.py        Human-in-the-loop suspended state and deadlines
  runner.py          Deterministic state machine runner

demo/              THE DOMAIN — Synapse implementation
  schema.py          Pydantic models (CanonicalNoteInput, AttemptInput, etc.)
  flow.py            State machine handlers implementing the backward edge
  stub.py            Deterministic canned responses for zero-network execution
  prompts/           Prompts for diagnosis, tailoring, and review
  SPEC.md            The complete Synapse AgentSpec document

contracts/         Shared Pydantic schemas and state machine logic across team roles
agent_runtime/     Runtime adapter wrapping slice.runner and slice.store
agents/            Diagnosis, tailoring, review, and analytics services
curriculum/        Concept extraction and MCQ test generation
analytics/         Class aggregation and mastery trend metrics
api/               FastAPI endpoints for teacher and student flows
dashboard/         Visualization components for student mastery and teacher trends
frontend/          Student and teacher interface code
web/               Human callback web interface for teacher review
scripts/           doctor.py, smoke.py, synapse_cycle.py, sync_types.py
tests/             Complete test suite: architecture, slice, contracts, runtime
```

---

## The Agentic Backward Edge

An agent is a workflow that can go backwards. In Synapse, the backward edge lives at the quality gate:

1. **`DRAFTING`**: The Tailoring Agent writes a personalized remediation note based on diagnosed student misconceptions.
2. **`GATING`**: The Review Agent audits the note against the teacher's canonical facts and prerequisite coverage.
3. **`BLOCK &rarr; DRAFTING`**: If any prerequisite is omitted or factually inconsistent, the reviewer issues a `BLOCK` with structured objections. The runner loops work **backwards to `DRAFTING`**, where a revised draft specifically resolves the objections.
4. **`PASS &rarr; COMPLETE`**: When verified, the note is marked `PASS` and committed. Revisions are strictly bounded at `MAX_REVISIONS = 3`.

---

## Five-Person Team Architecture

As documented in `AGENTS.md` and `perpersonprompts.md`:

| Role | Module | Ownership | Tests |
|---|---|---|---|
| **Person 1** | `agent_runtime/` | State machine adapter, store wiring, run lifecycle | `tests/test_p1a_async_generation.py`, `tests/test_p1b_graph_persistence.py` |
| **Person 2** | `agents/` | Diagnosis, tailoring, and review logic | `tests/test_synapse_slice.py` |
| **Person 3** | `curriculum/` | Concept extraction and MCQ test generation | `curriculum/` |
| **Person 4** | `analytics/`, `dashboard/` | Aggregation, mastery calculation, trends UI | `analytics/` |
| **Person 5** | `api/`, `frontend/` | FastAPI routes, client auth, student & teacher UI | `api/`, `frontend/` |

---

## Testing Standards

All tests can be executed locally or in Codespaces:

```bash
# Run all tests (spine tests + Synapse domain tests + contract tests)
python -m pytest

# Run only Synapse slice tests (verifying the backward edge)
python -m pytest tests/test_synapse_slice.py

# Run contract boundary tests
python -m pytest tests/test_contracts.py

# Run architecture document sync check
python -m pytest tests/test_architecture.py
```
