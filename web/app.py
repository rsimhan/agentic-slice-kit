from __future__ import annotations

import hashlib
import hmac
import html
import json
import os
import secrets
import time
from typing import Any

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from demo.impactloop.flow import build_flow
from slice import callback, runner
from slice.config import settings
from slice.store import Store

DB = os.environ.get("SLICE_DB", "impactloop.db")
app = FastAPI(title="ImpactLoop")
SESSIONS: dict[str, dict[str, Any]] = {}

STAGES = [
    ("student_goal", "Understand"),
    ("project_brief", "Design"),
    ("team_proposal", "Match"),
    ("task_plan", "Plan"),
    ("mentor_decision", "Mentor"),
    ("verification", "Verify"),
    ("proof_of_ability", "Proof"),
    ("opportunity_recommendation", "Next opportunity"),
]


def db() -> Store:
    store = Store(DB)
    store.db.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'student',
            created_at REAL NOT NULL
        );

        CREATE TABLE IF NOT EXISTS problems (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            created_by INTEGER NOT NULL,
            run_id TEXT,
            created_at REAL NOT NULL
        );

        CREATE TABLE IF NOT EXISTS student_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE NOT NULL,
            skills TEXT NOT NULL DEFAULT '[]',
            interests TEXT NOT NULL DEFAULT '[]',
            availability TEXT NOT NULL DEFAULT '',
            preferred_role TEXT NOT NULL DEFAULT '',
            bio TEXT NOT NULL DEFAULT '',
            evidence_links TEXT NOT NULL DEFAULT '[]',
            created_at REAL NOT NULL
        );
        """
    )

    mentor = store.db.execute(
        "SELECT id FROM users WHERE email=?",
        ("mentor@impactloop.local",),
    ).fetchone()

    if mentor is None:
        store.db.execute(
            "INSERT INTO users(name,email,password_hash,role,created_at) VALUES(?,?,?,?,?)",
            (
                "ImpactLoop Mentor",
                "mentor@impactloop.local",
                hash_password("mentor123"),
                "mentor",
                time.time(),
            ),
        )

    return store


def hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 120_000)
    return salt.hex() + ":" + digest.hex()


def check_password(password: str, stored: str) -> bool:
    try:
        salt_hex, digest_hex = stored.split(":", 1)
        candidate = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode(),
            bytes.fromhex(salt_hex),
            120_000,
        )
        return hmac.compare_digest(candidate.hex(), digest_hex)
    except ValueError:
        return False


def esc(value: Any) -> str:
    return html.escape(str(value))


def current_user(request: Request) -> dict[str, Any] | None:
    token = request.cookies.get("impactloop_session")
    return SESSIONS.get(token) if token else None


def layout(body: str, user: dict[str, Any] | None = None) -> HTMLResponse:
    nav_links = ""
    if user:
        nav_links = (
            '<a href="/">Workspace</a>'
            + ('<a href="/profile">Profile</a>' if user["role"] == "student" else "")
            + ('<a href="/mentor">Mentor queue</a>' if user["role"] == "mentor" else "")
            + '<a href="/logout">Log out</a>'
        )
        identity = f'<span class="identity">{esc(user["name"])}</span>'
    else:
        identity = ""
        nav_links = '<a href="/login">Log in</a>'

    return HTMLResponse(
        f"""<!doctype html>
<html>
<head>
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ImpactLoop</title>
<style>
:root {{
  --bg:#0b0c0f;
  --panel:#131519;
  --panel-2:#181a20;
  --line:#2a2d35;
  --text:#f7f7f2;
  --muted:#9a9ca5;
  --lime:#c8ff4d;
  --purple:#9b7cff;
  --green:#65e6a2;
  --amber:#ffd166;
  --red:#ff7f88;
}}
*{{box-sizing:border-box}}
body{{margin:0;background:radial-gradient(circle at 80% 0%,#252033 0,transparent 34rem),var(--bg);color:var(--text);font:15px/1.5 Inter,system-ui,sans-serif}}
a{{color:inherit}}
nav{{position:sticky;top:0;z-index:5;display:flex;justify-content:space-between;align-items:center;padding:16px 5%;background:#0b0c0ff2;border-bottom:1px solid var(--line);backdrop-filter:blur(12px)}}
nav a{{text-decoration:none;color:#d8d9de;margin-left:18px;font-weight:700;font-size:14px}}
nav a:hover{{color:var(--lime)}}
.brand{{font-size:21px;font-weight:950;letter-spacing:-.04em}}
.identity{{color:var(--muted);font-size:13px;margin-right:12px}}
main{{max-width:1180px;margin:auto;padding:38px 22px 80px}}
h1{{font-size:clamp(34px,5vw,62px);line-height:1.02;letter-spacing:-.06em;margin:0 0 12px}}
h2{{font-size:24px;letter-spacing:-.03em;margin:0 0 8px}}
h3{{margin:0 0 7px}}
p{{margin:8px 0}}
.muted{{color:var(--muted)}}
.grid{{display:grid;grid-template-columns:repeat(12,minmax(0,1fr));gap:16px}}
.card{{grid-column:span 12;background:linear-gradient(145deg,var(--panel-2),var(--panel));border:1px solid var(--line);border-radius:22px;padding:24px}}
.half{{grid-column:span 6}}
.third{{grid-column:span 4}}
.hero{{padding:32px}}
.eyebrow{{display:inline-flex;align-items:center;gap:8px;border:1px solid #3a3d47;background:#17191e;border-radius:999px;padding:6px 10px;color:var(--lime);font-weight:850;font-size:11px;letter-spacing:.12em;text-transform:uppercase}}
.button{{display:inline-block;margin:14px 10px 0 0;padding:12px 16px;border-radius:12px;background:var(--lime);color:#101207;text-decoration:none;font-weight:900;border:0;cursor:pointer}}
.button.secondary{{background:#25272d;color:var(--text);border:1px solid #383b44}}
.button.purple{{background:var(--purple);color:#120c21}}
button{{font:inherit}}
.badge{{display:inline-flex;border-radius:999px;padding:6px 10px;background:#22252b;color:#d7d8de;font-size:11px;font-weight:850;text-transform:uppercase;letter-spacing:.08em}}
.badge.active{{background:#2f351f;color:var(--lime)}}
.badge.waiting{{background:#352d1e;color:var(--amber)}}
.badge.done{{background:#1f3429;color:var(--green)}}
.badge.fail{{background:#382124;color:var(--red)}}
.stepper{{display:grid;grid-template-columns:repeat(8,1fr);gap:8px;margin-top:22px}}
.step{{min-height:66px;padding:11px;border:1px solid var(--line);border-radius:14px;background:#15171c}}
.step strong{{display:block;font-size:11px;color:#7f828b;text-transform:uppercase;letter-spacing:.08em}}
.step span{{display:block;margin-top:7px;font-size:13px;font-weight:800}}
.step.done{{border-color:#34452b;background:#1b2117}}
.step.done span{{color:var(--lime)}}
.step.current{{border-color:#6f5bb5;background:#211b2e}}
.step.current span{{color:#d3c6ff}}
.callout{{display:flex;justify-content:space-between;gap:18px;align-items:flex-start;padding:18px;border:1px solid #4b3c1e;background:#1e1a12;border-radius:18px}}
.callout h3{{color:var(--amber)}}
.kpi-row{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-top:16px}}
.kpi{{padding:15px;border:1px solid var(--line);border-radius:14px;background:#111318}}
.kpi b{{display:block;font-size:22px}}
.kpi span{{font-size:12px;color:var(--muted)}}
.list{{display:grid;gap:10px;margin-top:14px}}
.list-item{{padding:14px;border:1px solid var(--line);border-radius:14px;background:#111318}}
.list-item strong{{display:block}}
.pill-row{{display:flex;gap:7px;flex-wrap:wrap;margin-top:10px}}
.pill{{padding:6px 9px;border-radius:999px;background:#202229;color:#dddfe5;font-size:12px}}
.task{{display:grid;grid-template-columns:32px 1fr auto;gap:12px;align-items:start;padding:14px 0;border-bottom:1px solid var(--line)}}
.task:last-child{{border-bottom:0}}
.num{{width:28px;height:28px;border-radius:50%;display:grid;place-items:center;background:#262931;color:var(--lime);font-weight:900}}
.owner{{color:#b8b9c1;font-size:12px}}
.proof{{border:1px solid #304b3b;background:#15231c;border-radius:16px;padding:16px}}
.recommendation{{border:1px solid #4a3d6c;background:#1d1830;border-radius:18px;padding:18px}}
form{{margin:0}}
label{{display:block;color:var(--muted);font-size:11px;text-transform:uppercase;letter-spacing:.1em;margin:14px 0 6px;font-weight:850}}
input,textarea{{width:100%;padding:13px;border:1px solid var(--line);border-radius:11px;background:#0f1115;color:var(--text);font:inherit}}
textarea{{min-height:120px;resize:vertical}}
.option-grid{{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:14px}}
.option{{width:100%;text-align:left;padding:16px;border:1px solid #3b3e47;border-radius:14px;background:#15171c;color:var(--text);cursor:pointer}}
.option:hover{{border-color:var(--lime);background:#1a1d16}}
.option b{{display:block;margin-bottom:5px}}
.empty{{padding:24px;border:1px dashed #3a3d45;border-radius:14px;color:var(--muted)}}
.problem{{padding:17px 0;border-bottom:1px solid var(--line)}}
.problem:last-child{{border-bottom:0}}
.small{{font-size:12px}}
@media(max-width:900px){{.stepper{{grid-template-columns:repeat(4,1fr)}}}}
@media(max-width:760px){{.half,.third{{grid-column:span 12}}.option-grid,.kpi-row{{grid-template-columns:1fr}}nav{{align-items:flex-start;gap:12px}}.identity{{display:none}}}}
</style>
</head>
<body>
<nav>
  <div class="brand">↗ ImpactLoop</div>
  <div>{identity}{nav_links}</div>
</nav>
<main>{body}</main>
</body>
</html>"""
    )


def require_user(request: Request) -> dict[str, Any] | RedirectResponse:
    user = current_user(request)
    return user or RedirectResponse("/login", status_code=303)


def latest_payload(records: list[Any], kind: str) -> dict[str, Any] | None:
    for record in reversed(records):
        if record.kind == kind:
            return record.payload
    return None


def stage_markup(records: list[Any], state: str) -> str:
    kinds = {record.kind for record in records}
    parts = []
    for kind, label in STAGES:
        done = kind in kinds
        current = (
            state == "awaiting_expert"
            and (
                (kind == "mentor_decision" and "mentor_decision" not in kinds)
                or (kind == "verification" and "verification" not in kinds)
            )
        )
        cls = "step done" if done else "step current" if current else "step"
        status = "Complete" if done else "In progress" if current else "Waiting"
        parts.append(
            f'<div class="{cls}"><strong>{status}</strong><span>{esc(label)}</span></div>'
        )
    return '<div class="stepper">' + "".join(parts) + "</div>"


def list_items(values: list[Any], empty: str = "None yet.") -> str:
    if not values:
        return f'<div class="empty">{esc(empty)}</div>'
    return '<div class="list">' + "".join(
        f'<div class="list-item">{esc(item)}</div>' for item in values
    ) + "</div>"


def render_project(project: dict[str, Any] | None) -> str:
    if not project:
        return ""
    tasks = project.get("tasks") or []
    capabilities = project.get("required_capabilities") or []
    return f"""
    <section class="card">
      <span class="eyebrow">Project brief</span>
      <h2>{esc(project.get("project_title", "Project"))}</h2>
      <p class="muted">{esc(project.get("objective", project.get("problem_to_solve", "")))}</p>
      <div class="kpi-row">
        <div class="kpi"><b>{len(tasks)}</b><span>Project tasks</span></div>
        <div class="kpi"><b>{len(capabilities)}</b><span>Core capabilities</span></div>
        <div class="kpi"><b>{len(project.get("deliverables") or [])}</b><span>Deliverables</span></div>
      </div>
      <div class="pill-row">{"".join(f'<span class="pill">{esc(x)}</span>' for x in capabilities)}</div>
    </section>
    """


def render_team(team: dict[str, Any] | None) -> str:
    if not team:
        return ""
    members = team.get("members") or []
    cards = []
    for member in members:
        caps = member.get("matched_capabilities") or []
        cards.append(
            f"""
            <div class="list-item">
              <strong>{esc(member.get("student_name", "Student"))}</strong>
              <div class="small">{esc(member.get("role", "Contributor"))}</div>
              <p class="muted small">{esc(member.get("reason", ""))}</p>
              <div class="pill-row">{"".join(f'<span class="pill">{esc(c)}</span>' for c in caps)}</div>
            </div>
            """
        )
    gaps = team.get("unresolved_gaps") or []
    return f"""
    <section class="card">
      <span class="eyebrow">Team proposal</span>
      <h2>People matched to the work</h2>
      <div class="list">{"".join(cards) or '<div class="empty">No team members matched yet.</div>'}</div>
      {('<p class="muted small"><b>Open gaps:</b> ' + esc(", ".join(gaps)) + '</p>') if gaps else ""}
    </section>
    """


def render_plan(plan: dict[str, Any] | None) -> str:
    if not plan:
        return ""
    tasks = plan.get("tasks") or []
    owners = plan.get("owners") or []
    conditions = plan.get("acceptance_conditions") or []
    rows = []
    for i, task in enumerate(tasks):
        owner = owners[i] if i < len(owners) else "Unassigned"
        condition = conditions[i] if i < len(conditions) else ""
        rows.append(
            f"""
            <div class="task">
              <div class="num">{i + 1}</div>
              <div><strong>{esc(task)}</strong><div class="owner">{esc(condition)}</div></div>
              <div class="owner">{esc(owner)}</div>
            </div>
            """
        )
    return f"""
    <section class="card">
      <span class="eyebrow">Execution plan</span>
      <h2>What happens next</h2>
      {"".join(rows) or '<div class="empty">No tasks yet.</div>'}
    </section>
    """


def render_mentor(mentor: dict[str, Any] | None) -> str:
    if not mentor:
        return ""
    return f"""
    <section class="card">
      <span class="eyebrow">Mentor decision</span>
      <h2>{esc(mentor.get("priority", "Decision recorded"))}</h2>
      <p class="muted">{esc(mentor.get("question", ""))}</p>
      <div class="list-item"><strong>Decision</strong>{esc(mentor.get("decision", ""))}</div>
    </section>
    """


def render_verification(verification: dict[str, Any] | None) -> str:
    if not verification:
        return ""
    passed = verification.get("status") == "PASS"
    missing = verification.get("missing_evidence") or []
    tone = "done" if passed else "waiting"
    label = "Verified" if passed else "Revision needed"
    return f"""
    <section class="card">
      <span class="eyebrow">Evidence check</span>
      <h2><span class="badge {tone}">{label}</span></h2>
      <p class="muted">{esc(verification.get("reason", ""))}</p>
      {list_items(missing, "No missing evidence.") if not passed else ""}
    </section>
    """


def render_proof(proof: dict[str, Any] | None) -> str:
    if not proof:
        return ""
    evidence = proof.get("evidence") or []
    return f"""
    <section class="card">
      <span class="eyebrow">Proof of ability</span>
      <div class="proof">
        <h2>{esc(proof.get("capability", "Verified capability"))}</h2>
        <p>{esc(proof.get("contribution", ""))}</p>
        <div class="pill-row">{"".join(f'<span class="pill">{esc(x)}</span>' for x in evidence)}</div>
      </div>
    </section>
    """


def render_opportunity(opportunity: dict[str, Any] | None) -> str:
    if not opportunity:
        return ""
    return f"""
    <section class="card">
      <span class="eyebrow">Next opportunity</span>
      <div class="recommendation">
        <h2>{esc(opportunity.get("opportunity_title", "Opportunity"))}</h2>
        <p>{esc(opportunity.get("explanation", ""))}</p>
        <p class="muted small"><b>Matched evidence:</b> {esc(", ".join(opportunity.get("matched_evidence") or []))}</p>
      </div>
    </section>
    """


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    user = current_user(request)
    if not user:
        return layout(
            """
            <section class="card hero">
              <span class="eyebrow">Agentic campus platform</span>
              <h1>Turn real campus problems into real proof of ability.</h1>
              <p class="muted">ImpactLoop takes a messy student problem, coordinates the work, brings in a human mentor at the right moment, verifies the evidence, and connects the result to a next opportunity.</p>
              <a class="button" href="/signup">Create student account</a>
              <a class="button secondary" href="/login">Sign in</a>
            </section>
            """
        )

    s = db()
    problems = s.db.execute(
        "SELECT * FROM problems WHERE created_by=? ORDER BY created_at DESC",
        (user["id"],),
    ).fetchall()

    rows = []
    for p in problems:
        state = s.get_state(p["run_id"]).value if p["run_id"] else "not_started"
        status_class = "done" if state == "complete" else "waiting" if state == "awaiting_expert" else "active"
        rows.append(
            f"""
            <div class="problem">
              <span class="badge {status_class}">{esc(state.replace("_", " "))}</span>
              <h3>{esc(p["title"])}</h3>
              <p class="muted">{esc(p["description"])}</p>
              <a class="button secondary" href="/run/{p["id"]}">Open project</a>
            </div>
            """
        )

    mentor_link = (
        '<a class="button purple" href="/mentor">Open mentor queue</a>'
        if user["role"] == "mentor"
        else ""
    )

    return layout(
        f"""
        <div class="grid">
          <section class="card hero half">
            <span class="eyebrow">Workspace</span>
            <h1>Make campus work count.</h1>
            <p class="muted">Create a problem. ImpactLoop turns it into structured work, verified evidence, and a next step.</p>
            <a class="button" href="/problems/new">Start a project</a>
            {mentor_link}
          </section>
          <section class="card half">
            <span class="eyebrow">Your projects</span>
            <h2>Active work</h2>
            {''.join(rows) or '<div class="empty">No projects yet. Start with a real campus problem.</div>'}
          </section>
        </div>
        """,
        user,
    )


@app.get("/signup", response_class=HTMLResponse)
def signup_page():
    return layout(
        """
        <section class="card half">
          <span class="eyebrow">Get started</span>
          <h2>Create student account</h2>
          <form method="post">
            <label>Name</label><input name="name" required>
            <label>Email</label><input type="email" name="email" required>
            <label>Password</label><input type="password" name="password" minlength="6" required>
            <button class="button" type="submit">Create account</button>
          </form>
        </section>
        """
    )


@app.post("/signup")
def signup(name: str = Form(...), email: str = Form(...), password: str = Form(...)):
    s = db()
    try:
        s.db.execute(
            "INSERT INTO users(name,email,password_hash,role,created_at) VALUES(?,?,?,?,?)",
            (
                name.strip(),
                email.lower().strip(),
                hash_password(password),
                "student",
                time.time(),
            ),
        )
    except Exception:
        return RedirectResponse("/signup?error=exists", status_code=303)
    return RedirectResponse("/login", status_code=303)


@app.get("/login", response_class=HTMLResponse)
def login_page():
    return layout(
        """
        <div class="grid">
          <section class="card half">
            <span class="eyebrow">Welcome back</span>
            <h2>Sign in</h2>
            <form method="post" action="/login">
              <label>Email</label><input type="email" name="email" required>
              <label>Password</label><input type="password" name="password" required>
              <button class="button" type="submit">Sign in</button>
            </form>
          </section>
          <section class="card half">
            <span class="eyebrow">Demo</span>
            <h2>Mentor access</h2>
            <p class="muted">For the hackathon demo:</p>
            <div class="list-item"><strong>Email</strong>mentor@impactloop.local</div>
            <div class="list-item"><strong>Password</strong>mentor123</div>
          </section>
        </div>
        """
    )


@app.post("/login")
def login(request: Request, email: str = Form(...), password: str = Form(...)):
    s = db()
    row = s.db.execute(
        "SELECT * FROM users WHERE email=?",
        (email.lower().strip(),),
    ).fetchone()

    if not row or not check_password(password, row["password_hash"]):
        return RedirectResponse("/login?error=invalid", status_code=303)

    token = secrets.token_urlsafe(32)
    SESSIONS[token] = dict(row)
    response = RedirectResponse("/", status_code=303)
    response.set_cookie("impactloop_session", token, httponly=True, samesite="lax")
    return response


@app.get("/mentor", response_class=HTMLResponse)
def mentor(request: Request):
    user = require_user(request)
    if isinstance(user, RedirectResponse) or user["role"] != "mentor":
        return RedirectResponse("/login", status_code=303)

    s = db()
    qs = callback.pending(s)
    cards = []

    for q in qs:
        options = q.context.get("options") or []
        if options:
            option_html = "".join(
                f'<button class="option" name="answer" value="{esc(option)}"><b>{esc(option)}</b><span class="small muted">Choose this direction for the project.</span></button>'
                for option in options
            )
            form = f'<form method="post" action="/mentor/{esc(q.id)}"><div class="option-grid">{option_html}</div></form>'
        else:
            form = f"""
            <form method="post" action="/mentor/{esc(q.id)}">
              <textarea name="answer" required placeholder="Enter your decision..."></textarea>
              <button class="button" type="submit">Submit decision</button>
            </form>
            """

        cards.append(
            f"""
            <section class="card">
              <span class="eyebrow">Decision needed</span>
              <h2>{esc(q.question)}</h2>
              <p class="muted">{esc(q.context.get("reason", ""))}</p>
              {form}
            </section>
            """
        )

    return layout(
        f"""
        <section>
          <span class="eyebrow">Mentor workspace</span>
          <h1>Human decisions, at the right moment.</h1>
          <p class="muted">ImpactLoop pauses when a decision needs context that an agent should not invent.</p>
        </section>
        {''.join(cards) or '<section class="card"><div class="empty">No decisions are waiting.</div></section>'}
        """,
        user,
    )


@app.post("/mentor/{qid}")
def mentor_answer(request: Request, qid: str, answer: str = Form(...)):
    user = require_user(request)
    if isinstance(user, RedirectResponse) or user["role"] != "mentor":
        return RedirectResponse("/login", status_code=303)

    callback.answer(db(), qid, answer.strip(), who=user["email"])
    return RedirectResponse("/mentor", status_code=303)


@app.get("/problems/new", response_class=HTMLResponse)
def new_problem_page(request: Request):
    user = require_user(request)
    if isinstance(user, RedirectResponse):
        return user

    return layout(
        """
        <section class="card half">
          <span class="eyebrow">New project</span>
          <h1>What should students solve?</h1>
          <p class="muted">Describe a real campus problem. ImpactLoop will turn it into a small project with roles, tasks, evidence, and a next opportunity.</p>
          <form method="post">
            <label>Challenge title</label>
            <input name="title" placeholder="Students miss useful campus events" required>
            <label>Problem description</label>
            <textarea name="description" placeholder="Describe the real problem and why it matters." required></textarea>
            <button class="button" type="submit">Launch ImpactLoop</button>
          </form>
        </section>
        """
        ,
        user,
    )


@app.post("/problems/new")
def new_problem(request: Request, title: str = Form(...), description: str = Form(...)):
    user = require_user(request)
    if isinstance(user, RedirectResponse):
        return user

    s = db()
    cur = s.db.execute(
        "INSERT INTO problems(title,description,created_by,created_at) VALUES(?,?,?,?)",
        (title.strip(), description.strip(), user["id"], time.time()),
    )
    problem_id = cur.lastrowid
    run_id = s.create_run(
        "impactloop",
        {
            "problem_id": problem_id,
            "title": title.strip(),
            "created_by": user["email"],
        },
    )
    s.db.execute("UPDATE problems SET run_id=? WHERE id=?", (run_id, problem_id))

    profile_row = s.db.execute(
        "SELECT * FROM student_profiles WHERE user_id=?",
        (user["id"],),
    ).fetchone()

    def profile_dict(row):
        if not row:
            return {}
        return {
            "student_name": user["name"],
            "skills": json.loads(row["skills"]),
            "interests": json.loads(row["interests"]),
            "availability": row["availability"],
            "preferred_role": row["preferred_role"],
            "bio": row["bio"],
            "evidence_links": json.loads(row["evidence_links"]),
        }

    candidates = []
    rows = s.db.execute(
        """SELECT u.name, u.email, p.skills, p.interests, p.availability,
                  p.preferred_role, p.bio, p.evidence_links
           FROM users u
           JOIN student_profiles p ON p.user_id=u.id
           WHERE u.role='student' AND u.id != ?
           ORDER BY p.created_at DESC
           LIMIT 20""",
        (user["id"],),
    ).fetchall()

    for row in rows:
        candidates.append(
            {
                "student_name": row["name"],
                "email": row["email"],
                "skills": json.loads(row["skills"]),
                "interests": json.loads(row["interests"]),
                "availability": row["availability"],
                "preferred_role": row["preferred_role"],
                "bio": row["bio"],
                "evidence_links": json.loads(row["evidence_links"]),
            }
        )

    s.append(
        run_id,
        "input",
        {
            "title": title.strip(),
            "text": description.strip(),
            "student_profile": profile_dict(profile_row),
            "candidate_profiles": candidates,
        },
        produced_by=f"user:{user['email']}",
    )

    runner.advance(s, run_id, build_flow(), settings())
    return RedirectResponse(f"/run/{problem_id}", status_code=303)


@app.get("/run/{problem_id}", response_class=HTMLResponse)
def run_page(request: Request, problem_id: int):
    user = require_user(request)
    if isinstance(user, RedirectResponse):
        return user

    s = db()
    problem = s.db.execute(
        "SELECT * FROM problems WHERE id=?",
        (problem_id,),
    ).fetchone()
    if not problem:
        return RedirectResponse("/", status_code=303)

    records = s.replay(problem["run_id"])
    state = s.get_state(problem["run_id"]).value
    pending = callback.pending(s, problem["run_id"])
    mentor_question = next((q for q in pending if q.context.get("kind") == "mentor"), None)
    evidence_question = next((q for q in pending if q.context.get("kind") == "evidence"), None)

    project = latest_payload(records, "project_brief")
    team = latest_payload(records, "team_proposal")
    plan = latest_payload(records, "task_plan")
    mentor_decision = latest_payload(records, "mentor_decision")
    verification = latest_payload(records, "verification")
    proof = latest_payload(records, "proof_of_ability")
    opportunity = latest_payload(records, "opportunity_recommendation")

    hero_status = {
        "awaiting_expert": ("waiting", "Waiting for a mentor"),
        "complete": ("done", "Project complete"),
        "failed": ("fail", "Needs attention"),
    }.get(state, ("active", "Working"))

    mentor_box = ""
    if mentor_question:
        mentor_box = f"""
        <section class="card callout">
          <div>
            <h3>Mentor decision pending</h3>
            <h2>The project needs a human call.</h2>
            <p class="muted">{esc(mentor_question.question)}</p>
            <p class="small">{esc(mentor_question.context.get("reason", ""))}</p>
          </div>
          <a class="button purple" href="/mentor">Open mentor queue</a>
        </section>
        """

    evidence_box = ""
    if evidence_question:
        evidence_box = f"""
        <section class="card">
          <span class="eyebrow">Evidence required</span>
          <h2>Show what you actually completed.</h2>
          <p class="muted">{esc(evidence_question.question)}</p>
          <form method="post" action="/run/{problem_id}/evidence">
            <textarea name="evidence" required placeholder="Add links, file names, screenshots, notes, prototype URLs, or other concrete evidence."></textarea>
            <button class="button" type="submit">Submit evidence</button>
          </form>
        </section>
        """

    return layout(
        f"""
        <div class="grid">
          <section class="card hero">
            <span class="eyebrow">Live project</span>
            <h1>{esc(problem["title"])}</h1>
            <p class="muted">{esc(problem["description"])}</p>
            <p><span class="badge {hero_status[0]}">{esc(hero_status[1])}</span></p>
            {stage_markup(records, state)}
          </section>

          {mentor_box}
          {evidence_box}
          {render_project(project)}
          {render_team(team)}
          {render_plan(plan)}
          {render_mentor(mentor_decision)}
          {render_verification(verification)}
          {render_proof(proof)}
          {render_opportunity(opportunity)}

          <section class="card">
            <a class="button secondary" href="/">Back to workspace</a>
          </section>
        </div>
        """,
        user,
    )


@app.post("/run/{problem_id}/evidence")
def submit_evidence(
    request: Request,
    problem_id: int,
    evidence: str = Form(...),
):
    user = require_user(request)
    if isinstance(user, RedirectResponse):
        return user

    s = db()
    problem = s.db.execute(
        "SELECT * FROM problems WHERE id=?",
        (problem_id,),
    ).fetchone()

    if not problem:
        return RedirectResponse("/", status_code=303)

    questions = callback.pending(s, problem["run_id"])
    question = next(
        (q for q in questions if q.context.get("kind") == "evidence"),
        None,
    )

    if question:
        callback.answer(
            s,
            question.id,
            evidence.strip(),
            who=user["email"],
        )
        s.append(
            problem["run_id"],
            "evidence_submission",
            {
                "submitted_by": user["email"],
                "evidence": evidence.strip(),
            },
            produced_by=f"user:{user['email']}",
        )
        runner.advance(s, problem["run_id"], build_flow(), settings())

    return RedirectResponse(f"/run/{problem_id}", status_code=303)


@app.get("/profile", response_class=HTMLResponse)
def profile_page(request: Request):
    user = require_user(request)
    if isinstance(user, RedirectResponse):
        return user

    store = db()
    row = store.db.execute(
        "SELECT * FROM student_profiles WHERE user_id=?",
        (user["id"],),
    ).fetchone()

    profile = dict(row) if row else {
        "skills": "[]",
        "interests": "[]",
        "availability": "",
        "preferred_role": "",
        "bio": "",
        "evidence_links": "[]",
    }

    skills = ", ".join(json.loads(profile["skills"]))
    interests = ", ".join(json.loads(profile["interests"]))
    links = "\n".join(json.loads(profile["evidence_links"]))

    return layout(
        f"""
        <section class="card half">
          <span class="eyebrow">Student profile</span>
          <h1>Make your abilities discoverable.</h1>
          <p class="muted">ImpactLoop uses this information to match you to meaningful campus work.</p>
          <form method="post" action="/profile">
            <label>Skills</label>
            <input name="skills" value="{esc(skills)}" placeholder="Python, Figma, research, communication" required>
            <label>Interests</label>
            <input name="interests" value="{esc(interests)}" placeholder="student experience, sustainability, design">
            <label>Weekly availability</label>
            <input name="availability" value="{esc(profile["availability"])}" placeholder="6 hours per week" required>
            <label>Preferred role</label>
            <input name="preferred_role" value="{esc(profile["preferred_role"])}" placeholder="UX designer, researcher, data organiser">
            <label>Short bio</label>
            <textarea name="bio" required>{esc(profile["bio"])}</textarea>
            <label>Evidence or project links</label>
            <textarea name="evidence_links" placeholder="One link or project name per line">{esc(links)}</textarea>
            <button class="button" type="submit">Save profile</button>
          </form>
        </section>
        """,
        user,
    )


@app.post("/profile")
def save_profile(
    request: Request,
    skills: str = Form(...),
    interests: str = Form(""),
    availability: str = Form(...),
    preferred_role: str = Form(""),
    bio: str = Form(""),
    evidence_links: str = Form(""),
):
    user = require_user(request)
    if isinstance(user, RedirectResponse):
        return user

    store = db()

    def split_lines(value: str) -> list[str]:
        return [
            item.strip()
            for item in value.replace(",", "\n").splitlines()
            if item.strip()
        ]

    values = (
        user["id"],
        json.dumps(split_lines(skills)),
        json.dumps(split_lines(interests)),
        availability.strip(),
        preferred_role.strip(),
        bio.strip(),
        json.dumps(split_lines(evidence_links)),
        time.time(),
    )

    store.db.execute(
        """
        INSERT INTO student_profiles
        (user_id, skills, interests, availability, preferred_role, bio,
         evidence_links, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
          skills=excluded.skills,
          interests=excluded.interests,
          availability=excluded.availability,
          preferred_role=excluded.preferred_role,
          bio=excluded.bio,
          evidence_links=excluded.evidence_links
        """,
        values,
    )

    return RedirectResponse("/", status_code=303)


@app.get("/logout")
def logout(request: Request):
    token = request.cookies.get("impactloop_session")
    if token:
        SESSIONS.pop(token, None)
    response = RedirectResponse("/", status_code=303)
    response.delete_cookie("impactloop_session")
    return response


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
