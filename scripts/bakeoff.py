#!/usr/bin/env python3
"""
bakeoff.py - Which cheap model can actually hold a gate loop together?

Price and context you can read off a table. Instruction adherence under a
structured-output contract you cannot - so measure it. Each candidate gets the
same deliberately weak thesis and must return a Verdict as strict JSON.

Scored on what the architecture actually needs:
  parses     - valid JSON at all
  schema     - required fields, right types
  blocks     - correctly BLOCKS a thesis with no falsifiable claim
  specific   - objections that name a defect, not "needs more detail"

~20 calls. A few cents. Twenty minutes of your time buys a decision you would
otherwise make on vibes.

  export OPENROUTER_API_KEY='sk-or-v1-...'      # inference key, not management
  python3 scripts/bakeoff.py
"""
import json, os, statistics, sys, time, urllib.error, urllib.request

def load_env(path=".env"):
    """Read .env if present. The kit is configured by file, not by exported vars -
    one less thing to get wrong at 3am, and it survives a new terminal tab."""
    try:
        for line in open(path):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip("\"'"))
    except FileNotFoundError:
        pass


load_env()
KEY = os.environ.get("OPENROUTER_API_KEY", "").strip()
if not KEY:
    sys.exit("No OPENROUTER_API_KEY. Copy .env.example to .env and put your "
             "inference key (sk-or-v1-...) on the OPENROUTER_API_KEY line.")

CANDIDATES = [
    "qwen/qwen3.7-flash",
    "openai/gpt-oss-120b",
    "deepseek/deepseek-v4-flash-0731",
    "z-ai/glm-5.3-flash",
    "mistralai/mistral-small-3.2-24b-instruct",
    "inclusionai/ling-3.0-flash",
]
TRIALS = 3

SYSTEM = """You are a faculty reviewer gating a venture thesis before it proceeds to validation.

Return ONLY a JSON object, no prose, no markdown fence:
{"status": "PASS" | "BLOCK", "objections": [{"field": str, "problem": str}]}

BLOCK if any of these hold:
  - the customer is a category ("students", "SMEs") rather than a specific person
  - there is no falsifiable claim - nothing that could be shown false by evidence
  - the "why now" is a trend, not a change that just made this newly possible

Each objection must name the specific defect in THIS thesis. Never write generic
advice like "add more detail". If status is PASS, objections must be []."""

WEAK = """Problem: Students struggle to manage their time.
Who: University students.
Today: They use various apps and notebooks.
Why now: AI is advancing rapidly.
Value: An AI assistant that helps students be more productive."""


def chat(model, timeout=90):
    body = {"model": model, "max_tokens": 700, "temperature": 0,
            "messages": [{"role": "system", "content": SYSTEM},
                         {"role": "user", "content": WEAK}]}
    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions", data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            d = json.load(r)
        return (d["choices"][0]["message"]["content"], time.time() - t0,
                (d.get("usage") or {}).get("total_tokens", 0), None)
    except urllib.error.HTTPError as e:
        return None, time.time() - t0, 0, f"HTTP {e.code} {(e.read() or b'')[:120].decode(errors='replace')}"
    except Exception as e:
        return None, time.time() - t0, 0, str(e)


def score(text):
    """Four independent checks. Each is pass/fail; no partial credit, no vibes."""
    t = (text or "").strip()
    if t.startswith("```"):                       # tolerate a fence, note it later
        t = t.split("```")[1].removeprefix("json").strip()
    try:
        v = json.loads(t)
    except Exception:
        return dict(parses=0, schema=0, blocks=0, specific=0)
    parses = 1
    schema = int(isinstance(v, dict) and v.get("status") in ("PASS", "BLOCK")
                 and isinstance(v.get("objections"), list)
                 and all(isinstance(o, dict) and "field" in o and "problem" in o
                         for o in v.get("objections", [])))
    blocks = int(schema and v["status"] == "BLOCK" and len(v["objections"]) >= 2)
    generic = ("more detail", "be more specific", "add detail", "unclear", "needs work")
    specific = int(blocks and all(
        len(o["problem"]) > 40 and not any(g in o["problem"].lower() for g in generic)
        for o in v["objections"]))
    return dict(parses=parses, schema=schema, blocks=blocks, specific=specific)


print(f"{len(CANDIDATES)} candidates x {TRIALS} trials on the same weak thesis.\n")
print(f"{'model':<44}{'parse':>6}{'schema':>7}{'block':>6}{'spec':>6}{'p50 s':>7}{'tok':>7}")
print("-" * 83)

results = []
for m in CANDIDATES:
    agg, lat, toks, err = [], [], [], None
    for _ in range(TRIALS):
        text, dt, tk, e = chat(m)
        if e:
            err = e; break
        agg.append(score(text)); lat.append(dt); toks.append(tk)
    if err:
        print(f"{m:<44}  {err[:34]}")
        continue
    tot = {k: sum(a[k] for a in agg) for k in agg[0]}
    p50 = statistics.median(lat)
    print(f"{m:<44}{tot['parses']:>4}/{TRIALS}{tot['schema']:>5}/{TRIALS}"
          f"{tot['blocks']:>4}/{TRIALS}{tot['specific']:>4}/{TRIALS}{p50:>7.1f}"
          f"{int(statistics.mean(toks)):>7}")
    results.append((tot["specific"], tot["blocks"], tot["schema"], -p50, m))

if results:
    results.sort(reverse=True)
    print("\n" + "=" * 83)
    print(f"WINNER on behaviour: {results[0][-1]}")
    print("Set SLICE_MODEL to this in .env.example unless price moves you elsewhere.")
    print("=" * 83)
