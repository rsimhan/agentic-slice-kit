# demo/ — the reference implementation

**A venture-thesis validation agent.** One agent, four steps, two runs.

This is the worked example that ships with the kit. It exists to show the
principles in `docs/ARCHITECTURE.md` doing real work on a real problem, and to
be a thing another team can evolve rather than a thing they have to admire.

Nothing here touches `slice/`. If you find yourself editing the spine to make
this fit, stop and say so — that is a finding about the spine.

---

## What it does

**Input:** one paragraph describing an idea, plus a folder of documents.

**Output:** a validation brief — a thesis that survived review, the assumptions
it depends on, evidence for and against each with citations you can open, one
answer from a human expert, and an explicit list of what could not be
established.

**Then, later:** given new documents, it re-tests the standing thesis and
reports what changed. That second run is the point.

It does not decide anything. It assembles evidence so a person can.

---

## The design principle

An earlier version of this shipped in 2024 as a fixed-forward workflow: idea in,
then problem framing, then a needs and opportunity analysis, then a refined idea,
then solution, value proposition and a polished three-minute pitch. Every run
took the same path. The framework was good — the four thesis questions, the
domain and ecosystem assessment — and it survives here.

What it could not do was **stop**.

The author's own account of what was missing:

> *"What I wanted was to pause after the initial opportunity analysis, pin the
> critical assumptions, and find a way to validate before moving forward. No
> point looking at solution and value proposition and generating pitches on an
> idea on thin ice."*

That is not a request for better prompts. It is a request for a state machine
that can refuse — and in 2024, with state managed inside an orchestration
framework, pausing and resuming a half-finished run was the hard part. It is now
the cheapest part: `slice/store.py` is stdlib, and pause-and-resume is what it
does before anything else. That is why durable state is Tier 1 of the
architecture and not an optimisation.

### Why premature artifacts are worse than useless

A polished pitch is not a neutral by-product. **It manufactures confidence.** A
founder who has read their own well-written three-minute pitch feels further
along than the evidence supports, and is correspondingly less likely to go and
test anything. Generating the artifact early does not merely waste tokens; it
works against the validation it should have followed.

So the agent refuses. That refusal is the single most important behaviour in
this build.

### And the value arrives as interruptions

The 2024 report was read closely by mentors and judges and largely skimmed by
students — which is a finding about the *shape* of the output, not about
attention spans. A long, evenly-weighted document offers a first-time founder
nothing to do on Monday morning. Three short things do:

| | what the founder sees | why it cannot be skimmed past |
|---|---|---|
| **The block** | *Your customer is a category, not a person* | The run stops |
| **The question** | *Your documents cannot settle this. What do you know?* | It waits for a human answer |
| **The refusal** | *Not writing your pitch. Assumption 2 is unresolved* | The thing they wanted is withheld |

The full brief is still produced — as the **mentor, faculty and judge artifact**,
which is what it always actually was. One substrate, different constituencies,
different outputs.

### One rule for anything after DECIDING

> **Past the validation gate, no claim is written without a source the reader
> can open.**

Illustrative figures are fine in an early draft and should be labelled as such.
They must never survive into a generated pitch, because that is where a founder
stops treating them as illustrative and an investor starts treating them as
research.

## Who is doing the thinking

The agent in this build wears several stances. SPOT frames the problem, PROBE
decides which assumptions matter, ARTIFACTS writes the pitch — and in each of
those it is **standing in for the entrepreneur**. The faculty gate is different:
it critiques work rather than producing it.

That distinction is the most important thing on this page for anyone extending
this into the course, so it is worth being explicit rather than letting it hide
in the prompts.

### Two categories, not six avatars

| doing it FOR the founder is correct | doing it FOR the founder destroys the point |
|---|---|
| Searching a corpus | Framing the problem |
| Cross-referencing thesis against evidence | Naming a specific customer |
| Noticing a contradiction six weeks later | Deciding which assumptions are load-bearing |
| Rendering and formatting | Deciding whether to proceed |

The left column is tedious or superhuman — nobody learns anything doing it by
hand. **The right column is the course.** A system that does the right column
for a student produces a good document and no founder, which is exactly what the
2024 version did.

### The dial

Every stage sits somewhere on this, and **where it sits is a teaching decision,
not an engineering one**:

1. Agent does it, shows the result &nbsp;→&nbsp; *the 2024 workflow*
2. Agent does it, student edits &nbsp;→&nbsp; *"user provides input and clicks proceed"*
3. Agent drafts; student must justify keeping or changing each field
4. **Agent asks, student answers, agent structures** &nbsp;→&nbsp; *where most of the course belongs*
5. Student writes, agent critiques &nbsp;→&nbsp; *the faculty gate, already correct*

### What this demo does, and what it is skipping

**This build pins the entrepreneur stages at level 1.** One model call produces
the opportunity record; nobody is asked anything. That is a deliberate
simplification so the machinery is visible in ten minutes — and it is the single
largest gap between this demo and the system the Foundry has to build.

**Say so during the demo.** *"The agent stood in for the founder here. In the
course, it asks and she answers."* Naming the shortcut makes the demo more
credible, not less, and it is consistent with the system not being a co-founder.

### The seam, left clean

Two cheap things in this build make that a substitution later rather than a
rewrite:

**Tag every version with its author.** `slice/store.py` already records
`produced_by` on every write. Use it precisely:

```
agent:spot        the agent standing in for the founder     ← provisional
agent:probe       the agent standing in for the founder     ← provisional
faculty:gate      binding — this one decides something
human:expert      a real person, recorded as such
```

The Foundry then replaces `agent:spot` with `student:priya`, sourced from a
conversation instead of a single call. **Same record, same state machine, same
gate, different author.** Nothing downstream changes — which is the test of
whether this state model was the right one.

**Mark provisional records in the brief.** Anything authored by an `agent:*`
stance standing in for the founder is labelled as the agent's draft, not the
founder's position. A mentor reading the brief should be able to see instantly
which parts a human actually committed to.

### One asymmetry that belongs in the schema

Of all the stances, **only the faculty gate produces a binding output.** A
`Verdict` decides something and moves the run. An `OpportunityRecord` is a draft
that a human should later own. Keep that visible in the types rather than only
in the prompts — it is the difference between a stance and an authority, and it
is what stops "six avatars" from being mistaken for six agents.

(They are not six agents. Same tools, same trigger, same budget — the merge test
in the working note says one agent, six stances. A stance is a prompt and a
contract.)

---

## Run 1 — establishing

```
DRAFTING ──▶ GATING ──▶ PROBING ──▶ DECIDING ──▶ ARTIFACTS ──▶ COMPLETE
    ▲          │           │          │  │
    └─blocks───┘           ▼          │  └── not earned ──▶ STOPPED
       max 3        AWAITING_EXPERT ──┘                       │
                                                              │
                          add evidence, then `recheck` ───────┘
```

Five states, and the two that matter are `DECIDING` and `STOPPED`. Everything
before them is analysis; everything after them is artifact generation that has
earned the right to exist.

### SPOT · `DRAFTING`

Turns the raw paragraph into an `OpportunityRecord`. Does not chat, does not ask
questions, does not use the corpus. Restructuring only.

**Note what is absent: no solution, no value proposition, no pitch.** Those
cannot honestly be written yet, and the agent does not pretend otherwise.

```python
class OpportunityRecord(BaseModel):
    problem: str              # what is bad today
    who_specifically: str     # a person, not a category
    current_alternative: str  # what they do instead, right now
    why_now: str              # what CHANGED that makes this newly possible
```

On a revision, it also receives the gate's objections and must address each.

### FACULTY GATE · `GATING`

Reads the thesis, returns a verdict. **Does not converse.**

```python
class Objection(BaseModel):
    field: str                # which part of the thesis
    problem: str              # the specific defect, in THIS thesis

class Verdict(BaseModel):
    status: Literal["PASS", "BLOCK"]
    objections: list[Objection]
```

Blocks when any of these hold:

- the customer is a **category** ("students", "SMEs") not a specific person
- there is **no falsifiable claim** — nothing evidence could disprove
- the "why now" is a **trend**, not a change that just made this possible

Objections must name the defect in *this* thesis. Anything resembling "add more
detail" is a failure of the prompt, and `scripts/bakeoff.py` scores exactly this.

**Business rules, in `flow.py`, not in a prompt:**
- BLOCK → back to `DRAFTING` with the objections attached
- 3 blocks → stop, `FAILED`, with the objections recorded. Do not loop forever.
- PASS → `PROBING`, and reset the gate's attempt counter

### PROBE · `PROBING`

Two moves. First, derive the assumptions the thesis rests on:

```python
class Assumption(BaseModel):
    claim: str                # stated so evidence could disprove it
    why_load_bearing: str     # what collapses if this is false
    importance: int           # 1-5
```

Then, for each, search the corpus and record what it finds:

```python
class Evidence(BaseModel):
    assumption_index: int
    stance: Literal["supports", "contradicts", "unresolved"]
    source: str               # "notes.md#4" — from Chunk.cite()
    quote: str                # the actual passage. Never a paraphrase
```

**Every claim carries a source or it does not get written.** An empty corpus
returns nothing and PROBE says so; it never fills the gap from the model's own
knowledge.

### EXPERT · `AWAITING_EXPERT`

Take the **highest-importance unresolved** assumption. Ask a human one question
about it. Suspend.

- `callback.ask()` parks the question and sets the state
- the run may exit entirely; a later `advance()` resumes it
- the answer is recorded with `source: "human_expert"` — a distinct class of
  evidence, never blended with what the model already believed
- timeout → `unresolved_no_expert`, and the run continues. An absent expert must
  never strand a run.

Only one question. Resist the urge to ask five.

### DECIDE · `DECIDING`

**The gate that was missing in 2024, and the reason this build exists.**

Almost entirely deterministic — a rule about the programme, not a judgement
call, so it lives in `flow.py` and not in a prompt:

```python
blocking = [a for a in assumptions
            if a.importance >= 4 and stance_of(a) != "supports"]
```

If `blocking` is non-empty, the run goes to `STOPPED` and says exactly what is
missing and what would settle it:

> *Not proceeding to solution and pitch. Assumption 2 — &ldquo;small businesses
> without marketing teams will pay for speed&rdquo; — is load-bearing and
> unresolved. Two customer interviews would settle it. Come back with them.*

`STOPPED` is not a failure. It is the correct outcome for an untested idea, and
it is resumable: add evidence, run `recheck`, and the run continues from here.

### ARTIFACTS · `ARTIFACTS`

Only reached on the far side of the gate. Now, and only now, the solution, the
value proposition and the pitch artifacts get written — each able to cite the
validated assumption it rests on.

```python
class VentureArtifacts(BaseModel):
    solution_components: list[str]
    value_proposition: str
    elevator_pitch: str          # 20 seconds
    long_pitch: str              # 3 minutes
    rests_on: list[int]          # assumption indices, all validated
```

Keep the 2024 framework's four questions — *why does this matter, who benefits,
what is novel, how will we realise it* — as the structure of the long pitch.
That framing was distilled from a course, from resident advisors and from
practice, and it did not get commoditised. Only the shell around it did.

### BRIEF · `COMPLETE`

**For mentors, faculty and judges** — see the design principle above. The
student's value already arrived as the block, the question and the
contradiction. Renders `out/brief-<run_id>.html`:

- the thesis, **with its revision history** — v1 → objections → v2 is the story
- assumptions ranked by importance × unresolvedness
- an evidence table, each row quoting its source
- **"What we could not establish"** — the section that makes it honest, and
  the one to read aloud on stage
- **every number carries its source.** If it cannot, it does not appear

---

## Run 2 — recheck  *(the punchline)*

New documents arrive. Re-ingest, then:

```bash
python -m scripts.run recheck <run_id>
```

A new state, `RECHECKING`, which:

1. loads the **standing** thesis and its assumptions from the store
2. re-searches every assumption against the now-larger corpus
3. compares stance to what was recorded before
4. writes a `Delta` and appends it to the same run's history

```python
class Delta(BaseModel):
    assumption_index: int
    was: str                  # previous stance
    now: str                  # current stance
    changed_by: list[str]     # the new sources responsible
    still_load_bearing: bool
```

**Recheck runs in both directions, and this is the satisfying part:**

- An assumption that moves to `supports` can **unblock a `STOPPED` run** — the
  agent now writes the pitch it previously refused to write. The founder did the
  work; the artifact is the reward.
- An assumption that moves to `contradicts` while `still_load_bearing` is true
  gets surfaced loudly, to the team and to faculty, even on a run that had
  already completed.

One mechanism, two directions. The second is the one no chat window can have.

> *Assumption 3 — "lab technicians will pay for this" — was unresolved on
> 12 September. Two passages added on 19 September contradict it. Your thesis
> still depends on it.*

This is the capability a chat window cannot have at any model size, because it
requires state that outlived the conversation. Build it even if it is rough.

---

## What this deliberately does not do

Scope discipline is part of what the kit teaches, so the omissions are
deliberate and should stay omitted:

**The big one: the founder is not asked anything.** The entrepreneur stages run
at level 1 of the dial — one model call, no conversation. See *Who is doing the
thinking*. This is the largest gap between the demo and the course, it is
deliberate, and it should be said out loud.

Then: no accounts or multi-user · no cohort or faculty view · no scheduler
(recheck is invoked by hand; the trigger is the Foundry's job) · no UI beyond the
expert form and the rendered brief · **no decisions** — it assembles evidence, a
person decides

---

## Build order

Follow `docs/ARCHITECTURE.md`'s tiers. Roughly nine hours; the recheck is the
part to cut if time runs short, and it degrades gracefully.

| | | |
|---|---|---|
| H0–1 | `schema.py` — the records above | Tier 1 |
| H1–3 | `flow.py` with a **stubbed** model. Hard-coded answers, whole path green | Tier 1 |
| H3–5 | The three prompts. Real calls. Gate loop working end to end | Tier 1–2 |
| H5–6 | Corpus, retrieval, provenance in every evidence row | Tier 2 |
| H5.5–6 | Expert callback, live, over the tunnel | Tier 2 |
| H6–7 | `DECIDING` — the refusal. Mostly deterministic, in `flow.py` | Tier 1 |
| H7–8 | `ARTIFACTS` + `brief.py` + the golden test | Tier 3 |
| H8–9 | **Recheck**, in both directions | the punchline |

**Do not start with prompts.** Get the boring path working with stubs first.
Teams that start with prompts rewrite everything around hour thirty, and so
will you.

---

## The demo, in ten minutes

The arc is: **it refuses, you do the work, it delivers.**

1. Show the idea. One paragraph, weak in one specific way.
2. Run it. **The gate blocks.** Read the objections aloud — they name defects in
   *this* idea, not "add more detail".
3. v2 passes. Show the diff: v1 → objections → v2.
4. PROBE derives the assumptions and searches the corpus. Every finding cites a
   passage. One comes back unresolved.
5. **The run stops.** Put the expert form on screen. Someone in the room answers
   it live from their phone. The run resumes.
6. **It reaches `DECIDING` and refuses to write the pitch.** *&ldquo;Assumption 2
   is load-bearing and unresolved. Two customer interviews would settle it.&rdquo;*
   Sit with that for a moment — this is the whole argument.
7. Open the brief. Read **&ldquo;What we could not establish&rdquo;** aloud.
8. Now do the work: drop two interview notes into `corpus/`, re-ingest,
   `recheck`.
9. The assumption moves to `supports`. **The agent writes the pitch it refused
   to write ten minutes ago**, citing the evidence it now has.
10. `replay` — the whole arc as one diff, refusal and all.

**Rehearse step 5.** It depends on a tunnel and a reachable human, and it is the
best moment in the demo. Have a fallback ready: a pre-answered question, or
answer it yourself from a phone.

**And do not rescue step 6.** The instinct will be to hurry past the refusal to
get to the good bit. The refusal *is* the good bit. Everything else in this
build is machinery in service of an agent that can say "not yet".

### If you show one comparison

Same idea, two systems:

> **2024** — a fixed-forward workflow that produced a polished three-minute
> pitch in one pass, for an idea nobody had tested.
>
> **This** — an agent that stopped twice, asked a human one question, refused to
> write the pitch at all, and produced it only after two interviews arrived.

The second looks slower and less impressive. It is also the only one of the two
that would have changed what the founder did next.

---

## How the Foundry evolves this

Nothing here needs replacing to get to the full system. **Start with the first
one — it is the difference between a tool and a course:**

- **conversational elicitation** — the entrepreneur stages move from level 1 to
  level 4 of the dial: the agent asks, the student answers, the agent structures.
  Replace `produced_by: "agent:spot"` with `produced_by: "student:priya"`. The
  state machine, the gate and the evidence model are untouched. If that
  substitution turns out to require changes elsewhere, this state model was
  wrong and it is worth knowing early.


- **the scheduler** — recheck fires on upload and on week boundaries, instead of
  by hand. Property 4.
- **many teams** — the store already scopes by `run_id`. Add an owner. Property 1.
- **the cohort view** — a query over existing state, not a new agent. Property 3.
- **policy** — *no team advances on unvalidated demand* reads the same
  assumption records. Property 5.
- **PROBE proper** — interview preparation, transcript synthesis, product map.
  New steps in the same flow.

The state model — versioned theses, load-bearing assumptions, evidence with
provenance, human answers kept separate — is the one the full system needs. That
is the actual deliverable here. The demo is how you show it works.
