# ImpactLoop MVP Specification

## Purpose

ImpactLoop turns a real campus problem into a small piece of student work, coordinates the work with agents, asks a mentor for a human decision when needed, verifies the student's evidence, creates a Proof-of-Ability record, and connects that verified capability to a next opportunity.

## End-to-end flow

```
Campus problem
      ↓
Student profile + goal
      ↓
Project decomposition
      ↓
Team matching
      ↓
Task plan + acceptance criteria
      ↓
Mentor checkpoint
      ↓
Student submits evidence
      ↓
Verification
      ├── REVISION_REQUIRED → evidence submission → verification
      └── PASS
             ↓
      Proof-of-Ability
             ↓
      Retrieved opportunity candidates
             ↓
      Connector recommendation
```

## Agent contracts

### 1. Intake

Input:
- challenge title and description
- student profile

Output: `StudentGoal`

Rules:
- use only supplied information
- never invent skills, experience, time, achievements, or goals
- preserve the student's actual intent

### 2. Project Decomposer

Input:
- challenge
- StudentGoal

Output: `ProjectBrief`

The brief contains:
- problem
- objective
- tasks
- deliverables
- required capabilities
- evidence requirements

### 3. Team Matcher

Input:
- ProjectBrief
- candidate student profiles

Output: `TeamProposal`

The matcher may only use supplied profiles and must explain capability matches.

### 4. Orchestrator

Input:
- ProjectBrief
- TeamProposal

Output: `TaskPlan`

Every task has an owner, acceptance condition, and evidence requirement.

### 5. Mentor checkpoint

The runner moves the run to `AWAITING_EXPERT`.

The question is persisted in SQLite. The process may exit completely. A later request records the mentor answer and resumes the run.

### 6. Verification

Input:
- ProjectBrief
- TaskPlan
- MentorDecision
- EvidenceSubmission

Output: `VerificationResult`

The verifier must:
- PASS only when evidence exists, is relevant, and is sufficient
- request revision when important evidence is missing, weak, or unrelated
- never invent evidence

The domain revision limit is one revision.

### 7. Proof-of-Ability

Created only after verification passes.

The record describes a demonstrated capability, the student's concrete contribution, and the evidence that supports it.

### 8. Connector

The system first retrieves a small candidate set from `demo/impactloop/opportunities.json`.

The LLM may select and explain one candidate, but it cannot invent an opportunity outside the retrieved catalog.

## Durable state

The Slice engine provides:
- append-only run history
- deterministic state transitions
- persisted human questions
- resume after process restart
- token budgets
- typed model output

The database is the source of truth.

## Demo path

1. Create a student account.
2. Open `/profile` and add real skills, interests, availability, role, and project links.
3. Create a campus problem.
4. Show the Intake → Decomposer → Matcher → Orchestrator records.
5. Open the mentor queue and answer the persisted question.
6. Show the verifier requesting concrete evidence.
7. Submit evidence from the project page.
8. Show PASS → Proof-of-Ability → Connector recommendation.
9. Open the dashboard on port 8001 to show the complete journey.

## Known MVP boundaries

- Evidence is currently submitted as structured text/links rather than binary file uploads.
- The opportunity catalog is local and curated for the demo; it is not a live campus opportunity API.
- Authentication uses an in-memory session store and is suitable for a hackathon demo, not production deployment.
