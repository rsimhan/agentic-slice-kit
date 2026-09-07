#!/usr/bin/env python3
"""The smoke test. Spec: demo/SMOKE-SPEC.md

    python scripts/smoke.py run --stub        # no key, no network, no tokens
    python scripts/smoke.py run               # live, two model calls per cycle
    python scripts/smoke.py replay <run_id>

A green run proves eleven things at once: the environment builds, the key is
read, a model is reachable, structured output parses into a typed record, the
store creates and appends and reads back, the append-only trigger holds, the
runner dispatches handlers and moves state, the budget counts and survives -
and, the one that matters, work goes backwards.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from slice import runner
from slice.config import settings as load_settings
from slice.records import RunState
from slice.store import Store

from demo.smoke.flow import build_flow

DEFAULT_IDEA = (
    "AI can help students find better internships. Students struggle with "
    "placements and AI is growing fast."
)

DIM, BOLD, RESET = "\033[2m", "\033[1m", "\033[0m"
GREEN, RED, AMBER = "\033[32m", "\033[31m", "\033[33m"


def _c(s: str, colour: str) -> str:
    return s if not sys.stdout.isatty() else f"{colour}{s}{RESET}"


def cmd_run(args: argparse.Namespace) -> int:
    if args.stub:
        from demo.smoke.stub import Stub
        call = Stub()
        st = load_settings()
    else:
        from slice.llm import complete as call
        st = load_settings()
        if not st.api_key:
            print(_c("No OPENROUTER_API_KEY in .env.", RED),
                  "\nRun with --stub to prove the wiring without a key.")
            return 2

    store = Store(args.db)
    run_id = store.create_run("smoke")
    store.append(run_id, "input", {"text": args.idea}, produced_by="system")

    mode = "stub" if args.stub else st.model
    print(f"\n{_c('run', DIM)} {BOLD}{run_id}{RESET}   {_c(mode, DIM)}")
    print(f"{_c('idea', DIM)} {args.idea[:96]}")
    print()

    final = runner.advance(store, run_id, build_flow(call), st)

    seen = 0
    for v in store.replay(run_id):
        seen += 1
        if v.kind == "opportunity":
            who = v.payload["who_specifically"]
            print(f"  {_c('spot ', DIM)} opportunity v{_nth(store, run_id, 'opportunity', v.seq)}"
                  f"   {_c(who[:60], DIM)}")
        elif v.kind == "verdict":
            n = len(v.payload["objections"])
            tag = _c("BLOCK", AMBER) if v.payload["status"] == "BLOCK" else _c("PASS ", GREEN)
            extra = f"  x{n} objections" if n else ""
            print(f"  {_c('gate ', DIM)} {tag}{extra}")
            for o in v.payload["objections"]:
                print(f"         {_c('-', DIM)} {o['field']}: {o['problem'][:76]}")
        elif v.kind == "failure":
            print(f"  {_c('stop ', DIM)} {_c(v.payload['kind'], RED)} - {v.payload['detail']}")

    tokens = store.counter(run_id, "tokens")
    ok = final is RunState.COMPLETE
    print()
    print(f"  {_c('=>', DIM)} {_c(final.value.upper(), GREEN if ok else RED)}"
          f"   {seen} records · {int(tokens):,} tok")

    drafts = len(store.history(run_id, "opportunity"))
    if drafts > 1:
        print(f"  {_c('=>', DIM)} {_c('work went backwards', GREEN)}: "
              f"{drafts} drafts, so the gate sent one back. That is the agent.")
    else:
        print(f"  {_c('=>', DIM)} {_c('one draft only', AMBER)}: nothing was sent back. "
              "The loop is untested - see SMOKE-SPEC section 16.")

    print(f"\n  {_c('replay:', DIM)} python scripts/smoke.py replay {run_id}\n")
    return 0 if ok else 1


def _nth(store: Store, run_id: str, kind: str, seq: int) -> int:
    return sum(1 for v in store.history(run_id, kind) if v.seq <= seq)


def cmd_replay(args: argparse.Namespace) -> int:
    store = Store(args.db)
    for v in store.replay(args.run_id):
        import json
        body = json.dumps(v.payload, indent=2)
        print(f"\n{_c(f'#{v.seq}', DIM)} {BOLD}{v.kind}{RESET} {_c(v.produced_by, DIM)}")
        print("\n".join("    " + l for l in body.splitlines()))
    print()
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--db", default="run.db")
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run", help="draft, gate, revise, gate")
    r.add_argument("--stub", action="store_true", help="canned replies; no key needed")
    r.add_argument("--idea", default=DEFAULT_IDEA)
    r.set_defaults(fn=cmd_run)

    rp = sub.add_parser("replay", help="every record of a run, in order")
    rp.add_argument("run_id")
    rp.set_defaults(fn=cmd_replay)

    a = p.parse_args()
    return a.fn(a)


if __name__ == "__main__":
    raise SystemExit(main())
