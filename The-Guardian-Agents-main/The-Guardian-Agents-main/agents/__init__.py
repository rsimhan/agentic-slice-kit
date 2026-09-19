# agents package
from .diagnosis import diagnose, DiagnosisError, reset_mock_state, set_mock_diagnosis, set_mock_diagnosis_failure
from .tailoring import tailor, TailoringError, reset_mock_state as reset_tailoring_mock, set_mock_note, set_mock_tailoring_failure
from .review import review, ReviewError, reset_mock_state as reset_review_mock, set_mock_review, set_mock_review_failure
from .analysis import analyze, AnalysisError, reset_mock_state as reset_analysis_mock, set_mock_analysis, set_mock_analysis_failure

__all__ = [
    # Diagnosis
    "diagnose",
    "DiagnosisError",
    "reset_mock_state",
    "set_mock_diagnosis",
    "set_mock_diagnosis_failure",
    # Tailoring
    "tailor",
    "TailoringError",
    "reset_tailoring_mock",
    "set_mock_note",
    "set_mock_tailoring_failure",
    # Review
    "review",
    "ReviewError",
    "reset_review_mock",
    "set_mock_review",
    "set_mock_review_failure",
    # Analysis
    "analyze",
    "AnalysisError",
    "reset_analysis_mock",
    "set_mock_analysis",
    "set_mock_analysis_failure",
]