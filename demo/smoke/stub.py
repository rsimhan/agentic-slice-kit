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
  "problem": "Students struggle to get internships and it is a real problem",
  "who_specifically": "Karthik, a batchmate with a 7.2 CGPA and two Android apps on the Play Store",
  "current_alternative": "He applied through the campus portal",
  "why_now": "The portal only started filtering below 8.0 from the 2025 cycle"
}"""
# A faithful first pass. It found Karthik and it found the rule change - but it
# took the PROBLEM from the founder's opening sentence and skipped the specific
# version buried halfway through the long one. That is the weakness the gate
# catches, and the fix is in the text.

BLOCK = """{
  "status": "BLOCK",
  "objections": [
    {"field": "problem",
     "problem": "No observation would show this to be false, because \\"struggle to get internships\\" is true of almost everyone. What specifically happens to Karthik that would not happen to a student the system works for?"}
  ]
}"""

V2 = """{
  "problem": "Applications below the CGPA cutoff are auto-rejected within the hour, without a human ever opening the file, so project work is never seen",
  "who_specifically": "Karthik, a batchmate with a 7.2 CGPA and two Android apps on the Play Store",
  "current_alternative": "He applied through the portal all year, was auto-rejected every time, and got in through a senior instead",
  "why_now": "The portal only started filtering below 8.0 from the 2025 cycle"
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
