# On the day — the operational page

Everything here is logistics rather than engineering: keys, money, deadlines,
who to ask. One page, so that when something non-technical is in your way you
know where to look.

> **This page is not finished yet.** The lines marked ⚠️ are being settled with
> the organising team and will be filled in **during the week of 8 September** —
> well before you need any of them. Nothing in the two weeks of preparation
> depends on anything here, so carry on with the guides and check back before you
> turn up.
>
> *Organisers: every open decision in the kit is collected on this one page
> rather than scattered through the guides, so this is the only file to edit.*

---

## The preliminary submission

Your spec — the one that comes out of part one of [`DESIGNER.md`](DESIGNER.md) —
is what a strong preliminary submission has to be able to say. The submission
itself is a short deck; the spec is the substance behind it.

| | |
|---|---|
| **Deadline** | **Monday 15 September, end of day IST** |
| **How to submit** | ⚠️ *a Google Form the organising team will circulate — link here once it exists* |
| **What to send** | ⚠️ *deck format and slide limit* |
| **Name the file** | `TeamName_CollegeCode.pdf` — one file, so twenty-five submissions do not all arrive called `spec.pdf` |
| **Shortlisting announced** | ⚠️ *date* |
| **Questions about the submission** | `agentathon.cse@gmail.com` |

**One team, one submission.** Put every team member's name on it — individual
contribution is visible to the Foundry selection, and it cannot be visible if it
is not recorded.

**Upload early rather than perfectly.** The folder accepts a replacement, so a
draft on Saturday and a better version on Monday beats nothing on Monday. What is
being screened is whether you have a specific problem, a state model that can go
backwards, and an honest list of what you are unsure about — not polish.

---

## Your API key

You get a key at the registration desk beginning `sk-or-v1-`. It goes in `.env`
after `OPENROUTER_API_KEY=` and nowhere else — never in code, never in a commit,
never in a screenshot.

| | |
|---|---|
| **One key per** | ⚠️ *team, or per person* |
| **Starting allowance** | ⚠️ *dollar cap per key* |
| **Top-up** | ⚠️ *who to ask, where they sit, what they need from you* |
| **Hours the desk is staffed** | ⚠️ *9–6 both days, or narrower* |

**The cap is a real fence, not a warning.** When your key cannot cover a request,
the provider refuses it *before* running it — so you cannot accidentally overspend,
and you also cannot argue with it.

### Reading the two errors that look identical and are not

`python scripts/doctor.py` tells you which one you have, and they need opposite
responses.

| what you see | what it means | what to do |
|---|---|---|
| `refused for credit (402)` | **Your key** cannot cover a request this size | Lower `SLICE_MAX_TOKENS` first — the provider reserves against it, so a big ceiling can refuse you while you still have usable credit. If that does not fix it, go to the desk |
| `rate-limited (429)` | **Not your fault.** The provider is throttling | Wait a few minutes, or switch to `SLICE_FALLBACK_MODEL`. Do not go to the desk; there is nothing they can do |
| `unreachable (HTTP 000)` | Network, not code | Check the wifi before you check anything you wrote |
| `key works — $X of $Y left` | Healthy | Glance at it occasionally. If it is dropping fast, something is looping |

**If the whole room goes down at once**, it is the shared pool, not your key.
Tell the desk once and carry on with fixtures or stubbed answers — that is
exactly the situation recorded model responses exist for.

---

## What you are judged on

⚠️ *Organisers: the weighting below is indicative, drawn from what the guides
already tell teams. Replace with the final rubric.*

| | roughly |
|---|---|
| A working agentic slice — state, tools, decomposition, a human in the loop, a back-edge | ⚠️ |
| Evidence — three walkthroughs with real people, one recorded break-and-fix, and a change you made because of what you saw | ⚠️ *about a third* |
| Problem definition and design rationale — why it is shaped this way, and where its limits are | ⚠️ |
| Handoff — a repo another team could pick up | ⚠️ |

The one thing worth saying plainly whatever the final weights are: **a third of
this is not code**, it cannot be produced on the last afternoon, and it is the
part most teams discover too late.

---

## The two days

**19 and 20 September, 9:00 to 6:00 on site each day.** The venue empties at six.
You are free to keep working in the evening and pick up again the next morning,
but plan the work — and especially anything that needs other people in the room —
around the hours you are actually together.

That last point matters most for walkthroughs. Three testers, twenty minutes
each, plus someone willing to try to break it: book names and times, and book
them for when the building is full.

---

## Where to ask

| about | ask |
|---|---|
| Keys, money, the desk | ⚠️ *name and where they sit* |
| The starter kit, or something in `slice/` behaving oddly | ⚠️ *mentor channel or table* |
| Submission and logistics | `agentathon.cse@gmail.com` |
| Anything you have been stuck on for twenty minutes | a mentor — twenty minutes is the right threshold, long enough to have genuinely tried |

**If you find a bug in `slice/` itself**, say so in the shared channel rather
than only fixing your own copy. Every team is running the same code, and you will
have saved several of them an afternoon.
