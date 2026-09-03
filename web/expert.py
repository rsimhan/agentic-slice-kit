"""
The page a human expert answers on.

This is the other half of the human-in-the-loop mechanic. The agent suspends a
run and parks a question; a real person - an alum, a mentor, a domain expert -
opens this page and answers it; the run resumes with their answer recorded as a
distinct class of evidence, not blended in with what the model already thought.

Server-rendered, no JavaScript, no build step. An expert may be on a phone with
one bar of signal, and this has to work there.

Run it, then expose it:

    uvicorn web.expert:app --host 0.0.0.0 --port 8000
    cloudflared tunnel --url http://localhost:8000

The tunnel needs no account and prints a public URL. That URL is what you send
to the expert.
"""
from __future__ import annotations

import html
import os

from fastapi import Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi import FastAPI

from slice import callback
from slice.config import settings
from slice.store import Store

DB = os.environ.get("SLICE_DB", "run.db")
app = FastAPI(title="Expert callback")


def _store() -> Store:
    return Store(DB)


PAGE = """<!doctype html><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
<style>
:root{{color-scheme:light dark}}
body{{font:16px/1.6 system-ui,-apple-system,Segoe UI,sans-serif;max-width:38rem;
margin:0 auto;padding:2rem 1.2rem 4rem}}
h1{{font-size:1.35rem;margin:0 0 .3rem}}
.sub{{color:#6b7280;font-size:.9rem;margin:0 0 1.8rem}}
.card{{border:1px solid #d4d4d8;border-radius:8px;padding:1.1rem 1.2rem;margin:0 0 1rem}}
.q{{font-size:1.1rem;font-weight:600;margin:0 0 .8rem}}
.ctx{{background:rgba(127,127,127,.09);border-radius:6px;padding:.8rem 1rem;
font-size:.9rem;margin:0 0 1.2rem;white-space:pre-wrap;overflow-wrap:anywhere}}
.ctx b{{display:block;font-size:.72rem;letter-spacing:.09em;text-transform:uppercase;
color:#6b7280;margin-bottom:.35rem;font-weight:600}}
textarea{{width:100%;min-height:9rem;font:inherit;padding:.7rem;border:1px solid #a1a1aa;
border-radius:6px;background:transparent;color:inherit}}
button{{font:inherit;font-weight:600;padding:.6rem 1.4rem;margin-top:.8rem;
border:0;border-radius:6px;background:#0d5c5f;color:#fff;cursor:pointer}}
a{{color:#0d5c5f}} .empty{{color:#6b7280}}
.note{{font-size:.85rem;color:#6b7280;margin-top:1.2rem}}
</style>
{body}"""


def _page(title: str, body: str) -> HTMLResponse:
    return HTMLResponse(PAGE.format(title=html.escape(title), body=body))


@app.get("/", response_class=HTMLResponse)
def index():
    s = _store()
    callback.sweep(s)                     # expire anything past its deadline
    open_qs = callback.pending(s)
    if not open_qs:
        return _page("Nothing waiting",
                     "<h1>Nothing waiting</h1>"
                     "<p class='sub'>No agent is currently blocked on a human.</p>"
                     "<p class='empty'>This page will have something on it when a run "
                     "reaches a question its evidence cannot settle.</p>")
    items = "".join(
        f"<div class='card'><p class='q'>{html.escape(q.question)}</p>"
        f"<a href='/q/{q.id}'>Answer this &rarr;</a></div>" for q in open_qs)
    return _page("Questions waiting",
                 f"<h1>{len(open_qs)} question(s) waiting</h1>"
                 "<p class='sub'>An agent has paused because its evidence could not "
                 "settle these. Your answer resumes it.</p>" + items)


@app.get("/q/{qid}", response_class=HTMLResponse)
def show(qid: str):
    q = _store().get_question(qid)
    if q is None:
        return _page("Not found", "<h1>Not found</h1><p class='sub'>No such question.</p>")
    if q.is_answered:
        return _page("Already answered",
                     "<h1>Already answered</h1><p class='sub'>Someone got there first &mdash; "
                     "answers are recorded once and never overwritten.</p>"
                     f"<div class='ctx'><b>Their answer</b>{html.escape(q.answer or '')}</div>"
                     "<p><a href='/'>Back</a></p>")
    ctx = ""
    for k, v in (q.context or {}).items():
        if k == "resume_state":
            continue
        ctx += (f"<div class='ctx'><b>{html.escape(str(k).replace('_',' '))}</b>"
                f"{html.escape(str(v))}</div>")
    return _page("A question for you",
                 f"<h1>A question for you</h1>"
                 "<p class='sub'>Answer in your own words. Say plainly if you don't know "
                 "&mdash; that is a useful answer and it will be recorded as one.</p>"
                 f"<p class='q'>{html.escape(q.question)}</p>{ctx}"
                 f"<form method='post' action='/q/{q.id}'>"
                 "<textarea name='answer' autofocus placeholder='Your answer&hellip;'></textarea>"
                 "<input type='hidden' name='who' value='expert'>"
                 "<button type='submit'>Send</button></form>"
                 "<p class='note'>Recorded as expert evidence, kept separate from what the "
                 "model already believed.</p>")


@app.post("/q/{qid}")
def submit(qid: str, answer: str = Form(...), who: str = Form("expert")):
    text = (answer or "").strip()
    if not text:
        return RedirectResponse(f"/q/{qid}", status_code=303)
    callback.answer(_store(), qid, text, who=who)
    return RedirectResponse("/thanks", status_code=303)


@app.get("/thanks", response_class=HTMLResponse)
def thanks():
    return _page("Thank you",
                 "<h1>Thank you</h1><p class='sub'>The run has resumed with your answer.</p>"
                 "<p><a href='/'>Any others?</a></p>")
