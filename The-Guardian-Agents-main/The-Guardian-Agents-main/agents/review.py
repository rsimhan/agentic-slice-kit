# agents/review.py
# Review service - validates tailored notes against diagnosis and canonical content

import time
from typing import Optional
from typing import Optional
from contracts.schemas import (
    NoteVersion, Diagnosis, ReviewResult, ReviewStatus, DiagnosisItem, MistakeClassification
)


class ReviewError(Exception):
    """Raised when review fails."""
    pass


# Mock LLM responses for testing
MOCK_REVIEWS: dict[str, ReviewResult] = {}
MOCK_REVIEW_FAILURE_MODE: dict[str, bool] = {}
MOCK_REVIEW_FAILURE_COUNT: dict[str, int] = {}


def reset_mock_state() -> None:
    """Reset mock state for testing."""
    global MOCK_REVIEWS, MOCK_REVIEW_FAILURE_MODE, MOCK_REVIEW_FAILURE_COUNT
    MOCK_REVIEWS.clear()
    MOCK_REVIEW_FAILURE_MODE.clear()
    MOCK_REVIEW_FAILURE_COUNT.clear()


def set_mock_review(note_key: str, review: ReviewResult) -> None:
    """Set a mock review to return for a note."""
    MOCK_REVIEWS[note_key] = review


def set_mock_review_failure(concept_id: str, fail: bool, fail_count: int = 1) -> None:
    """Configure mock to fail for a concept."""
    MOCK_REVIEW_FAILURE_MODE[concept_id] = fail
    MOCK_REVIEW_FAILURE_COUNT[concept_id] = fail_count


def _get_review_key(note: NoteVersion) -> str:
    """Generate a key for the review based on note."""
    return f"{note.student_id}:{note.concept_id}:v{note.version}"


def _check_canonical_coverage(note: NoteVersion, canonical: str) -> tuple[bool, str]:
    """Check if the note covers the canonical content."""
    # Simple check - in production would use LLM
    note_lower = note.markdown.lower()
    canonical_keywords = canonical.lower().split()[:10]  # First 10 words
    covered = sum(1 for kw in canonical_keywords if kw in note_lower)
    return covered >= len(canonical_keywords) * 0.5, f"Covered {covered}/{len(canonical_keywords)} key concepts"


def _check_diagnosis_addressed(note: NoteVersion, diagnosis: Diagnosis) -> tuple[bool, str]:
    """Check if the note addresses the diagnosed mistakes."""
    if not diagnosis.items:
        return True, "No mistakes to address"
    
    note_lower = note.markdown.lower()
    addressed_count = 0
    
    for item in diagnosis.items:
        # Check if the mistake classification is mentioned in the note
        classification_term = item.classification.value.replace('_', ' ')
        if classification_term in note_lower or item.reason.lower()[:20] in note_lower:
            addressed_count += 1
    
    return addressed_count >= len(diagnosis.items) * 0.5, f"Addressed {addressed_count}/{len(diagnosis.items)} diagnosed issues"


def _check_links_valid(note: NoteVersion, existing_concepts: list[str]) -> tuple[bool, str]:
    """Check if all [[links]] in the note reference existing concepts."""
    import re
    links = re.findall(r'\[\[([^\]]+)\]\]', note.markdown)
    if not links:
        return True, "No links to validate"
    
    valid_count = sum(1 for link in links if link in existing_concepts)
    return valid_count == len(links), f"Validated {valid_count}/{len(links)} links"


def review(note: NoteVersion, diagnosis: Diagnosis, canonical: str, existing_concepts: Optional[list[str]] = None) -> ReviewResult:
    """
    Review a tailored note against the diagnosis and canonical content.
    
    Args:
        note: The tailored note version to review
        diagnosis: The diagnosis that prompted this note
        canonical: The canonical concept content
        existing_concepts: List of concept names the student already has notes for
    
    Returns:
        ReviewResult with pass/fail and detailed checks
    """
    import time
    time.sleep(0.05)  # Simulate LLM latency
    
    note_key = _get_review_key(note)
    
    # Check for mock failure mode
    if MOCK_REVIEW_FAILURE_MODE.get(diagnosis.concept_id, False):
        count = MOCK_REVIEW_FAILURE_COUNT.get(diagnosis.concept_id, 1)
        MOCK_REVIEW_FAILURE_COUNT[diagnosis.concept_id] = count - 1
        if count > 0:
            raise ReviewError(f"Mock LLM failure for review of concept {diagnosis.concept_id}")
        MOCK_REVIEW_FAILURE_MODE[diagnosis.concept_id] = False
    
    # Return mock review if available
    if note_key in MOCK_REVIEWS:
        return MOCK_REVIEWS[note_key]
    
    if existing_concepts is None:
        existing_concepts = []
    
    # Run checks
    canonical_coverage, canonical_reason = _check_canonical_coverage(note, canonical)
    diagnosis_addressed, diagnosis_reason = _check_diagnosis_addressed(note, diagnosis)
    links_valid, links_reason = _check_links_valid(note, existing_concepts)
    
    # Determine overall pass/fail
    passed = canonical_coverage and diagnosis_addressed and links_valid
    
    objections = []
    if not canonical_coverage:
        objections.append(f"Canonical coverage: {canonical_reason}")
    if not diagnosis_addressed:
        objections.append(f"Diagnosis addressed: {diagnosis_reason}")
    if not links_valid:
        objections.append(f"Links valid: {links_reason}")
    
    if passed:
        status = ReviewStatus.PASSED
    else:
        # Check if this is a revision limit case
        # In real implementation, would check revision count
        status = ReviewStatus.FAILED
    
    return ReviewResult(
        passed=passed,
        canonical_coverage=canonical_coverage,
        diagnosis_addressed=diagnosis_addressed,
        links_valid=links_valid,
        objections=objections,
        status=status
    )