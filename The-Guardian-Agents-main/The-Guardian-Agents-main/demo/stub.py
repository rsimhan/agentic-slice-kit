"""Canned responses for the Synapse agentic slice.

Zero tokens, zero network, zero API key required.
Exercises the complete Synapse cycle and proves the backward edge:
Draft v1 -> Review BLOCK -> Revised Draft v2 addressing objections -> Review PASS -> COMPLETE.
"""
from __future__ import annotations

from typing import Any, Type
from pydantic import BaseModel

# V1: First draft. Explains recursion well, but omits base-case termination
# and does not link to [[call_stack]], which caused the student's error.
V1_NOTE = """{
  "version": 1,
  "student_id": "student_42",
  "concept_id": "recursion_basics",
  "markdown": "# Understanding Recursion\\n\\nRecursion is when a function calls itself to break down a problem into subproblems. Think of Russian nesting dolls: opening one reveals a smaller doll inside until you reach the center.",
  "addressed_gaps": ["recursive_step"],
  "prerequisite_links": ["function_calls"]
}"""

# Reviewer blocks V1: Specific objection identifying the missing base case and call stack link.
BLOCK_VERDICT = """{
  "status": "BLOCK",
  "canonical_coverage": false,
  "objections": [
    {
      "field": "prerequisite_links",
      "problem": "The student failed question 2 due to stack overflow confusion. The draft explains self-invocation but omits base-case termination condition and lacks reference to [[call_stack]]."
    }
  ],
  "verdict_note": "Base case is non-negotiable for recursion mastery. Revise with base case explanation and [[call_stack]] reference."
}"""

# V2: Second draft. Directly incorporates reviewer objections: explains base case and links [[call_stack]].
V2_NOTE = """{
  "version": 2,
  "student_id": "student_42",
  "concept_id": "recursion_basics",
  "markdown": "# Understanding Recursion & Termination\\n\\nRecursion is when a function calls itself to solve smaller instances of a problem. Every recursive function MUST have a **base case** &mdash; a condition where it stops calling itself. Without a base case, frames keep piling onto the [[call_stack]] until memory is exhausted (Stack Overflow).\\n\\nExample:\\n```python\\ndef countdown(n):\\n    if n <= 0:  # Base case!\\n        return\\n    print(n)\\n    countdown(n - 1)  # Recursive step\\n```",
  "addressed_gaps": ["recursive_step", "base_case_termination"],
  "prerequisite_links": ["function_calls", "call_stack"]
}"""

# Reviewer passes V2: All objections resolved.
PASS_VERDICT = """{
  "status": "PASS",
  "canonical_coverage": true,
  "objections": [],
  "verdict_note": "Approved. Base case and stack mechanics are thoroughly explained and linked."
}"""

_SCRIPT: dict[str, list[str]] = {
    "tailor": [V1_NOTE, V2_NOTE],
    "review": [BLOCK_VERDICT, PASS_VERDICT]
}


class Stub:
    """A drop-in replacement for slice.llm.complete for deterministic testing."""

    def __init__(self) -> None:
        self.calls: list[str] = []
        self._n: dict[str, int] = {}

    def __call__(
        self,
        *,
        settings,
        budget,
        messages,
        schema: Type[BaseModel] | None = None,
        model: str | None = None,
        step: str = "call",
        timeout: float = 120.0
    ) -> Any:
        base = step.split(":")[0]
        i = self._n.get(base, 0)
        self._n[base] = i + 1
        self.calls.append(step)

        try:
            raw = _SCRIPT[base][i]
        except (KeyError, IndexError):
            raise AssertionError(
                f"Stub has no scripted reply for call #{i} of step '{step}'. "
                "The flow made an unexpected model call."
            )

        budget.record_tokens(len(raw) // 4)
        return schema.model_validate_json(raw) if schema else raw
