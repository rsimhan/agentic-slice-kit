# demo/smoke — the smallest thing that proves the kit works

**A spec at its minimum size.** Sixteen sections, two to five lines each. Written
to the same template as [`docs/SPEC-TEMPLATE.md`](../docs/SPEC-TEMPLATE.md) and
[`SPEC.md`](SPEC.md), to show that the template scales down — a two-page spec is
a real spec, and this one is buildable in about ninety minutes.

**It is also a genuine agent**, by the only test that matters: it can send work
backwards. And it runs against `slice/` **exactly as shipped** — no spine edits,
no corpus, no retrieval, no callback, no tunnel. If this goes green in a fresh
Codespace, the environment and the spine are both proven and everything after it
is domain work.

---

## 1. The setting

A student pastes in one paragraph describing an idea. Somebody who knows the
domain reads it and says *"this isn't specific enough to test yet"* — and says
exactly why. Today that person is a mentor with twenty other teams waiting.

## 2. The problem this solves

Nobody minds being told their idea is vague. What is useless is being told it is
vague **without being told which part.** A first draft that names "students" as
the customer and "AI is growing" as the reason to act cannot be validated by
anyone, and the founder cannot tell that from reading it back.

## 3. What you are building

**Input:** one paragraph of raw idea, and nothing else.
**Output:** a structured thesis that has survived a gate, or a clean stop after
three failed attempts, with every version and every objection on the record.
**Never:** a solution, a value proposition or a pitch. Not one has been earned.

**Why this is agentic, honestly stated:** state survives the process, work is
decomposed into steps that fail independently, and — the load-bearing one —
**the gate can send the draft back.** That back-edge is the entire point of the
slice. Everything else here exists to make the loop safe.

## 4. A complete walkthrough

```
idea    "AI can help students find better internships. Students struggle with
         placements and AI is growing fast. My friend Karthik has a 7.2 CGPA
         and two shipped Android apps, and last year he got auto-rejected
         within an hour by the campus portal every single time - he ended up
         getting his internship through a senior instead. The portal started
         filtering below 8.0 in the 2025 cycle, before any recruiter opens
         the file."

v1      problem              students struggle to find internships
        who_specifically     students                             <- category
        current_alternative  they apply through the portal and wait
        why_now              AI is growing fast                   <- a trend

        ^ a faithful first pass: it took the opening framing and flattened
          the last two sentences. Which is where everything useful was.

gate    BLOCK  . who_specifically names a category, not a person in a situation
               . why_now is a trend, not a change
               . no claim here could be shown to be false

v2      who_specifically     a third-year with a 7.2 CGPA and two shipped apps,
                             applying through the campus portal
        current_alternative  auto-rejected within the hour every time, then in
                             through a senior instead
        why_now              from the 2025 cycle the portal filters below 8.0
                             before a recruiter opens the file

gate    PASS   . objections: []

COMPLETE
```

**Three inputs, because one paragraph cannot prove everything.**

```
--case loop      (default)  blocks once on `problem`, recovers, PASS
--case clean                passes first time; proves the happy path, no back-edge
--case hopeless             blocks three times; proves the domain bound
--idea "..."                your own
```

**The paragraph opens generically and buries the specifics further down. That is
deliberate, and it is a bug fix.**

An earlier version of this spec used a paragraph that was vague all the way
through, and a v2 that introduced a CGPA, a portal and a date **that appeared
nowhere in the input.** Run live, SPOT correctly refused to invent them - three
times, at ten thousand tokens, until the revision limit stopped the run. It was
obeying `prompts/spot.md`, which forbids adding a fact the founder did not
supply. The prompt was right; the golden example was wrong.

Which is the mistake this kit warns about, made by its own authors: **§4 was
written by hand and never derived from the rules.** Two lessons worth more than
a clean first run.

Then the opposite happened. With the specifics made plainer, the model
structured the record correctly on the **first** pass, the gate passed it, and
the back-edge was never exercised — a clean `COMPLETE` that proved less than the
failure had. The run said so itself: *one draft only, the loop is untested.*

**A revision loop only works if a better answer is recoverable from the input.**
If the founder genuinely never said it, no amount of looping produces it, and a
system that appears to produce it anyway is inventing - which is the failure the
whole design exists to prevent. Here everything the gate demands is in the last
two sentences, badly framed. SPOT's second pass re-reads rather than invents.

**And when it truly is not there, the honest output is to say so.** `spot.md`
now instructs exactly that: write *"the founder did not say"* in the field
rather than manufacture a specific to satisfy a gate.

**The default case therefore carries exactly one weak field whose fix is buried
in the text.** `problem` is stated vaguely in the founder's opening sentence and
specifically halfway through the long one that follows. A first pass reliably
takes the opening; the objection sends it back to the detail.

Whether a given model takes that bait is a property of the model, not of this
harness — so the run reports which happened, and `--case clean` and
`--case hopeless` exercise the other two endings deliberately.

**And it did not take the bait.** `inclusionai/ling-3.0-flash` reads the buried
clause and structures `problem` correctly on the first pass, every time. Which is
the model doing its job well. Tuning the paragraph further, until a competent
model stumbles, would be manufacturing a defect in order to demonstrate a
recovery — the opposite of useful, and a short walk from a rigged demo.

**So the block-then-recover arc is not reliably reproducible live, in one run,
with a self-contained paragraph and a model that is any good.** That is worth
knowing rather than working around. The three endings are each provable, just not
simultaneously:

| ending | how it is proven |
|---|---|
| passes first time | `--case clean`, live |
| blocks, then recovers | `--stub`, deterministically, and by `tests/test_smoke.py` |
| blocks until the bound stops it | `--case hopeless`, live |

There is a deeper reason, and it is in [`SPEC.md`](SPEC.md). **In the real system
the founder revises, not SPOT.** A person reads the objections and rewrites their
own paragraph — a loop no model can short-circuit, because the missing
information is genuinely outside the system. SPOT-revises was always a smoke-test
convenience, and this is where the convenience shows its edge.

## 5. Who is doing the thinking

| step | the agent | the human | what the human loses if automated |
|---|---|---|---|
| structure the paragraph | ✓ | | nothing — it is transcription with a schema |
| judge whether it is testable | ✓ | | quite a lot, in the real system. Here the gate is standing in for a mentor and the demo should say so |
| decide whether to keep going | | ✓ | everything. The person reads the objections and rewrites |

## 6. The state machine

```
DRAFTING ──▶ GATING ──▶ COMPLETE
    ▲          │
    └──BLOCK───┘  max 3
               │
               └──▶ FAILED  (3 blocks)
```

| state | kind | handler |
|---|---|---|
| `DRAFTING` | active | `handle_drafting` |
| `GATING` | active | `handle_gating` |
| `COMPLETE` | terminal | none |
| `FAILED` | terminal | none |

**All four already exist in `slice/records.py`.** That is deliberate: a smoke
test that needs a spine edit is testing your edit, not the spine.

## 7. The data model

```python
class OpportunityRecord(BaseModel):
    problem: str             = Field(description="What is bad today. Must be falsifiable")
    who_specifically: str    = Field(description="A person in a situation, never a category")
    current_alternative: str = Field(description="What they actually do right now instead")
    why_now: str             = Field(description="What CHANGED. A trend is not a change")

class Objection(BaseModel):
    field: str               # which field of OpportunityRecord
    problem: str             # the defect in THIS thesis, never generic

class Verdict(BaseModel):
    status: Literal["PASS", "BLOCK"]
    objections: list[Objection] = []
```

Record kinds: `input` (the paragraph, at run start) · `opportunity`
(`agent:spot`, every draft) · `verdict` (`agent:gate`, every judgement) ·
`failure` (`runner`, any abnormal stop).

## 8. Step-by-step contracts

**SPOT · `DRAFTING` → `GATING`**

```python
def handle_drafting(ctx) -> RunState:
    idea    = ctx.latest("input")["text"]
    prior   = ctx.latest("opportunity")      # None on the first pass
    verdict = ctx.latest("verdict")          # objections to address, if any

    record = complete(settings=ctx.settings, budget=ctx.budget,
                      messages=build_spot_messages(idea, prior, verdict),
                      schema=OpportunityRecord, step="spot")

    ctx.append("opportunity", record.model_dump(), produced_by="agent:spot")
    return RunState.GATING
```

*Restructure only. Never invent a fact the founder did not supply. If they named
a category, put the category in the field — the gate's job is to catch it, and
SPOT papering over it is the one failure that makes the whole loop pointless.*

**GATE · `GATING` → `DRAFTING` | `COMPLETE` | `FAILED`**

```python
MAX_REVISIONS = 3

def handle_gating(ctx) -> RunState:
    verdict = complete(settings=ctx.settings, budget=ctx.budget,
                       messages=build_gate_messages(ctx.latest("opportunity")),
                       schema=Verdict, step="gate")
    ctx.append("verdict", verdict.model_dump(), produced_by="agent:gate")

    if verdict.status == "PASS":
        return RunState.COMPLETE

    blocks = sum(1 for v in ctx.history("verdict") if v.payload["status"] == "BLOCK")
    return RunState.FAILED if blocks >= MAX_REVISIONS else RunState.DRAFTING
```

Three block conditions, and they are the whole domain judgement in this slice:
the customer is a **category** rather than a person in a situation; there is **no
falsifiable claim**; the "why now" is a **trend**, not a change.

Note what the revision count is *not* built on. `MAX_REVISIONS` is a teaching
decision about how many rewrites a founder gets; the budget is a cost fence. They
must not share a counter, so the count comes from `history("verdict")`.

Tag it `agent:gate`, not `faculty:gate`. No faculty member touches this. It is
binding because the program treats it as binding, according to conditions a
person wrote.

## 9. The second encounter

None. This slice has no memory beyond one run, and pretending otherwise would be
the exact over-claim the kit exists to catch. `replay` on a finished run is the
closest thing, and it is worth showing: the whole arc, in order, including the
objections that were raised and then addressed.

## 10. Files and responsibilities

| file | owns | done when |
|---|---|---|
| `demo/smoke/schema.py` | the three records above | `pytest` imports them; a golden JSON validates |
| `demo/smoke/flow.py` | two handlers, `MAX_REVISIONS`, the `Flow` object | §4 runs end to end |
| `demo/smoke/prompts/spot.md` | restructure only; address objections on a revision | produces §4 v1 from the paragraph |
| `demo/smoke/prompts/gate.md` | the three block conditions | blocks §4 v1 on all three; passes v2 |
| `scripts/smoke.py` | `run · replay`, plus `--stub` | both work on a fresh database |

Helpers, all deterministic, all in `flow.py`: `build_spot_messages`,
`build_gate_messages`. Both are templates. There are exactly **two model calls**
in this build and no ambiguity about which they are.

## 11. What this deliberately does not do

1. **No corpus, no retrieval.** Nothing here needs evidence, so nothing here
   pretends to have any.
2. **No human in the loop.** A gate standing in for a mentor is not a human in
   the loop, and calling it one would be the first lie in the system.
3. **No decision about the venture.** It decides one thing: whether this thesis
   is specific enough to be worth testing. That is a workflow decision, in code,
   on the record.

## 12. Build order

| phase | what lands | time |
|---|---|---|
| 1 | `schema.py`, `flow.py`, `scripts/smoke.py`, running on `--stub` with hard-coded answers | 30 min |
| | *cut line: the wiring is proven and you have spent nothing* | |
| 2 | the two prompts; the loop running live | 45 min |
| | *cut line: this is the smoke test* | |
| 3 | the golden test and the failure-path check | 15 min |

**Build `--stub` first.** Canned responses for `spot` and `gate` — v1 weak, then
BLOCK, then v2, then PASS — so the whole state machine can be proven without a
key, without a network, and without a token. It takes twenty minutes and it means
that when the live run misbehaves you already know the wiring is not the problem.

Where the time actually goes: not the code, the **gate prompt**. It has to block a
weak thesis on three specific conditions *and* pass a revised one. Expect several
cycles.

## 13. The demo

Not a demo — a check. But the output is worth printing well, because you will read
it fifty times over two days:

```
run  smoke-4f2a   idea: "AI can help students find better internships..."
 ├ spot   opportunity v1                                    1,204 tok
 ├ gate   BLOCK  ×3 objections                                892 tok
 ├ spot   opportunity v2  (addresses who_specifically, why_now)
 ├ gate   PASS                                                741 tok
 └ COMPLETE                        4 records · 3,208 tok · 38s
```

## 14. How this grows

Straight into [`SPEC.md`](SPEC.md). This slice is §8.1 and §8.2 of that document,
unchanged — the same two handlers, the same three records, the same three block
conditions. Everything after it (assumptions, evidence with verified provenance,
the human callback, the decision, recheck) is added in front of `COMPLETE`
without rewriting any of this.

## 15. What you are least sure about

1. **Whether the gate blocks reliably.** Models are agreeable. The real risk is
   not a wrong objection, it is a PASS on a thesis written to fail. Two runs
   agreeing is the minimum evidence worth having.
2. **Whether the three conditions are the right three.** They came from one
   person's experience, not from a labelled set.
3. **Whether the objections are specific enough to act on.** *"Add more detail"*
   is a failure even though it parses, and no schema catches it. Observed
   degrading over rounds, from explaining the fault to repeating the offending
   value back. The test now strips the value and checks what is left — but only
   a person reading the output can judge whether an objection is *useful*.

4. **Whether SPOT should be revising at all.** In `SPEC.md` the founder revises;
   here SPOT does, because a smoke test wants a self-contained loop. It is a
   convenience, and every live run so far has pushed on exactly that seam.

## 16. Claims to verify

| claim | how to check | ☐ |
|---|---|---|
| A Codespace builds and `python -m pytest` is green | first thing, before any of this | ☐ |
| `scripts/doctor.py` reports all five checks healthy | second thing | ☐ |
| The whole loop runs on `--stub` with no key set | `python -m scripts.smoke run --stub` | ☐ |
| The default model returns a valid `OpportunityRecord` first try | run it; if it needs the repair pass every time, the prompt is wrong | ☐ |
| The gate BLOCKs §4 v1 and PASSes §4 v2 | ten trials each. Below ~9/10 on either, fix the prompt before going further | ☐ |
| **SPOT's v2 differs from v1** | observed failing: with a vague paragraph it correctly refuses to invent, and repeats itself until the limit stops the run. If v2 == v1, the input does not contain what the gate wants | ☐ |
| A live run blocks at all | `--case hopeless`. Proves the gate can say no and not only yes, and that the domain bound fires with a recorded reason | ☐ |
| A live run passes cleanly | `--case clean`. Two calls, no back-edge | ☐ |
| **Objections still explain the fault by round three** | observed failing: the gate degraded to echoing the offending value back, which parses and says nothing. `tests/test_smoke.py` checks the shape; only a live run checks the judgement | ☐ |
| Both provider families are reachable at once | observed failing on a first live run: primary and fallback both HTTP 429, and the recorded failure names only the fallback | ☐ |
| A BLOCK genuinely re-enters `DRAFTING` and writes a second `opportunity` | `replay` shows two, not one. **This is the one that proves it is an agent** | ☐ |
| Three blocks stop the run in `FAILED` with a `failure` record | feed it a paragraph that cannot be saved | ☐ |
| The store refuses an update | try to overwrite a version; expect the trigger to abort | ☐ |
| A bad key produces a recorded failure, not a stack trace | blank `OPENROUTER_API_KEY`, run live, read the record | ☐ |
| Token counts survive a restart | kill mid-run, resume, check the counter continued | ☐ |

---

## What a green run proves

Eleven things, from two prompts and about a hundred and twenty lines:

the Codespace builds · `.env` is read · the key is valid · a model is reachable ·
structured output parses into a typed record · the repair pass catches what does
not · the store creates, appends and reads back · the append-only trigger holds ·
the runner dispatches handlers and moves state · the budget counts and survives ·
**and work goes backwards.**

If all eleven hold, nothing you build after this is fighting the environment.
