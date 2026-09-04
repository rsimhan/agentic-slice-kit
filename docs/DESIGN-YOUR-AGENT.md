# Design your agent, before the event

**This is a starter kit, not homework.** Nobody is marking it, nobody is
checking whether you did it, and a team that turns up on 19 September with
nothing has broken no rule.

But you have a fortnight, and this is the best two hours you could spend in it.
Teams that arrive with a design start building at hour one instead of hour six —
and the thinking it asks for is the part a language model genuinely cannot do
for you.

You need a frontier chat — Claude, ChatGPT, Gemini, whichever you prefer. No
keys, no installation, free tiers are fine.

---

## The three rules

**Two hours, not two weeks.** Five short sessions. A polished twelve-page spec
is worse than a rough two-page one, because you will defend it instead of
testing it. You are producing a *hypothesis*, and the first person who tries
your agent at hour twelve should be allowed to demolish it.

**Separate sessions, not one marathon.** Chats degrade over long conversations
and free tiers have limits. Do one session, save the output, start a fresh chat
for the next and paste the output in.

**Argue with it.** This is the whole thing, so it is worth saying bluntly:
**the quality of what you get depends almost entirely on how hard you push
back.** These prompts are not magic. They set up a conversation; you still have
to have it.

---

## How to run each session

1. Open a **new** chat.
2. Paste **all** of [`PRINCIPLES-BRIEF.md`](PRINCIPLES-BRIEF.md) as your first
   message. Every time. It is what turns an agreeable assistant into a critic.
3. Paste the session prompt below.
4. Paste whatever you produced in earlier sessions.
5. Have the conversation. Argue. Then save the output into
   [`SPEC-TEMPLATE.md`](SPEC-TEMPLATE.md).

---

## Session 1 · Narrow the problem  *(20 min)*

> I want to build an agentic system for the following area: **[describe it in
> two or three sentences]**.
>
> Do not propose a solution yet, and do not tell me this is a great idea.
>
> Your job is to make me narrow this until it is one specific moment happening
> to one specific kind of person. Ask me questions one or two at a time. When I
> answer with a category — "students", "faculty", "small businesses" — push back
> and make me name an actual person in an actual situation.
>
> When you think it is narrow enough, say so and summarise it in one paragraph.
> Then tell me what you are still unsure about.

**You are done when** you can name a person, a moment, and what goes wrong,
without using the word "better".

---

## Session 2 · What it does, and what it refuses to do  *(25 min)*

> Here is the problem I settled on: **[paste session 1]**
>
> Help me decide what the agent does — in three sentences or fewer. Then, and
> this matters more, help me decide **what it refuses to do**. Name three things
> it will not do and why.
>
> Then take me through each step and ask: is the agent doing the *user's*
> thinking here? For every step where it is, challenge me on whether that is
> right. If my agent does the user's thinking for them, I have built a document
> generator, and I would rather find that out now.

**You are done when** you have three refusals you believe in, and you know which
steps are automation and which steps are you taking someone's job away from
them.

---

## Session 3 · The state machine  *(25 min)*

> Here is what my agent does and refuses to do: **[paste session 2]**
>
> Help me design the states it moves through. For each transition, tell me who
> decides — my code, or the model.
>
> Then test me on three things, and be strict:
>
> 1. Can you draw the exact sequence of steps before running it? If yes, I have
>    designed a workflow, not an agent. Tell me plainly and help me fix it.
> 2. **Which step can send work backwards?** If nothing can, I have not designed
>    an agent yet.
> 3. What stops it running forever? If I have not answered that, keep asking.

**You are done when** you can name the step that rejects another step's output,
and the thing that stops the loop.

---

## Session 4 · The evidence  *(25 min)*

> Here is my state machine: **[paste session 3]**
>
> My agent needs documents to reason over. Help me work out which ones.
>
> Start from the assumptions: what would have to be true for this to work? Then
> for each, what document could support **or undermine** it? I want the ones
> that could undermine it too — a corpus assembled only to agree with me
> produces an agent that agrees with me, which is worth nothing.
>
> Then: what happens when the evidence is not there? I want the agent to say it
> cannot establish something. Help me design that path, because it is the
> difference between a research tool and a machine that generates confident
> prose.

**You are done when** you have a document list, and a plan for what the agent
says when it finds nothing.

---

## Session 5 · Attack it  *(25 min)*

> Here is my whole spec: **[paste everything]**
>
> Stop helping me. **Argue against this design.**
>
> - What would a sceptical engineer say is wrong with it?
> - What will break first when a real person uses it?
> - Where am I doing something because it sounds impressive rather than because
>   it is needed?
> - If I merged two of these components, what would I actually lose?
>
> Then, separately: **list every factual claim in this spec** — about a model, a
> library, an API, a rate limit, a price — and for each, how I could verify it
> in ten minutes. Some of what you have told me during these sessions is wrong,
> and neither of us knows which parts.

**You are done when** you have a list of things to check, and at least one part
of your design has changed because of this session. If nothing changed, you did
not argue hard enough.

---

## The pushbacks worth demanding

These are the questions that make the difference. If the model is not asking
them, ask them yourself and refuse to move on until you have a real answer.

| ask | what it exposes |
|---|---|
| *If I merged two of these into one, what would I lose?* | Agents invented for the sake of it |
| *Draw the exact sequence before running it — can you?* | A workflow pretending to be an agent |
| *Which step can send work backwards?* | No loop, therefore no agent |
| *What stops this running forever?* | No bound, therefore a 3am disaster |
| *For each step — is the agent doing the user's thinking?* | A document generator |
| *What claim will this make that a reader cannot check?* | Confident invention |
| *What does it do when the evidence is not there?* | Whether it can say "I don't know" |
| *What would have to be true for this to fail?* | Whether you have any falsifiable claim at all |
| *Argue against this. What is wrong with it?* | Everything the agreeable version hid |

---

## What a real pushback sounds like

You will get a lot of this:

> *"That's a great approach! You could enhance it further by adding a
> Coordinator Agent to orchestrate the specialists…"*

That is agreement wearing a suggestion's clothes. It has told you nothing, and
it has just talked you into the first anti-pattern on the list.

This is what you are looking for:

> *"You have three agents that all use the same model with the same tools and
> differ only in their instructions. That is one agent with three prompts. What
> would you actually lose by merging them? And separately — your gate never
> rejects anything, so your path is fixed. That is a workflow."*

If you are only getting the first kind, paste the principles brief again and
tell it directly: **stop agreeing with me.**

---

## When you are done

You have two pages. It is wrong in places, and the last two sections say where.
That is exactly right.

**Send it in for review.** Raj Simhan (CEG '96) has offered to read the specs
teams produce and push back on what they have missed — which is the one thing a
chat cannot do for you, because it does not know what happens in the fourth week
of a real build.

> *Submit to: **[organisers to add address / form link]***

Two more things to do with it.

**Bring it to the event, and expect to change it.** The first person who tries
your agent at hour twelve will find something the spec got wrong. That is the
spec working, not failing.

**Do the verification list first.** Whatever is in section 11 — the claims about
models, libraries and limits — check those in the first hour on the night. Some
of them will be wrong, and finding out on Friday evening costs ten minutes.
Finding out on Saturday night costs the weekend.
