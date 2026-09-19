# curriculum/test_generator.py
# Test generation with mock LLM for testing

import uuid
from typing import Callable, Optional
from contracts.schemas import ConceptNode, Test, Question, TeacherConfirmation


class TestGenerationError(Exception):
    """Raised when test generation fails."""
    pass


# Mock LLM responses for testing
MOCK_TESTS: dict[str, Test] = {}
MOCK_FAILURE_MODE: dict[str, bool] = {}
MOCK_FAILURE_COUNT: dict[str, int] = {}


def reset_mock_state() -> None:
    """Reset mock state for testing."""
    global MOCK_TESTS, MOCK_FAILURE_MODE, MOCK_FAILURE_COUNT
    MOCK_TESTS.clear()
    MOCK_FAILURE_MODE.clear()
    MOCK_FAILURE_COUNT.clear()


def set_mock_test(concept_id: str, test: Test) -> None:
    """Set a mock test to return for a concept."""
    MOCK_TESTS[concept_id] = test


def set_mock_failure(concept_id: str, fail: bool, fail_count: int = 1) -> None:
    """Configure mock to fail for a concept."""
    MOCK_FAILURE_MODE[concept_id] = fail
    MOCK_FAILURE_COUNT[concept_id] = fail_count


def generate_test(concepts: list[ConceptNode], confirmation: TeacherConfirmation) -> Test:
    """
    Generate a test from confirmed concepts.
    
    In production, this would call an LLM. For testing, uses mock responses.
    """
    import time
    # Small delay to simulate LLM latency (helps tests catch TEST_GENERATING state)
    time.sleep(0.1)
    
    if not concepts:
        raise TestGenerationError("No concepts provided for test generation")
    
    if not confirmation.confirmed:
        raise TestGenerationError("Teacher confirmation required before test generation")
    
    # Use the first concept as the primary concept for the test
    primary_concept = concepts[0]
    concept_id = primary_concept.id
    
    # Check for mock failure mode
    if MOCK_FAILURE_MODE.get(concept_id, False):
        count = MOCK_FAILURE_COUNT.get(concept_id, 1)
        MOCK_FAILURE_COUNT[concept_id] = count - 1
        if count > 0:
            raise TestGenerationError(f"Mock LLM failure for concept {concept_id}")
        # After fail_count failures, succeed
        MOCK_FAILURE_MODE[concept_id] = False
    
    # Return mock test if available
    if concept_id in MOCK_TESTS:
        return MOCK_TESTS[concept_id]
    
    # Generate a default test based on concept
    return _generate_default_test(primary_concept)


def _generate_default_test(concept: ConceptNode) -> Test:
    """Generate a default test for a concept (used when no mock is set)."""
    questions = [
        Question(
            text=f"What is the main idea of {concept.name}?",
            correct_answer=concept.summary[:50] if concept.summary else "The main concept",
            options=[
                concept.summary[:50] if concept.summary else "The main concept",
                "An unrelated concept",
                "A different approach",
                "None of the above"
            ],
            concept_id=concept.id
        ),
        Question(
            text=f"Which of the following is a prerequisite for {concept.name}?",
            correct_answer=concept.prerequisites[0] if concept.prerequisites else "Basic understanding",
            options=[
                concept.prerequisites[0] if concept.prerequisites else "Basic understanding",
                "Advanced calculus",
                "Quantum mechanics",
                "No prerequisites needed"
            ],
            concept_id=concept.id
        ),
        Question(
            text=f"How would you apply {concept.name} in practice?",
            correct_answer="Use the concept to solve related problems",
            options=[
                "Use the concept to solve related problems",
                "Memorize the definition only",
                "Ignore the concept",
                "Apply it randomly"
            ],
            concept_id=concept.id
        )
    ]
    
    return Test(
        concept_id=concept.id,
        concept_name=concept.name,
        questions=questions
    )


def register_test_generator(runtime) -> None:
    """Register the test generator with the agent runtime."""
    runtime.set_test_generator(generate_test)