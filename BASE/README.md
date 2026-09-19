# COGNIX Diagnostic Agent — Agent-a-Thon Starter (debugged)

A narrow, reusable diagnostic-agent prototype for recursion.

## What it demonstrates
- Hypothesis-driven diagnosis
- One discriminating learner check at a time
- Evidence that can support, contradict, or remain uncertain
- Bounded hypothesis revision
- Explicit learner confirmation / rejection
- Persistent learner state (one JSON file per learner, under `state/`)
- Safe stopping
- Replay without an LLM

## Requirements
Python 3.10+. No third-party packages.

## Run
```bash
python demo.py        # scripted replay, no API needed
python test_agent.py  # 13 regression tests
pytest test_agent.py  # optional, if pytest is installed
```

Set `COGNIX_STATE_DIR` to change where learner records are written
(defaults to `./state`).

## Files
| File | Role |
|---|---|
| `models.py` | dataclasses for hypotheses, checks, learner state, run |
| `store.py` | per-learner JSON persistence (atomic writes) |
| `state_machine.py` | the deterministic controller — no model calls here |
| `llm.py` | the only model boundary; `model_request` is a stub |
| `demo.py` | four scripted cases, replayable without an API |
| `test_agent.py` | regression tests for the controller invariants |

## Wiring in a model
`llm.py:model_request` raises `NotImplementedError` by design. Implement it
against the organizer-approved API, validate the JSON it returns, then feed
the validated fields into `choose_hypothesis` / `ask` / `evaluate`. The
controller stays unchanged and stays deterministic.
