# agents/tailoring.py
# Tailoring service - generates personalized learning notes based on diagnosis

from typing import Optional
from contracts.schemas import (
    Diagnosis, NoteVersion, DiagnosisItem, MistakeClassification
)


class TailoringError(Exception):
    """Raised when note tailoring fails."""
    pass


# Mock LLM responses for testing
MOCK_NOTES: dict[str, NoteVersion] = {}
MOCK_TAILORING_FAILURE_MODE: dict[str, bool] = {}
MOCK_TAILORING_FAILURE_COUNT: dict[str, int] = {}


def reset_mock_state() -> None:
    """Reset mock state for testing."""
    global MOCK_NOTES, MOCK_TAILORING_FAILURE_MODE, MOCK_TAILORING_FAILURE_COUNT
    MOCK_NOTES.clear()
    MOCK_TAILORING_FAILURE_MODE.clear()
    MOCK_TAILORING_FAILURE_COUNT.clear()


def set_mock_note(note_key: str, note: NoteVersion) -> None:
    """Set a mock note to return for a diagnosis."""
    MOCK_NOTES[note_key] = note


def set_mock_tailoring_failure(concept_id: str, fail: bool, fail_count: int = 1) -> None:
    """Configure mock to fail for a concept."""
    MOCK_TAILORING_FAILURE_MODE[concept_id] = fail
    MOCK_TAILORING_FAILURE_COUNT[concept_id] = fail_count


def _get_note_key(diagnosis: Diagnosis, version: int) -> str:
    """Generate a key for the note based on diagnosis and version."""
    return f"{diagnosis.student_id}:{diagnosis.concept_id}:v{version}"


def _generate_mistake_section(items: list[DiagnosisItem]) -> str:
    """Generate the mistake pattern table section."""
    if not items:
        return "No mistakes identified - excellent work!"
    
    lines = [
        "### Your Mistake Pattern",
        "",
        "| Question | Your Answer | Correct Idea | What Happened |",
        "|---|---|---|---|"
    ]
    
    for item in items:
        classification = item.classification.value.replace('_', ' ').title()
        lines.append(f"| {item.question_id} | [Your answer] | {classification} | {item.reason} |")
    
    return "\n".join(lines)


def _generate_concept_explanation(concept_id: str, items: list[DiagnosisItem]) -> str:
    """Generate concept-specific explanation based on mistakes."""
    if not items:
        return "You have a solid understanding of this concept. Keep up the good work!"
    
    # Group by classification
    classifications = {}
    for item in items:
        cls = item.classification
        if cls not in classifications:
            classifications[cls] = []
        classifications[cls].append(item)
    
    explanations = []
    
    if MistakeClassification.CONCEPTUAL_GAP in classifications:
        explanations.append(
            "## Key Concept to Review\n\n"
            "You seem to be missing a fundamental understanding of this concept. "
            "The core idea you need to grasp is the relationship between the base case "
            "and the recursive step. Focus on understanding *why* the base case stops "
            "the recursion and *how* the recursive step moves toward it."
        )
    
    if MistakeClassification.CARELESS_MISTAKE in classifications:
        explanations.append(
            "## Attention to Detail\n\n"
            "You understand the concept but made some small errors. "
            "Take your time reading each question carefully. "
            "Double-check your work before submitting."
        )
    
    if MistakeClassification.CONTRADICTORY in classifications:
        explanations.append(
            "## Clarifying Confusion\n\n"
            "Your answers suggest some conflicting ideas. "
            "Try to identify where your understanding might be inconsistent. "
            "Review the definitions and make sure each concept has a clear, "
            "non-contradictory meaning in your mind."
        )
    
    if MistakeClassification.EMPTY in classifications:
        explanations.append(
            "## Completing the Work\n\n"
            "Some questions were left unanswered. "
            "Even if you're unsure, attempting an answer helps identify "
            "what you know and what needs review."
        )
    
    if MistakeClassification.UNRELATED in classifications:
        explanations.append(
            "## Focusing on the Topic\n\n"
            "Some answers seem to address a different concept. "
            "Make sure to read the question carefully and focus on what "
            "is specifically being asked about this topic."
        )
    
    return "\n\n".join(explanations) if explanations else "Keep practicing to strengthen your understanding."


def _generate_connections(concept_id: str, items: list[DiagnosisItem], existing_concepts: list[str]) -> str:
    """Generate connections to related concepts based on prerequisites and mistakes."""
    connections = []
    
    # Always suggest prerequisite if not already known
    if "Functions" in existing_concepts and "Functions" != concept_id:
        connections.append("[[Functions]] - Understanding functions is essential for this concept")
    
    if "Recursion" in concept_id and "Iteration" in existing_concepts:
        connections.append("[[Iteration]] - Compare recursive and iterative approaches")
    
    if "Base case" in str(items) and "Recursion" in existing_concepts:
        connections.append("[[Recursion]] - Deep dive into recursive patterns")
    
    if not connections:
        connections.append("No related concepts in your notes yet. As you learn more, connections will appear here.")
    
    return "\n".join(f"- {conn}" for conn in connections)


def tailor(diagnosis: Diagnosis, previous_note: Optional[NoteVersion], existing_concept_names: list[str]) -> NoteVersion:
    """
    Generate a tailored learning note based on diagnosis and previous note.
    
    Args:
        diagnosis: The diagnosis of the student's attempt
        previous_note: The student's previous note version (if any)
        existing_concept_names: Set of concept names the student already has notes for
    
    Returns:
        New NoteVersion with tailored content
    """
    import time
    time.sleep(0.05)  # Simulate LLM latency
    
    note_key = _get_note_key(diagnosis, (previous_note.version + 1) if previous_note else 1)
    
    # Check for mock failure mode
    if MOCK_TAILORING_FAILURE_MODE.get(diagnosis.concept_id, False):
        count = MOCK_TAILORING_FAILURE_COUNT.get(diagnosis.concept_id, 1)
        MOCK_TAILORING_FAILURE_COUNT[diagnosis.concept_id] = count - 1
        if count > 0:
            raise TailoringError(f"Mock LLM failure for tailoring concept {diagnosis.concept_id}")
        MOCK_TAILORING_FAILURE_MODE[diagnosis.concept_id] = False
    
    # Return mock note if available
    if note_key in MOCK_NOTES:
        return MOCK_NOTES[note_key]
    
    # Determine version number
    version = (previous_note.version + 1) if previous_note else 1
    
    # Build markdown content
    concept_name = diagnosis.concept_id  # In real impl, would fetch from store
    
    markdown_parts = [
        f"# {concept_name}",
        "",
        "## What You Need to Remember",
        "",
        _generate_concept_explanation(concept_id, diagnosis.items),
        "",
        _generate_mistake_section(diagnosis.items),
        "",
        "## Connections",
        "",
        _generate_connections(concept_id, diagnosis.items, existing_concept_names),
        "",
        f"---\n*Version {version} • Mastery: {diagnosis.mastery_estimate:.0%} • Trend: {diagnosis.trend.value}*"
    ]
    
    markdown = "\n".join(markdown_parts)
    
    return NoteVersion(
        student_id=diagnosis.student_id,
        concept_id=diagnosis.concept_id,
        version=version,
        markdown=markdown,
        diagnosis_id=diagnosis.id if hasattr(diagnosis, 'id') else None,
        review_id=None,
        run_id=None
    )