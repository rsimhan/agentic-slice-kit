# agents/analysis.py
# Analysis service - computes mastery estimates and trends from diagnosis history

import time
from typing import Optional
from contracts.schemas import (
    AnalysisPayload, Diagnosis, TrendLabel
)


class AnalysisError(Exception):
    """Raised when analysis fails."""
    pass


# Mock LLM responses for testing
MOCK_ANALYSES: dict[str, AnalysisPayload] = {}
MOCK_ANALYSIS_FAILURE_MODE: dict[str, bool] = {}
MOCK_ANALYSIS_FAILURE_COUNT: dict[str, int] = {}


def reset_mock_state() -> None:
    """Reset mock state for testing."""
    global MOCK_ANALYSES, MOCK_ANALYSIS_FAILURE_MODE, MOCK_ANALYSIS_FAILURE_COUNT
    MOCK_ANALYSES.clear()
    MOCK_ANALYSIS_FAILURE_MODE.clear()
    MOCK_ANALYSIS_FAILURE_COUNT.clear()


def set_mock_analysis(key: str, analysis: AnalysisPayload) -> None:
    """Set a mock analysis to return."""
    MOCK_ANALYSES[key] = analysis


def set_mock_analysis_failure(concept_id: str, fail: bool, fail_count: int = 1) -> None:
    """Configure mock to fail for a concept."""
    MOCK_ANALYSIS_FAILURE_MODE[concept_id] = fail
    MOCK_ANALYSIS_FAILURE_COUNT[concept_id] = fail_count


def _get_analysis_key(student_id: str, concept_id: str, cycle: int) -> str:
    """Generate a key for the analysis."""
    return f"{student_id}:{concept_id}:c{cycle}"


def _calculate_mastery_trend(current: Diagnosis, history: list[Diagnosis]) -> tuple[float, TrendLabel]:
    """Calculate mastery estimate and trend from history."""
    if not history:
        # First cycle - base on current mastery
        mastery = current.mastery_estimate
        if mastery >= 0.8:
            trend = TrendLabel.STABLE
        elif mastery >= 0.5:
            trend = TrendLabel.NEW
        else:
            trend = TrendLabel.STILL_WEAK
        return mastery, trend
    
    # Calculate trend from history
    prev_mastery = history[-1].mastery_estimate
    current_mastery = current.mastery_estimate
    delta = current_mastery - prev_mastery
    
    if delta > 0.1:
        trend = TrendLabel.IMPROVING
    elif delta < -0.1:
        trend = TrendLabel.DECLINING
    elif current_mastery >= 0.8:
        trend = TrendLabel.STABLE
    elif current_mastery < 0.5:
        trend = TrendLabel.STILL_WEAK
    else:
        trend = TrendLabel.STABLE
    
    return current_mastery, trend


def analyze(diagnosis: Diagnosis, history: list[Diagnosis], cycle_number: int) -> AnalysisPayload:
    """
    Analyze a diagnosis in the context of history to produce mastery/trend analysis.
    
    Args:
        diagnosis: The current diagnosis
        history: Previous diagnoses for this student/concept
        cycle_number: The current cycle number
    
    Returns:
        AnalysisPayload with mastery estimate and trend
    """
    import time
    time.sleep(0.05)  # Simulate LLM latency
    
    key = _get_analysis_key(diagnosis.student_id, diagnosis.concept_id, cycle_number)
    
    # Check for mock failure mode
    if MOCK_ANALYSIS_FAILURE_MODE.get(diagnosis.concept_id, False):
        count = MOCK_ANALYSIS_FAILURE_COUNT.get(diagnosis.concept_id, 1)
        MOCK_ANALYSIS_FAILURE_COUNT[diagnosis.concept_id] = count - 1
        if count > 0:
            raise AnalysisError(f"Mock LLM failure for analysis of concept {diagnosis.concept_id}")
        MOCK_ANALYSIS_FAILURE_MODE[diagnosis.concept_id] = False
    
    # Return mock analysis if available
    if key in MOCK_ANALYSES:
        return MOCK_ANALYSES[key]
    
    mastery_estimate, trend = _calculate_mastery_trend(diagnosis, history)
    
    return AnalysisPayload(
        student_id=diagnosis.student_id,
        concept_id=diagnosis.concept_id,
        mastery_estimate=mastery_estimate,
        trend=trend,
        cycle_number=cycle_number,
        run_id=None  # Would be set by caller
    )