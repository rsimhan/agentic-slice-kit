# Builder

**You get the machinery running and keep everyone else unblocked.** On the first
morning that means an environment that works, the spine understood well enough
to wire your own domain into it, and the state machine actually turning. After
that you are the person who reads the error message when something breaks at
four o'clock.

You will not be writing most of the code by hand — an assistant will. What you
bring is knowing what to ask it for, and noticing when what came back is subtly
wrong. That is a different skill from typing Python, and it is the scarcer one.

---

## Before you open this

Your team's spec comes from [`DESIGNER.md`](DESIGNER.md) — the problem, the
states, the records, the rules. Read it before you build anything; you are
implementing that, and an hour spent arguing with it now is worth a day of
rework. If your team has not written one, that is the first job, and everyone
does it together.

Then this document, in order. It takes about twenty minutes to get running and
another hour to understand what you are running.

---

## Twenty minutes to a running system

**Open in Codespaces.** The green *Code* button on the repo → *Codespaces* →
*Create codespace on main*. This gives you a full computer in a browser tab,
already set up. Nothing installs on your laptop. First open takes a couple of
minutes; after that it is seconds.

**Put your key in `.env`.** The registration desk gives you a key beginning
`sk-or-v1-`. Open the file called `.env`, paste it after `OPENROUTER_API_KEY=`,
save. That key is how your team pays for the AI models you use, and it has a
spending cap on it, so you cannot accidentally run up a bill.

**Check the environment before you build anything:**

```bash
python scripts/doctor.py
```

---

### What the doctor is doing, and what can go wrong

It is a pre-flight check. Five things, in the order they actually break. It is
worth understanding these, because **most of what looks like a broken agent at
hour six of day one is a broken environment**, and the difference is an hour.

**1. Is your config file there, and does it have a key?**
Without this nothing else can run. If you skipped the paste step, it says so.

**2. Does the key work, and how much credit is left?**
It reports your remaining balance. If you are below a quarter it warns you.
Useful to glance at occasionally — if it is dropping fast, something is looping.

**3. Can it reach the three AI models, right now?**
**This is the check that saves you.** Model providers go down and rate-limit
people. When that happens your agent fails in a way that looks *exactly* like a
mistake in your instructions — so you rewrite a prompt that was never wrong.
The doctor asks each model a one-word question and reports what came back.

**4. Does the search engine load?**
The bit that finds relevant passages in your documents. It is a small extension
to the built-in database and it either loads or it doesn't.

**5. Is the language-understanding model present?**
The thing that converts text into a form you can search by meaning. It is baked
into the environment so it works instantly and offline. If it is missing, your
first document ingest will try to download 80MB — fine on good wifi, painful on
venue wifi with two hundred people on it.

**What you might see:**

| what it says | what it means | what to do |
|---|---|---|
| `OPENROUTER_API_KEY is empty` | You haven't pasted the key | Paste it into `.env`, save, rerun |
| `key works — $2.100 of $12.00 left (18%)` | You're running low | Lower `SLICE_MAX_TOKENS`, or see the desk |
| `rate-limited right now (429)` | **Not your fault.** The provider is throttling | Wait a few minutes, or switch to the fallback model |
| `refused for credit (402)` | Your cap can't cover a request this size | Lower `SLICE_MAX_TOKENS`, or get a top-up |
| `unreachable (HTTP 000)` | Network problem, not a code problem | Check the wifi before you check your code |
| `sqlite-vec will not load` | Something is wrong with the environment | Rebuild the Codespace; ask a mentor |
| `embedding model not baked in` | Warning, not an error | It'll download on first use. Do it now, not mid-build |

**If the doctor is unhappy, stop and fix that.** Debugging your agent on a
broken environment is the most expensive mistake available to you this weekend.

Then:

```bash
python -m pytest
```

That runs the kit's own tests. It should be green. If it isn't, something in
the environment is wrong and it is not something you did.

---

---

## Read five functions, not eleven hundred lines

`slice/` is about 1,100 lines and the instruction "read it" is not useful on a
morning when four people are waiting for you. These five are the ones you will
actually touch. Forty-odd lines between them, and after that the rest of the
spine is predictable.

| read | in | because |
|---|---|---|
| `Store.append` · `Store.latest` · `Store.history` | `slice/store.py` | how state is written and read back. Everything else is built on these three |
| `advance` | `slice/runner.py` | the loop. Your handlers get called from here, and it is about thirty lines |
| `complete` | `slice/llm.py` | the only place a model is ever called, on purpose. One choke point to reason about |
| `ask` · `answer` | `slice/callback.py` | how a run suspends on a person and gets picked up later |
| `search` | `slice/retrieve.py` | what comes back from the documents, and what a citation actually is |

**Then write `demo/flow.py`.** Your handlers, your transitions, your rules. That
is where a domain lives and the spine does not change. `demo/SPEC.md` is a worked
example of one — including the parts that turned out to be wrong when three
reviewers went at it, which is the more useful half.

[`ARCHITECTURE.md`](ARCHITECTURE.md) is the reference for everything else. It is
not a tutorial and you should not read it cover to cover — go there when
something breaks, or when a judge asks why the system is shaped this way.

**One thing about copying rather than installing.** You got the spine by copying
it, so if a fix lands upstream nobody gets it automatically. Check the repo on
the morning of day two. And if you find a bug in `slice/` yourself, say so in
the shared channel — every team is running the same code, and you will have
saved several of them an afternoon.

## What you actually change

Three files. Everything else is machinery you can leave alone.

| file | what it holds | the question it answers |
|---|---|---|
| `demo/schema.py` | The shape of the records your agents pass each other | *What are we building up, and what fields must it have?* |
| `demo/prompts/*.md` | What each agent is told | *What is each one for?* |
| `demo/flow.py` | The transitions and the rules | *What happens next, and who decides?* |

**The check you owe the team.** [`DESIGNER.md`](DESIGNER.md) explains why a
citation the model wrote is not evidence. The code is yours, it is short, and it
runs after the model has answered and asks the model nothing:

> Is the source it cited one of the passages this search actually returned?
> And does the quote appear word for word inside that passage, ignoring spacing?

Both true and the row stands. Either false and the row is **demoted** — kept,
relabelled *could not establish*, with a note saying which check failed. Never
deleted. Write this before the prompts get good, not after; a system that claims
provenance and one that has it look identical right up to the moment someone
checks.

**`flow.py` is the one that matters**, and it is where your five rules from the
prep work land. It holds decisions like "three failed reviews means escalate"
and "a question the documents cannot answer goes to a human".

There is a trap inside that first example. "Three failed reviews" is a rule
about your problem, so it has to be counted from the record — how many verdicts
are already written down for this item — and never from the attempt counter the
kit uses to stop runaway spending. That counter is also ticking for retries
after a garbled response. Point your rule at it and a run that hit two bad
responses silently gets one review instead of three, which you find out on
stage. A spending fence and a domain limit are both "a small number you stop
at", and they must never be the same number.

Those decisions are made in **code**, not by a model. The model supplies
judgement inside a step — *is this thesis specific enough?* — and your rules
decide what that judgement means.

That split is the right default **for a two-day build**, and it is worth being
clear that it is a choice about time rather than a law. Letting a model decide
what happens next is a legitimate technique and people build good systems that
way. It simply costs more: when every run takes its own route, every route has
to be traced, and the fences have to hold on paths nobody wrote down. Sequencing
in code keeps the cost and the behaviour reviewable while you still have hours
in which to review them. Start there. If there is a step where the model
genuinely should be choosing, you will know exactly which one it is — and you
will be able to say why, which is the answer a judge is listening for.

---

## Working with an AI assistant on this

You have Copilot in the Codespace and probably Claude in another tab. Both are
far better at this than at "build me a multi-agent system", and the whole
difference is in what you ask for.

**Give it the contract, not the vibe.** Paste `demo/schema.py` and say *"write a
function that takes a ThesisRecord and returns a Verdict, blocking when the
customer is a category rather than a specific person."* That is a request that
can be satisfied exactly. "Build me an agent that reviews ideas" cannot.

**One function at a time.** A 300-line generated file that almost works is much
harder to fix than three 20-line pieces you understood as they arrived.

**Show it the real error.** Paste the actual message, not "it doesn't work",
and say what you expected instead. This one habit is most of the gap between
people who find assistants useful and people who find them maddening.

**Don't let it edit `slice/`.** If your assistant starts changing the machinery
to make your domain fit, stop. Either you have found a real limitation — tell a
mentor, that is interesting — or you are about to bury your logic somewhere
nobody will find it tomorrow. It is almost always the second.

**Read what it wrote to check the decision, not the syntax.** You do not need
to verify that the Python is valid; it will be. You need to notice that it wrote
a retry loop with no limit, or caught an error and carried on as though nothing
happened. Those are the bugs that cost you an afternoon, and spotting them is a
judgement call — which is your job, not the assistant's.

**Watch for `assert` on anything a model produced.** Assistants reach for it
constantly, and in a step that handles model output it is wrong twice over. A
model returning something odd is an ordinary Tuesday, not a programming error,
so an `assert` turns a normal bad answer into a stack trace with nothing written
down about what happened. Worse, Python is allowed to skip `assert` lines
entirely — run with `python -O` and your check is simply not there, silently.
Whatever it was guarding should be recorded as a finding the run can carry, or
raised as a named error your flow knows how to catch.

---

## Five ways this goes wrong

**You start with prompts.** Prompts are the last thing, not the first. Get one
boring path working end to end with a hard-coded fake answer, *then* make it
clever. Teams that start with prompts rewrite everything on the second morning.

**You add agents instead of behaviour.** Five personas is not five times as
agentic. What counts is state changes and tool calls, not how many instructions
are wearing a costume.

**You point at the expensive model.** `SLICE_MODEL` is cheap and was chosen by
running an evaluation, not by reading a price list. `SLICE_ESCALATION_MODEL`
costs roughly thirty times more per word. Escalate deliberately, for one hard
sub-problem — not out of frustration when something will not work.

**You keep everything in the conversation.** It works until the first restart.
Write it down; that is what the store is for.

**You leave the users until the end.** See [`VERIFIER.md`](VERIFIER.md). It is
worth more marks than your last feature and cannot be faked on the second afternoon.

---

## When you are stuck

```bash
python scripts/doctor.py                              # environment first, always
python -c "from slice.store import Store; \
  [print(v.seq, v.kind, v.produced_by, str(v.payload)[:90]) \
   for v in Store('run.db').replay('<run_id>')]"       # what actually happened
```

`replay` prints every step your agent took, in order — what each part produced
and when. Almost every "why on earth did it do that" question is answered by
reading it. It is also the best thing to put on screen when you demo: judges
want to see the agent **think**, not just its final answer.

**One thing to know about reading state back.** Asking the store for the
*latest* record of some kind means "the current one" only when there is a single
one of that kind per run — the current draft, the current verdict. For anything
you keep one of **per item** — an evidence row for each assumption — the latest
row is just whichever item happened to be written last. Walk the full history
for that kind and take the newest row per item instead. Get this wrong and you
get a table where every row shows the same answer, and it looks convincingly
like a prompt problem for about an hour.

And if you are stuck for more than twenty minutes, ask a mentor. Twenty minutes
is the right threshold — long enough to have genuinely tried, short enough that
the night is not gone.
