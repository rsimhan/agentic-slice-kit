"""
demo/feynman/batch.py - Cohort Aggregator & Professor Escalation Pipeline.

Implements Member 4 responsibilities for Socratic Feynman Check & Batch Gap Ping:
1. Persistence of student sessions to data/students/{student_id}.json
2. Scanning and deterministic aggregation of fallacy clusters across the cohort
3. Telemetry tracking in data/batch_telemetry.json
4. Threshold evaluation (BATCH_ALERT_THRESHOLD = 3)
5. 2-Minute Remediation Brief generation in reports/INSTRUCTOR_ALERT_<date>.md
6. Human-in-the-Loop review gates:
   - Interactive CLI ([A]cknowledge / [D]ismiss)
   - Slice Store / Web callback integration via slice.callback.ask & web/expert.py
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Literal, Optional, Tuple

from .schema import (
    BatchMisconceptionCluster,
    ProfessorEscalationReport,
    StudentSessionRecord,
)
from .stub import CANNED_CLUSTER, CANNED_ESCALATION_REPORT

# ---------------------------------------------------------------------------
# Architecture Constants
# ---------------------------------------------------------------------------
BATCH_ALERT_THRESHOLD: int = 3
DEFAULT_STUDENTS_DIR: Path = Path("data/students")
DEFAULT_TELEMETRY_PATH: Path = Path("data/batch_telemetry.json")
DEFAULT_REPORTS_DIR: Path = Path("reports")

# Curated pedagogical knowledge base for instant 2-minute lecture interventions
FALLACY_KNOWLEDGE_BASE: Dict[str, Dict[str, str]] = {
    "TLB_MISS_EQUALS_DISK_IO": {
        "title": "Conflating TLB Miss with Page Fault / Disk Swap",
        "derailment": (
            "Students assume that a Translation Lookaside Buffer (TLB) cache miss means "
            "the data is absent from physical RAM and immediately triggers a secondary storage read. "
            "They overlook that the MMU checks the in-memory Page Table in RAM first."
        ),
        "remediation_suggestion": (
            "Draw the 3-Tier Hierarchy on chalkboard:\n"
            "  (1) TLB Cache -> (2) RAM Page Table -> (3) Disk Swap.\n"
            "Key Takeaway: A TLB miss is resolved in RAM 99% of the time via page table walking "
            "without disk involvement. Disk read only occurs if Page Table valid bit is 0."
        ),
    },
    "OFFSET_MODIFIED_DURING_TRANSLATION": {
        "title": "Asserting Offset Modification during Address Translation",
        "derailment": (
            "Students assume that virtual offset bits are transformed or recalculated during "
            "virtual address translation. In reality, page size equals frame size, so offset bits pass "
            "directly into the physical address unchanged."
        ),
        "remediation_suggestion": (
            "Draw side-by-side Page vs Frame diagram showing 4KB boundaries.\n"
            "Key Takeaway: Address translation only maps Virtual Page Number (VPN) to Physical Frame "
            "Number (PFN); offset bits pass through unmodified."
        ),
    },
    "CIRCULAR_WAIT_ALONE_IS_DEADLOCK": {
        "title": "Circular Wait Alone Treated as Deadlock",
        "derailment": (
            "Students assume any cycle in a resource allocation graph implies deadlock, forgetting "
            "that in multi-instance resource systems, an un-blocked process can release an instance "
            "and break the cycle."
        ),
        "remediation_suggestion": (
            "Draw a 2-instance resource graph with a cycle where a 3rd process holds and releases.\n"
            "Key Takeaway: All 4 Coffman conditions must hold simultaneously; in multi-instance systems, "
            "a cycle is a necessary but NOT sufficient condition for deadlock."
        ),
    },
    "STARVATION_EQUALS_DEADLOCK": {
        "title": "Conflating Starvation with Deadlock",
        "derailment": (
            "Students conflate temporary indefinite delay caused by unfair scheduling priority "
            "with an unresolvable circular dependency."
        ),
        "remediation_suggestion": (
            "Draw Priority Queue vs Circular Dependency graph.\n"
            "Key Takeaway: Starvation resolves when high-priority load subsides; Deadlock can never "
            "resolve without external preemption or termination."
        ),
    },
    "ADVERSARIAL_INJECTION_OR_EVASION": {
        "title": "Prompt Injection or Evasion Attempt",
        "derailment": (
            "Submission attempted to bypass conceptual verification using prompt injection meta-prompts."
        ),
        "remediation_suggestion": (
            "Enforce strict conceptual guardrails and remind students that invariant checks are mandatory."
        ),
    },
}


# ---------------------------------------------------------------------------
# 1. Student Session Persistence
# ---------------------------------------------------------------------------

def save_student_session(
    record: StudentSessionRecord | Dict[str, Any],
    student_dir: Path | str = DEFAULT_STUDENTS_DIR,
) -> Path:
    """
    Persists a single student session audit record to data/students/{student_id}.json.
    Accepts a StudentSessionRecord instance or a compatible dictionary.
    """
    if isinstance(record, dict):
        validated_record = StudentSessionRecord.model_validate(record)
    else:
        validated_record = record

    target_dir = Path(student_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    file_path = target_dir / f"{validated_record.student_id}.json"
    file_path.write_text(validated_record.model_dump_json(indent=2), encoding="utf-8")
    return file_path


# ---------------------------------------------------------------------------
# 2. Scanning Student Records
# ---------------------------------------------------------------------------

def scan_student_records(
    student_dir: Path | str = DEFAULT_STUDENTS_DIR,
) -> List[StudentSessionRecord]:
    """
    Scans and deserializes all JSON student records in data/students/*.json.
    Returns a list of valid StudentSessionRecord instances.
    """
    target_dir = Path(student_dir)
    if not target_dir.exists():
        return []

    records: List[StudentSessionRecord] = []
    for json_file in sorted(target_dir.glob("*.json")):
        try:
            content = json_file.read_text(encoding="utf-8")
            record = StudentSessionRecord.model_validate_json(content)
            records.append(record)
        except Exception:
            # Skip invalid or non-matching files safely
            continue

    return records


# ---------------------------------------------------------------------------
# 3. Telemetry Aggregation & Clustering
# ---------------------------------------------------------------------------

def aggregate_cohort_telemetry(
    records: Optional[List[StudentSessionRecord]] = None,
    student_dir: Path | str = DEFAULT_STUDENTS_DIR,
    output_file: Optional[Path | str] = DEFAULT_TELEMETRY_PATH,
) -> Dict[str, BatchMisconceptionCluster]:
    """
    Deterministically aggregates fallacy clusters across student records.
    Groups records by `tagged_fallacy` and tallies occurrence count and quotes.
    Writes telemetry snapshot to data/batch_telemetry.json.
    """
    if records is None:
        records = scan_student_records(student_dir)

    # Group by tagged fallacy
    groups: Dict[str, List[StudentSessionRecord]] = {}
    for rec in records:
        tag = rec.tagged_fallacy
        if tag and tag.strip():
            groups.setdefault(tag.strip(), []).append(rec)

    clusters: Dict[str, BatchMisconceptionCluster] = {}
    for tag, group_records in groups.items():
        # Collect distinct quotes from initial text and revisions
        quotes: List[str] = []
        for r in group_records:
            if r.initial_text and r.initial_text.strip():
                # Extract representative snippet
                snip = r.initial_text.strip()
                if len(snip) > 120:
                    snip = snip[:117] + "..."
                if snip not in quotes:
                    quotes.append(snip)
            for rev in r.student_revisions:
                if rev and rev.strip():
                    rev_snip = rev.strip()
                    if len(rev_snip) > 120:
                        rev_snip = rev_snip[:117] + "..."
                    if rev_snip not in quotes:
                        quotes.append(rev_snip)

        # Fallback sample quote if empty
        if not quotes:
            quotes = [f"Student exhibited misconception tagged as {tag}"]

        # Look up remediation suggestion from knowledge base or fallback
        kb_entry = FALLACY_KNOWLEDGE_BASE.get(tag, {})
        suggestion = kb_entry.get(
            "remediation_suggestion",
            f"Review lecture invariants for concept regarding {tag.replace('_', ' ').lower()}.",
        )

        cluster = BatchMisconceptionCluster(
            fallacy_tag=tag,
            occurrence_count=len(group_records),
            affected_student_ids=[r.student_id for r in group_records],
            sample_student_quotes=quotes[:5],
            remediation_suggestion=suggestion,
        )
        clusters[tag] = cluster

    # Save to batch_telemetry.json if output path is requested
    if output_file is not None:
        out_path = Path(output_file)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        telemetry_payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_students_scanned": len(records),
            "cluster_count": len(clusters),
            "clusters": {k: v.model_dump() for k, v in clusters.items()},
        }
        out_path.write_text(json.dumps(telemetry_payload, indent=2), encoding="utf-8")

    return clusters


# ---------------------------------------------------------------------------
# 4. Threshold Evaluation
# ---------------------------------------------------------------------------

def check_escalation_threshold(
    clusters: Dict[str, BatchMisconceptionCluster],
    threshold: int = BATCH_ALERT_THRESHOLD,
) -> List[BatchMisconceptionCluster]:
    """
    Evaluates clusters against the alert threshold (default >= 3).
    Returns list of clusters that breached the threshold.
    """
    breached: List[BatchMisconceptionCluster] = []
    for cluster in clusters.values():
        if cluster.occurrence_count >= threshold:
            breached.append(cluster)
    return breached


# ---------------------------------------------------------------------------
# 5. Remediation Brief & Report Generator
# ---------------------------------------------------------------------------

def generate_instructor_alert(
    cluster: BatchMisconceptionCluster,
    concept_id: str = "virtual_memory",
    reports_dir: Path | str = DEFAULT_REPORTS_DIR,
    date_str: Optional[str] = None,
    call_llm: Optional[Callable] = None,
    stub_mode: bool = True,
) -> Tuple[ProfessorEscalationReport, Path]:
    """
    Generates the 2-Minute Remediation Brief formatted for the course professor.
    Writes markdown report to reports/INSTRUCTOR_ALERT_<date>.md.
    Returns (ProfessorEscalationReport, Path).
    """
    if date_str is None:
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    target_dir = Path(reports_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    report_id = f"INSTRUCTOR_ALERT_{date_str}_{concept_id.upper()}"
    timestamp = datetime.now(timezone.utc).isoformat()

    # Retrieve pedagogical derailment info
    kb_entry = FALLACY_KNOWLEDGE_BASE.get(cluster.fallacy_tag, {})
    fallacy_title = kb_entry.get("title", cluster.fallacy_tag.replace("_", " ").title())
    derailment = kb_entry.get(
        "derailment",
        "Students' mental models derailed from physical architecture realities.",
    )
    remediation_text = cluster.remediation_suggestion

    # Format quotes section
    quote_lines = []
    for i, q in enumerate(cluster.sample_student_quotes, start=1):
        stud_id = (
            cluster.affected_student_ids[i - 1]
            if i - 1 < len(cluster.affected_student_ids)
            else "Anonymous"
        )
        quote_lines.append(f'  - "{q}" *(Student {stud_id})*')
    quotes_formatted = "\n".join(quote_lines)

    # Build Markdown Content matching AgentSpec Section 4 & prompts/remediation.md
    report_md = f"""# [URGENT CONCEPT GAP DETECTED: CS8492 - {concept_id.replace('_', ' ').title()}]

**Date:** {date_str}  
**Report ID:** `{report_id}`  
**Status:** `WAITING_FOR_PROFESSOR`  
**Threshold Trigger:** {cluster.occurrence_count} students (Threshold $\\ge$ {BATCH_ALERT_THRESHOLD})

---

## 1. Summary of Misconception
- **Fallacy Name:** **{fallacy_title}** (`{cluster.fallacy_tag}`)
- **Affected Students:** {cluster.occurrence_count} students: {', '.join(cluster.affected_student_ids)}
- **Pedagogical Root Cause:**
  {derailment}

## 2. Anonymized Evidence
Direct excerpts demonstrating the misconception:
{quotes_formatted}

## 3. Recommended 2-Minute Lecture Intervention
{remediation_text}

---

> ### Human-in-the-Loop Review Gate
> **Action Required from Course Instructor:**
> - `[A]` **Acknowledge:** Add 2-minute remediation slide to next lecture queue.
> - `[D]` **Dismiss:** Mark as pedagogical noise.
"""

    report_file = target_dir / f"INSTRUCTOR_ALERT_{date_str}.md"
    report_file.write_text(report_md, encoding="utf-8")

    # Also write a static symlink/copy to INSTRUCTOR_ALERT.md for convenient reference
    generic_file = target_dir / "INSTRUCTOR_ALERT.md"
    generic_file.write_text(report_md, encoding="utf-8")

    report_model = ProfessorEscalationReport(
        report_id=report_id,
        concept_id=concept_id,
        timestamp=timestamp,
        cluster=cluster,
        status="WAITING_ACK",
    )

    return report_model, report_file


# ---------------------------------------------------------------------------
# 6. Human-in-the-Loop Review Gate
# ---------------------------------------------------------------------------

def escalate_to_professor(
    report: ProfessorEscalationReport,
    mode: Literal["cli", "web", "auto_ack"] = "cli",
    action: Optional[str] = None,
    store: Any = None,
    run_id: Optional[str] = None,
    settings: Any = None,
) -> ProfessorEscalationReport:
    """
    Executes the Human-in-the-Loop review gate.
    - 'cli': Prompts professor in terminal for [A]cknowledge / [D]ismiss.
    - 'auto_ack': Automatically marks as ACKNOWLEDGED (used in automated batch tests).
    - 'web': Suspends run on a human by parking a Question in slice.store.Store.
    """
    # 1. Web Callback via Slice Store
    if mode == "web" and store is not None and run_id is not None:
        try:
            from slice import callback
            question_text = (
                f"{report.cluster.occurrence_count} students exhibited identical fallacy: "
                f"[{report.cluster.fallacy_tag}]. Acknowledge 2-minute remediation slide? [A/D]"
            )
            context = {
                "report_id": report.report_id,
                "concept_id": report.concept_id,
                "fallacy_tag": report.cluster.fallacy_tag,
                "sample_quotes": "\n".join(report.cluster.sample_student_quotes),
                "remediation": report.cluster.remediation_suggestion,
                "resume_state": "complete",
            }
            callback.ask(store, run_id, question_text, context, settings)
            return report
        except Exception:
            pass  # Fall through to CLI mode

    # 2. Automated Action (Non-interactive)
    if mode == "auto_ack":
        report.status = "ACKNOWLEDGED"
        return report

    # 3. Provided Action
    if action is not None:
        act = action.strip().upper()
        if act.startswith("A"):
            report.status = "ACKNOWLEDGED"
        elif act.startswith("D"):
            report.status = "DISMISSED"
        return report

    # 4. Interactive CLI Mode
    print("\n" + "=" * 76)
    print(f" [!] PROFESSOR GAP ALERT: {report.concept_id.upper()} ({report.report_id})")
    print(f" Fallacy: {report.cluster.fallacy_tag} ({report.cluster.occurrence_count} students)")
    print("-" * 76)
    for q in report.cluster.sample_student_quotes[:3]:
        print(f"   * Quote: \"{q}\"")
    print("-" * 76)
    print(" 2-Minute Remediation Proposal:")
    for line in report.cluster.remediation_suggestion.splitlines():
        print(f"   {line}")
    print("=" * 76)

    try:
        user_input = input("Acknowledge to queue remediation in next lecture? [A]cknowledge / [D]ismiss: ").strip().upper()
        if user_input.startswith("A"):
            report.status = "ACKNOWLEDGED"
            print(" [OK] Alert ACKNOWLEDGED. Remediation slide queued for next lecture.\n")
        else:
            report.status = "DISMISSED"
            print(" [-] Alert DISMISSED by professor.\n")
    except (EOFError, KeyboardInterrupt):
        report.status = "WAITING_ACK"

    return report


# ---------------------------------------------------------------------------
# 7. Hook for demo/feynman/flow.py Integration
# ---------------------------------------------------------------------------

def check_and_escalate_batch(
    ctx: Any = None,
    student_dir: Path | str = DEFAULT_STUDENTS_DIR,
    threshold: int = BATCH_ALERT_THRESHOLD,
    interactive: bool = False,
) -> Optional[ProfessorEscalationReport]:
    """
    Hook called automatically by demo/feynman/flow.py:log_student_session_state.
    Scans student records, aggregates telemetry, checks threshold,
    and generates instructor alerts if threshold is reached.
    """
    records = scan_student_records(student_dir)
    clusters = aggregate_cohort_telemetry(records, student_dir=student_dir)
    breached = check_escalation_threshold(clusters, threshold=threshold)

    if not breached:
        return None

    # Handle breached clusters
    latest_report: Optional[ProfessorEscalationReport] = None
    for cluster in breached:
        report, _ = generate_instructor_alert(cluster)

        if ctx is not None and hasattr(ctx, "append"):
            ctx.append(
                "escalation_report",
                report.model_dump(),
                produced_by="agent:batch_aggregator",
            )

        if interactive:
            report = escalate_to_professor(report, mode="cli")

        latest_report = report

    return latest_report


# ---------------------------------------------------------------------------
# 8. Complete Pipeline Runner
# ---------------------------------------------------------------------------

def run_batch_pipeline(
    records: Optional[List[StudentSessionRecord]] = None,
    student_dir: Path | str = DEFAULT_STUDENTS_DIR,
    reports_dir: Path | str = DEFAULT_REPORTS_DIR,
    threshold: int = BATCH_ALERT_THRESHOLD,
    action: Optional[str] = None,
) -> Tuple[Dict[str, BatchMisconceptionCluster], List[ProfessorEscalationReport]]:
    """
    Orchestrates the entire batch aggregation and escalation pipeline:
    1. Scan/Receive records
    2. Aggregate telemetry & write data/batch_telemetry.json
    3. Detect clusters breaching threshold
    4. Generate reports/INSTRUCTOR_ALERT_<date>.md
    5. Evaluate professor action
    """
    clusters = aggregate_cohort_telemetry(records, student_dir=student_dir)
    breached = check_escalation_threshold(clusters, threshold=threshold)

    reports: List[ProfessorEscalationReport] = []
    for cluster in breached:
        report, _ = generate_instructor_alert(cluster, reports_dir=reports_dir)
        if action:
            report = escalate_to_professor(report, action=action)
        reports.append(report)

    return clusters, reports
