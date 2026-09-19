from demo.impactloop.flow import build_flow, rank_opportunities
from demo.impactloop.stub import Stub
from slice import callback, runner
from slice.config import settings
from slice.records import RunState
from slice.store import Store


def test_impactloop_completes_with_real_human_checkpoints(tmp_path):
    store = Store(tmp_path / "impactloop.db")
    run_id = store.create_run("impactloop")

    store.append(
        run_id,
        "input",
        {
            "title": "Campus opportunity discovery",
            "text": "Students struggle to discover relevant campus opportunities.",
            "student_profile": {
                "student_name": "Test Student",
                "skills": ["Research", "Communication"],
                "interests": ["student experience"],
                "availability": "6 hours/week",
                "preferred_role": "Researcher",
                "bio": "Student interested in improving campus experience.",
                "evidence_links": [],
            },
            "candidate_profiles": [],
        },
        produced_by="test",
    )

    stub = Stub()

    state = runner.advance(
        store,
        run_id,
        build_flow(call=stub),
        settings(),
    )
    assert state is RunState.AWAITING_EXPERT

    mentor_question = callback.pending(store, run_id)[0]
    callback.answer(
        store,
        mentor_question.id,
        "Prioritise one unified student experience.",
        who="mentor@test",
    )

    state = runner.advance(store, run_id, build_flow(call=stub), settings())
    assert state is RunState.AWAITING_EXPERT

    evidence_question = next(
        q for q in callback.pending(store, run_id)
        if q.context.get("kind") == "evidence"
    )
    callback.answer(
        store,
        evidence_question.id,
        "interview_notes.md; prototype.png; walkthrough_findings.md",
        who="student@test",
    )
    store.append(
        run_id,
        "evidence_submission",
        {
            "submitted_by": "student@test",
            "evidence": "interview_notes.md; prototype.png; walkthrough_findings.md",
        },
        produced_by="student@test",
    )

    state = runner.advance(store, run_id, build_flow(call=stub), settings())

    assert state is RunState.COMPLETE
    assert store.latest(run_id, "verification")["status"] == "PASS"
    assert store.latest(run_id, "proof_of_ability")["verification_status"] == "verified"
    assert store.latest(run_id, "opportunity_recommendation") is not None


def test_opportunity_retrieval_returns_catalog_records():
    from demo.impactloop.schema import ProofOfAbility

    proof = ProofOfAbility(
        capability="User Research and Opportunity Discovery",
        contribution="Interviewed students and designed a campus discovery flow.",
        evidence=["interview_notes.md", "prototype.png"],
        verification_status="verified",
    )

    candidates = rank_opportunities(proof)

    assert candidates
    assert all("title" in item for item in candidates)
    assert all("required_capabilities" in item for item in candidates)
