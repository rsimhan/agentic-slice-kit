# tests/test_p1a_async_generation.py
# P1-A Tests: Async test generation, retries, rejection, polling

import pytest
import time
import threading
from fastapi.testclient import TestClient

from contracts.schemas import (
    RunState, ConceptNode, Question, Test, TeacherConfirmation,
    MAX_TEST_GENERATION_RETRIES
)
from contracts.api_contracts import (
    CreateConceptRequest, ConfirmTagsRequest, RunStatusResponse
)
from agent_runtime.store import RunStore
from agent_runtime.runner import AgentRuntime, TransitionError
from curriculum.test_generator import (
    generate_test, reset_mock_state, set_mock_test, set_mock_failure, register_test_generator
)
from api.main import app, get_db, get_agent_runtime


# Test client
client = TestClient(app)


class TestAsyncTestGeneration:
    """Tests for async test generation flow."""

    def setup_method(self):
        """Reset state before each test."""
        reset_mock_state()
        # Create fresh store and runtime - use file-based DB for testing
        import tempfile
        import os
        self.db_fd, self.db_path = tempfile.mkstemp(suffix='.db')
        os.close(self.db_fd)
        
        self.store = RunStore(self.db_path)
        self.runtime = AgentRuntime(self.store)
        register_test_generator(self.runtime)
        
        # Override dependencies
        app.dependency_overrides[get_db] = lambda: self.store
        app.dependency_overrides[get_agent_runtime] = lambda: self.runtime

    def teardown_method(self):
        """Clean up after each test."""
        app.dependency_overrides.clear()
        import os
        if hasattr(self, 'db_path') and os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_create_concept_returns_run_id(self):
        """Creating a concept returns a run_id in TAG_CONFIRMATION state."""
        response = client.post("/teacher/concepts", json={
            "markdown": "Concept: Recursion\n\nA recursive function calls itself.",
            "concept_name": "Recursion"
        })
        
        assert response.status_code == 201
        data = response.json()
        assert "run_id" in data
        assert "concept" in data
        assert data["concept"]["name"] == "Recursion"
        
        # Verify run is in TAG_CONFIRMATION
        run_id = data["run_id"]
        run = self.store.get_run(run_id)
        assert run is not None
        assert run.state == RunState.TAG_CONFIRMATION

    def test_confirm_tags_starts_async_generation(self):
        """Confirming tags starts async test generation, returns 202."""
        # Create concept first
        create_resp = client.post("/teacher/concepts", json={
            "markdown": "Concept: Recursion\n\nA recursive function calls itself.",
            "concept_name": "Recursion"
        })
        run_id = create_resp.json()["run_id"]
        
        # Set up mock test
        test = Test(
            concept_id=run_id,  # Will be overridden
            concept_name="Recursion",
            questions=[
                Question(text="Q1?", correct_answer="A", options=["A","B","C","D"], concept_id=run_id),
                Question(text="Q2?", correct_answer="B", options=["A","B","C","D"], concept_id=run_id),
            ]
        )
        set_mock_test(run_id, test)
        
        # Confirm tags
        response = client.post(f"/teacher/concepts/{run_id}/confirm", json={
            "run_id": run_id,
            "confirmed": True
        })
        
        # Should return 202 Accepted
        assert response.status_code == 202
        data = response.json()
        assert data["run_id"] == run_id
        assert data["state"] == "test_generating"
        assert data["test"] is None
        
        # Verify run state
        run = self.store.get_run(run_id)
        assert run.state == RunState.TEST_GENERATING

    def test_poll_run_status_shows_generating(self):
        """Polling run status shows TEST_GENERATING during generation."""
        create_resp = client.post("/teacher/concepts", json={
            "markdown": "Concept: Recursion",
            "concept_name": "Recursion"
        })
        run_id = create_resp.json()["run_id"]
        
        test = Test(
            concept_id=run_id,
            concept_name="Recursion",
            questions=[
                Question(text="Q1?", correct_answer="A", options=["A","B","C","D"], concept_id=run_id),
            ]
        )
        set_mock_test(run_id, test)
        
        client.post(f"/teacher/concepts/{run_id}/confirm", json={
            "run_id": run_id,
            "confirmed": True
        })
        
        # Poll status
        response = client.get(f"/runs/{run_id}/status")
        assert response.status_code == 200
        data = response.json()
        assert data["state"] == "test_generating"
        assert data["test_generation_retry_count"] == 0

    def test_poll_run_status_shows_ready_after_generation(self):
        """Polling run status shows TEST_READY after generation completes."""
        create_resp = client.post("/teacher/concepts", json={
            "markdown": "Concept: Recursion",
            "concept_name": "Recursion"
        })
        run_id = create_resp.json()["run_id"]
        
        test = Test(
            concept_id=run_id,
            concept_name="Recursion",
            questions=[
                Question(text="Q1?", correct_answer="A", options=["A","B","C","D"], concept_id=run_id),
            ]
        )
        set_mock_test(run_id, test)
        
        client.post(f"/teacher/concepts/{run_id}/confirm", json={
            "run_id": run_id,
            "confirmed": True
        })
        
        # Wait for background generation
        max_wait = 5
        start = time.time()
        while time.time() - start < max_wait:
            response = client.get(f"/runs/{run_id}/status")
            data = response.json()
            if data["state"] == "test_ready":
                break
            time.sleep(0.1)
        
        # Verify final state
        response = client.get(f"/runs/{run_id}/status")
        assert response.status_code == 200
        data = response.json()
        assert data["state"] == "test_ready"
        assert data["test_generation_retry_count"] == 0
        assert data["test_generation_error"] is None


class TestTestGenerationRetries:
    """Tests for test generation retry logic."""

    def setup_method(self):
        reset_mock_state()
        import tempfile
        import os
        self.db_fd, self.db_path = tempfile.mkstemp(suffix='.db')
        os.close(self.db_fd)
        
        self.store = RunStore(self.db_path)
        self.runtime = AgentRuntime(self.store)
        register_test_generator(self.runtime)
        
        app.dependency_overrides[get_db] = lambda: self.store
        app.dependency_overrides[get_agent_runtime] = lambda: self.runtime

    def teardown_method(self):
        app.dependency_overrides.clear()
        import os
        if hasattr(self, 'db_path') and os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_generation_retry_on_failure(self):
        """Test generation retries on failure up to MAX_TEST_GENERATION_RETRIES."""
        create_resp = client.post("/teacher/concepts", json={
            "markdown": "Concept: Recursion",
            "concept_name": "Recursion"
        })
        run_id = create_resp.json()["run_id"]
        
        # Get the actual concept_id from the run
        run = self.store.get_run(run_id)
        concept_id = run.concept_id
        
        # Configure mock to fail 2 times then succeed
        set_mock_failure(concept_id, True, fail_count=2)
        
        test = Test(
            concept_id=concept_id,
            concept_name="Recursion",
            questions=[
                Question(text="Q1?", correct_answer="A", options=["A","B","C","D"], concept_id=concept_id),
            ]
        )
        set_mock_test(concept_id, test)
        
        client.post(f"/teacher/concepts/{run_id}/confirm", json={
            "run_id": run_id,
            "confirmed": True
        })
        
        # Wait for retries and success
        max_wait = 10
        start = time.time()
        while time.time() - start < max_wait:
            response = client.get(f"/runs/{run_id}/status")
            data = response.json()
            if data["state"] == "test_ready":
                break
            time.sleep(0.2)
        
        # Should succeed after retries
        response = client.get(f"/runs/{run_id}/status")
        data = response.json()
        assert data["state"] == "test_ready"
        assert data["test_generation_retry_count"] == 2

    def test_generation_fails_after_max_retries(self):
        """Test generation fails permanently after MAX_TEST_GENERATION_RETRIES."""
        create_resp = client.post("/teacher/concepts", json={
            "markdown": "Concept: Recursion",
            "concept_name": "Recursion"
        })
        run_id = create_resp.json()["run_id"]
        
        # Get the actual concept_id from the run
        run = self.store.get_run(run_id)
        concept_id = run.concept_id
        
        # Configure mock to fail more than max retries
        set_mock_failure(concept_id, True, fail_count=MAX_TEST_GENERATION_RETRIES + 1)
        
        client.post(f"/teacher/concepts/{run_id}/confirm", json={
            "run_id": run_id,
            "confirmed": True
        })
        
        # Wait for failure
        max_wait = 10
        start = time.time()
        while time.time() - start < max_wait:
            response = client.get(f"/runs/{run_id}/status")
            data = response.json()
            if data["state"] == "failed":
                break
            time.sleep(0.2)
        
        # Should be in FAILED state
        response = client.get(f"/runs/{run_id}/status")
        data = response.json()
        assert data["state"] == "failed"
        assert data["test_generation_retry_count"] == MAX_TEST_GENERATION_RETRIES
        assert data["test_generation_error"] is not None
        assert data["error"] is not None


class TestTeacherRejection:
    """Tests for teacher rejection flow."""

    def setup_method(self):
        reset_mock_state()
        import tempfile
        import os
        self.db_fd, self.db_path = tempfile.mkstemp(suffix='.db')
        os.close(self.db_fd)
        
        self.store = RunStore(self.db_path)
        self.runtime = AgentRuntime(self.store)
        register_test_generator(self.runtime)
        
        app.dependency_overrides[get_db] = lambda: self.store
        app.dependency_overrides[get_agent_runtime] = lambda: self.runtime

    def teardown_method(self):
        app.dependency_overrides.clear()
        import os
        if hasattr(self, 'db_path') and os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_teacher_rejection_returns_to_setup(self):
        """Teacher rejection transitions run back to TEACHER_SETUP."""
        create_resp = client.post("/teacher/concepts", json={
            "markdown": "Concept: Recursion",
            "concept_name": "Recursion"
        })
        run_id = create_resp.json()["run_id"]
        
        # Teacher rejects
        response = client.post(f"/teacher/concepts/{run_id}/confirm", json={
            "run_id": run_id,
            "confirmed": False
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["state"] == "teacher_setup"
        assert data["test"] is None
        
        # Verify run state
        run = self.store.get_run(run_id)
        assert run.state == RunState.TEACHER_SETUP

    def test_can_re_extract_after_rejection(self):
        """After rejection, teacher can re-extract concepts."""
        create_resp = client.post("/teacher/concepts", json={
            "markdown": "Concept: Recursion",
            "concept_name": "Recursion"
        })
        run_id = create_resp.json()["run_id"]
        
        # Reject
        client.post(f"/teacher/concepts/{run_id}/confirm", json={
            "run_id": run_id,
            "confirmed": False
        })
        
        # Verify can transition again
        run = self.store.get_run(run_id)
        assert run.state == RunState.TEACHER_SETUP
        
        # Can transition to TAG_CONFIRMATION again
        from contracts.state_machine import can_transition
        assert can_transition(RunState.TEACHER_SETUP, RunState.TAG_CONFIRMATION)


class TestDuplicateConfirmation:
    """Tests for idempotency of duplicate confirmation requests."""

    def setup_method(self):
        reset_mock_state()
        import tempfile
        import os
        self.db_fd, self.db_path = tempfile.mkstemp(suffix='.db')
        os.close(self.db_fd)
        
        self.store = RunStore(self.db_path)
        self.runtime = AgentRuntime(self.store)
        register_test_generator(self.runtime)
        
        app.dependency_overrides[get_db] = lambda: self.store
        app.dependency_overrides[get_agent_runtime] = lambda: self.runtime

    def teardown_method(self):
        app.dependency_overrides.clear()
        import os
        if hasattr(self, 'db_path') and os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_duplicate_confirm_returns_same_run(self):
        """Duplicate confirm request doesn't create duplicate generation."""
        create_resp = client.post("/teacher/concepts", json={
            "markdown": "Concept: Recursion",
            "concept_name": "Recursion"
        })
        run_id = create_resp.json()["run_id"]
        
        # Get the actual concept_id from the run
        run = self.store.get_run(run_id)
        concept_id = run.concept_id
        
        test = Test(
            concept_id=concept_id,
            concept_name="Recursion",
            questions=[
                Question(text="Q1?", correct_answer="A", options=["A","B","C","D"], concept_id=concept_id),
            ]
        )
        set_mock_test(concept_id, test)
        
        # First confirm
        resp1 = client.post(f"/teacher/concepts/{run_id}/confirm", json={
            "run_id": run_id,
            "confirmed": True
        })
        
        # Second confirm (duplicate) - should return current state
        response = client.post(f"/teacher/concepts/{run_id}/confirm", json={
            "run_id": run_id,
            "confirmed": True
        })
        
        # Should return current state (might be test_generating or test_ready)
        assert response.status_code in (200, 202)
        data = response.json()
        assert data["run_id"] == run_id
        assert data["state"] in ("test_generating", "test_ready")
        
        # Verify only one generation started
        steps = self.store.get_steps(run_id)
        gen_steps = [s for s in steps if s.step_name == "test_generation"]
        assert len(gen_steps) == 1


class TestInvalidTransitions:
    """Tests for invalid state transition handling."""

    def setup_method(self):
        reset_mock_state()
        import tempfile
        import os
        self.db_fd, self.db_path = tempfile.mkstemp(suffix='.db')
        os.close(self.db_fd)
        
        self.store = RunStore(self.db_path)
        self.runtime = AgentRuntime(self.store)
        register_test_generator(self.runtime)
        
        app.dependency_overrides[get_db] = lambda: self.store
        app.dependency_overrides[get_agent_runtime] = lambda: self.runtime

    def teardown_method(self):
        app.dependency_overrides.clear()
        import os
        if hasattr(self, 'db_path') and os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_reject_on_wrong_state_returns_409(self):
        """Rejecting tags on wrong state returns 409 Conflict."""
        create_resp = client.post("/teacher/concepts", json={
            "markdown": "Concept: Recursion",
            "concept_name": "Recursion"
        })
        run_id = create_resp.json()["run_id"]
        
        # Get the actual concept_id from the run
        run = self.store.get_run(run_id)
        concept_id = run.concept_id
        
        # Run is already in TAG_CONFIRMATION after create_concept
        # Set up mock test and transition to TEST_GENERATING
        test = Test(
            concept_id=concept_id,
            concept_name="Test",
            questions=[Question(text="Q1?", correct_answer="A", options=["A","B","C","D"], concept_id=concept_id)]
        )
        set_mock_test(concept_id, test)
        
        self.runtime.transition(run_id, RunState.TEST_GENERATING,
                               concepts=[ConceptNode(id=concept_id, name="Test", summary="Test")],
                               confirmation=TeacherConfirmation(
                                   concept_id=concept_id, teacher_id="t1", confirmed=True
                               ))
        
        # Wait for background generation
        import time
        max_wait = 5
        start = time.time()
        while time.time() - start < max_wait:
            run = self.store.get_run(run_id)
            if run.state == RunState.TEST_READY:
                break
            time.sleep(0.1)
        
        self.runtime.transition(run_id, RunState.AWAITING_STUDENT)
        
        # Now try to reject - should fail because not in TAG_CONFIRMATION
        response = client.post(f"/teacher/concepts/{run_id}/confirm", json={
            "run_id": run_id,
            "confirmed": False
        })
        
        assert response.status_code == 409
        assert "Cannot reject from state" in response.json()["detail"]

    def test_invalid_transition_raises_error(self):
        """Direct invalid transition raises TransitionError."""
        run = self.runtime.start_run("concept-1", "teacher-1")
        
        # Try to jump from TEACHER_SETUP to COMPLETE
        with pytest.raises(TransitionError):
            self.runtime.transition(run.run_id, RunState.COMPLETE)


class TestNewCycle:
    """Tests for new learning cycle creation."""

    def setup_method(self):
        reset_mock_state()
        import tempfile
        import os
        self.db_fd, self.db_path = tempfile.mkstemp(suffix='.db')
        os.close(self.db_fd)
        
        self.store = RunStore(self.db_path)
        self.runtime = AgentRuntime(self.store)
        register_test_generator(self.runtime)
        
        app.dependency_overrides[get_db] = lambda: self.store
        app.dependency_overrides[get_agent_runtime] = lambda: self.runtime

    def teardown_method(self):
        app.dependency_overrides.clear()
        import os
        if hasattr(self, 'db_path') and os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_complete_to_awaiting_student_creates_new_cycle(self):
        """COMPLETE -> AWAITING_STUDENT increments cycle count."""
        run = self.runtime.start_run("concept-1", "teacher-1")
        
        # Manually advance to COMPLETE
        self.runtime.transition(run.run_id, RunState.TAG_CONFIRMATION)
        
        # Set up mock test for generation
        test = Test(
            concept_id="c1",
            concept_name="Test",
            questions=[Question(text="Q1?", correct_answer="A", options=["A","B","C","D"], concept_id="c1")]
        )
        set_mock_test("c1", test)
        
        self.runtime.transition(run.run_id, RunState.TEST_GENERATING,
                               concepts=[ConceptNode(id="c1", name="Test", summary="Test")],
                               confirmation=TeacherConfirmation(concept_id="c1", teacher_id="t1", confirmed=True))
        
        # Wait for background generation to complete (auto-transitions to TEST_READY)
        import time
        max_wait = 5
        start = time.time()
        while time.time() - start < max_wait:
            run = self.store.get_run(run.run_id)
            if run.state == RunState.TEST_READY:
                break
            time.sleep(0.1)
        
        # Continue from TEST_READY (already set by background task)
        self.runtime.transition(run.run_id, RunState.AWAITING_STUDENT)
        self.runtime.transition(run.run_id, RunState.ATTEMPT_RECEIVED)
        self.runtime.transition(run.run_id, RunState.DIAGNOSING)
        self.runtime.transition(run.run_id, RunState.TAILORING)
        self.runtime.transition(run.run_id, RunState.REVIEWING)
        self.runtime.transition(run.run_id, RunState.NOTE_SAVED)
        self.runtime.transition(run.run_id, RunState.ANALYSING)
        self.runtime.transition(run.run_id, RunState.AGGREGATING)
        self.runtime.transition(run.run_id, RunState.COMPLETE)
        
        # Refresh run from store
        run = self.store.get_run(run.run_id)
        assert run.current_cycle == 1
        assert run.revision_count == 0
        
        # Transition to new cycle
        self.runtime.transition(run.run_id, RunState.AWAITING_STUDENT)
        
        run = self.store.get_run(run.run_id)
        assert run.current_cycle == 2
        assert run.revision_count == 0  # Reset for new cycle
        assert run.state == RunState.AWAITING_STUDENT


class TestRevisionVsRetry:
    """Tests for revision count vs retry count separation."""

    def setup_method(self):
        reset_mock_state()
        import tempfile
        import os
        self.db_fd, self.db_path = tempfile.mkstemp(suffix='.db')
        os.close(self.db_fd)
        
        self.store = RunStore(self.db_path)
        self.runtime = AgentRuntime(self.store)
        register_test_generator(self.runtime)
        
        app.dependency_overrides[get_db] = lambda: self.store
        app.dependency_overrides[get_agent_runtime] = lambda: self.runtime

    def teardown_method(self):
        app.dependency_overrides.clear()
        import os
        if hasattr(self, 'db_path') and os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_revision_count_separate_from_retry_count(self):
        """Revision count (REVIEWING->TAILORING) separate from test_generation_retry_count."""
        run = self.runtime.start_run("concept-1", "teacher-1")
        
        # Set up mock test for generation
        test = Test(
            concept_id="c1",
            concept_name="Test",
            questions=[Question(text="Q1?", correct_answer="A", options=["A","B","C","D"], concept_id="c1")]
        )
        set_mock_test("c1", test)
        
        # Advance to REVIEWING
        self.runtime.transition(run.run_id, RunState.TAG_CONFIRMATION)
        self.runtime.transition(run.run_id, RunState.TEST_GENERATING,
                               concepts=[ConceptNode(id="c1", name="Test", summary="Test")],
                               confirmation=TeacherConfirmation(concept_id="c1", teacher_id="t1", confirmed=True))
        
        # Wait for background generation
        import time
        max_wait = 5
        start = time.time()
        while time.time() - start < max_wait:
            run = self.store.get_run(run.run_id)
            if run.state == RunState.TEST_READY:
                break
            time.sleep(0.1)
        
        self.runtime.transition(run.run_id, RunState.AWAITING_STUDENT)
        self.runtime.transition(run.run_id, RunState.ATTEMPT_RECEIVED)
        self.runtime.transition(run.run_id, RunState.DIAGNOSING)
        self.runtime.transition(run.run_id, RunState.TAILORING)
        self.runtime.transition(run.run_id, RunState.REVIEWING)
        
        # Refresh run from store
        run = self.store.get_run(run.run_id)
        assert run.revision_count == 0
        assert run.test_generation_retry_count == 0
        
        # Revision: REVIEWING -> TAILORING
        self.runtime.transition(run.run_id, RunState.TAILORING)
        
        run = self.store.get_run(run.run_id)
        assert run.revision_count == 1
        assert run.test_generation_retry_count == 0  # Unchanged
        
        # Another revision
        self.runtime.transition(run.run_id, RunState.REVIEWING)
        self.runtime.transition(run.run_id, RunState.TAILORING)
        
        run = self.store.get_run(run.run_id)
        assert run.revision_count == 2
        assert run.test_generation_retry_count == 0

    def test_max_revisions_enforced(self):
        """Max 3 revisions enforced."""
        run = self.runtime.start_run("concept-1", "teacher-1")
        
        # Set up mock test for generation
        test = Test(
            concept_id="c1",
            concept_name="Test",
            questions=[Question(text="Q1?", correct_answer="A", options=["A","B","C","D"], concept_id="c1")]
        )
        set_mock_test("c1", test)
        
        # Advance to REVIEWING
        self.runtime.transition(run.run_id, RunState.TAG_CONFIRMATION)
        self.runtime.transition(run.run_id, RunState.TEST_GENERATING,
                               concepts=[ConceptNode(id="c1", name="Test", summary="Test")],
                               confirmation=TeacherConfirmation(concept_id="c1", teacher_id="t1", confirmed=True))
        
        # Wait for background generation
        import time
        max_wait = 5
        start = time.time()
        while time.time() - start < max_wait:
            run = self.store.get_run(run.run_id)
            if run.state == RunState.TEST_READY:
                break
            time.sleep(0.1)
        
        self.runtime.transition(run.run_id, RunState.AWAITING_STUDENT)
        self.runtime.transition(run.run_id, RunState.ATTEMPT_RECEIVED)
        self.runtime.transition(run.run_id, RunState.DIAGNOSING)
        self.runtime.transition(run.run_id, RunState.TAILORING)
        self.runtime.transition(run.run_id, RunState.REVIEWING)
        
        # Refresh run from store
        run = self.store.get_run(run.run_id)
        
        # 3 revisions
        for i in range(3):
            self.runtime.transition(run.run_id, RunState.TAILORING)
            self.runtime.transition(run.run_id, RunState.REVIEWING)
        
        run = self.store.get_run(run.run_id)
        assert run.revision_count == 3
        
        # 4th revision should fail
        with pytest.raises(TransitionError, match="Revision limit reached"):
            self.runtime.transition(run.run_id, RunState.TAILORING)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])