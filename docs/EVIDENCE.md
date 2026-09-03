# Evidence

**For the person on the team who is not writing code.**

Read this first: you have the highest-leverage job on the team, and almost
nobody does it well.

Roughly **40% of what you are judged on** is not the code. It is evidence that
real people used your agent, that you learned something from watching them, and
that you changed the thing in response. That work cannot be done on Sunday
morning. It cannot be invented. And every year, most teams pile everyone onto
features until hour forty and then produce it in a panic — which is visible
instantly to anyone who has ever done user research.

If you take this role seriously, your team will stand out. Not because the
others cannot do it, but because they will not have.

---

## What you have to produce

Four things. All four are explicitly required.

**1. Three fellow students who walked through the intended flow**, with their
feedback captured and **at least one visible iteration** — meaning something
changed because of what you saw.

**2. One recorded stress test.** A classmate deliberately trying to break or
confuse your agent's logic, followed by **a fix commit that addresses what
broke**.

**3. A design rationale.** Short. Why this shape of agent, what it does, what
its limits are.

**4. Handoff-readiness.** Could someone else pick up the repo and keep building?

Notice that three of the four are about *what happened*, not *what you built*.
That is deliberate. They are selecting for people who iterate on feedback rather
than defend their first design.

---

## How to run a walkthrough

You need three people, twenty minutes each. Do the first one **as soon as
anything works at all** — hour twelve, not hour forty. A rough thing tested
early beats a polished thing tested never.

**Recruit from outside your team.** Someone who has not heard you explain it.
Another team, someone in the corridor, an organiser.

**Do not explain it first.** This is the hardest rule and the most important
one. The moment you say "so what this does is…", you have destroyed the thing
you were trying to measure. Hand it over and say: *"Have a go. Talk out loud
while you do — tell me what you're thinking, even if it sounds obvious."*

**Then be quiet.** Genuinely quiet. Count to ten before you rescue them. The
silence is uncomfortable and it is where all the findings are.

**Write down what they did, not what they said.** People are unreliable
narrators of their own behaviour and reliably kind about your work. What they
*do* is the data. Where did they hesitate? What did they click that you did not
expect? What did they read twice?

Three questions at the end, in this order:

> What did you think it was going to do?
> Where did you get stuck?
> What would you have wanted it to do instead?

**Capture it as you go** in `docs/evidence/walkthrough-1.md` — who, when, what
they tried, where they stalled, what they said. Two hundred words is plenty. A
photo of a sticky note counts.

**Then change something.** One thing, because of what you saw. Commit it with a
message that names the walkthrough — `"Rename the confusing button (walkthrough
2)"`. That commit *is* your visible iteration, and it is the single most
persuasive artefact you can produce, because it proves the loop closed.

---

## How to run a stress test

Different job. The walkthrough asks *does this work for someone trying to use
it*. The stress test asks *what happens when someone tries to break it*.

**Recruit a hostile classmate.** Ideally someone technical who would enjoy this.
Give them fifteen minutes and this brief: *"Try to make it do something stupid.
Confuse it, contradict it, give it nonsense, give it nothing."*

Things worth pointing them at:

- **Empty and absurd input.** Nothing at all. Ten thousand words. Emoji only.
- **Contradiction.** Tell it one thing, then the opposite.
- **Out of scope.** Ask it something the corpus cannot possibly answer — does
  it say "I don't know", or does it invent?
- **The instruction it was told not to break.** If the agent is forbidden from
  giving the answer, can they trick it into giving the answer?
- **Interruption.** Close the browser mid-run and reopen it. Does the run
  survive? (It should — that is what the store is for.)

**Record it.** A screen recording is best; a photo of the terminal plus notes is
fine. Save it under `docs/evidence/`. The requirement is that it is recorded,
not that it is polished.

**Then fix one thing it broke, and say so in the commit message.** That pairing
— a recorded break and a commit that answers it — is exactly what is being
asked for. One good one beats five vague ones.

---

## The design rationale

One page. Four headings. Write it at hour forty, not hour forty-seven.

**What it does.** Two sentences, in plain language, no jargon. If you cannot
explain it to someone from another department, the team does not understand it
either — and that is worth discovering while there is still time.

**Why this shape.** What did you choose *not* to build? Scope decisions are more
interesting than features, and "we deliberately did not do X because Y" reads as
judgement rather than omission.

**What it can't do.** Be specific and be honest. *"It fails on handwritten
input"* is a stronger line than any feature claim, because it tells a judge you
know where your own edges are. Teams hide limits; strong teams name them.

**What we'd do next.** Shows you know where you stopped and why.

---

## Handoff-readiness

Ask a person from another team to clone your repo and get it running, from your
README alone, without asking you anything. Time them.

Whatever they get stuck on is your README's real content. Fix that, and nothing
else. This takes twenty minutes and is worth more than the day you would spend
writing documentation nobody reads.

---

## Where all this lives

```
docs/evidence/
  walkthrough-1.md      who, when, what they tried, where they stalled
  walkthrough-2.md
  walkthrough-3.md
  stress-test.md        + the recording
  design-rationale.md
```

Commit as you go, not at the end. The timestamps are part of the evidence: they
show you tested early and iterated, rather than assembling a story on Sunday.

---

## Your hour-by-hour

| when | you |
|---|---|
| **H0–4** | Sit with the build. Understand what it is meant to do — you are about to explain it, or deliberately not explain it, to strangers |
| **H8–12** | Line up your three walkthrough people and one hostile classmate. Book them now; they get busy |
| **H12–16** | **First walkthrough, on whatever exists.** Yes, it is rough. That is the point |
| **H16–20** | Feed findings back. Make sure one change lands and the commit says why |
| **H24–30** | Walkthroughs two and three |
| **H30–36** | Stress test, then the fix commit |
| **H36–42** | Design rationale. Handoff test with an outside team |
| **H42–48** | Rehearse the demo. Time it. Then time it again |

If the build is late and you are tempted to skip the first walkthrough — don't.
A twenty-minute session on something half-broken at hour twelve routinely
changes what a team builds for the next thirty. That is the whole point of doing
it early, and it is worth more than the feature you would have shipped instead.
