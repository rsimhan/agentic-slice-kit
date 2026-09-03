"""
The one place a model is ever called.

Every architectural concern that touches a model call is enforced HERE, in one
function, rather than sprinkled across the agents:

    typed contracts   the reply is parsed into your schema, or repaired once
    bounded loops     the token fence is checked before the request goes out
    degradation       a named fallback model, a different provider family
    observability     one span per call, no-ops if tracing is not configured
    cost classifying  a 402 means one of two very different things

That last one is worth reading twice. OpenRouter refuses a request BEFORE
running it if the worst case exceeds the remaining balance - so a 402 arrives
with nothing spent. But there are two reasons it can arrive, and they need
opposite responses at 3am:

    your TEAM's key cap is spent    -> routine, go and get a top-up
    the SHARED account is empty     -> every team is about to stop, tell an
                                        organiser immediately

A student cannot tell those apart from a raw error, so we do it for them.
"""
from __future__ import annotations

import json
import time
from typing import Any, Type

import httpx
from pydantic import BaseModel, ValidationError

from .budget import Budget
from .config import Settings

API = "https://openrouter.ai/api/v1"


class ModelError(RuntimeError):
    """Base for everything that can go wrong at the model boundary."""


class CapExhausted(ModelError):
    """This team's key has spent its cap. One team affected."""


class PoolExhausted(ModelError):
    """The shared account is out of credit. EVERY team is affected."""


class SchemaFailure(ModelError):
    """The model would not produce the agreed shape, even after a repair pass."""


def _classify_402(body: dict) -> ModelError:
    """Read the error rather than guessing at it.

    Verified 3 Sep 2026: a key-cap rejection carries
    metadata.limit_source == "openrouter_key_limit". The account-level string
    is NOT verified - we have never run the pool dry - so anything that is not
    a key limit is treated as the more serious case. Erring toward "tell an
    organiser" is the right bias: a false alarm costs a conversation, a missed
    one costs the event.
    """
    err = (body or {}).get("error", {}) or {}
    src = ((err.get("metadata") or {}).get("limit_source") or "").lower()
    msg = err.get("message", "") or json.dumps(body)[:300]
    if "key" in src:
        return CapExhausted(
            "Your team's API key has reached its spending cap.\n"
            "  -> Reduce SLICE_MAX_TOKENS, or ask the key desk for a top-up.\n"
            f"  (provider said: {msg})")
    return PoolExhausted(
        "The SHARED account is out of credit - this affects every team, not "
        "just yours.\n  -> Tell an organiser now. Do not wait.\n"
        f"  (provider said: {msg})")


class _Span:
    """Tracing that costs nothing when it is not configured.

    If Langfuse keys are absent this is an empty context manager, so no team is
    ever blocked at hour zero by an observability signup they have not done.
    """

    def __init__(self, s: Settings, name: str, meta: dict):
        self.enabled, self.name, self.meta = s.tracing_enabled, name, meta
        self._span = None

    def __enter__(self):
        if self.enabled:
            try:
                from langfuse import Langfuse  # imported lazily and optionally
                self._client = Langfuse()
                self._span = self._client.trace(name=self.name, metadata=self.meta)
            except Exception:
                self._span = None       # tracing must never break the run
        return self

    def record(self, **kw):
        if self._span is not None:
            try:
                self._span.update(**kw)
            except Exception:
                pass

    def __exit__(self, *exc):
        return False


def complete(
    *,
    settings: Settings,
    budget: Budget,
    messages: list[dict],
    schema: Type[BaseModel] | None = None,
    model: str | None = None,
    step: str = "call",
    timeout: float = 120.0,
) -> Any:
    """Call a model. Returns a parsed `schema` instance, or raw text if no
    schema was asked for.

    Raises CapExhausted / PoolExhausted / SchemaFailure / BudgetExceeded - all
    of which the runner handles explicitly. Nothing here raises a bare
    HTTPError into caller code.
    """
    budget.check_tokens()                       # refuse to start, not to finish

    primary = model or settings.model
    attempts: list[tuple[str, str]] = [(primary, "primary")]
    if settings.fallback_model and settings.fallback_model != primary:
        attempts.append((settings.fallback_model, "fallback"))

    last_text = ""
    with _Span(settings, f"llm:{step}", {"model": primary, "step": step}) as span:
        for mid, role in attempts:
            body = {
                "model": mid,
                "max_tokens": settings.max_tokens,
                "temperature": 0,
                "messages": messages,
            }
            if schema is not None:
                body["response_format"] = {"type": "json_object"}

            t0 = time.time()
            try:
                r = httpx.post(f"{API}/chat/completions", json=body, timeout=timeout,
                               headers={"Authorization": f"Bearer {settings.api_key}"})
            except httpx.RequestError as e:
                if role == "fallback":
                    raise ModelError(f"Both models unreachable: {e}") from e
                continue                       # network hiccup: try the fallback

            if r.status_code == 402:
                raise _classify_402(_safe_json(r))     # never worth a retry
            if r.status_code in (429, 500, 502, 503) and role == "primary":
                continue                                # transient: fall back
            if r.status_code != 200:
                raise ModelError(f"{mid} returned HTTP {r.status_code}: {r.text[:300]}")

            data = r.json()
            used = (data.get("usage") or {}).get("total_tokens", 0)
            budget.record_tokens(used)
            last_text = data["choices"][0]["message"]["content"] or ""
            span.record(output={"model": mid, "role": role, "tokens": used,
                                "seconds": round(time.time() - t0, 2)})

            if schema is None:
                return last_text

            parsed = _parse(last_text, schema)
            if parsed is not None:
                return parsed

            # One repair pass. Show the model its own output and the error -
            # a second identical request usually fails identically.
            repaired = _repair(settings, budget, messages, last_text, schema, mid, timeout)
            if repaired is not None:
                return repaired
            if role == "fallback":
                break
            # primary could not hold the contract; the fallback might

    raise SchemaFailure(
        f"No model produced valid {schema.__name__ if schema else 'output'} "
        f"after a repair pass. Last reply began: {last_text[:200]!r}")


def _safe_json(r: httpx.Response) -> dict:
    try:
        return r.json()
    except Exception:
        return {"error": {"message": r.text[:300]}}


def _strip_fence(text: str) -> str:
    """Models wrap JSON in markdown fences even when told not to. That is a
    formatting habit, not a failure to follow the contract, so we forgive it
    here rather than burning a repair pass on it."""
    t = (text or "").strip()
    if t.startswith("```"):
        parts = t.split("```")
        if len(parts) > 1:
            t = parts[1]
            if t.lstrip().lower().startswith("json"):
                t = t.lstrip()[4:]
    return t.strip()


def _parse(text: str, schema: Type[BaseModel]):
    try:
        return schema.model_validate_json(_strip_fence(text))
    except (ValidationError, ValueError):
        return None


def _repair(settings, budget, messages, bad_text, schema, mid, timeout):
    budget.check_tokens()
    try:
        schema.model_validate_json(_strip_fence(bad_text))
    except Exception as e:
        why = str(e)[:600]
    else:
        return None
    fix = messages + [
        {"role": "assistant", "content": bad_text[:2000]},
        {"role": "user", "content":
            "That did not match the required schema.\n\n"
            f"Error:\n{why}\n\n"
            f"Required JSON schema:\n{json.dumps(schema.model_json_schema())}\n\n"
            "Reply with the corrected JSON object and nothing else."},
    ]
    try:
        r = httpx.post(f"{API}/chat/completions", timeout=timeout,
                       headers={"Authorization": f"Bearer {settings.api_key}"},
                       json={"model": mid, "max_tokens": settings.max_tokens,
                             "temperature": 0, "messages": fix,
                             "response_format": {"type": "json_object"}})
    except httpx.RequestError:
        return None
    if r.status_code == 402:
        raise _classify_402(_safe_json(r))
    if r.status_code != 200:
        return None
    data = r.json()
    budget.record_tokens((data.get("usage") or {}).get("total_tokens", 0))
    return _parse(data["choices"][0]["message"]["content"] or "", schema)
