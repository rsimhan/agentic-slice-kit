# **CEG ASTRA — Agent-a-thon — Sep 2026**

**19 and 20 September.** Two days, 9:00 AM to 6:00 PM on site each day. The
evening in between is yours — carry on remotely if your team wants to.

**If you missed Info Session 1** — Dr. Viji Krishnamurthy (VP of AI, Oracle Industries) on the AI economy, and Raj Simhan (CEG '96) on what separates an agent from everything else being called one — the recording is worth an hour. *\[check with your college organizing team for recording link\]*. This document assumes none of it, so you lose nothing by reading on.

> One thing is worth doing this week rather than next: the **GitHub Student Developer Pack** application, because approvals have taken up to a fortnight and nothing else here has a queue in front of it. Details at the end.

> **The preliminary 'Agent Specs' submission is due Tueday, 15 September, end of day.** The organising team will circulate a submission form nearer the date; Everything else operational — keys, judging weights, who to ask on the day — lands in `docs/ON-THE-DAY.md` in the repo next week.

---

## **Who this is for**

Everyone. No prior AI experience, no particular department, all four Anna University campuses.

You do not need to be a software engineer to build an agent. Some of you will write Python or JavaScript directly. Others will work through AI-assisted tools, describing what they want in plain English and correcting what comes back. Both get you to something that runs, and a team usually has people doing each.

One caveat worth having up front, though, because it decides how you spend the weekend: **AI assistance is a good way to write code. It is not a substitute for designing the system.** A single clever prompt wrapped in an interface will not qualify, however good the prompt.

### What actually counts as an agent

Four things, and you want at least one:

* it remembers things between steps
* it decides for itself to use a tool or an API
* it breaks a problem into steps and works through them
* it knows when to stop and ask a human

There's a quicker test. **Can you draw the exact sequence of steps before you run it?** If you can, it's a workflow — a fixed path, the same every time. If you can't, because the number of loops and what happens next depend on what it finds, it's an agent.

Or, as a design instinct: **an agent is a workflow that can go backwards.** If nothing in your design can look at an earlier step's output and send it back for another go, you haven't got one yet.

### Mixed teams do better, and it isn't a platitude

Someone who genuinely understands a specific problem — a lab that never runs on time, a subject where everyone fails the same question, a process that wastes an afternoon a week — paired with someone who can build, tends to beat a team of strong coders hunting for a problem to solve.

Deep familiarity with a real situation is the scarcer ingredient, by a distance. It comes from having sat through the thing, not from what you study.

---

## **The three jobs in a team**

Teams tend to split three ways. It's an observation, not a rule — but it's worth deciding deliberately rather than by drift, because the third one gets forgotten and it's the one that decides a lot of the outcome.

**Designer.** Owns the problem and the spec. Decides what the agent should do, what a good answer looks like, what should make it refuse, and which rules it enforces. Writes the instructions the agent works from and judges whether its output is any good. Design work rather than coding, and the part no assistant can do for you — it depends on knowing what actually happens in the situation you're fixing.

**Builder.** Gets the machinery running and keeps everyone else unblocked. Sets up the environment, wires the pieces together, and becomes the person who reads the error message when something breaks at four o'clock. Front-loaded — heaviest on the first morning, lighter after that.

**Verifier.** Establishes that it works for real people, not just that it runs. Puts it in front of someone who has never seen it, watches without helping, recruits someone to try to break it, and makes sure the team changes something in response. Also writes up why the agent is shaped the way it is and where its limits are.

Roughly a third of what we're judging is that third job — evidence that real people used your agent and that you changed it after watching them. It's the part most teams leave until the last few hours, by which point it can't be done honestly.

Pick by what you want to own, not by what you already know how to do. All three jobs involve directing an assistant, and none of them is only for people who already write code.

## **Ways to spend the fortnight**

None of this is required. All of it means arriving with a head start.

### Bring a problem you actually care about

The strongest preparation isn't technical. One specific moment in teaching or learning that genuinely annoys you — one lab, one assignment, one thing your department does badly. Concrete beats comprehensive, and a small idea that works beats a big idea that doesn't.

### Design your agent before you arrive

Three hours, no keys, no installation, no code, and everyone on the team can do it — together over a coffee, or alone and argue about it after. The starter kit includes a guided design session you run with any frontier chat — Claude, ChatGPT, Gemini, whichever you like.

Five short conversations of about twenty minutes: narrow your problem until it's one specific person in one specific moment, decide what your agent does *and refuses to do*, design the states it moves through, work out what evidence it needs, and then — the useful one — instruct the model to attack your own design rather than polish it.

You end up with a rough spec that will be wrong in places. The guide makes you write down where, which is the point — and it is the substance a preliminary submission has to be able to say. There's a worked example in the repo to read it against.

Two things the guide keeps repeating. **Three hours, not two weeks** — a polished twelve-page spec is worse than a rough three-page one, because you'll defend it instead of testing it. And **argue with the model**, because it will agree with you by default and agreement is worth nothing. The guide gives you the specific questions to put to it.

### Learn four ideas rather than four tools

Andrew Ng's free short courses on agentic workflows are a good hour: planning and decomposition, tool use, memory.

Our fourth idea differs from his, and it's worth knowing why. Where those courses cover *multi-agent collaboration*, we care about **human-in-the-loop** — an agent that knows when to stop and ask a person. Most systems described as multi-agent turn out to be one agent wearing several costumes, and in two days you'll get further with one agent that does something real than with five passing paragraphs to each other.

Frameworks are a day-three decision, not an hour-three one. We'll show you a working example on Saturday.

### Get fluent at directing an assistant

Build something small this fortnight — a quiz, a data cleaner, anything. **GitHub Copilot** (free with the Student Pack) or **Claude** are closest to what you'll have on the day.

What you're practising isn't coding. It's describing a task precisely enough that a machine can satisfy it, then reading what came back and saying what's wrong with it. Three habits carry most of the difference between people who find these tools useful and people who find them maddening:

* one small, precise task at a time — not "build me the whole thing"
* show it **the actual error message**, never "it doesn't work"
* read what it wrote to check **the decision, not the syntax** — the syntax will be fine; the retry loop it quietly added with no limit will not be

---

## **The starter kit**

**github.com/rsimhan/agentic-slice-kit**

Optional, and free to ignore. It's a working agent with the awkward parts already solved, so your two days go on your problem instead of on plumbing.

Two folders, and the split is the whole idea:

**`slice/`** is the spine — about 1,100 lines that handle durable memory, typed handoffs between steps, spending limits, evidence retrieval, the state machine, and the pause-and-resume when a human is needed. Deliberately **not** a library you install. You copy it, read it, and edit it, because a black box you import is a black box you don't learn from.

**`demo/`** is the domain — the prompts, the rules, the problem being solved. That's the half you replace with your own.

Open it in the browser and it runs; nothing installs on your laptop.

### Everyone starts in the same place

Whatever seat you end up in, the fortnight has one job: **decide what your agent
is, and write it down.** That is part one of [`docs/DESIGNER.md`](https://github.com/rsimhan/agentic-slice-kit/blob/main/docs/DESIGNER.md) — five short
sessions you run with any frontier chat, no keys and nothing installed. **The
whole team should be in it**, whatever seat they end up taking: the builder
argues about what is feasible, and the person who will watch strangers use it has
the sharpest instinct for where it will confuse them.

What comes out is a filled-in spec: a specific moment worth fixing, a state
machine with a back-edge, three things your agent refuses to do, and an honest
list of what you are unsure about. That is the substance a preliminary
submission has to be able to say. The deck is the easy part once you have it.

There is a worked example in the repo — `demo/SPEC.md` is the same template
filled in for a real agent, section for section, so you can see how much detail
is actually useful.

### Then, once you have a spec

The three guides below are for the days themselves. Open one the night before if
you want a head start, but nothing here needs a fortnight.

| seat | read | what it gives you |
|---|---|---|
| Designer | `docs/DESIGNER.md` part two | the corpus, the prompts, and how to judge whether an answer is any good |
| Builder | `docs/BUILDER.md` | a running system in about twenty minutes, then the five functions worth reading |
| Verifier | `docs/VERIFIER.md` | how to run a walkthrough, what to write down, and why roughly a third of the marks live here |

The ideas all three assume are in `docs/PRINCIPLES-BRIEF.md` — short, and worth reading before any of them. `docs/ARCHITECTURE.md` is the reference to consult when something breaks, not a document to read cover to cover.

**One thing that cannot wait.** Whoever takes the evidence seat should line up
their testers this week — three people for twenty minutes each during the event,
and one willing to try to break it. Names and times, not a vague ask on the day.

---

## **GitHub Student Developer Pack**

**education.github.com → *Sign up as a student*.**

Free, about ten minutes, and it unlocks three things you'll want: **GitHub Copilot free**, **$100 of Microsoft Azure credit**, and a larger allowance on the cloud development environment we'll be using.

You'll need a student ID, class schedule or enrolment letter, and ideally your college email address.

The reason to do it now is simply that GitHub publishes no turnaround time and approvals have been reported taking anywhere from a couple of days to a couple of weeks. Applying on the morning of the event won't work.

**Already have it?** Three checks, two minutes. Confirm it's **still active** at education.github.com/benefits, since it's tied to your expected graduation date and does lapse. Check that **Copilot is actually switched on** — holding the Pack doesn't enable it, and it's the benefit you'll use most. And if you're 18 or over, **redeem the Azure credit**, which is also a separate step.

**Everyone applies individually**, by the way — this isn't one per team. The cloud development allowance attaches to each personal account, so four verified teammates give your team roughly 50% more capacity than one verified and three not.
