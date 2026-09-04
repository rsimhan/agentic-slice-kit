# corpus/

**This is not background reading for the AI. It is the evidence base your agent
is allowed to cite.**

It does not make your agent smarter. It defines what your agent can *prove* —
and, just as importantly, what it must admit it cannot.

## How to decide what goes in here

Only one step in the flow reads these documents: **PROBE**, the step that looks
for evidence. So the question is not "what should it know about?" but:

> When my agent makes a claim, what should it be able to point at?

Work backwards from your assumptions. Write down the three to five things that
must be true for your thesis to hold. Then, for each one, add a document that
could **support or undermine it**. One or two files per assumption.

## The trap

**The corpus is where bias enters your agent.** If you write a document that
contains your conclusion, PROBE will "discover" it and you will be impressed by
your own system. That is a rigged demo, and it is the most common way people
fool themselves with retrieval.

Write facts, not conclusions. Let the agent do the inference. If it connects two
neutral documents into a finding you did not spell out, that is worth showing. If
you had to tell it, you have a parrot.

## Practical

- **Plain `.md` or `.txt`.** Not PDF, not Word.
- **Name files descriptively.** The filename appears in every citation, so
  `founder-interviews-2024.md#3` is useful and `doc1.md#3` is not.
- **Several hundred to a couple of thousand words each.** Retrieval returns
  passages, so one enormous file dilutes rather than helps.
- **Ten to twenty files is plenty.** More is not better.
- **Real notes beat official documentation.** Three transcribed conversations
  will produce more useful answers than a hundred pages of policy.

## Before you build, check the corpus can actually answer

```bash
python -c "
from slice.store import Store
from slice import retrieve
s = Store('run.db'); retrieve.ingest(s, 'corpus')
for q in ['<your assumption 1>', '<your assumption 2>', '<your assumption 3>']:
    print('\n' + q)
    for c in retrieve.search(s, q, k=3):
        print(f'   {c.cite():<32} {c.text[:70]}...')
"
```

**If an assumption returns nothing relevant, your corpus cannot support it.**
Better to learn that now than halfway through day two.
