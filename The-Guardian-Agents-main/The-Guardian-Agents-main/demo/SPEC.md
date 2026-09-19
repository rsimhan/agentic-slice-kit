# Synapse Cycle — AgentSpec

An AI-driven adaptive learning platform that diagnoses student misconceptions, generates tailored remediation notes, and subjects them to an autonomous quality review loop.

---

## 1. The Setting
Anna University engineering students in core curriculum courses (e.g. Data Structures, Algorithms, Systems Programming). Classes have high student-to-teacher ratios (60:1 to 120:1). Professors lecture and distribute canonical notes, but cannot individually diagnose every student's misconception on formative quizzes.

## 2. The Problem This Solves
When students fail questions on foundational concepts (e.g. recursion, pointers, state machines), standard platforms only report scores ("6/10") or correct answer keys. They do not distinguish between **careless mistakes** and deep **conceptual gaps**, nor do they generate personalized, verified remediation notes that bridge the student's specific missing prerequisites.

## 3. What We Are Building
An autonomous learning cycle:
1. Teacher provides a canonical note on a core concept.
2. The agent breaks it down into concepts and generates an assessment.
3. When the student submits an attempt, the agent diagnoses errors into root-cause classifications (`conceptual_gap`, `careless_mistake`).
4. The Tailoring Agent writes a personalized note addressing those gaps.
5. **The Quality Gate**: The Review Agent audits the note against the teacher's canonical facts and verified prerequisite links.
6. **The Backward Edge**: If the reviewer detects inaccuracies or omitted prerequisites, it BLOCKS the note and sends work **backwards** to the Tailoring Agent with specific objections. The revision loop continues until the note passes review or hits the 3-revision fence.

## 4. What This Deliberately Does NOT Do
1. It does NOT automatically award grades or alter final student evaluation scores (grading remains teacher-owned).
2. It does NOT invent external syllabus content outside the teacher's canonical notes.
3. It does NOT permit unbounded LLM looping; all revisions are strictly bounded at 3 passes.

## 5. Who Does the Thinking
- **Automated**: Misconception classification, candidate note drafting, consistency review against canonical notes, provenance tracking.
- **Human Teacher**: Canonical note creation, tag confirmation, intervention when revisions exceed bounds.
- **Human Student**: Reading, practicing, and reflecting on the tailored feedback.

## 6. The State Machine & Back-Edge
```
[DRAFTING] (Tailor note)
    │
    ▼
 [GATING] (Review against canonical facts)
    │
    ├─► PASS  ──► [COMPLETE]
    │
    └─► BLOCK ──► (if revisions < 3) ──► BACK TO [DRAFTING] with objections!
```

## 7. Data Models
- `CanonicalNoteInput`: Subject matter, key concepts, extracted terms.
- `AttemptInput`: Student answers to diagnostic questions.
- `DiagnosisRecord`: Items classified into conceptual gap, careless mistake, etc.
- `TailoredNoteRecord`: Versioned private remediation note with `[[concept]]` links.
- `ReviewVerdict`: `status: Literal["PASS", "BLOCK"]` with structured `objections`.

## 8. Bounded Loops & Fences
- **Revision Limit**: Maximum 3 revisions per learning cycle, counted from `slice.store` history.
- **Token Ceilings**: Governed by `slice.budget` (`SLICE_MAX_TOKENS`, `SLICE_MAX_TOKENS_PER_RUN`).
- **Step Retry Fence**: Maximum 3 model call attempts per step before escalating.
