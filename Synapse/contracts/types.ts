// contracts/types.ts
// GENERATED FROM contracts/schemas.py + api_contracts.py
// DO NOT EDIT DIRECTLY — Run scripts/sync_types.py to regenerate

export type UUID = string;
export type ISODateTime = string; // ISO 8601 UTC

// ═════════════════════════════════════════════════════════════════════════
// ENUMS
// ═══════════════════════════════════════════════════════════════════════════

export type RunState =
  | "teacher_setup"
  | "tag_confirmation"
  | "test_generating"
  | "test_ready"
  | "awaiting_student"
  | "attempt_received"
  | "diagnosing"
  | "tailoring"
  | "reviewing"
  | "note_saved"
  | "analysing"
  | "aggregating"
  | "complete"
  | "failed";

export type MistakeClassification =
  | "conceptual_gap"
  | "careless_mistake"
  | "contradictory"
  | "unrelated"
  | "empty";

export type TrendLabel =
  | "new"
  | "improving"
  | "stable"
  | "still_weak"
  | "declining";

export type ReviewStatus =
  | "passed"
  | "failed"
  | "revision_limit_reached";

// ════════════════════════════════════════════════════════════════════════════
// CORE DOMAIN MODELS
// ════════════════════════════════════════════════════════════════════════════

export interface ConceptNode {
  id?: string;
  name: string;
  summary: string;
  prerequisites?: string[];
  created_at?: ISODateTime;
  updated_at?: ISODateTime;
}

export interface CanonicalNote {
  concept_id: string;
  markdown: string;
  extracted_concepts?: unknown[];
  teacher_confirmed?: boolean;
  confirmed_at?: unknown;
  created_at?: ISODateTime;
}

export interface Question {
  id?: string;
  text: string;
  correct_answer: string;
  options: string[];
  concept_id: string;
}

export interface Test {
  id?: string;
  concept_id: string;
  concept_name: string;
  questions: unknown[];
  created_at?: ISODateTime;
}

export interface Attempt {
  student_id: string;
  test_id: string;
  concept_id: string;
  answers?: Record<string, string>;
  score?: number;
  total?: number;
  submitted_at?: ISODateTime;
}

export interface DiagnosisItem {
  question_id: string;
  classification: unknown;
  reason: string;
}

export interface Diagnosis {
  student_id: string;
  concept_id: string;
  items?: unknown[];
  mastery_estimate: number;
  trend: unknown;
  created_at?: ISODateTime;
}

export interface NoteVersion {
  student_id: string;
  concept_id: string;
  version: number;
  markdown: string;
  diagnosis_id?: unknown;
  review_id?: unknown;
  run_id?: unknown;
  created_at?: ISODateTime;
}

export interface TeacherNoteVersion {
  student_id: string;
  concept_id: string;
  version: number;
  diagnosis_id?: unknown;
  review_id?: unknown;
  run_id?: unknown;
  created_at: ISODateTime;
}

export interface ReviewResult {
  passed: boolean;
  canonical_coverage: boolean;
  diagnosis_addressed: boolean;
  links_valid: boolean;
  objections?: string[];
  status: unknown;
  created_at?: ISODateTime;
}

export interface AnalysisPayload {
  student_id: string;
  concept_id: string;
  mastery_estimate: number;
  trend: unknown;
  cycle_number: number;
  run_id?: unknown;
  created_at?: ISODateTime;
}

export interface TeacherConfirmation {
  concept_id: string;
  teacher_id: string;
  confirmed: boolean;
  edited_concepts?: unknown;
  confirmed_at?: unknown;
  timed_out?: boolean;
}

// ════════════════════════════════════════════════════════════════════════════
// AGGREGATE / HISTORY
// ════════════════════════════════════════════════════════════════════════════

export interface StudentHistory {
  student_id: string;
  concept_id: string;
  previous_diagnoses?: unknown[];
  previous_notes?: unknown[];
  mastery_history?: [number, number][];
  existing_concept_names?: string[];
}

export interface ClassAnalytics {
  concept_id: string;
  concept_name: string;
  student_count: number;
  average_mastery: number;
  trend_distribution?: Record<string, number>;
  weak_students?: string[];
  updated_at?: ISODateTime;
}

// ════════════════════════════════════════════════════════════════════════════
// RUNTIME RECORDS
// ════════════════════════════════════════════════════════════════════════════

export interface RunRecord {
  run_id?: string;
  concept_id: string;
  student_id?: unknown;
  teacher_id?: unknown;
  state?: unknown;
  current_cycle?: number;
  revision_count?: number;
  model_call_count?: number;
  test_generation_retry_count?: number;
  test_generation_error?: unknown;
  created_at?: ISODateTime;
  updated_at?: ISODateTime;
  completed_at?: unknown;
  error?: unknown;
}

export interface StepRecord {
  id?: string;
  run_id: string;
  step_name: string;
  input_data: unknown;
  output_data?: unknown;
  state_before: unknown;
  state_after?: unknown;
  started_at?: ISODateTime;
  completed_at?: unknown;
  error?: unknown;
  retry_count?: number;
}

// ════════════════════════════════════════════════════════════════════════════
// GRAPH MODELS
// ════════════════════════════════════════════════════════════════════════════

export interface GraphEdge {
  from_concept_id: string;
  to_concept_id: string;
  edge_type?: string;
}

export interface ConceptGraph {
  nodes: unknown[];
  edges: unknown[];
}

// ════════════════════════════════════════════════════════════════════════════
// API REQUEST/RESPONSE
// ════════════════════════════════════════════════════════════════════════════

export interface CreateConceptRequest {
  markdown: string;
  concept_name: string;
}

export interface CreateConceptResponse {
  concept: unknown;
  run_id: string;
}

export interface ConfirmTagsRequest {
  run_id: string;
  confirmed: boolean;
  edited_concepts?: unknown;
}

export interface ConfirmTagsResponse {
  run_id: string;
  state: unknown;
  test?: unknown;
  error?: unknown;
}

export interface TeacherAnalyticsResponse {
  concept_id: string;
  concept_name: string;
  analytics: unknown;
}

export interface TeacherTrendsResponse {
  concept_id: string;
  trends: unknown[];
}

export interface SubmitAttemptRequest {
  test_id: string;
  answers?: Record<string, string>;
}

export interface SubmitAttemptResponse {
  attempt: unknown;
  diagnosis: unknown;
  note: unknown;
  review: unknown;
  analysis: unknown;
}

export interface StudentNotesResponse {
  notes: unknown[];
}

export interface TeacherStudentNotesResponse {
  notes: unknown[];
}

export interface StudentGraphResponse {
  nodes: unknown[];
  edges: unknown[];
}

export interface RunStatusResponse {
  run_id: string;
  state: unknown;
  current_cycle: number;
  revision_count: number;
  model_call_count: number;
  test_generation_retry_count?: number;
  test_generation_error?: unknown;
  error?: unknown;
}

export interface ErrorResponse {
  error: string;
  message: string;
  details?: unknown;
}

// ═════════════════════════════════════════════════════════════════════════════
// CONSTANTS
// ═══════════════════════════════════════════════════════════════════════════

export const MAX_REVISIONS_PER_CYCLE = 3;
export const MAX_MODEL_CALL_RETRIES = 3;
export const MAX_TEST_GENERATION_RETRIES = 3;
export const TAG_CONFIRMATION_TIMEOUT_SECONDS = 600;
export const MASTERY_WEAK_THRESHOLD = 0.5;
export const DEFAULT_MASTERY_ESTIMATE = 0.5;
export const SCHEMA_VERSION = 3;
