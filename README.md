# Agentic Slice Kit

A starter kit for building a **working agentic slice** in 48 hours.

Not a framework. Not a library. About 400 lines you are expected to read,
understand, and edit — because the architecture is the thing being taught, and
you cannot learn an architecture you have imported.

> **Status: spine complete, 23 tests passing. `demo/` is next.**

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

This kit demonstrates all four, and [`docs/anatomy-of-an-agentic-slice.html`](docs/anatomy-of-an-agentic-slice.html)
explains how — nine principles, tiered by build order, with the line of code
each one lives on.

**Read that document before you write anything.** It will save you the rewrite
that happens around hour thirty to teams who start with prompts.

---

## Who does what

A team of four will not all do the same job, and the strongest teams split it
like this. This is a strong recommendation, not a rule - organise differently if
you have a better idea, but decide deliberately rather than by drift.

| | owns | starts with |
|---|---|---|
| **The builder** | `slice/` - the spine, the plumbing, unblocking everyone else | [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) |
| **The domain lead** | `demo/` - prompts, schema, the rules in `flow.py` | [`docs/QUICKSTART.md`](docs/QUICKSTART.md) |
| **The evidence lead** | user tests, the stress test, the design rationale | [`docs/EVIDENCE.md`](docs/EVIDENCE.md) |

**If you write no code at all, take the third role.** It is not the consolation
prize. Roughly 40% of what you are judged on is evidence that real people used
your agent and that you changed it in response - and it is the part almost every
team leaves until hour 40, by which point it is too late to do honestly.

---

## Layout

```
slice/      THE SPINE — read this, edit it, do not treat it as a black box
  records.py    what a run is made of                   stdlib   88
  store.py      durable append-only state               stdlib  246
  config.py     the one place .env is read              stdlib   64
  budget.py     the fences: attempts and tokens         stdlib   94
  llm.py        the ONE place a model is ever called            249
  retrieve.py   chunk / embed / search, in the same db          138
  callback.py   suspend on a human, resume, time out            101
  runner.py     the state machine                                81

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
