# Spec template

*The shape of what you are producing. Two pages is plenty; four is too many.
Delete every prompt in italics as you replace it.*

---

## 1. The moment

*One paragraph. What specific thing happens today, to whom, and why is it bad?
Not "students struggle with X" — a named kind of person, in a named situation.*

**Who exactly:**
**What they do today:**
**Why that is bad:**

## 2. What the agent does

*Three sentences maximum. If you need more, it is doing too much.*

## 3. What it refuses to do

*Just as important. Name three things it will NOT do, and why. An agent with no
refusals has no design.*

## 4. Who is doing the thinking

| step | the agent does it | the human does it | why |
|---|---|---|---|
| | | | |

*If every row says "the agent", you have built a document generator.*

## 5. The states

*List them. Then draw the transitions.*

```
        ──▶          ──▶
   ▲      │
   └──────┘
```

**What can send work backwards:**
**What is unknown until it runs:**
**What stops it running forever:**

## 6. What it passes between steps

*Typed records, not prose. Name the fields.*

```python
class ...(BaseModel):
```

## 7. The evidence

**What documents it reads:**
**What each one lets it prove:**
**What it does when the evidence is not there:**

*"Says it cannot establish this" is the right answer. "Uses general knowledge"
is the wrong one.*

## 8. When it asks a human

**The question it asks:**
**Who answers:**
**What happens if nobody does:**

## 9. How you will know it works

*At least one check that is not you looking at the output and being pleased.*

## 10. What we are least sure about

*Three things. Be honest — this is the most useful section in the document and
the one a reviewer will read first.*

1.
2.
3.

## 11. Claims to verify

*Every factual assumption about a model, a library, an API or a limit — and how
you would check each in ten minutes. Some of these will be wrong.*

| claim | how to check | checked? |
|---|---|---|
| | | |
