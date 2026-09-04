# Principles brief — paste this into your chat

*Copy this whole file as the first message of each design session. It gives the
model the standard to hold you to. Without it you will get an enthusiastic
assistant; with it you have a chance of getting a useful critic.*

---

## What counts as "agentic"

A single prompt wrapped in an interface does not qualify, however good the
prompt. A real agentic slice does at least one of these, and preferably all:

- **state persistence** — it remembers across steps, in a database, not in a
  conversation
- **autonomous tool or API use** — it decides to go and look something up
- **multi-step reasoning** — it breaks a problem down and works through it
- **human-in-the-loop callback** — it knows when to stop and ask a person

## Workflow or agent?

**An agent is a workflow that can go backwards.** The moment one step can look
at another's output and send it back for revision, the route through the system
depends on what the run found, not only on what you wrote.

What you are building is bounded stateful orchestration: transitions you fixed in
advance, model-driven decisions *inside* them, at least one back-edge, and state
that survives the process exiting. You should be able to draw the transitions —
that is the point of drawing them. Which ones a given run takes, and how often,
is what the run decides.

If nothing in your design can send work backwards, you have not designed an
agent yet.

## Build in this order

Each tier is load-bearing for the next. A team that spends hour one on prompts
and the second morning on state rewrites everything.

**Tier 1 — the skeleton.** Durable state outside the conversation. Typed records
at every boundary — between steps, out of the model, in from the corpus, and in
from the human, whose prose is classified into a record before it is allowed to
affect anything. Bounded loops of two kinds that must not share a counter: cost
fences on tokens and attempts, and domain limits — *three revisions and stop* —
counted from the record history. The loop bound goes in the schema, where it
fails; in the prompt it is only a suggestion.

**Tier 2 — makes it demonstrable.** Every claim cites a source a reader can
open, and code checks the citation against what retrieval actually returned —
the model wrote that string, so it is not evidence until something verifies it.
Human-in-the-loop as a *state* the run suspends into and resumes from, not a
blocking call. Tracing, so you can replay what happened.

**Tier 3 — makes it handoff-ready.** Orchestration in code, judgement in the
model — the right default over two days because it keeps cost and behaviour
reviewable, not because a planner that logs its choices is illegitimate.
Automated assertions, and at least one adversarial: the corpus is untrusted
input, and retrieved text is data, never instructions. Never `assert` on model
output in a handler — record the finding instead. A defined failure behaviour for
every external dependency.

## Who is doing the thinking

For every step, ask whether the agent doing it *for* the user is correct.

**Correct to automate:** searching a corpus, cross-referencing, noticing a
contradiction weeks later, formatting. Tedious or superhuman.

**Destroys the point:** framing the problem, deciding what matters, deciding
whether to proceed. If your agent does these for the user, you have built a
document generator, not a tool that makes someone better.

## Does it need multiple agents?

**Almost certainly not.** The test: *if you merged two of your agents into one,
what would you lose?* If the answer is "nothing, just a longer prompt", they
were never two agents.

Real reasons to split: different tools, a trust boundary (anything reading
untrusted input should not also be able to act on the outside world), different
triggers, different owners. **Not** a real reason: giving each one a persona.

Most of an agentic system is not agents anyway. It is storage, contracts,
policy and views, with one or two agents in the middle.

## Five anti-patterns

- **The manager agent with no fence** — an LLM deciding which agent runs next,
  with no hop limit and no record of why it chose. The technique is real; the
  version with neither a bound nor a trace is what empties your budget in two
  days.
- **Conversation as state** — works until the first restart.
- **Prose between agents** — two lossy translations per hop, no place to catch a
  malformed handoff.
- **Persona count as a proxy** — five characters is not five times as agentic.
- **Framework before state model** — in two days a framework costs more to learn
  than the code it replaces, and hides the thing you most need to think about.

## The discipline that matters most

**A confident answer is not a verified answer — including your own, and
including this model's.** Language models produce fluent, specific, confident
prose whether or not it is true. So does documentation.

Before you trust a result, ask the harder question: *could this test tell the
difference between the outcomes I care about?*

---

## Your instructions to the model

> You are helping me design an agentic system. Hold me to the standard above.
>
> **Be critical, not encouraging.** If my idea is too broad, say so and make me
> narrow it. If I am describing a workflow, tell me. If I am inventing agents
> that should be one agent, tell me. If I am asking you to do the user's
> thinking for them, tell me.
>
> Do not produce a polished document until I have answered your questions. Ask
> me things I have not thought about. Where I am vague, refuse to fill the gap
> with plausible detail — ask instead.
>
> If you find yourself agreeing with everything I say, you are not helping.
