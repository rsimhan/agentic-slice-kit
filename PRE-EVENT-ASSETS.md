# Pre-Event Assets Declaration

**Team Name:** AgentX  
**Project:** Socratic "Feynman Check" & Batch Gap Ping  
**Track:** Multi-Agent Learning Solutions  
**Institution:** College of Engineering Guindy (DCSE CEG), Anna University  
**Date:** 19 September 2026  

---

## Declaration of Prior Work and Assets

In accordance with the CEG ASTRA Agent-a-thon guidelines (`docs/ON-THE-DAY.md`), this document declares all assets, code, and materials prepared prior to the commencement of the hackathon on 19 September 2026:

### 1. Prior Code
* **None.** 
* No pre-existing codebase, private repository, or prior project implementation has been imported or reused.
* The team is starting with a clean repository based strictly on the official event starter kit (`agentic-slice-kit`).

### 2. Prior Prompts, Agent Definitions & Evaluation Sets
* **None**, with the sole exception of our preliminary project proposal:
  * [`docs/Agent_Specification.md`](docs/Agent_Specification.md): The AgentSpec submitted on Tuesday, 15 September 2026, defining the problem setting (CS8492 Operating Systems Virtual Memory / TLB misconceptions), target state machine, data contracts, and verification criteria.
* No system prompts, prompt engineering iterations, or evaluation scripts were pre-built before Day 1. All prompts and agent nodes will be developed live during the event.

### 3. Datasets & Corpora
* **None.** 
* No external or private student datasets, lecture transcripts, or benchmarks have been brought into the workspace.
* All concept invariants (e.g., `data/concepts/virtual_memory.md`) and mock student response fixtures will be authored during the hackathon based on the standard Anna University CS8492 syllabus.

### 4. Third-Party Libraries & Dependencies
* **Standard starter kit dependencies only**, as defined in `requirements.txt`:
  * `pydantic` (schema validation and typed contracts)
  * `httpx` (model API calls)
  * `sqlite-vec` & `fastembed` (local vector embeddings and retrieval)
  * `fastapi` & `uvicorn` (human expert callback interface)
  * `pytest` (automated testing)
* No heavy external agent frameworks (e.g., LangChain, CrewAI, AutoGen) or vector databases (e.g., Pinecone, Chroma) are being brought in.
