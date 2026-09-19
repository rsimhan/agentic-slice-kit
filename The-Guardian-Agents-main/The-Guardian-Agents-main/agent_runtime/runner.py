# agent_runtime/runner.py
# State machine runner with background task support

import threading
import uuid
import time
import logging
from typing import Optional, Callable, Any
from datetime import datetime
from contextlib import contextmanager

from contracts.schemas import (
    RunRecord, StepRecord, RunState, ConceptNode, Test, TeacherConfirmation,
    MAX_TEST_GENERATION_RETRIES, Attempt, Diagnosis, NoteVersion, ReviewResult,
    AnalysisPayload, MAX_MODEL_CALL_RETRIES, TrendLabel
)
from contracts.state_machine import (
    can_transition, get_transition_rule, can_revise, can_retry_test_generation,
    FAILURE_RETRY_STATE
)
from agent_runtime.store import RunStore, get_store, set_store
from agents.diagnosis import diagnose, DiagnosisError
from agents.tailoring import tailor, TailoringError
from agents.review import review, ReviewError
from agents.analysis import analyze, AnalysisError


# Configure logger
logger = logging.getLogger(__name__)


class TransitionError(Exception):
    """Raised when an invalid state transition is attempted."""
    pass


class AgentRuntime:
    """
    Reusable state machine runner with SQLite persistence.
    
    Handles synchronous state transitions and async background tasks
    (like test generation) with retry logic and failure handling.
    """

    def __init__(self, store: Optional[RunStore] = None):
        self.store = store or get_store()
        self._background_tasks: dict[str, threading.Thread] = {}
        self._task_lock = threading.Lock()
        self._test_generator: Optional[Callable[[list[ConceptNode], TeacherConfirmation], Test]] = None
        self._diagnosis_generator: Optional[Callable[[Attempt, Test, Optional[list]], Diagnosis]] = None
        self._tailoring_generator: Optional[Callable[[Diagnosis, Optional[NoteVersion], list[str]], NoteVersion]] = None
        self._review_generator: Optional[Callable[[NoteVersion, Diagnosis, str], ReviewResult]] = None
        self._analysis_generator: Optional[Callable[[Diagnosis, list[Diagnosis]], AnalysisPayload]] = None

    def set_test_generator(self, generator: Callable[[list[ConceptNode], TeacherConfirmation], Test]) -> None:
        """Register the test generation function (called from curriculum module)."""
        self._test_generator = generator

    def set_diagnosis_generator(self, generator: Callable[[Attempt, Test, Optional[list]], Diagnosis]) -> None:
        """Register the diagnosis function."""
        self._diagnosis_generator = generator

    def set_tailoring_generator(self, generator: Callable[[Diagnosis, Optional[NoteVersion], list[str]], NoteVersion]) -> None:
        """Register the tailoring function."""
        self._tailoring_generator = generator

    def set_review_generator(self, generator: Callable[[NoteVersion, Diagnosis, str], ReviewResult]) -> None:
        """Register the review function."""
        self._review_generator = generator

    def set_analysis_generator(self, generator: Callable[[Diagnosis, list[Diagnosis]], AnalysisPayload]) -> None:
        """Register the analysis function."""
        self._analysis_generator = generator

    def start_run(self, concept_id: str, teacher_id: str, canonical_note: str = "") -> RunRecord:
        """Create a new run in TEACHER_SETUP state."""
        run = RunRecord(
            concept_id=concept_id,
            teacher_id=teacher_id,
            state=RunState.TEACHER_SETUP,
            current_cycle=1
        )
        self.store.create_run(run)
        self._record_step(run.run_id, "start_run", {"concept_id": concept_id, "teacher_id": teacher_id}, RunState.TEACHER_SETUP)
        logger.info("Run created", extra={"run_id": run.run_id, "concept_id": concept_id, "teacher_id": teacher_id})
        return run

    def transition(self, run_id: str, to_state: RunState, **context) -> RunRecord:
        """
        Perform a state transition with validation.
        
        Raises TransitionError if the transition is invalid.
        """
        run = self.store.get_run(run_id)
        if not run:
            logger.warning("Transition failed: run not found", extra={"run_id": run_id})
            raise TransitionError(f"Run {run_id} not found")

        if not can_transition(run.state, to_state):
            logger.warning("Invalid transition attempted", extra={"run_id": run_id, "from_state": run.state.value, "to_state": to_state.value})
            raise TransitionError(f"Invalid transition: {run.state.value} -> {to_state.value}")

        # Handle special transitions
        if run.state == RunState.TAG_CONFIRMATION and to_state == RunState.TEST_GENERATING:
            return self._start_test_generation(run, **context)
        
        if run.state == RunState.TEST_GENERATING and to_state == RunState.TEST_GENERATING:
            return self._retry_test_generation(run, **context)
        
        if run.state == RunState.TEST_GENERATING and to_state == RunState.FAILED:
            return self._fail_test_generation(run, **context)

        if run.state == RunState.REVIEWING and to_state == RunState.TAILORING:
            if not can_revise(run.revision_count):
                raise TransitionError(f"Revision limit reached (max 3)")
            run.revision_count += 1

        if run.state == RunState.COMPLETE and to_state == RunState.AWAITING_STUDENT:
            # New cycle for same concept
            run.current_cycle += 1
            run.revision_count = 0

        # Perform the transition
        from_state = run.state
        run.state = to_state
        run.updated_at = datetime.utcnow()
        
        if to_state == RunState.COMPLETE:
            run.completed_at = datetime.utcnow()

        self.store.update_run(run)
        self._record_step(run_id, f"transition_{to_state.value}", context, from_state, to_state)
        logger.info("State transition", extra={"run_id": run_id, "from_state": from_state.value, "to_state": to_state.value})
        
        return run

    def _start_test_generation(self, run: RunRecord, concepts: list[ConceptNode], 
                               confirmation: TeacherConfirmation) -> RunRecord:
        """Start async test generation in background."""
        if self._test_generator is None:
            raise TransitionError("Test generator not registered")

        # Check for duplicate generation (idempotency)
        existing_steps = self.store.get_steps(run.run_id)
        for step in existing_steps:
            if step.step_name == "test_generation" and step.state_after == RunState.TEST_GENERATING:
                # Already generating - return current run
                return run

        run.state = RunState.TEST_GENERATING
        run.test_generation_retry_count = 0
        run.test_generation_error = None
        run.updated_at = datetime.utcnow()
        self.store.update_run(run)
        self._record_step(run.run_id, "test_generation", 
                         {"concepts": [c.model_dump(mode='json') for c in concepts], "confirmation": confirmation.model_dump(mode='json')},
                         RunState.TAG_CONFIRMATION, RunState.TEST_GENERATING)

        # Start background generation
        self._run_background_test_generation(run.run_id, concepts, confirmation)
        return run

    def _run_background_test_generation(self, run_id: str, concepts: list[ConceptNode], 
                                        confirmation: TeacherConfirmation) -> None:
        """Run test generation in background thread with retries."""
        def generate():
            run = self.store.get_run(run_id)
            if not run:
                return

            max_retries = MAX_TEST_GENERATION_RETRIES
            
            while can_retry_test_generation(run.test_generation_retry_count, max_retries):
                try:
                    # Call the test generator
                    test = self._test_generator(concepts, confirmation)
                    
                    # Success - transition to TEST_READY
                    run = self.store.get_run(run_id)
                    if run and run.state == RunState.TEST_GENERATING:
                        run.state = RunState.TEST_READY
                        run.updated_at = datetime.utcnow()
                        self.store.update_run(run)
                        self._record_step(run_id, "test_generation_complete", 
                                         {"test_id": test.id}, RunState.TEST_GENERATING, RunState.TEST_READY)
                    break
                    
                except Exception as e:
                    run = self.store.get_run(run_id)
                    if not run or run.state != RunState.TEST_GENERATING:
                        break
                    
                    run.test_generation_retry_count += 1
                    run.test_generation_error = str(e)
                    run.model_call_count += 1
                    run.updated_at = datetime.utcnow()
                    self.store.update_run(run)
                    self._record_step(run_id, "test_generation_retry", 
                                     {"error": str(e), "retry": run.test_generation_retry_count},
                                     RunState.TEST_GENERATING, RunState.TEST_GENERATING)
                    
                    if not can_retry_test_generation(run.test_generation_retry_count, max_retries):
                        # Max retries reached - mark as failed
                        run.state = RunState.FAILED
                        run.error = f"Test generation failed after {max_retries} retries: {e}"
                        run.updated_at = datetime.utcnow()
                        self.store.update_run(run)
                        self._record_step(run_id, "test_generation_failed", 
                                         {"error": str(e)}, RunState.TEST_GENERATING, RunState.FAILED)
                    else:
                        # Wait before retry (exponential backoff)
                        time.sleep(2 ** run.test_generation_retry_count)

        thread = threading.Thread(target=generate, daemon=True)
        with self._task_lock:
            self._background_tasks[run_id] = thread
        thread.start()

    def _retry_test_generation(self, run: RunRecord, **context) -> RunRecord:
        """Manually trigger a retry (e.g., from API)."""
        # This would be called if teacher wants to retry after a failure
        # For now, just increment retry count and let background task handle it
        run.test_generation_retry_count += 1
        run.updated_at = datetime.utcnow()
        self.store.update_run(run)
        return run

    def _fail_test_generation(self, run: RunRecord, error: str = "Test generation failed") -> RunRecord:
        """Mark test generation as permanently failed."""
        run.state = RunState.FAILED
        run.error = error
        run.updated_at = datetime.utcnow()
        self.store.update_run(run)
        self._record_step(run.run_id, "test_generation_failed", {"error": error}, RunState.TEST_GENERATING, RunState.FAILED)
        return run

    def get_run_status(self, run_id: str) -> Optional[RunRecord]:
        """Get current run status for polling."""
        return self.store.get_run(run_id)

    def _record_step(self, run_id: str, step_name: str, input_data: dict, 
                     state_before: RunState, state_after: Optional[RunState] = None) -> None:
        """Record a step in the run history."""
        step = StepRecord(
            run_id=run_id,
            step_name=step_name,
            input_data=input_data,
            state_before=state_before,
            state_after=state_after,
            started_at=datetime.utcnow()
        )
        self.store.create_step(step)

    def get_history(self, run_id: str) -> list[StepRecord]:
        """Get full step history for a run."""
        return self.store.get_steps(run_id)

    # ─── Pipeline Generator Registration ────────────────────────────────

    def set_diagnosis_generator(self, generator: Callable[[Attempt, Test, Optional[list]], Diagnosis]) -> None:
        """Register the diagnosis function."""
        self._diagnosis_generator = generator

    def set_tailoring_generator(self, generator: Callable[[Diagnosis, Optional[NoteVersion], list[str]], NoteVersion]) -> None:
        """Register the tailoring function."""
        self._tailoring_generator = generator

    def set_review_generator(self, generator: Callable[[NoteVersion, Diagnosis, str], ReviewResult]) -> None:
        """Register the review function."""
        self._review_generator = generator

    def set_analysis_generator(self, generator: Callable[[Diagnosis, list[Diagnosis]], AnalysisPayload]) -> None:
        """Register the analysis function."""
        self._analysis_generator = generator

    # ─── Pipeline Orchestration ────────────────────────────────────────

    def run_pipeline(self, run_id: str) -> RunRecord:
        """
        Run the full learning pipeline: attempt -> diagnosis -> tailoring -> review -> analysis -> complete.
        
        This should be called after a student submits an attempt (ATTEMPT_RECEIVED state).
        """
        run = self.store.get_run(run_id)
        if not run:
            raise TransitionError(f"Run {run_id} not found")

        # Get the test and attempt from the run context
        steps = self.store.get_steps(run_id)
        attempt_data = None
        test_data = None
        
        for step in reversed(steps):
            if step.step_name == "student_attempt":
                attempt_data = step.input_data
            elif step.step_name == "test_generation_complete":
                test_data = step.output_data
        
        if not attempt_data:
            raise TransitionError(f"No attempt found for run {run_id}")
        
        # Create attempt object
        attempt = Attempt(**attempt_data)
        if not attempt.test_id or not attempt.concept_id:
            raise TransitionError(f"Invalid attempt data for run {run_id}")

        # Get test
        test = None
        if test_data:
            test = Test(**test_data)
        
        # Run pipeline stages
        run = self._run_diagnosis_stage(run, attempt, test)
        if run.state == RunState.FAILED:
            return run
            
        run = self._run_tailoring_stage(run, attempt)
        if run.state == RunState.FAILED:
            return run
            
        run = self._run_review_stage(run, attempt)
        if run.state == RunState.FAILED:
            return run
            
        run = self._run_analysis_stage(run, attempt)
        if run.state == RunState.FAILED:
            return run
            
        run = self._run_aggregation_stage(run)
        
        return run

    def _run_diagnosis_stage(self, run: RunRecord, attempt: Attempt, test: Optional[Test]) -> RunRecord:
        """Run the diagnosis stage using the diagnosis agent."""
        self.transition(run.run_id, RunState.DIAGNOSING)
        
        max_retries = MAX_MODEL_CALL_RETRIES
        for retry in range(max_retries + 1):
            try:
                diagnosis = diagnose(attempt, test, [])
                # Store diagnosis in step
                self._record_step(run.run_id, "diagnosis", 
                                 {"diagnosis": diagnosis.model_dump(mode='json')},
                                 RunState.DIAGNOSING, RunState.TAILORING)
                break
            except DiagnosisError as e:
                run = self.store.get_run(run.run_id)
                if retry >= max_retries:
                    run.state = RunState.FAILED
                    run.error = f"Diagnosis failed after {max_retries} retries: {e}"
                    self.store.update_run(run)
                    return run
                time.sleep(2 ** retry)
        
        # Transition to TAILORING
        self.transition(run.run_id, RunState.TAILORING)
        return self.store.get_run(run.run_id)

    def _run_tailoring_stage(self, run: RunRecord, attempt: Attempt) -> RunRecord:
        """Run the tailoring stage using the tailoring agent."""
        max_retries = MAX_MODEL_CALL_RETRIES
        for retry in range(max_retries + 1):
            try:
                # Get latest note version for this student/concept
                previous_note = self.store.get_latest_note_version(attempt.student_id, attempt.concept_id)
                existing_concepts = []  # Would fetch from store
                
                # Get diagnosis from the step
                steps = self.store.get_steps(run.run_id)
                diagnosis = None
                for step in reversed(steps):
                    if step.step_name == "diagnosis" and step.output_data:
                        diagnosis = Diagnosis(**step.output_data.get("diagnosis", {}))
                        break
                
                if not diagnosis:
                    raise TransitionError("No diagnosis found for tailoring")
                
                note = tailor(diagnosis, previous_note, existing_concepts)
                
                # Store note version
                note.run_id = run.run_id
                self.store.create_note_version(note)
                self._record_step(run.run_id, "tailoring",
                                 {"note_version": note.model_dump(mode='json')},
                                 RunState.TAILORING, RunState.REVIEWING)
                break
            except TailoringError as e:
                run = self.store.get_run(run.run_id)
                if retry >= MAX_MODEL_CALL_RETRIES:
                    run.state = RunState.FAILED
                    run.error = f"Tailoring failed after {MAX_MODEL_CALL_RETRIES} retries: {e}"
                    self.store.update_run(run)
                    return run
                time.sleep(2 ** retry)
        
        # Transition to REVIEWING
        self.transition(run.run_id, RunState.REVIEWING)
        return self.store.get_run(run.run_id)

    def _run_review_stage(self, run: RunRecord, attempt: Attempt) -> RunRecord:
        """Run the review stage using the review agent."""
        max_retries = MAX_MODEL_CALL_RETRIES
        for retry in range(max_retries + 1):
            try:
                # Get the latest note version
                note = self.store.get_latest_note_version(attempt.student_id, attempt.concept_id)
                if not note:
                    raise TransitionError("No note version found for review")
                
                # Get diagnosis from step
                steps = self.store.get_steps(run.run_id)
                diagnosis = None
                for step in reversed(steps):
                    if step.step_name == "diagnosis" and step.output_data:
                        diagnosis = Diagnosis(**step.output_data.get("diagnosis", {}))
                        break
                
                if not diagnosis:
                    raise TransitionError("No diagnosis found for review")
                
                # Get canonical content - would be fetched from store
                canonical = "Canonical concept content"
                
                review_result = review(note, diagnosis, canonical, [])
                
                self._record_step(run.run_id, "review",
                                 {"review": review_result.model_dump(mode='json')},
                                 RunState.REVIEWING, RunState.NOTE_SAVED)
                
                if not review_result.passed:
                    # Check revision limit
                    if not can_revise(run.revision_count):
                        self.transition(run.run_id, RunState.FAILED)
                        run = self.store.get_run(run.run_id)
                        run.error = "Revision limit reached"
                        self.store.update_run(run)
                        return run
                    # Will transition back to TAILORING via normal transition logic
                    run.revision_count += 1
                    self.store.update_run(run)
                    self.transition(run.run_id, RunState.TAILORING)
                    return self._run_tailoring_stage(run, attempt)
                
                break
            except ReviewError as e:
                run = self.store.get_run(run.run_id)
                if retry >= MAX_MODEL_CALL_RETRIES:
                    run.state = RunState.FAILED
                    run.error = f"Review failed after {MAX_MODEL_CALL_RETRIES} retries: {e}"
                    self.store.update_run(run)
                    return run
                time.sleep(2 ** retry)
        
        # Transition to NOTE_SAVED
        self.transition(run.run_id, RunState.NOTE_SAVED)
        return self.store.get_run(run.run_id)

    def _run_analysis_stage(self, run: RunRecord, attempt: Attempt) -> RunRecord:
        """Run the analysis stage using the analysis agent."""
        self.transition(run.run_id, RunState.ANALYSING)
        
        max_retries = MAX_MODEL_CALL_RETRIES
        for retry in range(max_retries + 1):
            try:
                # Get diagnosis from step
                steps = self.store.get_steps(run.run_id)
                diagnosis = None
                for step in reversed(steps):
                    if step.step_name == "diagnosis" and step.output_data:
                        diagnosis = Diagnosis(**step.output_data.get("diagnosis", {}))
                        break
                
                if not diagnosis:
                    raise TransitionError("No diagnosis found for analysis")
                
                history = []  # Would fetch from store
                
                analysis = analyze(diagnosis, history, run.current_cycle)
                
                self._record_step(run.run_id, "analysis",
                                 {"analysis": analysis.model_dump(mode='json')},
                                 RunState.ANALYSING, RunState.AGGREGATING)
                break
            except AnalysisError as e:
                run = self.store.get_run(run.run_id)
                if retry >= MAX_MODEL_CALL_RETRIES:
                    run.state = RunState.FAILED
                    run.error = f"Analysis failed after {MAX_MODEL_CALL_RETRIES} retries: {e}"
                    self.store.update_run(run)
                    return run
                time.sleep(2 ** retry)
        
        # Transition to AGGREGATING
        self.transition(run.run_id, RunState.AGGREGATING)
        return self.store.get_run(run.run_id)

    def _run_aggregation_stage(self, run: RunRecord) -> RunRecord:
        """Run the aggregation stage - marks run as complete."""
        self.transition(run.run_id, RunState.COMPLETE)
        run = self.store.get_run(run.run_id)
        run.completed_at = datetime.utcnow()
        self.store.update_run(run)
        return run


# Global runtime instance
_runtime: Optional[AgentRuntime] = None


def get_runtime(store: Optional[RunStore] = None) -> AgentRuntime:
    global _runtime
    if _runtime is None:
        _runtime = AgentRuntime(store)
    return _runtime


def set_runtime(runtime: AgentRuntime) -> None:
    global _runtime
    _runtime = runtime