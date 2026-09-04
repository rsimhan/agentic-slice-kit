# Quickstart — the domain lead

**You do not have to be a programmer to own this role.** Plenty of people build
substantial systems without reading the code their assistant writes — what they
bring is judgement about *what should happen*, and that turns out to be the
scarcer skill.

So this guide explains the **system**, not the syntax. Where something technical
happens, you get told what it is for and what it means when it breaks. If you
find yourself reading Python here, that is a failure of this document, not of
you.

**Your actual job:** decide what the agent should do, what counts as a good
answer, and when it should refuse. Those are product decisions. The code is
downstream of them.

---

## Before the event — two weeks, three hours

You have until 19 September. These are worth more than any amount of tutorial.

### 1. Pick your problem, and make it small

Not "improve education". One specific moment that annoys you: the lab report
nobody knows how to structure, the first-year course where everyone fails the
same question, the way project groups get assigned.

**Write one paragraph** describing what happens today and why it is bad. If you
can't do that in a paragraph, the problem is still too big.

### 2. Write down the rules, in plain English

This is the real work of the domain role, and it is entirely non-technical.

Imagine your agent has produced an answer. **What would make it wrong?** Write
five specific things — not "it's not good enough" but "it named a whole
department instead of a specific person", "it gave the answer instead of asking
a question", "it claimed something with no source".

That list becomes the gate: the rules your agent is checked against. On the
night, translating those five sentences into code is about twenty minutes. Not
having thought about them is what costs teams their Saturday.

### 3. Gather what your agent should read

Ten to twenty documents about your problem. Syllabus pages, lab manuals, past
papers, forum threads, notes from talking to three students about it. Plain text
or markdown. **Notes from real conversations are worth more than anything
official** — they contain the specifics that make an answer useful.

### 4. Get fluent at directing an assistant

Build something small this fortnight — a script that renames files, a page that
shows a timetable. Anything. What you are practising is not coding; it is the
habit of describing a task precisely enough that a machine can satisfy it, then
reading what came back and saying what is wrong with it.

That habit is the whole job, and two weeks of it is a lot.

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
3am is a broken environment**, and the difference is an hour.

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
venue wifi at midnight.

**What you might see:**

| what it says | what it means | what to do |
|---|---|---|
| `OPENROUTER_API_KEY is empty` | You haven't pasted the key | Paste it into `.env`, save, rerun |
| `key works — $2.100 of $12.00 left (18%)` | You're running low | Lower `SLICE_MAX_TOKENS`, or see the desk |
| `rate-limited right now (429)` | **Not your fault.** The provider is throttling | Wait a few minutes, or switch to the fallback model |
| `refused for credit (402)` | Your cap can't cover a request this size | Lower `SLICE_MAX_TOKENS`, or get a top-up |
| `unreachable (HTTP 000)` | Network problem, not a code problem | Check the wifi before you check your code |
| `sqlite-vec will not load` | Something is wrong with the environment | Rebuild the Codespace; ask a mentor |
| `embedding model not baked in` | Warning, not an error | It'll download on first use. Do it now, not at 2am |

**If the doctor is unhappy, stop and fix that.** Debugging your agent on a
broken environment is the most expensive mistake available to you this weekend.

Then:

```bash
python -m pytest
```

That runs the kit's own tests. It should be green. If it isn't, something in
the environment is wrong and it is not something you did.

---

## Give your agent something to read — and why

Right now your agent knows whatever the language model picked up from the
internet. It knows **nothing about your problem** — not your syllabus, not your
lab manuals, not the notes you took talking to three students last Tuesday.

Ingesting fixes that. Drop your documents into `corpus/` as `.md` or `.txt`,
then:

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

**Three things just happened.** Your documents were chopped into passages of a
few hundred words. Each passage was converted into a list of numbers that
captures its *meaning*. Those were stored in a file next to your code.

Later, when your agent has a question, the question gets converted the same way
and the closest passages come back — **closest in meaning, not in wording**.
Asking "how fast is AI improving" will surface a passage about "model capability
growth" that shares no words with the question at all. That is the whole trick,
and it is why this is better than searching for keywords.

**This is a design decision, not a technical step.** What you put in `corpus/`
determines what your agent can know — and, more importantly, what it can be held
to. That choice is yours and it matters more than any prompt you will write. An
agent with ten pages of real interview notes will say more useful things than one
with a hundred pages of official documentation.

---

## Why the citation matters

Every result comes back tagged like `notes.md#2` — document name, passage
number. **Keep that all the way through to your output.**

Here is what it buys you. Language models produce fluent, confident, specific
prose whether or not it is true. Faced with an output that says *"students
consistently struggle with free-body diagrams"*, nobody — not you, not a judge —
can tell whether your agent **found that in your documents** or **made it up**.
Both look identical on the page. This is the single most common way agentic
demos quietly mislead the people watching them.

The citation removes the ambiguity. An output that says:

> Students consistently struggle with free-body diagrams
> — `interviews.md#4`: *"three of the five students I spoke to redrew the
> diagram before they could start the problem"*

is **checkable**. A judge can follow it back. And when your agent genuinely
cannot find support for something, it can say so, which is far more impressive
than confident invention — it means your system knows the difference between
what it found and what it assumed.

It costs you nothing. The citation is already attached to every passage; you
only have to not throw it away.

---

## What you actually change

Three files. Everything else is machinery you can leave alone.

| file | what it holds | the question it answers |
|---|---|---|
| `demo/schema.py` | The shape of the records your agents pass each other | *What are we building up, and what fields must it have?* |
| `demo/prompts/*.md` | What each agent is told | *What is each one for?* |
| `demo/flow.py` | The transitions and the rules | *What happens next, and who decides?* |

**`flow.py` is the one that matters**, and it is where your five rules from the
prep work land. It holds decisions like "three failed reviews means escalate"
and "a question the documents cannot answer goes to a human".

Those decisions are made in **code**, not by a model. The model supplies
judgement inside a step — *is this thesis specific enough?* — and your rules
decide what that judgement means. That separation is most of what distinguishes
a system from a chatbot, and it is entirely a design question. It is your call.

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
happened. Those are the bugs that cost you Saturday night, and spotting them is a
judgement call — which is your job, not the assistant's.

---

## Five ways this goes wrong

**You start with prompts.** Prompts are the last thing, not the first. Get one
boring path working end to end with a hard-coded fake answer, *then* make it
clever. Teams that start with prompts rewrite everything around hour thirty.

**You add agents instead of behaviour.** Five personas is not five times as
agentic. What counts is state changes and tool calls, not how many instructions
are wearing a costume.

**You point at the expensive model.** `SLICE_MODEL` is cheap and was chosen by
running an evaluation, not by reading a price list. `SLICE_ESCALATION_MODEL`
costs roughly thirty times more per word. Escalate deliberately, for one hard
sub-problem — not out of frustration at 3am.

**You keep everything in the conversation.** It works until the first restart.
Write it down; that is what the store is for.

**You leave the users until the end.** See [`EVIDENCE.md`](EVIDENCE.md). It is
worth more marks than your last feature and cannot be faked on Sunday morning.

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

And if you are stuck for more than twenty minutes, ask a mentor. Twenty minutes
is the right threshold — long enough to have genuinely tried, short enough that
the night is not gone.
