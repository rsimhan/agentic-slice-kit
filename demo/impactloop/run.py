from __future__ import annotations

import os

from demo.impactloop.flow import build_flow
from demo.impactloop.stub import Stub

from slice import runner
from slice.config import settings as load_settings
from slice.store import Store


DB_PATH = os.environ.get("SLICE_DB", "impactloop.db")


def print_run(store: Store, run_id: str) -> None:
    print("\n==============================")
    print("IMPACTLOOP DEMO")
    print("==============================")
    print("Challenge: Student Event Discovery")
    print("Run ID:", run_id)
    print("Current state:", store.get_state(run_id))
    print()

    for record in store.replay(run_id):
        print(f"[{record.kind}] {record.produced_by}")
        print(record.payload)
        print("-" * 50)


def main() -> None:
    store = Store(DB_PATH)

    run_id = store.create_run(
        "impactloop",
        {
            "description": "ImpactLoop MVP - Student Event Discovery",
        },
    )

    store.append(
        run_id,
        "input",
        {
            "text": (
                "Students miss useful campus events and opportunities "
                "because information is scattered across WhatsApp groups, "
                "posters, club pages, and separate channels."
            )
        },
        "user",
    )

    # Stub mode: no live model and no API credits.
    final_state = runner.advance(
        store,
        run_id,
        build_flow(call=Stub()),
        load_settings(),
    )

    print_run(store, run_id)

    if final_state.value == "awaiting_expert":
        print("\nA mentor question is waiting.")
        print("Open the mentor page at http://localhost:8000" )


if __name__ == "__main__":
    main()
