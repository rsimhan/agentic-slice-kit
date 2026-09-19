# Pre-Event Assets Declaration

**Team**: The Guardian Agents  
**Project**: Synapse (Adaptive Learning Agentic Slice)  
**Event**: CEG ASTRA &mdash; Agent-a-thon (September 2026)  
**Repository**: https://github.com/Ojas-Krisshnan/The-Guardian-Agents  

---

## Declaration of Prior Work & Assets Brought In

As required by `docs/ON-THE-DAY.md` (Section 1: "Tell us what you are bringing"), we hereby declare all assets, code, prompt templates, schemas, and libraries developed prior to Day 1 of the hackathon:

### 1. Prior Code & Architecture
- **Synapse Architecture & Contracts**:
  - Pydantic domain models in `contracts/schemas.py` and `contracts/state_machine.py` specifying canonical concept nodes, test questions, student attempts, mistake classifications, tailored note structures, and review verdicts.
  - State machine transition rules, retry boundaries, and trust boundary schemas.
  - TypeScript interface synchronization utility in `scripts/sync_types.py`.
- **Runtime & Service Stubs**:
  - `agent_runtime/`: State management and SQLite persistence adapter integrating with the Agentic Slice Kit (`slice/store.py` and `slice/runner.py`).
  - `agents/`: Heuristic diagnostic classifier (`diagnosis.py`), note versioning generator (`tailoring.py`), and validation checker (`review.py`).
  - `curriculum/`: Canonical note concept extractor (`curriculum_agent.py`) and MCQ question generator (`test_generator.py`).
  - `api/` & `frontend/`: FastAPI application (`api/main.py`) and Next.js frontend skeleton (`frontend/`).

### 2. Pre-Written Prompts & Agent Specifications
- System prompt templates for:
  - Diagnosis agent (`demo/prompts/diagnose.md`, `agents/prompts/`)
  - Note tailoring agent (`demo/prompts/tailor.md`, `agents/prompts/`)
  - Review and gating agent (`demo/prompts/review.md`, `agents/prompts/`)
  - Curriculum concept extraction & test generation prompts (`curriculum/prompts/`)
- Pre-event teammate assignment prompts and architecture documentation (`AGENTS.md`, `perpersonprompts.md`, `demo/SPEC.md`).

### 3. Pre-Gathered Datasets & Fixtures
- Sample canonical computer science notes on Recursion, Binary Search Trees, and Memory Management.
- Mock student quiz attempts with synthetic misconceptions (careless errors vs. deep prerequisite gaps).
- Synthetic test fixtures and canned responses in `demo/stub.py`.

### 4. Libraries Used
- Core: `pydantic>=2.7`, `httpx>=0.27`, `fastapi>=0.115`, `uvicorn>=0.30`, `pytest>=8.0`.
- Vector Search & Local Embeddings: `sqlite-vec>=0.1.9`, `fastembed>=0.4`.
- Standard Python libraries: `sqlite3`, `json`, `dataclasses`, `typing`, `pathlib`.
