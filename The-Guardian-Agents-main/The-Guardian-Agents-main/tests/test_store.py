"""
Tests for the foundation. If these fail, nothing above them can be trusted.

Invariant 5 from the architecture doc lives here: a suspended run resumes to
the state it left. It is the property most teams claim and fewest have.
"""
import time

import pytest

from slice.records import RunState
from slice.store import Store


@pytest.fixture()
def store(tmp_path):
    s = Store(tmp_path / "t.db")
    yield s
    s.close()


def test_run_lifecycle(store):
    run = store.create_run("demo", {"idea": "a thing"})
    assert store.get_state(run) is RunState.DRAFTING
    assert store.meta(run)["idea"] == "a thing"
    store.set_state(run, RunState.PROBING)
    assert store.get_state(run) is RunState.PROBING


def test_versions_accumulate_and_latest_wins(store):
    run = store.create_run("demo")
    store.append(run, "thesis", {"v": 1, "who": "students"}, produced_by="spot")
    store.append(run, "verdict", {"status": "block"}, produced_by="faculty")
    store.append(run, "thesis", {"v": 2, "who": "second-year CSE students"}, produced_by="spot")

    assert store.latest(run, "thesis")["v"] == 2
    assert store.latest(run, "verdict")["status"] == "block"
    assert store.latest(run, "evidence") is None

    hist = store.history(run, "thesis")
    assert [h.payload["v"] for h in hist] == [1, 2], "history is oldest-first"
    assert hist[0].produced_by == "spot"


def test_replay_is_the_whole_run_in_order(store):
    run = store.create_run("demo")
    for i in range(5):
        store.append(run, "thesis" if i % 2 == 0 else "verdict", {"i": i}, produced_by="x")
    seqs = [v.seq for v in store.replay(run)]
    assert seqs == sorted(seqs) and len(seqs) == 5


def test_history_is_immutable(store):
    """The append-only rule is enforced by the database, not by good manners."""
    run = store.create_run("demo")
    store.append(run, "thesis", {"v": 1}, produced_by="spot")

    with pytest.raises(Exception, match="append-only"):
        store.db.execute("UPDATE versions SET payload_json='{}' WHERE run_id=?", (run,))
    with pytest.raises(Exception, match="append-only"):
        store.db.execute("DELETE FROM versions WHERE run_id=?", (run,))

    assert store.latest(run, "thesis")["v"] == 1


def test_counters_survive_reopen(tmp_path):
    """Attempt counts must outlive the process, or resume silently loses the fence."""
    path = tmp_path / "t.db"
    s1 = Store(path)
    run = s1.create_run("demo")
    s1.bump(run, "gate_attempts")
    s1.bump(run, "gate_attempts")
    s1.bump(run, "tokens", 1234)
    s1.close()

    s2 = Store(path)
    assert s2.counter(run, "gate_attempts") == 2
    assert s2.counter(run, "tokens") == 1234
    s2.close()


def test_suspended_run_resumes_to_the_state_it_left(tmp_path):
    """Invariant 5. The process dies; the run does not."""
    path = tmp_path / "t.db"
    s1 = Store(path)
    run = s1.create_run("demo")
    s1.append(run, "thesis", {"v": 3}, produced_by="spot")
    qid = s1.ask(run, "Will frontier models commoditise this?", {"assumption": 2}, timeout_minutes=45)
    s1.set_state(run, RunState.AWAITING_EXPERT)
    s1.close()                                    # process exits here

    s2 = Store(path)                              # ... and later comes back
    assert s2.get_state(run) is RunState.AWAITING_EXPERT
    open_qs = s2.open_questions(run)
    assert len(open_qs) == 1 and open_qs[0].id == qid
    assert s2.latest(run, "thesis")["v"] == 3

    s2.answer(qid, "Yes - within twelve months.")
    s2.set_state(run, RunState.PROBING)
    assert s2.open_questions(run) == []
    assert s2.get_question(qid).answer.startswith("Yes")
    s2.close()


def test_question_expiry(store):
    run = store.create_run("demo")
    qid = store.ask(run, "q?", {}, timeout_minutes=0)
    time.sleep(0.01)
    q = store.get_question(qid)
    assert q.is_expired and not q.is_answered

    store.answer(qid, "late but here")
    assert not store.get_question(qid).is_expired


def test_answer_does_not_overwrite(store):
    run = store.create_run("demo")
    qid = store.ask(run, "q?", {}, timeout_minutes=10)
    store.answer(qid, "first")
    store.answer(qid, "second")
    assert store.get_question(qid).answer == "first", "answers are write-once"
