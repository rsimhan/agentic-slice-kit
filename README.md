# Agentic Slice Kit

A starter kit for building a **working agentic slice** in 48 hours.

Not a framework. Not a library. About 400 lines you are expected to read,
understand, and edit — because the architecture is the thing being taught, and
you cannot learn an architecture you have imported.

> **Status: under construction.** The spine's foundation is built and tested.
> The demo, retrieval, model routing and expert callback are landing next.

---

## Start here

Click **Open in Codespaces**. Nothing to install — no Python, no Node, no
Docker. You need a browser and a GitHub account.

```bash
cp .env.example .env      # then paste the key from the registration desk
python -m pytest          # should be green
```

Only `OPENROUTER_API_KEY` is required. Everything else in `.env` is an upgrade
you can add at hour four, not a blocker at hour zero.

---

## What "agentic" means here

A single-prompt LLM wrapper does not qualify, however clever the prompt. A real
agentic slice demonstrates at least one of:

- **state persistence** across steps
- **autonomous tool or API use**
- **multi-step reasoning or decomposition**
- **human-in-the-loop callback mechanics**

This kit demonstrates all four, and `docs/anatomy-of-an-agentic-slice.html`
explains how — nine principles, tiered by build order, with the line of code
each one lives on.

**Read that document before you write anything.** It will save you the rewrite
that happens around hour thirty to teams who start with prompts.

---

## Layout

```
slice/      THE SPINE — read this, edit it, do not treat it as a black box
  records.py    what a run is made of                    stdlib
  store.py      durable append-only state                stdlib
  budget.py     the fences: attempts, tokens, wall-clock
  llm.py        the ONE place a model is ever called
  retrieve.py   chunk / embed / search
  runner.py     the state machine
  callback.py   suspend, resume, time out

demo/       THE DOMAIN — rewrite this for your own problem
web/        the form a human expert answers on
scripts/    ingest · start · resume · replay · bakeoff
tests/      a golden case and five invariants
```

The split is the point. Swap `demo/` for your problem and keep the machinery.

---

## Three things that will bite you

**Your Codespaces quota is finite.** 120 core-hours a month, which is 60 hours
on the 2-core machine this repo asks for. Enough for the event with headroom —
unless you leave codespaces running that you have abandoned. If you do get
blocked, you can still export your work to a branch and a teammate can open a
fresh codespace on it.

**Your API key has a hard cap.** It is enforced, and it refuses a request
*before* running it if the worst case would exceed your balance — so an
oversized `max_tokens` produces a 402 while you still have credit. Leave
`SLICE_MAX_TOKENS` where it is unless you know why you are changing it.

**Default to the cheap model.** `SLICE_MODEL` is Flash-class and will carry
almost everything. `SLICE_ESCALATION_MODEL` costs roughly thirty times as much
per token. Escalate for the one hard subproblem, deliberately — not by habit at
3am when something is not working.

---

## The bar you are actually being judged against

Working code is necessary, not sufficient. You also owe: three fellow students
who walked your flow with their feedback captured and one visible iteration; a
recorded stress test where a classmate tried to break your agent, and the fix
commit that answers it; a short design rationale saying what your agent does and
where its limits are; and a repo someone else could pick up and continue.

Budget for that. Teams that treat hour 24 as a feature deadline rather than a
feedback deadline consistently ship the least convincing demos.
