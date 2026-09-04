"""
The fences.

The characteristic failure of an agent is not a crash. It is a loop that runs
all night and spends everything you have. So every loop stops on something
real, and the counters live in the DATABASE, not in a Python variable - a fence
that dies with the process is not a fence.

Three scopes, smallest first:

    attempts per step   the gate revises 3 times, then escalates
    tokens per run      one run cannot consume the whole budget
    dollars per key     enforced by the provider, outside this code

That last one is the outermost ring and you do not control it from here. It is
worth knowing it exists: OpenRouter refuses a request BEFORE running it if the
worst case would exceed the key's remaining balance.
"""
from __future__ import annotations

from .config import Settings
from .store import Store


class BudgetExceeded(RuntimeError):
    """A fence was reached. Not an error in the usual sense - the system
    working as designed. Callers decide whether that means escalate, degrade,
    or stop, and the runner makes that decision explicitly rather than letting
    an exception bubble into a stack trace a tired student has to decode."""

    def __init__(self, kind: str, used: float, limit: float, detail: str = ""):
        self.kind, self.used, self.limit = kind, used, limit
        super().__init__(
            f"{kind} budget reached: {used:g} of {limit:g}."
            + (f" {detail}" if detail else "")
        )


class Budget:
    """Fences for one run. Reads and writes counters through the store, so
    everything here survives a process restart and a resume."""

    TOKENS = "tokens"

    def __init__(self, store: Store, run_id: str, settings: Settings):
        self.store, self.run_id, self.s = store, run_id, settings

    # ---------------------------------------------------------------- tokens

    def tokens_used(self) -> float:
        return self.store.counter(self.run_id, self.TOKENS)

    def tokens_remaining(self) -> float:
        return max(0.0, self.s.max_tokens_per_run - self.tokens_used())

    def check_tokens(self) -> None:
        """Call BEFORE a model request, not after. Refusing to start is
        cheaper than discovering you should not have."""
        used = self.tokens_used()
        if used >= self.s.max_tokens_per_run:
            raise BudgetExceeded("token", used, self.s.max_tokens_per_run,
                                 "Raise SLICE_MAX_TOKENS_PER_RUN or start a new run.")

    def record_tokens(self, n: int) -> float:
        return self.store.bump(self.run_id, self.TOKENS, n)

    # -------------------------------------------------------------- attempts

    def attempt(self, step: str) -> int:
        """Count one attempt at a named step and return the new total.
        Raises once the step has had its allowance."""
        name = f"attempts:{step}"
        n = self.store.bump(self.run_id, name)
        if n > self.s.max_attempts_per_step:
            raise BudgetExceeded("attempt", n, self.s.max_attempts_per_step,
                                 f"Step '{step}' did not converge.")
        return int(n)

    def attempts(self, step: str) -> int:
        return int(self.store.counter(self.run_id, f"attempts:{step}"))

    def reset_attempts(self, step: str) -> None:
        """Called when a step genuinely succeeds, so a later retry of the same
        step starts fresh rather than inheriting a spent allowance."""
        self.store.reset_counter(self.run_id, f"attempts:{step}")

    # ----------------------------------------------------------------- report

    def summary(self) -> dict:
        return {
            "tokens_used": self.tokens_used(),
            "tokens_limit": self.s.max_tokens_per_run,
            "tokens_remaining": self.tokens_remaining(),
        }
