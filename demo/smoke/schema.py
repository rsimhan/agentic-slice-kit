"""The three records this slice passes between steps.

Nothing crosses a step boundary as prose. A schema fails loudly at the boundary
where you can still see it - and slice/llm.py gets one repair pass out of it,
which only works because there is something to repair against.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class OpportunityRecord(BaseModel):
    """What SPOT produces. NOTE what is absent: no solution, no value
    proposition, no pitch. None of them has been earned yet."""

    problem: str = Field(
        description="What is bad today. Stated so that it could be shown to be false")
    who_specifically: str = Field(
        description="A person in a situation. Never a category")
    current_alternative: str = Field(
        description="What they actually do right now instead")
    why_now: str = Field(
        description="What CHANGED. A trend is not a change")


class Objection(BaseModel):
    """One defect in THIS thesis. Never generic advice."""

    field: str = Field(description="Which field of OpportunityRecord is at fault")
    problem: str = Field(description="The specific defect, quoting the offending text")


class Verdict(BaseModel):
    """What the gate produces. The only record here that moves the run."""

    status: Literal["PASS", "BLOCK"]
    objections: list[Objection] = Field(default_factory=list)
