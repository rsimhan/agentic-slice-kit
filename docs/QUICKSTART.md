# Quickstart

**For the person who can read code but has never built an agent** — and for
anyone driving this with an AI assistant.

You do not need to understand `slice/` to build something good. You need to
understand *what you are changing and why*. That is what this page is for.
Twenty minutes to a running system, then three files.

---

## 1. Get it running

**Open in Codespaces.** Green *Code* button → *Codespaces* → *Create codespace
on main*. Nothing installs on your laptop. First open takes a couple of minutes.

**Put your key in `.env`.** The registration desk gives you a key beginning
`sk-or-v1-`. Open `.env` and paste it after `OPENROUTER_API_KEY=`. Nothing else
in that file needs touching.

**Check the environment before you write a line:**

```bash
python scripts/doctor.py     # should end "all clear"
python -m pytest             # should be green
```

If the doctor complains, fix that first. **Most of what looks like a broken
agent at 3am is a broken environment**, and you can lose an hour to that.

**Give it something to read.** Drop a few `.md` or `.txt` files into `corpus/`:

```bash
python -c "
from slice.store import Store
from slice import retrieve
s = Store('run.db')
print(retrieve.ingest(s, 'corpus'))
for c in retrieve.search(s, 'your question here', k=3):
    print(f'{c.cite():<16} {c.text[:70]}...')
"
```

Every result comes back with a citation like `notes.md#2`. **Keep that.** It is
what lets a judge tell retrieval from invention, and it costs you nothing.

---

## 2. What you actually change

Three files. Everything else is machinery you can leave alone.

| file | what it holds | the question it answers |
|---|---|---|
| `demo/schema.py` | The typed records your agents pass each other | *What shape is the thing we're building up?* |
| `demo/prompts/*.md` | What each agent is told | *What is each one for?* |
| `demo/flow.py` | The state transitions and the business rules | *What happens next, and who decides?* |

**`flow.py` is the important one.** It holds the rules — "three failed reviews
means escalate", "an unanswerable question goes to a human". Those are decisions
made in **Python**, not by a model. The model supplies judgement inside a step;
your code decides what that judgement means.

That distinction is most of what separates a system from a chatbot.

---

## 3. How to use an AI assistant on this well

You have Copilot in the Codespace, and probably Claude in another tab. Both are
much better at this than they are at "build me a multi-agent system", and the
difference is entirely in what you ask for.

**Give it the contract, not the vibe.** Paste `demo/schema.py` and say *"write a
function that takes a ThesisRecord and returns a Verdict, blocking when the
customer is a category rather than a person."* That is a request a model can
satisfy exactly. "Build me an agent that reviews ideas" is not.

**One function at a time.** A 300-line generated file that almost works is
harder to fix than three 20-line functions you understood as they arrived.

**Show it the real error.** Paste the actual traceback, not "it doesn't work".
Include what you expected. This single habit is most of the gap between people
who find AI assistants useful and people who find them frustrating.

**Do not let it edit `slice/`.** If your assistant starts changing the spine to
make your domain fit, stop. Either you have found a genuine limitation — which
is interesting, tell a mentor — or you are about to bury domain logic somewhere
nobody will find it tomorrow. Ninety percent of the time it is the second.

**Read what it wrote before you run it.** Not to check the syntax — to check the
*decision*. An assistant will happily write a retry loop with no limit, or catch
an exception and carry on as if nothing happened. Those are the bugs that cost
you Saturday night.

---

## 4. Five ways this goes wrong

**You start with prompts.** Prompts are the last thing, not the first. Get one
boring path working end to end with a hard-coded stub, *then* make it clever.
Teams that start with prompts rewrite everything around hour thirty.

**You add agents instead of behaviour.** Five personas is not five times as
agentic. The measure is state transitions and tool calls, not how many system
prompts are wearing a costume.

**You point at the expensive model.** `SLICE_MODEL` is cheap and was chosen by
running an evaluation, not by reading a pricing page. `SLICE_ESCALATION_MODEL`
costs about thirty times more per token. Escalate deliberately, for one hard
subproblem — not by habit at 3am when something isn't working.

**You keep state in the conversation.** It works until the first restart. Write
it to the store; that is the entire point of `slice/store.py`.

**You leave the users until the end.** See [`EVIDENCE.md`](EVIDENCE.md). It is worth more marks
than your last feature and it cannot be faked on Sunday morning.

---

## 5. When you are stuck

```bash
python scripts/doctor.py                              # environment first, always
python -c "from slice.store import Store; \
  [print(v.seq, v.kind, v.produced_by, str(v.payload)[:90]) \
   for v in Store('run.db').replay('<run_id>')]"       # what actually happened
```

`replay` prints every step in order — what each agent produced and when. Almost
every "why did it do that" question is answered by reading it. It is also the
single best thing to put on screen when you demo: judges want to see the agent
*think*, not just its final answer.

And if you are properly stuck for more than twenty minutes, ask a mentor. That
is what they are there for, and twenty minutes is the right threshold — long
enough to have tried, short enough that the night is not gone.
