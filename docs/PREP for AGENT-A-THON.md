# **CEG ASTRA — Agent-a-thon — Sep 2026**

**The event:** 19–20 September 2026, 48 hours.
**Info Session 1:** Saturday 5 September, 6:30 PM IST — Dr. Viji Krishnamurthy (VP of AI, Oracle Industries) and Raj Simhan (CEG '96).

> **One thing that cannot wait:** apply for the **GitHub Student Developer Pack** today. It takes ten minutes, and approvals have been reported taking up to a fortnight. Details at the bottom of this page. Everything else can happen after Saturday.

---

## **Prerequisites**

**No prior AI experience required.** Open to students from all departments — CSE, ECE, EEE, Mech, Civil, SAP, ACT and others — across all four Anna University campuses.

**You do not need to be a software engineer to build an agent.** CSE and IT students can write Python or JavaScript directly. Everyone else can work through AI-assisted tools, describing what you want in plain English and iterating on what comes back.

One honest caveat, so nobody spends the weekend on the wrong thing: **AI assistance is a good way to write code. It is not a substitute for designing the system.** A single clever prompt wrapped in an interface will not qualify, however good the prompt.

What we're looking for is an agent that does at least one of these:

* remembers things between steps
* decides for itself to use a tool or an API
* breaks a problem into steps and works through them
* knows when to stop and ask a human

Here is the quickest test of whether you have one. **Can you draw the exact sequence of steps before you run it?** If yes, you have built a workflow — a fixed path, the same every time. If no, because the number of loops and what it does next depend on what it finds, you have built an agent.

Put another way: **an agent is a workflow that can go backwards.** If nothing in your design can look at an earlier step's output and send it back for another go, you have not designed an agent yet.

We'll give you a starter kit that already has that structure in place, so you can spend your 48 hours on your problem rather than on plumbing.

**Interdisciplinary teams do best.** A Mech, Civil or EEE student who genuinely understands a lab, curriculum or workshop problem, paired with someone who can build, beats a team of pure coders looking for a problem to solve. Domain insight is the scarcer ingredient.

#### **Every team needs three jobs covered**

Teams tend to split like this. It's a strong recommendation, not a rule — but decide it deliberately rather than by drift.

* **The builder.** Wires up the plumbing and unblocks everyone else.
* **The "domain lead".** Owns the actual problem — the rules, the prompts, what "good" looks like. This is often a non-CSE student and it is often the most important role.
* **The "evidence lead".** Tests the agent on real students, runs a stress test to try to break it, and records what changed as a result.

**If you write no code at all, take the third job.** It is not a consolation prize. Around 40% of what we're judging is evidence that real people used your agent and that you changed it in response to watching them — and it's the part almost every team leaves until the last few hours, by which point it can't be done honestly.

**Two of these three roles need no programming at all**, and both have real preparation worth doing beforehand. The starter kit has a short guide for each.

---

## **Recommended starting points**

**1. Bring a problem you actually care about.** The strongest prep isn't technical. Pick one specific moment in teaching or learning that genuinely annoys you — one lab, one assignment, one thing your department does badly — and come with that. Concrete beats comprehensive; a small idea that works beats a big idea that doesn't.

**2. Design your agent before you arrive — two hours, with a chat.** This is the highest-leverage thing available to you in the fortnight, and it needs no keys, no installation and no coding.

The starter kit includes a guided design session you run with any frontier chat — Claude, ChatGPT, Gemini, your choice. Five short conversations, roughly twenty minutes each: narrow your problem, decide what your agent does *and refuses to do*, design its states, work out what evidence it needs, and then instruct the model to attack your own design.

You end up with a rough two-page spec. It will be wrong in places — the guide makes you write down where.

> **Raj Simhan has offered to read the specs teams send in and push back on what you've missed.** That's the one thing a chat cannot do for you, because it doesn't know what goes wrong in week four of a real build. Submission details: **[organisers to add]**

Two warnings the guide repeats, because they matter. **Two hours, not two weeks** — a polished twelve-page spec is worse than a rough two-page one, because you'll defend it instead of testing it. And **argue with the model.** It will agree with you by default, and agreement is worth nothing. The guide gives you the specific pushbacks to demand.

**3. Attend Info Session 1** — Saturday 5 September, 6:30 PM IST. We'll walk through the technical stack, the starter kit, and exactly what we're looking for.

**4. Understand four ideas, not four tools.** Andrew Ng's free short courses on agentic workflows are an excellent hour: planning and decomposition, tool use, and memory.

Note that our fourth idea is different from his. Where those courses cover *multi-agent collaboration*, we care about **human-in-the-loop** — an agent that knows when to stop and ask a person. Most systems described as multi-agent are one agent wearing several costumes, and in 48 hours you will get further with one agent that does something real than with five that pass paragraphs to each other.

Learn the ideas. The specific frameworks are a day-three decision, not an hour-three one, and we'll show you a working example on Saturday.

**5. Get comfortable directing an AI assistant.** Try building something small — an interactive quiz, a data cleaner — by describing it in plain English and correcting what comes back. **GitHub Copilot** (free with the Student Pack) or **Claude** are closest to what you'll use on the night.

Three habits worth practising, because they are most of the difference between people who find these tools useful and people who find them maddening:

* give it **one small, precise task** at a time, not "build me the whole thing"
* always show it **the actual error message**, not "it doesn't work"
* read what it wrote to check **the decision, not the syntax** — the syntax will be fine; the unbounded loop it quietly added will not be

Everything you need to run the tools will be provided on the day. Nothing has to be installed on your laptop — a browser is enough.

---

## **GitHub Student Developer Pack**

**Apply at education.github.com → *Sign up as a student*.**

It's free, it takes about ten minutes, and it unlocks three things you'll want during the hackathon: **GitHub Copilot free** (an AI coding assistant), **$100 of Microsoft Azure credit**, and a larger allowance on the cloud development environment we'll be using.

You'll need a student ID, class schedule, or enrolment letter, and ideally your college email address.

**Do it today rather than next week.** GitHub publishes no turnaround time and approvals have been reported taking anywhere from a couple of days to a couple of weeks. If you apply on the morning of the event, it will not come through in time.

#### Already have the Student Pack?

Three quick checks, about two minutes:

1. Confirm it's **still active** at education.github.com/benefits — it's tied to your expected graduation date and does lapse. If it's expired, reapply now.
2. Make sure **GitHub Copilot is actually switched on**. Holding the Pack doesn't enable it automatically, and it's the single benefit you'll use most on the night.
3. If you're 18 or over, **redeem the $100 Azure credit** — also a separate step.

**And everyone applies individually.** This isn't one per team. The cloud development allowance is attached to each personal account, so four verified teammates give your team roughly 50% more capacity than one verified and three not.

---

## **The starter kit**

**[organisers to add repo link]**

Optional, and free to ignore. If you want it, the three guides worth opening first are:

| if you are the | open |
|---|---|
| **domain lead** | `docs/DESIGN-YOUR-AGENT.md`, then `docs/QUICKSTART.md` |
| **evidence lead** | `docs/EVIDENCE.md` — including its two-week prep section |
| **builder** | `docs/ARCHITECTURE.md` |
