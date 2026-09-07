"""The golden case for demo/smoke, plus the two failure paths.

Runs entirely on canned replies: no key, no network, no tokens. If these pass,
the wiring is proven and anything that then goes wrong live is the model or the
prompt, not the machine.
"""
from __future__ import annotations

import sqlite3

import pytest

from demo.smoke.flow import MAX_REVISIONS, build_flow
from demo.smoke.stub import BLOCK, V1, Stub
from slice import runner
from slice.config import settings as load_settings
from slice.records import RunState
from slice.store import Store

IDEA = "AI can help students find internships. Students struggle and AI is growing fast."


def _run(tmp_path, call):
    store = Store(str(tmp_path / "t.db"))
    run_id = store.create_run("smoke")
    store.append(run_id, "input", {"text": IDEA}, produced_by="system")
    final = runner.advance(store, run_id, build_flow(call), load_settings())
    return store, run_id, final


# ------------------------------------------------------------- the golden run

def test_the_loop_completes(tmp_path):
    _, _, final = _run(tmp_path, Stub())
    assert final is RunState.COMPLETE


def test_work_goes_backwards(tmp_path):
    """The one that proves this is an agent and not a pipeline: a BLOCK sends
    the run back to DRAFTING and a SECOND draft is written."""
    store, run_id, _ = _run(tmp_path, Stub())
    drafts = store.history(run_id, "opportunity")
    assert len(drafts) == 2, "the gate did not send the draft back"
    assert drafts[0].payload != drafts[1].payload, "the revision changed nothing"


def test_the_revision_addresses_the_objection(tmp_path):
    """Going backwards is not enough - it has to go backwards *usefully*.

    Observed live: three revisions that repeated themselves, because the fix the
    gate wanted was not in the founder's paragraph. A loop that turns without
    changing the objected field is a loop that will exhaust its bound."""
    store, run_id, _ = _run(tmp_path, Stub())
    v1, v2 = [d.payload for d in store.history(run_id, "opportunity")]
    objected = {o["field"] for o in store.history(run_id, "verdict")[0].payload["objections"]}

    for field in objected:
        assert v1[field] != v2[field], f"{field} was objected to and did not change"
    untouched = set(v1) - objected
    assert any(v1[f] == v2[f] for f in untouched), (
        "every field changed; a revision should address the objections, "
        "not silently rewrite the record")


def test_both_verdicts_are_recorded_in_order(tmp_path):
    store, run_id, _ = _run(tmp_path, Stub())
    verdicts = [v.payload["status"] for v in store.history(run_id, "verdict")]
    assert verdicts == ["BLOCK", "PASS"]


def test_objections_are_specific_enough_to_act_on(tmp_path):
    """A schema cannot catch 'add more detail'. These are the cheapest proxies.

    The echo check earns its place: on a live run the gate degraded over rounds
    from explaining the fault to repeating the offending value back
    ("Students (the category named by the founder)."), which parses perfectly
    and tells the founder nothing. A length bar alone missed it by one
    character."""
    store, run_id, _ = _run(tmp_path, Stub())
    record = store.history(run_id, "opportunity")[0].payload
    first = store.history(run_id, "verdict")[0].payload

    assert first["objections"], "a BLOCK with no objections tells the founder nothing"
    for o in first["objections"]:
        assert o["field"] in record, f"objection names no real field: {o}"
        assert len(o["problem"]) > 60, f"objection too thin: {o}"
        # Quoting the offending text inside an explanation is good practice.
        # The failure is an objection that is ONLY the value. So: remove the
        # value and check that what remains still says something.
        value = record[o["field"]].lower().rstrip(".")
        remainder = o["problem"].lower().replace(value, "")
        assert len(remainder) > 45, (
            f"objection is mostly a restatement of the value, not a reason: {o}")


def test_everything_is_attributed(tmp_path):
    store, run_id, _ = _run(tmp_path, Stub())
    by = {v.kind: v.produced_by for v in store.replay(run_id)}
    assert by["opportunity"] == "agent:spot"
    assert by["verdict"] == "agent:gate", "no faculty member touches this"


def test_tokens_are_counted_against_the_run(tmp_path):
    store, run_id, _ = _run(tmp_path, Stub())
    assert store.counter(run_id, "tokens") > 0


# --------------------------------------------------------------- failure paths

class AlwaysBlocks(Stub):
    """A thesis that cannot be saved. Proves the domain bound, not the budget."""

    def __call__(self, **kw):
        if kw.get("step") == "gate":
            kw["budget"].record_tokens(10)
            return kw["schema"].model_validate_json(BLOCK)
        kw["budget"].record_tokens(10)
        return kw["schema"].model_validate_json(V1)


def test_three_blocks_stop_the_run_with_a_reason(tmp_path):
    store, run_id, final = _run(tmp_path, AlwaysBlocks())
    assert final is RunState.FAILED
    assert len(store.history(run_id, "verdict")) == MAX_REVISIONS
    failures = store.history(run_id, "failure")
    assert failures, "a run that fails without leaving a reason is the thing you cannot debug"
    assert failures[-1].payload["kind"] == "gate_exhausted"


def test_history_cannot_be_rewritten(tmp_path):
    """The append-only invariant, enforced by the database rather than by
    convention. This is the trigger in slice/store.py doing its job."""
    store, run_id, _ = _run(tmp_path, Stub())
    with pytest.raises(sqlite3.IntegrityError):
        store.db.execute(
            "UPDATE versions SET payload_json='{}' WHERE run_id=? AND seq=1", (run_id,))
    with pytest.raises(sqlite3.IntegrityError):
        store.db.execute("DELETE FROM versions WHERE run_id=?", (run_id,))
