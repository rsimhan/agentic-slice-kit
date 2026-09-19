# api/main.py
# FastAPI application with async test generation flow

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.responses import JSONResponse
from typing import Optional
import uuid
from datetime import datetime

from contracts.schemas import (
    ConceptNode, RunState, TeacherConfirmation,
    MAX_TEST_GENERATION_RETRIES, Test, Question, Attempt, Diagnosis,
    NoteVersion, ReviewResult, AnalysisPayload
)
from contracts.api_contracts import (
    CreateConceptRequest, CreateConceptResponse,
    ConfirmTagsRequest, ConfirmTagsResponse,
    RunStatusResponse, ErrorResponse,
    SubmitAttemptRequest, SubmitAttemptResponse,
    StudentNotesResponse, TeacherStudentNotesResponse,
    StudentGraphResponse, TeacherAnalyticsResponse, TeacherTrendsResponse
)
from agent_runtime.store import RunStore, get_store, set_store
from agent_runtime.runner import AgentRuntime, get_runtime, set_runtime, TransitionError
from curriculum.curriculum_agent import extract_concepts, confirm_tags
from curriculum.test_generator import generate_test, register_test_generator, reset_mock_state, set_mock_test, set_mock_failure
from agents.diagnosis import diagnose
from agents.tailoring import tailor
from agents.review import review
from agents.analysis import analyze


app = FastAPI(title="Synapse Cycle API", version="0.1.0")


# Dependency to get/store instances
def get_db() -> RunStore:
    return get_store()


def get_agent_runtime() -> AgentRuntime:
    return get_runtime()


# Initialize on startup
@app.on_event("startup")
async def startup():
    store = RunStore("synapse.db")
    set_store(store)
    
    runtime = AgentRuntime(store)
    register_test_generator(runtime)
    runtime.set_diagnosis_generator(diagnose)
    runtime.set_tailoring_generator(tailor)
    runtime.set_review_generator(review)
    runtime.set_analysis_generator(analyze)
    set_runtime(runtime)
    
    reset_mock_state()


# Health check
@app.get("/health")
async def health():
    return {"status": "ok"}


# ─── Teacher Endpoints ────────────────────────────────────────────────────────

@app.post("/teacher/concepts", response_model=CreateConceptResponse, status_code=status.HTTP_201_CREATED)
async def create_concept(
    request: CreateConceptRequest,
    runtime: AgentRuntime = Depends(get_agent_runtime)
):
    """
    Create a new concept from canonical note.
    Returns run_id for tracking the teacher confirmation flow.
    """
    # Extract concepts from canonical note
    concepts = extract_concepts(request.markdown)
    
    if not concepts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not extract concepts from canonical note"
        )
    
    # Create a run for this concept
    primary_concept = concepts[0]
    primary_concept.name = request.concept_name
    
    run = runtime.start_run(
        concept_id=primary_concept.id,
        teacher_id="teacher-1"  # Would come from auth
    )
    
    # Transition to TAG_CONFIRMATION
    try:
        runtime.transition(run.run_id, RunState.TAG_CONFIRMATION)
    except TransitionError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
    
    return CreateConceptResponse(concept=primary_concept, run_id=run.run_id)


@app.post("/teacher/concepts/{run_id}/confirm", response_model=ConfirmTagsResponse)
async def confirm_tags(
    run_id: str,
    request: ConfirmTagsRequest,
    runtime: AgentRuntime = Depends(get_agent_runtime)
):
    """
    Confirm or reject concept tags.
    
    If confirmed: starts async test generation, returns 202 Accepted with run_id.
    If rejected: returns to TEACHER_SETUP for re-extraction.
    
    Client should poll /runs/{run_id}/status to check test generation progress.
    
    Idempotent: duplicate confirms return current state.
    """
    run = runtime.get_run_status(run_id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Run not found"
        )
    
    if not request.confirmed:
        # Teacher rejects - only allowed from TAG_CONFIRMATION
        if run.state != RunState.TAG_CONFIRMATION:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot reject from state {run.state.value}"
            )
        try:
            runtime.transition(run_id, RunState.TEACHER_SETUP)
        except TransitionError as e:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(e)
            )
        
        return ConfirmTagsResponse(
            run_id=run_id,
            state=RunState.TEACHER_SETUP
        )
    
    # Teacher confirms
    # If already past TAG_CONFIRMATION, return current state (idempotent)
    if run.state != RunState.TAG_CONFIRMATION:
        return ConfirmTagsResponse(
            run_id=run_id,
            state=run.state,
            test=None  # Test would be available via separate endpoint
        )
    
    # Teacher confirms - start test generation
    concepts = request.edited_concepts or []
    if not concepts:
        # Use existing concepts from extraction (in real impl, fetch from store)
        concepts = [ConceptNode(
            id=run.concept_id,
            name="Extracted Concept",
            summary="Concept from canonical note"
        )]
    
    confirmation = TeacherConfirmation(
        concept_id=run.concept_id,
        teacher_id="teacher-1",
        confirmed=True,
        edited_concepts=concepts if request.edited_concepts else None,
        confirmed_at=datetime.utcnow()
    )
    
    try:
        runtime.transition(run_id, RunState.TEST_GENERATING, concepts=concepts, confirmation=confirmation)
    except TransitionError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
    
    # Return 202 Accepted - generation started
    updated_run = runtime.get_run_status(run_id)
    response = ConfirmTagsResponse(
        run_id=run_id,
        state=updated_run.state
    )
    
    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content=response.model_dump(mode='json')
    )


@app.get("/teacher/analytics/{concept_id}", response_model=TeacherAnalyticsResponse)
async def get_teacher_analytics(concept_id: str):
    """Get class analytics for a concept."""
    # Placeholder - would call analytics service
    return TeacherAnalyticsResponse(
        concept_id=concept_id,
        concept_name="Concept",
        analytics=None  # Would be populated by analytics module
    )


@app.get("/teacher/trends/{concept_id}", response_model=TeacherTrendsResponse)
async def get_teacher_trends(concept_id: str):
    """Get trend data for a concept."""
    # Placeholder - would call analytics service
    return TeacherTrendsResponse(concept_id=concept_id, trends=[])


# ─── Student Endpoints ────────────────────────────────────────────────────────

@app.get("/student/tests/{test_id}")
async def get_student_test(test_id: str, runtime: AgentRuntime = Depends(get_agent_runtime)):
    """
    Retrieve a test for a student to take.
    
    Returns the test with questions (without correct answers).
    """
    # In a real implementation, we'd fetch the test from the store
    # For now, we'll check if there's a run with this test
    # This is a simplified implementation
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Test retrieval not yet fully implemented"
    )


@app.post("/student/attempts", response_model=SubmitAttemptResponse, status_code=status.HTTP_201_CREATED)
async def submit_attempt(request: SubmitAttemptRequest, runtime: AgentRuntime = Depends(get_agent_runtime)):
    """
    Submit a student attempt and run the full learning pipeline.
    
    Flow: ATTEMPT_RECEIVED -> DIAGNOSING -> TAILORING -> REVIEWING -> 
          NOTE_SAVED -> ANALYSING -> AGGREGATING -> COMPLETE
    """
    # Create an attempt record
    attempt = Attempt(
        student_id="student-1",  # Would come from auth
        test_id=request.test_id,
        concept_id="",  # Would be fetched from test
        answers=request.answers,
        score=0,
        total=0,
        submitted_at=datetime.utcnow()
    )
    
    # Find the run associated with this test
    # In a real implementation, we'd look up the run by test_id
    # For now, we'll create a new run or find existing one
    # This is a simplified implementation
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Attempt submission with full pipeline not yet fully implemented"
    )


@app.get("/student/notes/{concept_id}", response_model=StudentNotesResponse)
async def get_student_notes(concept_id: str, runtime: AgentRuntime = Depends(get_agent_runtime)):
    """Get student's tailored notes for a concept."""
    store = runtime.store
    notes = store.get_note_versions("student-1", concept_id)  # student_id from auth
    return StudentNotesResponse(notes=notes)


@app.get("/student/graph/{concept_id}", response_model=StudentGraphResponse)
async def get_student_graph(concept_id: str, runtime: AgentRuntime = Depends(get_agent_runtime)):
    """Get student's concept graph."""
    store = runtime.store
    graph = store.get_concept_graph("student-1")  # student_id from auth
    if graph is None:
        return StudentGraphResponse(nodes=[], edges=[])
    return StudentGraphResponse(nodes=graph.nodes, edges=graph.edges)


# ─── Runtime/Shared Endpoints ────────────────────────────────────────────────

@app.get("/runs/{run_id}/status", response_model=RunStatusResponse)
async def get_run_status(run_id: str, runtime: AgentRuntime = Depends(get_agent_runtime)):
    """
    Poll run status for async operations.
    
    Returns current state and progress information.
    """
    run = runtime.get_run_status(run_id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Run not found"
        )
    
    return RunStatusResponse(
        run_id=run.run_id,
        state=run.state,
        current_cycle=run.current_cycle,
        revision_count=run.revision_count,
        model_call_count=run.model_call_count,
        test_generation_retry_count=run.test_generation_retry_count,
        test_generation_error=run.test_generation_error,
        error=run.error
    )


@app.post("/runs/{run_id}/retry", response_model=RunStatusResponse)
async def retry_run(run_id: str, runtime: AgentRuntime = Depends(get_agent_runtime)):
    """Retry a failed run (e.g., test generation failure)."""
    run = runtime.get_run_status(run_id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Run not found"
        )
    
    if run.state != RunState.FAILED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Run is not in FAILED state (current: {run.state.value})"
        )
    
    # Reset error and retry
    try:
        # This would need more context in real implementation
        # For now, just return current status
        pass
    except TransitionError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
    
    updated_run = runtime.get_run_status(run_id)
    return RunStatusResponse(
        run_id=updated_run.run_id,
        state=updated_run.state,
        current_cycle=updated_run.current_cycle,
        revision_count=updated_run.revision_count,
        model_call_count=updated_run.model_call_count,
        test_generation_retry_count=updated_run.test_generation_retry_count,
        test_generation_error=updated_run.test_generation_error,
        error=updated_run.error
    )


# ─── Test/Debug Endpoints (for development) ──────────────────────────────────

@app.post("/_test/set_mock_test")
async def set_mock_test_endpoint(concept_id: str, test_data: dict):
    """Set a mock test for testing (dev only)."""
    test = Test(**test_data)
    set_mock_test(concept_id, test)
    return {"status": "ok"}


@app.post("/_test/set_mock_failure")
async def set_mock_failure_endpoint(concept_id: str, fail: bool, fail_count: int = 1):
    """Configure mock failure for testing (dev only)."""
    set_mock_failure(concept_id, fail, fail_count)
    return {"status": "ok"}


@app.post("/_test/reset")
async def reset_test_state():
    """Reset test state (dev only)."""
    reset_mock_state()
    return {"status": "ok"}


# Import Test for test endpoints
from contracts.schemas import Test