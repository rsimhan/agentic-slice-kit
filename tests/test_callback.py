"""Human-in-the-loop as a state. The process may die; the run may not."""
from slice import callback
from slice.config import Settings
from slice.records import RunState
from slice.store import Store

S = Settings(api_key="x", model="m", fallback_model="f", escalation_model="e",
             max_tokens=100, max_tokens_per_run=1000, max_attempts_per_step=3,
             expert_timeout_minutes=45, langfuse_public="", langfuse_secret="",
             langfuse_host="")
S0 = Settings(**{**S.__dict__, "expert_timeout_minutes": 0})


def test_ask_suspends_and_answer_resumes(tmp_path):
    s = Store(tmp_path / "c.db")
    run = s.create_run("t")
    qid = callback.ask(s, run, "Will this commoditise within a year?",
                       {"assumption": 2, "resume_state": "probing"}, S)
    assert s.get_state(run) is RunState.AWAITING_EXPERT
    assert len(callback.pending(s, run)) == 1

    assert callback.answer(s, qid, "Yes, within twelve months.", who="raj") == run
    assert s.get_state(run) is RunState.PROBING
    assert callback.pending(s, run) == []

    rec = s.latest(run, "expert_answer")
    assert rec["source"] == "human_expert" and rec["who"] == "raj"


def test_answers_are_write_once(tmp_path):
    s = Store(tmp_path / "c.db")
    run = s.create_run("t")
    qid = callback.ask(s, run, "q?", {"resume_state": "probing"}, S)
    callback.answer(s, qid, "first")
    callback.answer(s, qid, "second")
    assert s.get_question(qid).answer == "first"


def test_timeout_records_unknown_rather_than_guessing(tmp_path):
    s = Store(tmp_path / "c.db")
    run = s.create_run("t")
    callback.ask(s, run, "nobody will answer this", {"resume_state": "probing"}, S0)
    expired = callback.sweep(s, run)

    assert len(expired) == 1
    assert s.get_state(run) is RunState.PROBING, "an absent expert must not strand the run"
    rec = s.latest(run, "expert_answer")
    assert rec["source"] == "unresolved_no_expert" and rec["answer"] is None


def test_unknown_question_is_not_an_error(tmp_path):
    s = Store(tmp_path / "c.db")
    assert callback.answer(s, "q_doesnotexist", "hello") is None
