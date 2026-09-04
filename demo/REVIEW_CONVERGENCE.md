# SPEC review — convergence and decisions

Three independent adversarial reviews of `demo/SPEC.md` (Gemini, OpenAI, Claude),
run against the same eight-dimension prompt and the same two documents.
This page holds the twelve findings that more than one reviewer reached
independently, synthesised into one statement each.

**How to use this.** Each finding has a *Gist* (merged from all three, no
attribution clutter), *My view* (Claude, this session), and a blank *Raj's view*.
Fill in your view and set the decision. Once decided, the SPEC edits follow
mechanically.

**Decision options:** `ACCEPT` (fix before the build) · `ACCEPT-LITE` (fix the
words, not the code) · `DEFER` (Foundry problem, note it in §14) · `REJECT`
(reviewer is wrong, or it is taste)

**Consensus key:** 3/3 = all three reviewers · 2/3 = two, independently.

**Suggested order of attack.** F11 → F1 → F12 → F2 → F3/F4 are the paper
decisions; they close the blocking cluster before anyone opens an editor.
F6, F7, F9 are scheduling and staging. F5, F8, F10 are the Foundry's inheritance.

---

## F11 — The expert answer has no path into the decision

**Consensus:** 2/3, both blocking. (Gemini never traced the run.)
**Where:** §8.3 `handle_probing` · §8.4 · §7 record kinds

**Gist.** On resume, the assumption already has an evidence row with stance
`unresolved`, so `has_evidence` skips it. `already_asked` is true, so no second
question. `stance_of` reads `evidence` records, but the answer was written as
kind `expert_answer`. No step, no record and no line of code converts one into
the other. The human can answer "yes, portfolio evidence changes screening
decisions" and the run proceeds exactly as if they had not.

The worked example hides this: assumption 3 is contradicted anyway, so the run
refuses either way. That is not proof the loop works — it means §4 never tests
whether the human answer causes anything.

**My view.** ACCEPT, and this is the one I would fix first. It is not a bug in
an edge case; it is the demo's only interactive beat being decorative. Everything
you have argued about human-in-the-loop being *a state, not a blocking call*
depends on the state having a consequence.

Fix: the answer is appended as an `Evidence` row with
`source: "human_expert:<id>"` and the answer text as the quote, and `stance_of`
takes the newest evidence row per index. That converts the human into a first-class
evidence source, which is also the more honest model — an alum's judgement is
evidence, not an oracle.

Note what it costs: the raw answer is prose, so something has to classify it into
a stance. That is an eighth model call nobody budgeted (see F8).

**Raj's view.**

> Agreed, pls fix

**Decision:** ACCEPT

---

## F1 — `recheck` cannot revive a `STOPPED` run

**Consensus:** 3/3, all blocking.
**Where:** §6 spine change · §9 · §13 steps 8–9

**Gist.** §6 says extend `is_terminal` to include `STOPPED`. §9 requires `recheck`
to take a STOPPED run forward into ARTIFACTS. A runner does not advance a terminal
run — that is what terminal means. No transition is specified for
`STOPPED → RECHECKING → DECIDING → ARTIFACTS`, `RECHECKING` has no successor state
declared, and the last third of the demo is exactly this path.

The second direction in §9 — surfacing a contradiction on an already-COMPLETE run —
has no mechanism at all. It is a sentence.

**My view.** ACCEPT. The fix is a single reclassification: `STOPPED` is *suspended*,
not terminal. It is the same category as `AWAITING_EXPERT` and for the same reason —
waiting on the outside world, resumable by a later invocation. Put it in
`is_suspended`.

Two consequences worth naming. First, this is a second spine edit, and §10 currently
promises only one (the enum). Say so plainly rather than smuggling it. Second, the
COMPLETE-reopening claim should be dropped or narrowed to "recheck on a COMPLETE run
writes a delta and a warning without reopening". Do not ship a sentence with no
machinery under it — that is exactly the failure mode we are teaching against.

**Raj's view.**

> Agreed, pls fix

**Decision:** ACCEPT

---

## F12 — Provenance is asserted, never enforced

**Consensus:** 2/3 (OpenAI's single biggest problem; Claude's C1, returned to five times).
**Where:** §8.3 · §3 output contract · ARCHITECTURE principle 4

**Gist.** `search` returns chunks with ids. A separate model call then produces
`Evidence` rows whose `source` and `quote` are free text the model wrote. The only
check is `assert e.stance == "unresolved" or e.source` — that the field is non-empty.
Nothing verifies that the source is one of the chunks actually retrieved, or that
the quote appears in it.

So the headline claim — *every claim traceable to a source* — is honour-system. A
model that invents `student-interviews.md#7` and a plausible quote passes every check
in the spec, and the most impressive part of the demo becomes fabricated evidence
wearing a provenance badge.

**My view.** ACCEPT. This is the best value-per-line fix in the whole review: after
parsing, `valid = {c.cite() for c in chunks}`; reject any row whose source is not in
that set; require the quote to appear in the chunk text, whitespace-normalised. Rows
that fail demote to `unresolved` with a note rather than being dropped silently.

Two bonuses. It turns a principle into a property, which is the difference between
the standard being real and being decorative. And it is most of the answer to prompt
injection — a poisoned corpus document can still lie, but it cannot manufacture a
citation that does not exist.

One caution: the assert must go regardless. A bare assert on model output in the hot
path is a stack trace instead of a failure record, in the file we offer as the model
of "every dependency has a defined failure behaviour".

**Raj's view.**

> Agreed, pls fix

**Decision:** ACCEPT

---

## F2 — "Conversation is a free upgrade" is false

**Consensus:** 3/3, all blocking. Gemini's single biggest problem.
**Where:** §5 dial · §14 first bullet · §7 `OpportunityRecord`

**Gist.** §14 claims conversational elicitation can replace `agent:spot` with
`student:priya` and leave the state model untouched. It cannot. A conversation is
n ordered turns with the run suspended between each: it needs a new state and
handler, a record kind for turns, a *partial* thesis type (the current schema
requires all four fields, so there is no representation for a half-elicited idea),
a turn bound, and a different timeout policy — an absent expert yields a legitimate
finding, an absent founder yields nothing.

The hard break is in the spine: `slice/callback.py` is single-question-per-run and
hard-codes the answer's provenance as `human_expert`. A second human role forces a
spine change.

**My view.** ACCEPT the finding, REJECT the implied verdict. The state model is not
wrong — the sentence in §14 is. And §5 already sets the test that catches this:
*if that substitution requires changes elsewhere, this state model was wrong.* The
honest rewrite is stronger than the claim it replaces: this needs a founder-turn
record, a partial-thesis type and a second addressee; the gate, the evidence model
and the decision rule are untouched. That is still a good boast, with the advantage
of being true.

One thing worth doing now rather than later, because twenty-five teams are about to
copy it: parameterise the callback on an addressee — `ask(..., role=...)`, answer
records `produced_by=f"human:{role}"`, questions carry an id, `is_suspended` covers
both waits. Small now, structural in six months.

**Raj's view.**

> Agreed, pls fix; yes we should parameterise

**Decision:** ACCEPT — including the callback addressee parameter

---

## F3 — The agentic claim in §3 is overstated

**Consensus:** 3/3 (minor, minor, serious).
**Where:** §3 "why it qualifies as agentic"

**Gist.** §3 argues the sequence is unknowable in advance because the gate may loop,
the assumption count varies, the searches vary and a human may be called. Two of
those four are weak: gate iterations are bounded 0–3 and scripted in the demo, and
whether a human is asked is a deterministic function of the evidence. What is
genuinely unknown is the assumption count and the search queries.

You *can* draw this sequence in advance: a linear pipeline with one bounded back-edge
and one optional suspend.

**My view.** ACCEPT, and it costs nothing. The system clears the agentic bar on the
four properties we published — state persistence, autonomous tool use, multi-step
decomposition, human callback — without needing "unknowable". Claiming more than the
artifact supports is the exact behaviour the whole event is teaching students not to
do, and it is the sentence they will imitate rhetorically in their own submissions.

Replace with the precise property: *bounded stateful orchestration, with model-driven
decisions inside fixed transitions, and a control loop that can go backwards.*
That last clause is your own line and it does more work than the paragraph it replaces.

**Raj's view.**

> Agreed, pls fix

**Decision:** ACCEPT

---

## F4 — Labels claim human authority the code does not have

**Consensus:** 3/3 (minor, blocking, minor).
**Where:** §8.2 `produced_by="faculty:gate"` · §3 "never a decision" · §11 "no decisions"

**Gist.** The gate verdict is produced by a `complete(... schema=Verdict ...)` call —
it is model judgement. It is tagged `faculty:gate` and called binding. No faculty
member touches it. An audience can leave believing a human reviewer blocked the idea.

Same slippage in the other direction: the spec says "no decisions, a person decides",
then implements a deterministic proceed/stop at DECIDING that refuses to produce the
artifacts.

**My view.** ACCEPT. Rename to `agent:gate` and state that faculty own the three
block conditions.

The replacement wording is better than what it replaces, and it is *your* argument:
the gate is binding because the program treats it as binding, according to conditions
a faculty member wrote. That is the whole thesis of orchestration-in-code, stated
plainly. And on "no decisions" — say what is true: the system makes no venture
decision; it makes workflow and evidence-state decisions, in code, visibly.

This is the finding where the demo is most at risk of being *believed wrongly* by a
friendly audience, which is worse than being disbelieved by a hostile one.

**Raj's view.**

> Agreed, pls fix

**Decision:** ACCEPT

---

## F6 — Nine hours is not credible

**Consensus:** 3/3 — but they disagree on which step blows up.
**Where:** §12

**Gist.** Gemini says corpus and provenance (budget 3h, not 1). OpenAI says the
expert callback over the tunnel (half an hour for routing, ports, phone access,
duplicate submits, timeouts and a proof that a fresh process resumes). Claude says
prompt calibration — five prompts, not three, plus the two hiding in unspecified
functions plus a classifier, calibrated against a non-deterministic judge, at
60–90s a cycle, on models our own bakeoff scored 0/3 and 2/5 for contract compliance.
Claude's total: 16–20 hours.

**My view.** ACCEPT. Three reviewers naming three *different* steps as the 3x risk is
not disagreement — it is the union, and the union is the answer.

But the deeper point is one none of them made: the nine hours only matters if the
complete build is the deliverable. It is not. On 19 September what has to exist is a
credible reference and a starter kit. My recommendation is to restructure §12 as three
phases with an explicit cut line — spine + flow green on stubs, then real calls, then
recheck — and to state which phase must land. Also move the corpus before H0; it is
several hours of writing that determines whether anything downstream looks convincing,
and it is currently budgeted nowhere.

**Raj's view.**

> Agreed, pls fix

**Decision:** ACCEPT

---

## F7 — The ten-minute demo has no slack and no fallback

**Consensus:** 3/3.
**Where:** §13 steps 8–10

**Gist.** Run one is eight live model calls plus a human wait. Recheck adds a
re-search, re-evidence and a generation call that produces a three-minute pitch.
At 5–15s a call that is two to four minutes of dead air inside a ten-minute slot with
ten content beats — before any provider latency, tunnel hiccup or repair pass. The
punchline also bets on a live model returning `supports` for assumption 3 given two
new notes; if it returns `unresolved` the demo ends on a second refusal.

And the inverse risk nobody has mitigated: models are agreeable. If the gate *passes*
the deliberately weak v1 in front of the room, there is no demo at all.

**My view.** ACCEPT. Fixtures: record every completion keyed by step and prompt hash,
replay by default, live behind a flag. One mechanism that fixes four things — the
demo's failure mode, the golden test's flakiness, the cost of prompt calibration, and
a 402 mid-demo, which is a failure our own architecture document anticipates and the
demo plan does not.

The honesty condition is non-negotiable and costs one sentence on stage: *these model
responses are recorded from a real run; the expert answer is live.* Said out loud, it
reads as engineering discipline. Discovered afterwards, it reads as a fake.

**Raj's view.**

> Agreed, pls fix

**Decision:** ACCEPT

---

## F9 — The tunnel is undocumented

**Consensus:** 3/3.
**Where:** §8.4 "over the tunnel" · §13 step 5

**Gist.** No mechanism, host binding, callback URL scheme, authentication or failure
mode. Anyone with the link answers as "the expert". The routing from a stateless HTTP
request back to the right `run_id` in a local SQLite file is unspecified. This is the
class of hidden dependency that fails in a room.

**My view.** ACCEPT, but downgrade it in your head. This is an operational task, not
a spec defect: pick the mechanism (cloudflared quick tunnel is already verified in the
stack work), sign the callback URL with the question id, preflight it, and have a
static pre-answered page as the fallback. Half a day, done once, and it becomes
starter-kit material every team can use.

The one part that *is* a spec defect: principle 4 applies to humans too. An unsigned
URL means the provenance of a human finding is unverifiable, which undercuts F12 from
the other side.

**Raj's view.**

> For a demo, this is a unreal expectation. On design principle, yes; We can skip; We dont want to overcomplicate the non-fun aspects into a student hackathon is my honest view. 

**Decision:** REJECT the auth/token work — an unreal expectation for a student hackathon, and not worth complicating the non-fun parts. ACCEPT-LITE the routing only.

**Note on the split.** Gemini bundled two things under one finding. *Auth* — proving the
answering human is the intended expert — is dropped, agreed. *Routing* — the incoming
HTTP request finding its way back to the right `question` on the right `run_id` — is not
optional, because F11's fix depends on the answer landing on the right assumption. Keep
the question id in the URL; drop the signature.

One free mitigation for the demo, since there is no auth: generate the link at demo time
and do not put it on a slide. Costs nothing, and removes the only realistic failure —
a stray click from the audience answering as the expert mid-run.

---

## F5 — Concurrency and multi-team isolation

**Consensus:** 3/3 (Gemini's headline absence).
**Where:** §14 "many teams — add an owner" · resume/recheck paths

**Gist.** Two invocations racing: expert submits twice, a scheduler advances a run
while a person runs `resume`, two rechecks start. Append-only is not concurrency
control — with no compare-and-swap on state you get double spend, double append and
two divergent branches with no way to say which is current. And "add an owner" solves
data association, not authorisation or retrieval scope: `retrieve.search` searches the
store, so two teams in one store means team A's interview transcripts surface as
evidence for team B's assumptions.

**My view.** ACCEPT for §14, REJECT for the event. The reviewers did not know the
deployment model: each team gets its own Codespace and its own `run.db`. There is no
shared store on 19–20 September, so this is not a hackathon risk.

It is, however, exactly the wall the Foundry hits on day one — and it is the honest
content of "from an agent to an agentic system", which is a phrase we use a lot. Two
edits: delete the "basically free, add an owner" line, and replace it with what the
jump actually costs — a scope parameter on `search` and `ingest`, a lease or
compare-and-swap on state advancement, and an authorisation model for who may answer,
recheck or read a run.

**Raj's view.**

> Not for the demo. Not for the foundry as well until we go live, as tests can be managed 

**Decision:** DEFER — not for the demo, and not for the Foundry until it goes live; tests can be managed.

**One residue.** Deferring the *work* is right. The *claim* in §14 — many teams are
basically free, add an owner — is a sentence we now know to be wrong, and it sits in the
same document where we are correcting §3 and §14 for exactly this reason (F2, F3).
Two-word edit: say the scoping work is understood and deferred, rather than that it is
free.

---

## F8 — The human boundary is the least-specified boundary in the system

**Consensus:** 3/3 (typing, typing, auth+routing).
**Where:** §7 record kinds · §8.4

**Gist.** `question` and `expert_answer` are persisted kinds with no schema. Every
model-to-model handoff has a typed contract; the one place where ambiguity is
guaranteed — a human typing free prose on a phone — has none. No structure for
question id, author identity, timestamp, relation to assumption, timeout status or
revision. The standard itself never lists humans as a boundary at all.

**My view.** ACCEPT, and note that this is the finding that generalises furthest.
An `ExpertFinding` record — assumption index, stance, the answer verbatim as quote,
expert id — produced by a classification call over the raw prose, with the raw prose
stored alongside. That is the same fix F11 needs, so they are one piece of work.

The meta-version is worth taking too: add humans to principle 2's boundary list and
require an explicit prose-to-record conversion. With that in the standard, F11 becomes
impossible to write. This is the single best answer to the "is the standard
self-serving?" question — it is a place where the standard was genuinely incomplete
in a way that let the spec off a hook.

**Raj's view.**

> Agreed, pls fix

**Decision:** ACCEPT

---

## F10 — Teams will cargo-cult domain policy as architecture

**Consensus:** 3/3 — but with one divergent fix, see below.
**Where:** §8.2 gate conditions · §8.5 `BLOCKING_IMPORTANCE = 4`

**Gist.** "The customer must be a person, never a category", "`why_now` must be a
change, not a trend", `BLOCKING_IMPORTANCE = 4` — these are venture-domain policy
sitting beside the architectural spine, in a file the spec calls the home of "all
business rules". A robotics or compiler or reliability team copies the shape without
noticing that the policy layer must be reinvented. Related: the reference teaches
production concerns (three budget scopes, 402 classification, provider failover) at
hour three, for systems that will live twenty minutes.

**My view.** ACCEPT the finding. REJECT Gemini's fix, which is to move the DECIDING
rule into an LLM prompt returning a structured boolean. That inverts principle 7 and
twenty-five years of your own experience, and Gemini itself marked it as taste.

The right fix is labelling, not relocation. Mark every domain constant as replaceable
example policy, in place. Add one line to §6 admitting that DECIDING exists as a
separate state so the refusal is visible in replay, not because control flow requires
it — *your domain probably needs fewer states than this.* And mark the spine by
hackathon relevance rather than architectural purity: copy the store, the failure
record, provenance checking and one bounded loop; do not copy budget scopes or 402
classification until you hit the problem.

That last one is a real concession. It costs us the "look how production-grade this
is" line and buys twenty-five teams who build something that fits their two days.

**Raj's view.**

> Agree to your view and fix the label

**Decision:** ACCEPT — label, do not relocate

---

# Appendix A — What none of the three raised

Where the method runs out. Three models, two identical documents, one prompt naming
eight dimensions: agreement on the dimensions I named is weaker evidence than it looks.
The genuinely independent signal is where one went off-prompt. These four are places
no model could see, and they need your judgement rather than another review.

**A1 — There is no student in the demo.** You designed six avatars. The demo cuts the
founder's voice entirely and leaves one outside expert as the only human. All three
reviewers checked whether the human loop *works mechanically*; none asked whether the
right human is in it. For a room of students, a system that does entrepreneurship *to*
them is a positioning problem, not an architecture one.

**A2 — §5 is the intellectual centre and all three read it only as a source of
evolvability claims.** Nobody asked whether the demo, staged at level 1 throughout,
contradicts the dial we are teaching from.

**A3 — Nobody asked whether the demo needs to be built.** All three assumed the nine
hours happens. What has to exist on 19 September is a credible reference and a starter
kit. A spec this scrutinised plus a phase-1 build may serve that better than a complete
build with a fragile live demo.

**A4 — Nobody costed the review.** Forty-plus findings across three reviews. Fixing all
of them takes longer than the build. There is no triage here between *must be true by
19 September* and *must be true before the Foundry inherits this* — that division is
the actual decision on this page.

**Raj's additions.**

> 

---

# Appendix B — Notable findings from a single reviewer

Not part of the twelve. Recorded because they are cheap to check and expensive to miss.

- **§4 may be unreachable (Claude).** Assumption 3 has `importance: 3`; the DECIDING
  predicate is `importance >= 4`. The centrepiece refusal does not occur by either
  branch. Proposed rule that makes §4 work as written and keeps the two concepts
  distinct: `block if (contradicts and load_bearing) or (unresolved and importance >= 4)`.
  Checkable in a minute; nobody else looked.
- **Seven helper functions carry real logic and are specified nowhere (Claude).**
  `load_assumptions`, `has_evidence`, `stance_of`, `highest_importance_unresolved`,
  `already_asked`, `frame_question`, `render_refusal`. Two are ambiguous in kind — the
  refusal text in §4 cannot be produced by deterministic code, so it is either an
  unbudgeted model call or hand-written prose.
- **Nothing invokes `sweep` (Claude).** The expert timeout guarantee never fires. One
  line: `resume` calls `sweep` before `advance`.
- **Prompt injection is unmentioned in either document (OpenAI, Claude).** The corpus is
  user-supplied text fed verbatim into a model whose output the system acts on. Both
  named it as their headline absence. F12's provenance check is most of the answer, and
  it is also the best demo beat available — show the poisoned document, show the check
  reject it.
- **No evaluation of judgement quality (Claude).** `bakeoff.py` measures whether a model
  can hold a contract, not whether the gate's verdicts are *correct*. An hour of a
  faculty member's time labelling ten theses pass/block gets a real number.
- **fastembed latency is unverified on event hardware (Gemini).** The 0.23s / 12ms
  figures are real but measured elsewhere. Cheap to re-run in a Codespace.
- **Assumption identity is positional (Claude).** If recheck re-derives assumptions and
  the model reorders them, every evidence row rebinds to a different claim. Freeze the
  set after first derivation, or give them stable ids.

**Agreed — all seven. But they are not all the same kind of item.** Two of them stopped
being optional the moment the twelve were accepted:

- **§4 unreachable** is now *forced*. Accepting F11 means the expert answer resolves
  assumption 2. Under the current `importance >= 4` rule, nothing else blocks — so the
  run proceeds to ARTIFACTS and the agent built to refuse writes the pitch instead.
  Fixing F11 without fixing the decision rule produces a demo with no refusal in it.
- **Assumption identity** is now *load-bearing*. Accepting F1 makes recheck real, and
  recheck is exactly the moment assumptions get written a second time. Freeze the set
  after first derivation.

Three are cheap and unconditional: `sweep` on `resume` (one line — and it matters
slightly more now that F9's auth is dropped, since the timeout is the only guard left on
the human wait); the fastembed re-measure in a Codespace (ten minutes); and naming the
seven helpers.

Two carry a caveat:

- **Prompt injection.** The check comes free with F12 — a fabricated citation cannot
  survive source-and-quote verification. What is *not* free is the demo beat. Showing a
  poisoned document being rejected is the best sixty seconds available, but F7 already
  says the ten minutes has no slack. Treat it as a swap, not an addition.
- **Judgement-quality evaluation.** Worth asking a faculty member for an hour to label
  ten theses pass/block. But note that accepting F7 (fixtures) removes the *demo* risk
  this was guarding against — the gate will not surprise us on stage. So this is now
  about whether the claim is true, not about whether the demo survives. Ask for it;
  do not block on it.

---

# Appendix C — What I would not act on

**Status: agreed, no action.**

- Gemini's fix for F10 — moving the DECIDING rule into an LLM. See F10.
- Gemini's meta-answer, that principle 7 "was clearly written retroactively to avoid
  LangChain". It asserts motive and is unfalsifiable. The other two reach a sharper
  version of the same point without it: the standard mixes principles ("state must
  survive restart") with solutions ("this is the line where it lives"), so a team can
  pass conformance by *resembling* the reference rather than demonstrating the property.
  That one is real, and separating the two is a half-hour edit to ARCHITECTURE.md.
- Claude's severity calibration in aggregate. That review believes the event is four
  days away with 48 people. It is fifteen days and roughly a hundred. The findings stand;
  the urgency is dialled higher than reality warrants.
- Collapsing DECIDING into ARTIFACTS. Two reviewers would; there is a teaching reason
  not to. Label it (F10) rather than remove it.

---

# Appendix D — The paper afternoon, re-verified

Re-checked against the twelve decisions above and against Appendix B being accepted.
The original six still stand, unchanged. Two more are now required, and one number needs
settling before §12 can be rewritten.

**Everything here is a decision on paper. None of it is code.**

### The original six — confirmed

1. **Decision rule.** `block if (contradicts and load_bearing) or (unresolved and
   importance >= 4)`. Keeps the two concepts distinct; makes §4 reachable. *No longer
   optional — F11 forces it, see Appendix B.* **(F11, App-B 1)**
2. **Expert answer becomes evidence.** Appended as an `Evidence` row with
   `source: "human_expert:<id>"`; `stance_of` takes the newest row per index. **(F11, F8)**
3. **`STOPPED` is suspended, not terminal.** `recheck` becomes legal. **(F1)**
4. **Provenance is verified, not asserted.** Reject any evidence row whose source is not
   in the retrieved cite set, or whose quote does not appear in that chunk. Closes the
   injection absence for free. **(F12, App-B 4)**
5. **Rewrite the two over-claims** — §3's agentic claim, §14's conversation bullet. Add
   §14's multi-team sentence to the same pass. **(F3, F2, F5 residue)**
6. **`faculty:gate` → `agent:gate`**, with a line saying faculty own the block
   conditions. **(F4, F10)**

### Two added by the Appendix B decisions

7. **Freeze the assumption set after first derivation.** Recheck re-searches the existing
   set and never re-derives. Without this, F1's recheck path silently rebinds evidence
   to different claims — provenance corrupting at the exact moment the spec claims its
   unique capability. **(App-B 7, consequence of F1)**
8. **Name the seven helpers in §10 and declare which are model calls.**
   `load_assumptions`, `has_evidence`, `stance_of`, `highest_importance_unresolved`,
   `already_asked`, `frame_question`, `render_refusal`. The last two are ambiguous in
   kind and must be settled explicitly: a model call needs a prompt file, a `step=` name
   and a budget line; deterministic code needs a template. **(App-B 2, F8)**

### The number that has to be settled first

§12 budgets **three prompts**. The real count after these decisions is **five to eight**:

| Call | Status |
|---|---|
| spot · gate · assumptions · evidence · artifacts | 5, always |
| expert-answer → stance classifier | +1, required by F8 and D2 |
| `frame_question` | +1 if it is a model call — undecided |
| `render_refusal` | +1 if it is a model call — undecided; §4's refusal text cannot be produced deterministically |

This single number is what makes F6 real. Two hours for three prompts becomes six for
eight, against models our own bakeoff scored 0/3 and 2/5 on contract compliance. Settle
D8 and the schedule rewrite follows arithmetically rather than by argument.

### What the two rejections do *not* change

Dropping F9's auth and deferring F5 removes work from the build. Neither touches this
list — every item above is spec text or a rule, and none of them depended on the tunnel
token or on multi-team scoping. The two residues are already folded in: routing stays
(D-none, build note), and §14's multi-team sentence joins the honesty pass at item 5.

### Then the scope decision, which is yours alone

What has to be true by 19 September, versus what has to be true before the Foundry
inherits this. Nothing above answers that, and it is the decision the whole review has
been circling.

**Raj's call on scope.**

> 
