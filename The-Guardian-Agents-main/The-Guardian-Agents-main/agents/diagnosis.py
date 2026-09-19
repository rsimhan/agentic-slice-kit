# agents/diagnosis.py
# Diagnosis service - evaluates student attempts and identifies mistake patterns

from typing import Optional
from contracts.schemas import (
    Attempt, Diagnosis, DiagnosisItem, 
    MistakeClassification, TrendLabel, Test, Question
)


class DiagnosisError(Exception):
    """Raised when diagnosis fails."""
    pass


# Mock LLM responses for testing
MOCK_DIAGNOSES: dict[str, Diagnosis] = {}
MOCK_DIAGNOSIS_FAILURE_MODE: dict[str, bool] = {}
MOCK_DIAGNOSIS_FAILURE_COUNT: dict[str, int] = {}


def reset_mock_state() -> None:
    """Reset mock state for testing."""
    global MOCK_DIAGNOSES, MOCK_DIAGNOSIS_FAILURE_MODE, MOCK_DIAGNOSIS_FAILURE_COUNT
    MOCK_DIAGNOSES.clear()
    MOCK_DIAGNOSIS_FAILURE_MODE.clear()
    MOCK_DIAGNOSIS_FAILURE_COUNT.clear()


def set_mock_diagnosis(attempt_key: str, diagnosis: Diagnosis) -> None:
    """Set a mock diagnosis to return for an attempt."""
    MOCK_DIAGNOSES[attempt_key] = diagnosis


def set_mock_diagnosis_failure(concept_id: str, fail: bool, fail_count: int = 1) -> None:
    """Configure mock to fail for a concept."""
    MOCK_DIAGNOSIS_FAILURE_MODE[concept_id] = fail
    MOCK_DIAGNOSIS_FAILURE_COUNT[concept_id] = fail_count


def _get_attempt_key(attempt: Attempt) -> str:
    """Generate a key for the attempt based on test_id and student_id."""
    return f"{attempt.student_id}:{attempt.test_id}"


def _get_test_for_attempt(attempt: Attempt) -> Optional[Test]:
    """Get the test associated with an attempt."""
    # Try to get from mock tests first
    for test in MOCK_TESTS.values():
        if test.id == attempt.test_id:
            return test
    return None


def _analyze_answer(question: Question, student_answer: str) -> tuple[MistakeClassification, str]:
    """
    Analyze a single student answer against the correct answer.
    Returns (classification, reason).
    """
    correct = question.correct_answer.strip().lower()
    student = student_answer.strip().lower()
    
    if not student:
        return MistakeClassification.EMPTY, "No answer provided"
    
    if student == correct:
        return MistakeClassification.CONCEPTUAL_GAP, "Answer is correct"  # Will be filtered out
    
    # Simple heuristic-based classification
    # In production, this would use an LLM
    
    # Check for conceptual gap - answer relates to concept but wrong
    if any(word in student for word in ["concept", "principle", "theory", "definition"]):
        return MistakeClassification.CONCEPTUAL_GAP, f"Answer shows misunderstanding of core concept"
    
    # Check for careless mistake - close to correct answer
    if len(student) > 3 and len(correct) > 3:
        # Simple similarity check
        common_chars = set(student) & set(correct)
        if len(common_chars) / max(len(set(student)), len(set(correct))) > 0.5:
            return MistakeClassification.CARELESS_MISTAKE, "Answer is close to correct but has minor errors"
    
    # Check for contradictory - answer contradicts itself or known facts
    if "not" in student and "not" not in correct:
        return MistakeClassification.CONTRADICTORY, "Answer contradicts expected knowledge"
    
    # Default to unrelated
    return MistakeClassification.UNRELATED, "Answer does not relate to the question"


def diagnose(attempt: Attempt, test: Test, student_history: Optional[list] = None) -> Diagnosis:
    """
    Diagnose a student's attempt by evaluating each answer.
    
    Args:
        attempt: The student's submitted attempt with answers
        test: The test that was taken
        student_history: Previous diagnoses and notes for context (optional)
    
    Returns:
        Diagnosis with itemized analysis, mastery estimate, and trend
    """
    import time
    time.sleep(0.05)  # Simulate LLM latency
    
    attempt_key = _get_attempt_key(attempt)
    
    # Check for mock failure mode
    if MOCK_DIAGNOSIS_FAILURE_MODE.get(attempt.concept_id, False):
        count = MOCK_DIAGNOSIS_FAILURE_COUNT.get(attempt.concept_id, 1)
        MOCK_DIAGNOSIS_FAILURE_COUNT[attempt.concept_id] = count - 1
        if count > 0:
            raise DiagnosisError(f"Mock LLM failure for diagnosis of concept {attempt.concept_id}")
        MOCK_DIAGNOSIS_FAILURE_MODE[attempt.concept_id] = False
    
    # Return mock diagnosis if available
    if attempt_key in MOCK_DIAGNOSES:
        return MOCK_DIAGNOSES[attempt_key]
    
    # Build question map for easy lookup
    question_map = {q.id: q for q in test.questions}
    
    items = []
    correct_count = 0
    
    for question_id, student_answer in attempt.answers.items():
        question = question_map.get(question_id)
        if not question:
            continue
            
        classification, reason = _analyze_answer(question, student_answer)
        
        if classification == MistakeClassification.CONCEPTUAL_GAP and student_answer.strip().lower() == question.correct_answer.strip().lower():
            # Actually correct
            correct_count += 1
            continue
            
        if student_answer.strip().lower() == question.correct_answer.strip().lower():
            correct_count += 1
            continue
        
        items.append(DiagnosisItem(
            question_id=question_id,
            classification=classification,
            reason=reason
        ))
    
    # Calculate mastery estimate
    total_questions = len(test.questions)
    attempt.score = correct_count
    attempt.total = total_questions
    
    if total_questions > 0:
        mastery_estimate = correct_count / total_questions
    else:
        mastery_estimate = 0.0
    
    # Determine trend based on history
    trend = TrendLabel.NEW
    if student_history and len(student_history) > 0:
        # Compare with previous mastery
        prev_mastery = student_history[-1].mastery_estimate if hasattr(student_history[-1], 'mastery_estimate') else 0.5
        if mastery_estimate > prev_mastery + 0.1:
            trend = TrendLabel.IMPROVING
        elif mastery_estimate < prev_mastery - 0.1:
            trend = TrendLabel.DECLINING
        else:
            trend = TrendLabel.STABLE
    else:
        # First attempt - determine based on score
        if mastery_estimate >= 0.8:
            trend = TrendLabel.STABLE
        elif mastery_estimate >= 0.5:
            trend = TrendLabel.NEW
        else:
            trend = TrendLabel.STILL_WEAK
    
    return Diagnosis(
        student_id=attempt.student_id,
        concept_id=attempt.concept_id,
        items=items,
        mastery_estimate=mastery_estimate,
        trend=trend
    )