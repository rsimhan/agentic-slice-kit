"""
What a run is made of.

Deliberately stdlib-only: no pydantic, no framework. The store below has to be
understandable in one sitting, and a dependency-free core is easier to trust.
Domain schemas (ThesisRecord, Verdict, Evidence) use pydantic and live in
demo/schema.py - that is the layer you rewrite for your own problem.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class RunState(str, Enum):
    """
    Where a run is. Code - not a model - decides every transition between these.

    Terminal states are COMPLETE and FAILED. AWAITING_EXPERT is *suspended*,
    not terminal: the process can exit entirely and a later invocation picks
    the run back up. That is only possible because state lives in the database
    rather than in a conversation.
    """

    DRAFTING        = "drafting"          # an agent is producing a record
    GATING          = "gating"            # a judge is deciding pass / block
    PROBING         = "probing"           # evidence gathering, tool use
    AWAITING_EXPERT = "awaiting_expert"   # suspended on a human
    COMPLETE        = "complete"
    FAILED          = "failed"

    @property
    def is_terminal(self) -> bool:
        return self in (RunState.COMPLETE, RunState.FAILED)

    @property
    def is_suspended(self) -> bool:
        return self is RunState.AWAITING_EXPERT


@dataclass(frozen=True)
class Version:
    """
    One immutable entry in a run's history.

    `kind` groups a series - "thesis", "verdict", "evidence". `seq` orders the
    whole run. Asking for the latest "thesis" gives you current state; asking
    for its history gives you the diff a judge wants to see.
    """

    seq: int
    kind: str
    produced_by: str          # which agent or human wrote this
    payload: dict[str, Any]
    created_at: float

    @property
    def age_seconds(self) -> float:
        return time.time() - self.created_at


@dataclass
class Question:
    """A question parked for a human. The run is suspended until it is answered."""

    id: str
    run_id: str
    question: str
    context: dict[str, Any] = field(default_factory=dict)
    asked_at: float = 0.0
    timeout_at: float = 0.0
    answered_at: float | None = None
    answer: str | None = None

    @property
    def is_answered(self) -> bool:
        return self.answer is not None

    @property
    def is_expired(self) -> bool:
        return not self.is_answered and time.time() > self.timeout_at


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"
