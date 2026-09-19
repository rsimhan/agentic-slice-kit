from __future__ import annotations

import html
import os

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from slice.store import Store

DB = os.environ.get("SLICE_DB", "impactloop.db")
app = FastAPI(title="ImpactLoop")


def esc(value) -> str:
    return html.escape(str(value))


def get_latest(records, kind):
    matches = [r for r in records if r.kind == kind]
    return matches[-1].payload if matches else None


def page(content: str) -> HTMLResponse:
    return HTMLResponse(f"""
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ImpactLoop</title>
<style>
:root {{
  --bg: #090b12;
  --panel: #111521;
  --panel2: #171c2a;
  --line: #293248;
  --text: #f5f7fb;
  --muted: #929db2;
  --violet: #9146ff;
  --cyan: #00e5ff;
  --green: #35d07f;
  --amber: #ffc857;
  --red: #ff6b81;
}}

* {{ box-sizing: border-box; }}

body {{
  margin: 0;
  background:
    radial-gradient(circle at 80% 0%, rgba(145,70,255,.18), transparent 32rem),
    radial-gradient(circle at 0% 30%, rgba(0,229,255,.08), transparent 28rem),
    var(--bg);
  color: var(--text);
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}}

header {{
  border-bottom: 1px solid var(--line);
  background: rgba(9,11,18,.86);
  backdrop-filter: blur(14px);
  position: sticky;
  top: 0;
  z-index: 5;
}}

.nav {{
  max-width: 1180px;
  margin: auto;
  padding: 18px 24px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}}

.brand {{
  display: flex;
  align-items: center;
  gap: 12px;
  font-weight: 800;
  letter-spacing: -.03em;
  font-size: 21px;
}}

.logo {{
  width: 34px;
  height: 34px;
  border-radius: 11px;
  display: grid;
  place-items: center;
  color: #05070c;
  background: linear-gradient(135deg, var(--cyan), var(--violet));
  box-shadow: 0 0 28px rgba(0,229,255,.25);
}}

.nav-link {{
  color: var(--muted);
  text-decoration: none;
  font-size: 14px;
}}

main {{
  max-width: 1180px;
  margin: auto;
  padding: 44px 24px 80px;
}}

.hero {{
  display: flex;
  justify-content: space-between;
  gap: 30px;
  align-items: end;
  margin-bottom: 30px;
}}

.eyebrow {{
  color: var(--cyan);
  font-size: 12px;
  font-weight: 800;
  letter-spacing: .14em;
  text-transform: uppercase;
}}

h1 {{
  margin: 8px 0;
  font-size: clamp(34px, 6vw, 64px);
  line-height: .98;
  letter-spacing: -.065em;
}}

h2 {{
  margin: 0 0 16px;
  letter-spacing: -.03em;
}}

h3 {{
  margin: 8px 0;
}}

p {{
  color: var(--muted);
  line-height: 1.6;
}}

.hero-copy {{
  max-width: 700px;
}}

.hero-copy p {{
  font-size: 17px;
}}

.pill {{
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 8px 12px;
  border: 1px solid rgba(53,208,127,.35);
  border-radius: 999px;
  color: var(--green);
  background: rgba(53,208,127,.08);
  font-size: 13px;
  font-weight: 700;
  white-space: nowrap;
}}

.grid {{
  display: grid;
  grid-template-columns: repeat(12, 1fr);
  gap: 16px;
}}

.card {{
  background: linear-gradient(145deg, rgba(23,28,42,.96), rgba(13,17,27,.96));
  border: 1px solid var(--line);
  border-radius: 20px;
  padding: 22px;
  box-shadow: 0 16px 55px rgba(0,0,0,.18);
}}

.span-12 {{ grid-column: span 12; }}
.span-8 {{ grid-column: span 8; }}
.span-6 {{ grid-column: span 6; }}
.span-4 {{ grid-column: span 4; }}

.label {{
  color: var(--muted);
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: .1em;
  font-weight: 800;
}}

.value {{
  font-size: 18px;
  font-weight: 750;
  margin-top: 8px;
}}

.challenge {{
  color: #dce5f4;
  font-size: 20px;
  line-height: 1.4;
  font-weight: 650;
}}

.status {{
  display: inline-block;
  color: #07100b;
  background: var(--green);
  padding: 7px 11px;
  border-radius: 999px;
  font-weight: 850;
  font-size: 12px;
  text-transform: uppercase;
}}

.timeline {{
  display: flex;
  gap: 0;
  overflow-x: auto;
  padding: 5px 0 12px;
}}

.step {{
  min-width: 150px;
  position: relative;
  padding-right: 22px;
}}

.step:not(:last-child)::after {{
  content: "";
  position: absolute;
  top: 14px;
  left: 31px;
  width: calc(100% - 42px);
  height: 2px;
  background: var(--violet);
}}

.step-dot {{
  width: 29px;
  height: 29px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  background: var(--violet);
  color: white;
  font-size: 12px;
  font-weight: 900;
  position: relative;
  z-index: 1;
}}

.step-name {{
  color: #dbe4f5;
  font-size: 12px;
  margin-top: 10px;
  font-weight: 700;
}}

.agent {{
  color: var(--muted);
  font-size: 11px;
  margin-top: 3px;
}}

.person {{
  display: flex;
  gap: 13px;
  align-items: center;
  padding: 14px 0;
  border-bottom: 1px solid var(--line);
}}

.person:last-child {{
  border-bottom: 0;
}}

.avatar {{
  width: 42px;
  height: 42px;
  border-radius: 14px;
  display: grid;
  place-items: center;
  background: linear-gradient(135deg, rgba(0,229,255,.9), rgba(145,70,255,.9));
  color: #070910;
  font-weight: 900;
}}

.person-name {{
  font-weight: 800;
}}

.person-role {{
  color: var(--cyan);
  font-size: 13px;
  margin-top: 3px;
}}

.task {{
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 15px;
  padding: 14px 0;
  border-bottom: 1px solid var(--line);
}}

.task:last-child {{
  border-bottom: 0;
}}

.task-title {{
  font-weight: 700;
}}

.task-owner {{
  color: var(--muted);
  font-size: 13px;
  margin-top: 4px;
}}

.check {{
  color: var(--green);
  font-weight: 900;
}}

.warning {{
  border-color: rgba(255,200,87,.35);
  background: linear-gradient(145deg, rgba(60,46,20,.45), rgba(18,20,27,.96));
}}

.success {{
  border-color: rgba(53,208,127,.35);
}}

.quote {{
  color: #eaf3ff;
  font-size: 20px;
  line-height: 1.45;
  font-weight: 700;
}}

.evidence {{
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 15px;
}}

.file {{
  padding: 8px 10px;
  border: 1px solid var(--line);
  border-radius: 9px;
  color: #cbd6e8;
  font-size: 12px;
  background: rgba(255,255,255,.035);
}}

.button {{
  display: inline-block;
  margin-top: 18px;
  padding: 12px 16px;
  border-radius: 11px;
  color: #05070c;
  background: linear-gradient(135deg, var(--cyan), #79f3ff);
  text-decoration: none;
  font-weight: 850;
  font-size: 14px;
}}

.muted {{
  color: var(--muted);
}}

@media (max-width: 800px) {{
  main {{ padding: 28px 16px 60px; }}
  .nav {{ padding: 15px 16px; }}
  .hero {{ display: block; }}
  .hero .pill {{ margin-top: 16px; }}
  .span-8, .span-6, .span-4 {{ grid-column: span 12; }}
  .timeline {{ padding-bottom: 15px; }}
}}
</style>
</head>
<body>
<header>
  <div class="nav">
    <div class="brand"><div class="logo">↗</div>ImpactLoop</div>
    <a class="nav-link" href="/refresh">Refresh workspace ↻</a>
  </div>
</header>
<main>
{content}
</main>
</body>
</html>
""")


@app.get("/", response_class=HTMLResponse)
def dashboard():
    store = Store(DB)
    runs = [r for r in store.list_runs() if r["domain"] == "impactloop"]

    if not runs:
        return page("""
        <div class="hero">
          <div class="hero-copy">
            <div class="eyebrow">ImpactLoop workspace</div>
            <h1>No active project yet.</h1>
            <p>Start the ImpactLoop demo first, then refresh this page.</p>
          </div>
        </div>
        """)

    run = runs[0]
    records = store.replay(run["id"])
    challenge = get_latest(records, "input") or {}
    team = get_latest(records, "team_proposal") or {}
    plan = get_latest(records, "task_plan") or {}
    mentor = get_latest(records, "mentor_decision") or {}
    proof = get_latest(records, "proof_of_ability") or {}
    opportunity = get_latest(records, "opportunity_recommendation") or {}

    verifications = [r.payload for r in records if r.kind == "verification"]
    first_verification = verifications[0] if verifications else {}
    final_verification = verifications[-1] if verifications else {}

    people = ""
    for member in team.get("members", []):
        name = member.get("student_name", "Student")
        initials = "".join(x[0] for x in name.split())[:2].upper()
        people += f"""
        <div class="person">
          <div class="avatar">{esc(initials)}</div>
          <div>
            <div class="person-name">{esc(name)}</div>
            <div class="person-role">{esc(member.get("role", ""))}</div>
            <div class="muted">{esc(member.get("reason", ""))}</div>
          </div>
        </div>
        """

    tasks = ""
    owners = plan.get("owners", {})
    for task in plan.get("tasks", []):
        tasks += f"""
        <div class="task">
          <div>
            <div class="task-title">{esc(task)}</div>
            <div class="task-owner">Owner: {esc(owners.get(task, "Unassigned"))}</div>
          </div>
          <div class="check">✓</div>
        </div>
        """

    evidence_files = "".join(
        f'<span class="file">{esc(item)}</span>'
        for item in proof.get("evidence", [])
    )

    return page(f"""
    <div class="hero">
      <div class="hero-copy">
        <div class="eyebrow">Agentic campus opportunity platform</div>
        <h1>Turn campus problems into proven ability.</h1>
        <p>
          ImpactLoop helps students work on meaningful challenges,
          build real evidence, and discover their next opportunity.
        </p>
      </div>
      <div class="pill">● Workflow complete</div>
    </div>

    <div class="grid">
      <section class="card span-8">
        <div class="label">Active challenge</div>
        <div class="challenge">
          Students miss useful campus events and opportunities because
          information is scattered across WhatsApp groups, posters,
          club pages, and separate channels.
        </div>
        <p class="muted">Run ID: {esc(run["id"])}</p>
      </section>

      <section class="card span-4">
        <div class="label">Project status</div>
        <div class="value"><span class="status">{esc(run["state"])}</span></div>
        <p>One complete journey from challenge to verified student contribution.</p>
      </section>

      <section class="card span-12">
        <h2>Agent journey</h2>
        <div class="timeline">
          <div class="step"><div class="step-dot">1</div><div class="step-name">Intake</div><div class="agent">Validates challenge</div></div>
          <div class="step"><div class="step-dot">2</div><div class="step-name">Decomposer</div><div class="agent">Finds the work</div></div>
          <div class="step"><div class="step-dot">3</div><div class="step-name">Matcher</div><div class="agent">Builds the team</div></div>
          <div class="step"><div class="step-dot">4</div><div class="step-name">Orchestrator</div><div class="agent">Plans execution</div></div>
          <div class="step"><div class="step-dot">5</div><div class="step-name">Mentor</div><div class="agent">Adds human judgement</div></div>
          <div class="step"><div class="step-dot">6</div><div class="step-name">Verifier</div><div class="agent">Checks evidence</div></div>
          <div class="step"><div class="step-dot">7</div><div class="step-name">Connector</div><div class="agent">Finds next step</div></div>
        </div>
      </section>

      <section class="card span-6">
        <h2>Matched team</h2>
        {people or '<p class="muted">Team proposal not available yet.</p>'}
      </section>

      <section class="card span-6">
        <h2>Execution plan</h2>
        {tasks or '<p class="muted">Task plan not available yet.</p>'}
      </section>

      <section class="card span-6 warning">
        <div class="label">Human-in-the-loop</div>
        <h2>Mentor decision</h2>
        <p class="quote">
          {esc(mentor.get("decision", "The mentor decision is waiting."))}
        </p>
        <p>Recorded by: {esc(mentor.get("answered_by", "Mentor"))}</p>
        <a class="button" href="http://localhost:8000">Open mentor workspace</a>
      </section>

      <section class="card span-6 success">
        <div class="label">Verification</div>
        <h2>Evidence-backed result</h2>
        <p><span class="status">{esc(final_verification.get("status", "PENDING" ))}</span></p>
        <p>{esc(final_verification.get("reason", "Evidence review is in progress."))}</p>
        {f'<p class="muted">Earlier review: {esc(first_verification.get("status", ""))} — weak evidence was not accepted.</p>' if first_verification else ""}
      </section>

      <section class="card span-8">
        <div class="label">Proof-of-Ability</div>
        <h2>{esc(proof.get("capability", "Verified capability"))}</h2>
        <p class="quote">{esc(proof.get("contribution", "No verified contribution yet."))}</p>
        <div class="evidence">{evidence_files}</div>
      </section>

      <section class="card span-4">
        <div class="label">Next opportunity</div>
        <h2>{esc(opportunity.get("opportunity_title", "Recommendation pending"))}</h2>
        <p>{esc(opportunity.get("explanation", "The Connector will recommend a next step after verification."))}</p>
      </section>
    </div>
    """)


@app.get("/refresh")
def refresh():
    from fastapi.responses import RedirectResponse
    return RedirectResponse("/", status_code=303)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
