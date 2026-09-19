# test_contracts.py
# Basic contract validation tests

import pytest
from contracts import (
    RunState, MistakeClassification, TrendLabel, ReviewStatus,
    ConceptNode, Attempt, NoteVersion, TeacherNoteVersion,
    SubmitAttemptRequest, SubmitAttemptResponse,
    TeacherStudentNotesResponse, StudentNotesResponse,
    can_transition, can_revise, VALID_TRANSITIONS,
    MAX_REVISIONS_PER_CYCLE, TAG_CONFIRMATION_TIMEOUT_SECONDS,
)


class TestEnums:
    def test_run_state_values(self):
        assert RunState.TEACHER_SETUP.value == "teacher_setup"
        assert RunState.COMPLETE.value == "complete"
        assert RunState.TEST_GENERATING.value == "test_generating"
        assert RunState.FAILED.value == "failed"
        assert len(list(RunState)) == 14

    def test_mistake_classification_values(self):
        assert MistakeClassification.CONCEPTUAL_GAP.value == "conceptual_gap"
        assert MistakeClassification.CARELESS_MISTAKE.value == "careless_mistake"

    def test_trend_label_values(self):
        assert TrendLabel.NEW.value == "new"
        assert TrendLabel.IMPROVING.value == "improving"

    def test_review_status_values(self):
        assert ReviewStatus.PASSED.value == "passed"
        assert ReviewStatus.FAILED.value == "failed"
        assert ReviewStatus.REVISION_LIMIT_REACHED.value == "revision_limit_reached"


class TestStateMachine:
    def test_valid_transitions_count(self):
        # 14 states with transitions (including TEST_GENERATING and FAILED)
        assert len(VALID_TRANSITIONS) == 14

    def test_teacher_rejection_transition(self):
        # NEW: Teacher can reject concepts, returning to TEACHER_SETUP
        assert can_transition(RunState.TAG_CONFIRMATION, RunState.TEACHER_SETUP)

    def test_test_generation_transitions(self):
        # Test generation flow
        assert can_transition(RunState.TAG_CONFIRMATION, RunState.TEST_GENERATING)
        assert can_transition(RunState.TEST_GENERATING, RunState.TEST_READY)
        assert can_transition(RunState.TEST_GENERATING, RunState.TEST_GENERATING)  # retry
        assert can_transition(RunState.TEST_GENERATING, RunState.FAILED)  # permanent failure

    def test_standard_flow(self):
        assert can_transition(RunState.TEACHER_SETUP, RunState.TAG_CONFIRMATION)
        assert can_transition(RunState.TAG_CONFIRMATION, RunState.TEST_GENERATING)
        assert can_transition(RunState.TEST_GENERATING, RunState.TEST_READY)
        assert can_transition(RunState.TEST_READY, RunState.AWAITING_STUDENT)
        assert can_transition(RunState.AWAITING_STUDENT, RunState.ATTEMPT_RECEIVED)
        assert can_transition(RunState.ATTEMPT_RECEIVED, RunState.DIAGNOSING)
        assert can_transition(RunState.DIAGNOSING, RunState.TAILORING)
        assert can_transition(RunState.TAILORING, RunState.REVIEWING)
        assert can_transition(RunState.REVIEWING, RunState.NOTE_SAVED)
        assert can_transition(RunState.REVIEWING, RunState.TAILORING)  # revision
        assert can_transition(RunState.NOTE_SAVED, RunState.ANALYSING)
        assert can_transition(RunState.ANALYSING, RunState.AGGREGATING)
        assert can_transition(RunState.AGGREGATING, RunState.COMPLETE)
        assert can_transition(RunState.COMPLETE, RunState.AWAITING_STUDENT)

    def test_invalid_transitions(self):
        assert not can_transition(RunState.TEACHER_SETUP, RunState.COMPLETE)
        assert not can_transition(RunState.DIAGNOSING, RunState.COMPLETE)
        assert not can_transition(RunState.COMPLETE, RunState.TEACHER_SETUP)

    def test_can_revise(self):
        assert can_revise(0) is True
        assert can_revise(2) is True
        assert can_revise(3) is False
        assert can_revise(5) is False


class TestBackendTrustBoundaries:
    def test_submit_attempt_request_no_score_total(self):
        # Client cannot send score/total
        req = SubmitAttemptRequest(test_id="t1", answers={"q1": "a1"})
        assert req.test_id == "t1"
        assert req.answers == {"q1": "a1"}
        # score and total should not be in request fields
        assert "score" not in SubmitAttemptRequest.model_fields
        assert "total" not in SubmitAttemptRequest.model_fields

    def test_attempt_score_total_server_owned(self):
        # Attempt defaults score/total to 0 (server computes)
        attempt = Attempt(student_id="s1", test_id="t1", concept_id="c1", answers={})
        assert attempt.score == 0
        assert attempt.total == 0

    def test_attempt_rejects_negative_score(self):
        with pytest.raises(Exception):
            Attempt(student_id="s1", test_id="t1", concept_id="c1", answers={}, score=-1)


class TestPrivacyContracts:
    def test_teacher_note_version_excludes_markdown(self):
        tnv = TeacherNoteVersion(
            student_id="s1", concept_id="c1", version=1,
            created_at=NoteVersion(student_id="s1", concept_id="c1", version=1, markdown="x").created_at
        )
        assert "markdown" not in TeacherNoteVersion.model_fields
        assert hasattr(tnv, "student_id")
        assert hasattr(tnv, "version")

    def test_student_notes_response_uses_note_version(self):
        resp = StudentNotesResponse(notes=[])
        # Uses full NoteVersion with markdown
        notes_field = StudentNotesResponse.model_fields["notes"]
        assert "NoteVersion" in str(notes_field.annotation)

    def test_teacher_student_notes_response_uses_teacher_note_version(self):
        resp = TeacherStudentNotesResponse(notes=[])
        # Uses TeacherNoteVersion WITHOUT markdown
        notes_field = TeacherStudentNotesResponse.model_fields["notes"]
        assert "TeacherNoteVersion" in str(notes_field.annotation)


class TestConstants:
    def test_constants_single_source(self):
        assert MAX_REVISIONS_PER_CYCLE == 3
        assert TAG_CONFIRMATION_TIMEOUT_SECONDS == 600


class TestConceptNode:
    def test_prerequisites_field(self):
        # NEW: ConceptNode has prerequisites field
        cn = ConceptNode(name="Test", summary="Test concept", prerequisites=["c1", "c2"])
        assert cn.prerequisites == ["c1", "c2"]
        # Default empty list
        cn2 = ConceptNode(name="Test2", summary="Test2")
        assert cn2.prerequisites == []


class TestNoteVersion:
    def test_run_id_field(self):
        # NEW: NoteVersion has run_id for traceability
        nv = NoteVersion(student_id="s1", concept_id="c1", version=1, markdown="note", run_id="run-123")
        assert nv.run_id == "run-123"


class TestGraphModels:
    def test_graph_edge(self):
        from contracts import GraphEdge, ConceptGraph
        edge = GraphEdge(from_concept_id="c1", to_concept_id="c2")
        assert edge.from_concept_id == "c1"
        assert edge.to_concept_id == "c2"

    def test_graph_edge_self_reference_fails(self):
        from contracts import GraphEdge
        import pytest
        with pytest.raises(Exception, match="self-reference"):
            GraphEdge(from_concept_id="c1", to_concept_id="c1")

    def test_concept_graph(self):
        from contracts import GraphEdge, ConceptGraph, ConceptNode
        node1 = ConceptNode(name="C1", summary="Concept 1")
        node2 = ConceptNode(name="C2", summary="Concept 2")
        edges = [GraphEdge(from_concept_id=node1.id, to_concept_id=node2.id)]
        graph = ConceptGraph(nodes=[node1, node2], edges=edges)
        assert len(graph.nodes) == 2
        assert len(graph.edges) == 1

    def test_concept_graph_invalid_edge_fails(self):
        from contracts import GraphEdge, ConceptGraph, ConceptNode
        import pytest
        node1 = ConceptNode(name="C1", summary="Concept 1")
        # Edge references unknown node ID
        edges = [GraphEdge(from_concept_id="unknown", to_concept_id=node1.id)]
        with pytest.raises(Exception, match="unknown from_concept_id"):
            ConceptGraph(nodes=[node1], edges=edges)


class TestConfirmTagsResponse:
    def test_async_test_generation(self):
        from contracts.api_contracts import ConfirmTagsResponse
        from contracts import RunState
        # Test generation is async - test is optional, state is required
        resp = ConfirmTagsResponse(run_id="run-123", state=RunState.TEST_GENERATING)
        assert resp.run_id == "run-123"
        assert resp.state == RunState.TEST_GENERATING
        assert resp.test is None
        assert resp.error is None

        # Can also include test if generation completed
        from contracts import Test, Question
        test = Test(
            concept_id="c1", concept_name="Test",
            questions=[Question(text="Q?", correct_answer="A", options=["A","B","C","D"], concept_id="c1")]
        )
        resp2 = ConfirmTagsResponse(run_id="run-123", state=RunState.TEST_READY, test=test)
        assert resp2.state == RunState.TEST_READY
        assert resp2.test is not None

        # Failed state includes error
        resp3 = ConfirmTagsResponse(run_id="run-123", state=RunState.FAILED, error="LLM timeout")
        assert resp3.state == RunState.FAILED
        assert resp3.error == "LLM timeout"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])