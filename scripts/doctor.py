#!/usr/bin/env python3
"""
doctor.py - Is this environment actually going to work?

Runs automatically when you attach to the Codespace. Run it yourself any time
something feels wrong, and BEFORE you start debugging your own code - most of
what looks like a broken agent at 3am is a broken environment.

Checks, in the order that things actually fail:
  1. .env exists and has a key
  2. the key works and has credit left
  3. the pinned models are reachable RIGHT NOW  (a provider 429 looks exactly
     like a bug in your prompt if you do not check)
  4. sqlite-vec loads
  5. the embedding model is baked into the image
"""
import json, os, sqlite3, sys, urllib.error, urllib.request

API = "https://openrouter.ai/api/v1"
OK, BAD, WARN = "  ok  ", " FAIL ", " warn "
fails = 0


def line(state, what, detail=""):
    global fails
    if state is BAD:
        fails += 1
    print(f"[{state}] {what}" + (f"\n         {detail}" if detail else ""))


def load_env(path=".env"):
    try:
        for ln in open(path):
            ln = ln.strip()
            if ln and not ln.startswith("#") and "=" in ln:
                k, v = ln.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip("\"'"))
        return True
    except FileNotFoundError:
        return False


def get(path, token, body=None, timeout=45):
    req = urllib.request.Request(
        API + path, data=json.dumps(body).encode() if body else None,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.load(r)
    except urllib.error.HTTPError as e:
        raw = e.read() or b"{}"
        try:    return e.code, json.loads(raw)
        except Exception: return e.code, {"raw": raw.decode(errors="replace")[:200]}
    except Exception as e:
        return 0, {"error": str(e)}


print("\nagentic-slice-kit doctor\n" + "-" * 60)

# 1 --------------------------------------------------------------------------
if not load_env():
    line(BAD, ".env not found", "Run:  cp .env.example .env   then paste your key.")
    sys.exit(1)
key = os.environ.get("OPENROUTER_API_KEY", "").strip()
if not key:
    line(BAD, "OPENROUTER_API_KEY is empty",
         "Paste the key from the registration desk into .env")
    sys.exit(1)
line(OK, ".env loaded")

# 2 --------------------------------------------------------------------------
st, me = get("/key", key)
if st != 200:
    line(BAD, f"key rejected (HTTP {st})", json.dumps(me)[:160])
else:
    d = me.get("data", {})
    used, lim = d.get("usage"), d.get("limit")
    if lim:
        left = float(lim) - float(used or 0)
        pct = 100 * left / float(lim)
        state = OK if pct > 25 else WARN
        line(state, f"key works - ${left:.3f} of ${float(lim):.2f} left ({pct:.0f}%)",
             "" if pct > 25 else "Running low. Lower SLICE_MAX_TOKENS or see the desk.")
    else:
        line(OK, f"key works - ${float(used or 0):.3f} used, no cap set")

# 3 --------------------------------------------------------------------------
for var in ("SLICE_MODEL", "SLICE_FALLBACK_MODEL", "SLICE_ESCALATION_MODEL"):
    mid = os.environ.get(var, "").strip()
    if not mid:
        line(WARN, f"{var} not set"); continue
    if ":batch" in mid or mid.startswith("~"):
        line(BAD, f"{var}={mid}",
             "batch variants are not callable here, and ~latest aliases drift. Pin a version.")
        continue
    st, body = get("/chat/completions", key,
                   {"model": mid, "max_tokens": 1, "messages": [{"role": "user", "content": "hi"}]})
    if st == 200:
        line(OK, f"{var}={mid} reachable")
    elif st == 429:
        line(WARN, f"{var}={mid} rate-limited right now (429)",
             "Not your code. Retry, or switch to the fallback for a while.")
    elif st == 402:
        line(BAD, f"{var}={mid} refused for credit (402)",
             "Your cap cannot cover this request. Lower SLICE_MAX_TOKENS or top up.")
    else:
        line(BAD, f"{var}={mid} unreachable (HTTP {st})", json.dumps(body)[:160])

# 4 --------------------------------------------------------------------------
try:
    import sqlite_vec
    db = sqlite3.connect(":memory:")
    db.enable_load_extension(True); sqlite_vec.load(db); db.enable_load_extension(False)
    line(OK, f"sqlite-vec {db.execute('select vec_version()').fetchone()[0]} loads")
except Exception as e:
    line(BAD, "sqlite-vec will not load", str(e)[:160])

# 5 --------------------------------------------------------------------------
cache = os.environ.get("FASTEMBED_CACHE_PATH", "/opt/fastembed")
if os.path.isdir(cache) and any(os.scandir(cache)):
    line(OK, f"embedding model present in the image ({cache})")
else:
    line(WARN, "embedding model not baked in",
         "First ingest will download ~80MB. Fine on good wifi, painful otherwise.")

print("-" * 60)
print(("all clear\n" if not fails else
       f"{fails} problem(s) above - fix these BEFORE debugging your agent\n"))
sys.exit(1 if fails else 0)
