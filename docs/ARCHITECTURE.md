# Architecture

Nine principles, and the line of code each one actually lives on.

An agent is a control loop wrapped around a non-deterministic function.
Everything below is derived from that one fact: production architecture is not
about making the model better, it is about making it **safe to put in a loop**.

The references below are `file:line · symbol`. They are checked by
`../tests/test_architecture.py`, so if the code moves and this document does not,
the suite fails and tells you the new line. Documentation that cannot go stale
silently is the only kind worth trusting.

---

## Tier 1 — the skeleton

Below this line it is not agentic, it is a chatbot with extra steps. Everything
in Tier 2 and Tier 3 depends on these three.

### 1. Durable state outside the context window

The context window is a cache. The system of record is external, versioned, and
reconstructed into context each turn — never the other way round.

| | |
|---|---|
| `slice/store.py:30` · `SCHEMA` | The tables. Note the two triggers at the bottom |
| `slice/store.py:133` · `Store.append` | The only way to write. There is no update |
| `slice/store.py:147` · `Store.latest` | Current state of one record kind — what an agent reads before acting |
| `slice/store.py:156` · `Store.history` | Every version, oldest first — the diff a judge wants to see |
| `slice/store.py:165` · `Store.replay` | The whole run in order |

**The design choice worth copying:** the versions table is append-only, and that
is enforced by *SQLite triggers* rather than by convention. `UPDATE` or `DELETE`
on the history raises. Four lines of schema mean a well-meaning refactor at hour
thirty cannot quietly turn your audit trail into mutable state.

Append-only buys four things for nothing: replay, diffs, resume, and an answer
to "why did it decide that".

### 2. Typed contracts at every boundary

Agents pass records, not prose. Prose compounds ambiguity silently; a schema
fails loudly at the boundary where you can still see it.

| | |
|---|---|
| `slice/llm.py:111` · `complete` | Takes a `schema=`; returns a parsed instance, never a string |
| `slice/llm.py:212` · `_parse` | Validation |
| `slice/llm.py:219` · `_repair` | One repair pass: shows the model its own output and the validation error |
| `slice/llm.py:198` · `_strip_fence` | Forgives a markdown fence — a formatting habit, not a broken contract |
| `slice/records.py:45` · `Version` | The envelope every record travels in |

**Why a repair pass and not a retry:** an identical second request usually fails
identically. Showing the model its own bad output plus the specific error is
what changes the outcome.

### 3. Bounded loops

The characteristic failure of an agent is not a crash — it is an expensive
infinite loop. Every loop stops on something real.

| | |
|---|---|
| `slice/budget.py:39` · `Budget` | Three scopes, smallest first |
| `slice/budget.py:56` · `Budget.check_tokens` | Called **before** a request, not after |
| `slice/budget.py:69` · `Budget.attempt` | Per-step allowance; raises when spent |
| `slice/budget.py:82` · `Budget.reset_attempts` | Cleared on genuine success, so a later retry starts fresh |
| `slice/runner.py:51` · `advance` | `max_steps` — a fence on the state machine itself |

**The counters live in the database, not in Python.** A fence that dies with the
process is not a fence. `tests/test_budget.py::test_fences_survive_a_restart`
closes the store, reopens it, and proves the counts came back.

There is a fourth ring you do not control from here: your API key's dollar cap,
enforced by the provider. Verified 3 Sep 2026 — it refuses a request *before*
running it if the worst case exceeds your balance.

---

## Tier 2 — what makes it demonstrable

What turns a working system into one a judge can believe without reading your
source.

### 4. Tool use with provenance

Not "the model said X" but "X — from `notes.md#3`, quoting this passage."

| | |
|---|---|
| `slice/retrieve.py:42` · `Chunk` | Text **and** where it came from |
| `slice/retrieve.py:51` · `Chunk.cite` | What an evidence row records |
| `slice/retrieve.py:88` · `ingest` | Chunk, embed locally, store — idempotent via content hashing |
| `slice/retrieve.py:118` · `search` | Returns ids, not just text |

Retrieval runs inside the run database: no vector service, no API key, no
network. Embeddings are computed locally with fastembed, baked into the
devcontainer image. On this environment, 5,000 chunks insert in 0.23s and a
nearest-neighbour query returns in 12ms — two orders of magnitude more headroom
than a hackathon corpus needs.

`search` returns `[]` on an empty corpus rather than inventing anything. That is
principle 9 showing up early.

### 5. Human-in-the-loop as a state, not an exception

The naive version blocks: call a human, wait, hope the process survives. It
never does.

| | |
|---|---|
| `slice/records.py:40` · `RunState.is_suspended` | Suspended is not terminal |
| `slice/callback.py:23` · `ask` | Parks the question, suspends the run, returns immediately |
| `slice/callback.py:37` · `answer` | Records it as `human_expert` evidence and wakes the run |
| `slice/callback.py:56` · `sweep` | Times out unanswered questions into `unresolved_no_expert` |
| `web/expert.py` | The page a real person answers on |

**This only works because of principle 1.** You cannot suspend a run whose
memory is a conversation. The process is free to exit entirely; a later
invocation picks the run up from the database.

**And every wait has a deadline.** An expert who never replies must not strand a
run forever. The timeout converts silence into a recorded "nobody knew" — a
legitimate finding, and an honest one.

### 6. Observability

You do not debug an agent by reading its output. You debug it by replaying its
decisions, because every interesting failure is in the middle steps.

| | |
|---|---|
| `slice/llm.py:79` · `_Span` | One span per call |
| `slice/config.py:44` · `Settings.tracing_enabled` | Off unless configured |

**Tracing no-ops when Langfuse is not set up**, and that is deliberate: no team
should be blocked at hour zero by an observability signup. Add it at hour four.

---

## Tier 3 — what makes it handoff-ready

The tier that answers "could someone else pick this up and keep building?" —
which you will be asked.

### 7. Orchestration in code, judgement in the model

Use the model for judgement *inside* a step. Use deterministic code for
sequencing *between* steps.

| | |
|---|---|
| `slice/runner.py:51` · `advance` | The state machine. Knows nothing about your domain |
| `slice/runner.py:31` · `Context` | What a step is handed |
| `slice/runner.py:45` · `Flow` | What a domain must provide — see `demo/flow.py` |

A model that picks its own next action is unbounded in cost and unauditable
afterwards, because the control flow differs on every run. Here the model
returns a verdict and **Python decides** what that verdict means.

**Resume is free.** There is no separate resume path to keep in sync: a
suspended run is just a run in a state whose handler is "wait", so calling
`advance` again is all resuming is.

### 8. At least one assertion a human is not making by eye

Without it, "we improved the prompt" is an unfalsifiable claim — a delicious
irony in a system built to test falsifiable claims.

| | |
|---|---|
| `tests/test_store.py` | Immutability, replay, resume |
| `tests/test_budget.py` | The fences, including surviving a restart |
| `tests/test_callback.py` | Suspend, resume, timeout, write-once answers |
| `tests/test_runner.py` | Control flow, and every failure path |
| `scripts/bakeoff.py` | Which model can actually hold the contract |

`bakeoff.py` earned its place the hard way. The model originally chosen from a
price table scored **0 of 3** — it could not produce parseable output at all.
Running the same eval again with five trials instead of three found another
model that complied only **2 times in 5**, at temperature zero. One clean run is
an anecdote. See `confident-and-wrong.html`.

### 9. A defined failure behaviour per dependency

Everything external will fail during 48 hours. Decide in advance, or discover it
in front of judges.

| | |
|---|---|
| `slice/llm.py:55` · `_classify_402` | The two 402s that look identical and mean opposite things |
| `slice/llm.py:43` · `CapExhausted` | **Your team** is capped — routine, get a top-up |
| `slice/llm.py:47` · `PoolExhausted` | **The shared account** is empty — every team is about to stop |
| `slice/llm.py:111` · `complete` | Falls back to a different provider family on 429/5xx |
| `slice/callback.py:56` · `sweep` | No expert → recorded unknown, run continues |
| `slice/retrieve.py:118` · `search` | Empty corpus → say so, invent nothing |
| `slice/runner.py:96` · `_fail` | Records **why** a run stopped, into the replayable history |

**A run that fails without leaving a reason is the one you cannot debug.**
Every failure path writes a `failure` record with a kind and a detail, so
`replay` shows you what happened rather than leaving you with a stack trace.

The 402 classification is honest about its own limits — read the docstring. We
verified the key-cap string against a live key; we have never run the shared
account dry, so anything that is *not* a key limit is treated as the more
serious case. A false alarm costs a conversation; a missed one costs the event.

---

## The split, and why it matters

```
slice/      the spine    — domain-independent, ~900 lines, READ IT
demo/       the domain   — rewrite this for your problem
```

`slice/` is deliberately **not** a package you install. Copy it, read it, edit
it. A library you import is a black box you do not learn from; nine hundred
readable lines is something you can hold in your head by hour six.

Swap `demo/` for your problem and keep the machinery. If you find yourself
editing `slice/` to make your domain fit, that is interesting — either you have
found a real limitation, or you are about to put domain logic somewhere it will
be hard to find later. Both are worth a minute's thought.

---

## Five anti-patterns

**The manager agent.** An LLM that decides which agent runs next. Feels
sophisticated, is unbounded in cost, and cannot be debugged — the control flow
is different every run.

**Conversation as state.** Works until the first restart, the first context
overflow, or the first time someone asks what happened at step four.

**Prose between agents.** Two lossy translations per hop, and no boundary where
a malformed handoff can be caught.

**Persona count as a proxy.** Five characters in the cast is not five times as
agentic. The measure is state transitions and tool calls, not how many system
prompts are wearing a costume.

**Framework before state model.** In 48 hours an orchestration framework costs
more to learn than the hundred lines it replaces, and it hides the state model
you most need to think about. Write the loop by hand. Adopt a framework on day
three of a project, not hour three.

---

*Companion documents: `anatomy-of-an-agentic-slice.html` for the principles
in full, `confident-and-wrong.html` for what happened when we tested our own
assumptions.*
