"""
Unit and integration tests for Member 4: Cohort & Escalation Pipeline.
Validates:
- Student session persistence
- Batch telemetry scanning and mathematical aggregation
- Threshold-based escalation trigger (count >= 3)
- Instructor Alert Markdown report formatting
- Human-in-the-Loop review gate ([A]cknowledge / [D]ismiss)
- Flow hook integration (check_and_escalate_batch)
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from demo.feynman.batch import (
    BATCH_ALERT_THRESHOLD,
    aggregate_cohort_telemetry,
    check_and_escalate_batch,
    check_escalation_threshold,
    escalate_to_professor,
    generate_instructor_alert,
    run_batch_pipeline,
    save_student_session,
    scan_student_records,
)
from demo.feynman.schema import (
    BatchMisconceptionCluster,
    ProfessorEscalationReport,
    StudentSessionRecord,
)
from demo.feynman.stub import CANNED_STUDENTS, get_cohort_records


@pytest.fixture
def temp_workspace(tmp_path: Path):
    """Provides isolated students, telemetry, and reports directories."""
    students_dir = tmp_path / "students"
    students_dir.mkdir(parents=True, exist_ok=True)

    reports_dir = tmp_path / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    telemetry_file = tmp_path / "batch_telemetry.json"

    return {
        "students_dir": students_dir,
        "reports_dir": reports_dir,
        "telemetry_file": telemetry_file,
    }


class TestSessionPersistence:
    def test_save_and_scan_student_session(self, temp_workspace):
        students_dir = temp_workspace["students_dir"]
        rec = StudentSessionRecord(
            student_id="20231035053",
            concept_id="virtual_memory",
            iteration_count=1,
            initial_text="TLB miss is a page fault",
            probes_issued=["What happens in RAM first?"],
            student_revisions=["MMU walks the page table in RAM first"],
            final_verdict="MASTERED",
            tagged_fallacy="TLB_MISS_EQUALS_DISK_IO",
        )

        saved_path = save_student_session(rec, student_dir=students_dir)
        assert saved_path.exists()
        assert saved_path.name == "20231035053.json"

        # Verify on-disk JSON
        data = json.loads(saved_path.read_text(encoding="utf-8"))
        assert data["student_id"] == "20231035053"
        assert data["tagged_fallacy"] == "TLB_MISS_EQUALS_DISK_IO"

        # Scan back
        scanned = scan_student_records(student_dir=students_dir)
        assert len(scanned) == 1
        assert scanned[0].student_id == "20231035053"

    def test_scan_empty_directory(self, temp_workspace):
        empty_dir = temp_workspace["students_dir"]
        records = scan_student_records(student_dir=empty_dir)
        assert records == []


class TestCohortTelemetryAggregation:
    def test_aggregate_cohort_telemetry_grouping(self, temp_workspace):
        students_dir = temp_workspace["students_dir"]
        telemetry_file = temp_workspace["telemetry_file"]

        # Commit Dilshan, Siva, and Bakia
        cohort = get_cohort_records()
        for rec in cohort:
            save_student_session(rec, student_dir=students_dir)

        clusters = aggregate_cohort_telemetry(
            student_dir=students_dir, output_file=telemetry_file
        )

        assert "TLB_MISS_EQUALS_DISK_IO" in clusters
        cluster = clusters["TLB_MISS_EQUALS_DISK_IO"]
        assert cluster.occurrence_count == 3
        assert len(cluster.affected_student_ids) == 3
        assert "20231035053" in cluster.affected_student_ids
        assert "20231037154" in cluster.affected_student_ids
        assert "2023103057" in cluster.affected_student_ids
        assert len(cluster.sample_student_quotes) >= 1

        # Check telemetry file on disk
        assert telemetry_file.exists()
        telemetry_json = json.loads(telemetry_file.read_text(encoding="utf-8"))
        assert telemetry_json["total_students_scanned"] == 3
        assert "TLB_MISS_EQUALS_DISK_IO" in telemetry_json["clusters"]

    def test_aggregate_cohort_telemetry_excludes_none_fallacies(self, temp_workspace):
        students_dir = temp_workspace["students_dir"]
        telemetry_file = temp_workspace["telemetry_file"]

        ideal = CANNED_STUDENTS["mastered"]["session_record"]
        save_student_session(ideal, student_dir=students_dir)

        clusters = aggregate_cohort_telemetry(
            student_dir=students_dir, output_file=telemetry_file
        )
        assert len(clusters) == 0


class TestThresholdEvaluation:
    def test_sub_threshold_does_not_breach(self):
        cluster = BatchMisconceptionCluster(
            fallacy_tag="TLB_MISS_EQUALS_DISK_IO",
            occurrence_count=2,  # Below threshold 3
            affected_student_ids=["s1", "s2"],
            sample_student_quotes=["quote"],
            remediation_suggestion="suggestion",
        )
        breached = check_escalation_threshold({"tag": cluster}, threshold=3)
        assert len(breached) == 0

    def test_threshold_breached_at_three(self):
        cluster = BatchMisconceptionCluster(
            fallacy_tag="TLB_MISS_EQUALS_DISK_IO",
            occurrence_count=3,  # Meets threshold 3
            affected_student_ids=["s1", "s2", "s3"],
            sample_student_quotes=["quote"],
            remediation_suggestion="suggestion",
        )
        breached = check_escalation_threshold({"tag": cluster}, threshold=3)
        assert len(breached) == 1
        assert breached[0].fallacy_tag == "TLB_MISS_EQUALS_DISK_IO"


class TestAlertGenerationAndRemediation:
    def test_generate_instructor_alert_report(self, temp_workspace):
        reports_dir = temp_workspace["reports_dir"]
        cluster = BatchMisconceptionCluster(
            fallacy_tag="TLB_MISS_EQUALS_DISK_IO",
            occurrence_count=3,
            affected_student_ids=["20231035053", "20231037154", "2023103057"],
            sample_student_quotes=[
                "TLB miss means data is not in memory",
                "Fetches from hard drive",
            ],
            remediation_suggestion="Draw the 3-Tier Hierarchy on chalkboard: (1) TLB Cache -> (2) RAM Page Table -> (3) Disk Swap.",
        )

        report, report_path = generate_instructor_alert(
            cluster=cluster,
            concept_id="virtual_memory",
            reports_dir=reports_dir,
            date_str="2026-09-19",
        )

        assert report.status == "WAITING_ACK"
        assert report.concept_id == "virtual_memory"
        assert report_path.exists()
        assert report_path.name == "INSTRUCTOR_ALERT_2026-09-19.md"

        content = report_path.read_text(encoding="utf-8")
        assert "URGENT CONCEPT GAP DETECTED" in content
        assert "TLB_MISS_EQUALS_DISK_IO" in content
        assert "3-Tier Hierarchy" in content
        assert "WAITING_FOR_PROFESSOR" in content

        # Generic symlink/file exists too
        assert (reports_dir / "INSTRUCTOR_ALERT.md").exists()


class TestProfessorEscalationGates:
    def test_escalate_to_professor_acknowledge(self):
        report = ProfessorEscalationReport(
            report_id="rep_test_01",
            concept_id="virtual_memory",
            timestamp="2026-09-19T12:00:00Z",
            cluster=BatchMisconceptionCluster(
                fallacy_tag="TLB_MISS_EQUALS_DISK_IO",
                occurrence_count=3,
                affected_student_ids=["s1", "s2", "s3"],
                sample_student_quotes=["q"],
                remediation_suggestion="r",
            ),
            status="WAITING_ACK",
        )

        updated = escalate_to_professor(report, action="A")
        assert updated.status == "ACKNOWLEDGED"

    def test_escalate_to_professor_dismiss(self):
        report = ProfessorEscalationReport(
            report_id="rep_test_02",
            concept_id="virtual_memory",
            timestamp="2026-09-19T12:00:00Z",
            cluster=BatchMisconceptionCluster(
                fallacy_tag="TLB_MISS_EQUALS_DISK_IO",
                occurrence_count=3,
                affected_student_ids=["s1", "s2", "s3"],
                sample_student_quotes=["q"],
                remediation_suggestion="r",
            ),
            status="WAITING_ACK",
        )

        updated = escalate_to_professor(report, action="D")
        assert updated.status == "DISMISSED"

    def test_escalate_to_professor_auto_ack(self):
        report = ProfessorEscalationReport(
            report_id="rep_test_03",
            concept_id="virtual_memory",
            timestamp="2026-09-19T12:00:00Z",
            cluster=BatchMisconceptionCluster(
                fallacy_tag="TLB_MISS_EQUALS_DISK_IO",
                occurrence_count=3,
                affected_student_ids=["s1", "s2", "s3"],
                sample_student_quotes=["q"],
                remediation_suggestion="r",
            ),
            status="WAITING_ACK",
        )

        updated = escalate_to_professor(report, mode="auto_ack")
        assert updated.status == "ACKNOWLEDGED"


class TestPipelineEndToEnd:
    def test_run_batch_pipeline_full_flow(self, temp_workspace):
        students_dir = temp_workspace["students_dir"]
        reports_dir = temp_workspace["reports_dir"]

        # 3 student files with same fallacy
        records = get_cohort_records()
        for r in records:
            save_student_session(r, student_dir=students_dir)

        clusters, reports = run_batch_pipeline(
            student_dir=students_dir,
            reports_dir=reports_dir,
            threshold=3,
            action="A",
        )

        assert len(clusters) == 1
        assert "TLB_MISS_EQUALS_DISK_IO" in clusters
        assert len(reports) == 1
        assert reports[0].status == "ACKNOWLEDGED"
        assert (reports_dir / "INSTRUCTOR_ALERT.md").exists()

    def test_check_and_escalate_batch_hook(self, temp_workspace):
        students_dir = temp_workspace["students_dir"]

        # Commit 3 records
        for r in get_cohort_records():
            save_student_session(r, student_dir=students_dir)

        # Mock context from slice.runner
        mock_ctx = MagicMock()
        mock_ctx.append = MagicMock()

        report = check_and_escalate_batch(
            ctx=mock_ctx,
            student_dir=students_dir,
            threshold=3,
            interactive=False,
        )

        assert report is not None
        assert report.cluster.fallacy_tag == "TLB_MISS_EQUALS_DISK_IO"
        assert mock_ctx.append.called
        call_args = mock_ctx.append.call_args[0]
        assert call_args[0] == "escalation_report"
