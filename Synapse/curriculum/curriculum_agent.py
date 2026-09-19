# curriculum/curriculum_agent.py
# Curriculum agent: canonical note -> concepts

from typing import Optional
from contracts.schemas import ConceptNode, CanonicalNote, TeacherConfirmation


def extract_concepts(canonical_note: str) -> list[ConceptNode]:
    """
    Extract concepts from a canonical note.
    
    In production, this would use an LLM. For testing, uses simple parsing.
    """
    # Simple mock extraction - in reality this would use an LLM
    concepts = []
    
    # Parse the canonical note for concept-like structures
    lines = canonical_note.strip().split('\n')
    current_concept = None
    
    for line in lines:
        line = line.strip()
        if line.startswith("Concept:") or line.startswith("concept:"):
            name = line.split(":", 1)[1].strip()
            if name:
                current_concept = ConceptNode(
                    name=name,
                    summary=f"Extracted from canonical note: {canonical_note[:200]}",
                    prerequisites=[]
                )
                concepts.append(current_concept)
    
    # If no explicit concept found, create one from the whole note
    if not concepts:
        concepts.append(ConceptNode(
            name="Extracted Concept",
            summary=canonical_note[:500],
            prerequisites=[]
        ))
    
    return concepts


def confirm_tags(concepts: list[ConceptNode], teacher_edits: Optional[dict] = None) -> TeacherConfirmation:
    """
    Process teacher confirmation of concepts.
    
    Returns a TeacherConfirmation record.
    """
    edited_concepts = None
    if teacher_edits:
        # Apply teacher edits (simplified)
        edited_concepts = []
        for concept in concepts:
            if concept.id in teacher_edits:
                edit = teacher_edits[concept.id]
                edited_concepts.append(ConceptNode(
                    id=concept.id,
                    name=edit.get("name", concept.name),
                    summary=edit.get("summary", concept.summary),
                    prerequisites=edit.get("prerequisites", concept.prerequisites)
                ))
            else:
                edited_concepts.append(concept)
    
    return TeacherConfirmation(
        concept_id=concepts[0].id if concepts else "",
        teacher_id="teacher-1",  # Would come from auth context
        confirmed=True,
        edited_concepts=edited_concepts,
        confirmed_at=None  # Set by caller
    )