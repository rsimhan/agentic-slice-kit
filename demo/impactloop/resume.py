from __future__ import annotations

import os

from demo.impactloop.flow import build_flow
from demo.impactloop.stub import Stub

from slice import runner
from slice.config import settings as load_settings
from slice.store import Store


DB_PATH = os.environ.get("SLICE_DB", "impactloop.db")

store = Store(DB_PATH)

runs = [
    run
    for run in store.list_runs()
    if run["domain"] == "impactloop"
    and run["state"] not in {"complete", "failed"}
]

if not runs:
    raise SystemExit("No unfinished ImpactLoop run found.")

run_id = runs[0]["id"]

final_state = runner.advance(
    store,
    run_id,
    build_flow(call=Stub()),
    load_settings(),
)

print("Resumed run:", run_id)
print("Final state:", final_state)

for record in store.replay(run_id):
    print(f"[{record.kind}] {record.produced_by}")
    print(record.payload)
    print("-" * 50)
