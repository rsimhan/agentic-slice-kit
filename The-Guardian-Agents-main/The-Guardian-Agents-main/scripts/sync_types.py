#!/usr/bin/env python3
"""
scripts/sync_types.py
Generates contracts/types.ts from contracts/schemas.py + api_contracts.py
Run in CI to prevent drift
"""

import sys
import json
from pathlib import Path
from typing import get_origin, get_args, Optional, Literal, Union
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from contracts.schemas import (
    RunState, MistakeClassification, TrendLabel, ReviewStatus,
    ConceptNode, CanonicalNote, Question, Test, Attempt,
    DiagnosisItem, Diagnosis, NoteVersion, TeacherNoteVersion,
    ReviewResult, AnalysisPayload, TeacherConfirmation,
    StudentHistory, ClassAnalytics, RunRecord, StepRecord,
    GraphEdge, ConceptGraph,
    MAX_REVISIONS_PER_CYCLE, MAX_MODEL_CALL_RETRIES,
    MAX_TEST_GENERATION_RETRIES,
    TAG_CONFIRMATION_TIMEOUT_SECONDS, MASTERY_WEAK_THRESHOLD,
    DEFAULT_MASTERY_ESTIMATE,
    SCHEMA_VERSION,
)
from contracts.api_contracts import (
    CreateConceptRequest, CreateConceptResponse,
    ConfirmTagsRequest, ConfirmTagsResponse,
    TeacherAnalyticsResponse, TeacherTrendsResponse,
    SubmitAttemptRequest, SubmitAttemptResponse,
    StudentNotesResponse, TeacherStudentNotesResponse,
    StudentGraphResponse, RunStatusResponse, ErrorResponse,
)


def python_type_to_ts(t) -> str:
    """Convert Python type annotation to TypeScript type"""
    origin = get_origin(t)
    args = get_args(t)

    if origin is list:
        return f"{python_type_to_ts(args[0])}[]"
    elif origin is dict:
        return f"Record<string, {python_type_to_ts(args[1])}>"
    elif origin is Optional:
        return f"{python_type_to_ts(args[0])} | undefined"
    elif origin is tuple:
        return f"[{', '.join(python_type_to_ts(a) for a in args)}]"
    elif origin is set:
        return f"{python_type_to_ts(args[0])}[]"

    # Handle literal types
    if hasattr(t, '__origin__') and t.__origin__ is Literal:
        return ' | '.join(f'"{v}"' for v in args)

    # Basic types
    type_map = {
        str: "string",
        int: "number",
        float: "number",
        bool: "boolean",
        datetime: "ISODateTime",
    }
    return type_map.get(t, "unknown")


def get_field_type(field) -> str:
    """Get TypeScript type for a Pydantic field"""
    return python_type_to_ts(field.annotation)


def generate_enum(enum_class) -> str:
    """Generate TypeScript enum from Python str Enum"""
    values = [f'  | "{v.value}"' for v in enum_class]
    return f"export type {enum_class.__name__} =\n" + "\n".join(values) + ";"


def generate_interface(model_class) -> str:
    """Generate TypeScript interface from Pydantic model"""
    lines = [f"export interface {model_class.__name__} {{"]
    for name, field in model_class.model_fields.items():
        ts_type = get_field_type(field)
        optional = "?" if not field.is_required() else ""
        lines.append(f"  {name}{optional}: {ts_type};")
    lines.append("}")
    return "\n".join(lines)


def main():
    contracts_dir = Path(__file__).parent.parent / "contracts"
    output_file = contracts_dir / "types.ts"

    output = []
    output.append("// contracts/types.ts")
    output.append("// GENERATED FROM contracts/schemas.py + api_contracts.py")
    output.append("// DO NOT EDIT DIRECTLY — Run scripts/sync_types.py to regenerate")
    output.append("")

    # Type aliases
    output.append("export type UUID = string;")
    output.append("export type ISODateTime = string; // ISO 8601 UTC")
    output.append("")

    # Enums
    output.append("// ═════════════════════════════════════════════════════════════════════════")
    output.append("// ENUMS")
    output.append("// ═══════════════════════════════════════════════════════════════════════════")
    output.append("")
    output.append(generate_enum(RunState))
    output.append("")
    output.append(generate_enum(MistakeClassification))
    output.append("")
    output.append(generate_enum(TrendLabel))
    output.append("")
    output.append(generate_enum(ReviewStatus))
    output.append("")

    # Core Domain Models
    output.append("// ════════════════════════════════════════════════════════════════════════════")
    output.append("// CORE DOMAIN MODELS")
    output.append("// ════════════════════════════════════════════════════════════════════════════")
    output.append("")
    for model in [ConceptNode, CanonicalNote, Question, Test, Attempt,
                  DiagnosisItem, Diagnosis, NoteVersion, TeacherNoteVersion,
                  ReviewResult, AnalysisPayload, TeacherConfirmation]:
        output.append(generate_interface(model))
        output.append("")

    # Aggregate / History Models
    output.append("// ════════════════════════════════════════════════════════════════════════════")
    output.append("// AGGREGATE / HISTORY")
    output.append("// ════════════════════════════════════════════════════════════════════════════")
    output.append("")
    for model in [StudentHistory, ClassAnalytics]:
        output.append(generate_interface(model))
        output.append("")

    # Runtime Records
    output.append("// ════════════════════════════════════════════════════════════════════════════")
    output.append("// RUNTIME RECORDS")
    output.append("// ════════════════════════════════════════════════════════════════════════════")
    output.append("")
    for model in [RunRecord, StepRecord]:
        output.append(generate_interface(model))
        output.append("")

    # Graph Models
    output.append("// ════════════════════════════════════════════════════════════════════════════")
    output.append("// GRAPH MODELS")
    output.append("// ════════════════════════════════════════════════════════════════════════════")
    output.append("")
    for model in [GraphEdge, ConceptGraph]:
        output.append(generate_interface(model))
        output.append("")

    # API Request/Response
    output.append("// ════════════════════════════════════════════════════════════════════════════")
    output.append("// API REQUEST/RESPONSE")
    output.append("// ════════════════════════════════════════════════════════════════════════════")
    output.append("")
    for model in [CreateConceptRequest, CreateConceptResponse,
                  ConfirmTagsRequest, ConfirmTagsResponse,
                  TeacherAnalyticsResponse, TeacherTrendsResponse,
                  SubmitAttemptRequest, SubmitAttemptResponse,
                  StudentNotesResponse, TeacherStudentNotesResponse,
                  StudentGraphResponse, RunStatusResponse, ErrorResponse]:
        output.append(generate_interface(model))
        output.append("")

# Constants
    output.append("// ═════════════════════════════════════════════════════════════════════════════")
    output.append("// CONSTANTS")
    output.append("// ═══════════════════════════════════════════════════════════════════════════")
    output.append("")
    output.append(f"export const MAX_REVISIONS_PER_CYCLE = {MAX_REVISIONS_PER_CYCLE};")
    output.append(f"export const MAX_MODEL_CALL_RETRIES = {MAX_MODEL_CALL_RETRIES};")
    output.append(f"export const MAX_TEST_GENERATION_RETRIES = {MAX_TEST_GENERATION_RETRIES};")
    output.append(f"export const TAG_CONFIRMATION_TIMEOUT_SECONDS = {TAG_CONFIRMATION_TIMEOUT_SECONDS};")
    output.append(f"export const MASTERY_WEAK_THRESHOLD = {MASTERY_WEAK_THRESHOLD};")
    output.append(f"export const DEFAULT_MASTERY_ESTIMATE = {DEFAULT_MASTERY_ESTIMATE};")
    output.append(f"export const SCHEMA_VERSION = {SCHEMA_VERSION};")

    output_file.write_text("\n".join(output) + "\n")
    print(f"Generated {output_file}")
    return 0


if __name__ == "__main__":
    sys.exit(main())