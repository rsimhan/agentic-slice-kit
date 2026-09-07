"""Canned responses, so the whole state machine can be proven with no key, no
network and no tokens.

Build this FIRST. It takes twenty minutes and it means that when the live run
misbehaves, you already know the wiring is not the problem.

The canned payloads are parsed through the real schema rather than constructed
as objects - so a mistake in schema.py still fails here, where it is cheap.
"""
from __future__ import annotations

from typing import Any, Type

from pydantic import BaseModel

# The scripted run in SMOKE-SPEC.md section 4. Weak draft, three objections,
# revised draft, pass.

V1 = """{
  "problem": "Students struggle to find internships that match what they can do",
  "who_specifically": "Students",
  "current_alternative": "They apply through the campus portal and wait",
  "why_now": "AI is growing fast and changing hiring"
}"""
# A faithful first pass: it took the opening framing and flattened the last two
# sentences, which is exactly what a real model does with this paragraph.

BLOCK = """{
  "status": "BLOCK",
  "objections": [
    {"field": "who_specifically",
     "problem": "\\"Students\\" is a category, not a person in a situation. Which student, at what moment, does this bite?"},
    {"field": "why_now",
     "problem": "\\"AI is growing fast\\" is a trend, not a change. Trends are always true, so they justify anything."},
    {"field": "problem",
     "problem": "No observation would show this to be false. \\"Struggle to find internships\\" is true of almost everyone, so there is nothing to test."}
  ]
}"""

V2 = """{
  "problem": "Applications below the CGPA cutoff are rejected before a human reads them, so project work never gets seen",
  "who_specifically": "A third-year with a 7.2 CGPA and two shipped side projects, applying through the campus portal",
  "current_alternative": "They apply anyway, get auto-rejected within the hour every time, then get in through a senior instead",
  "why_now": "From the 2025 placement cycle the portal auto-filters below 8.0 before any recruiter sees the file"
}"""

PASS = """{"status": "PASS", "objections": []}"""

_SCRIPT: dict[str, list[str]] = {"spot": [V1, V2], "gate": [BLOCK, PASS]}


class Stub:
    """A drop-in for slice.llm.complete. Same keyword signature, no network."""

    def __init__(self) -> None:
        self.calls: list[str] = []
        self._n: dict[str, int] = {}

    def __call__(self, *, settings, budget, messages, schema: Type[BaseModel] | None = None,
                 model: str | None = None, step: str = "call", timeout: float = 120.0) -> Any:
        base = step.split(":")[0]
        i = self._n.get(base, 0)
        self._n[base] = i + 1
        self.calls.append(step)

        try:
            raw = _SCRIPT[base][i]
        except (KeyError, IndexError):
            raise AssertionError(
                f"stub has no scripted reply {i} for step {step!r}. The flow made a "
                "call the script did not expect - which is usually the finding, not a "
                "problem with the stub."
            )

        budget.record_tokens(len(raw) // 4)     # a plausible count, so fences move
        return schema.model_validate_json(raw) if schema else raw
