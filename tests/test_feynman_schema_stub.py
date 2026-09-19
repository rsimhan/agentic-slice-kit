"""
Unit tests for Member 2 contracts and stubs:
- demo.feynman.schema
- demo.feynman.stub
"""
import pytest
from pydantic import ValidationError

from demo.feynman.schema import (
    BatchMisconceptionCluster,
    ConceptInvariant,
    CriticVerdict,
    ProbeMessage,
    ProfessorEscalationReport,
    StudentSessionRecord,
    StudentSubmission,
)
from demo.feynman.stub import (
    CANNED_CLUSTER,
    CANNED_ESCALATION_REPORT,
    CANNED_STUDENTS,
    StubCompleter,
    evaluate_student_text,
    generate_probe_for_flaw,
    get_canned_session_record,
    get_canned_student,
    get_cohort_records,
    stub_complete,
)


class TestCriticVerdictSchema:
    def test_mastered_verdict(self):
        v = CriticVerdict(
            verdict="MASTERED",
            violates_invariant=False,
            confidence=0.98,
        )
        assert v.verdict == "MASTERED"
        assert v.detected_flaw_tag is None
        assert not v.violates_invariant
        assert v.confidence == 0.98

    def test_misconception_verdict(self):
        v = CriticVerdict(
            verdict="MISCONCEPTION",
            detected_flaw_tag="TLB_MISS_EQUALS_DISK_IO",
            flaw_explanation="Conflated TLB miss with disk fault",
            violates_invariant=True,
            confidence=0.95,
        )
        assert v.verdict == "MISCONCEPTION"
        assert v.detected_flaw_tag == "TLB_MISS_EQUALS_DISK_IO"
        assert v.violates_invariant is True

    def test_ambiguous_verdict(self):
        v = CriticVerdict(
            verdict="AMBIGUOUS",
            detected_flaw_tag="VAGUE_EXPLANATION",
            confidence=0.8,
        )
        assert v.verdict == "AMBIGUOUS"

    def test_normalize_legacy_verdict_names(self):
        v1 = CriticVerdict(verdict="FALLACY_DETECTED", confidence=0.9)
        assert v1.verdict == "MISCONCEPTION"

        v2 = CriticVerdict(verdict="misconception", confidence=0.9)
        assert v2.verdict == "MISCONCEPTION"

    def test_confidence_validation_bounds(self):
        with pytest.raises(ValidationError):
            CriticVerdict(verdict="MASTERED", confidence=1.5)

        with pytest.raises(ValidationError):
            CriticVerdict(verdict="MASTERED", confidence=-0.1)


class TestProbeMessageSchema:
    def test_probe_message_valid(self):
        p = ProbeMessage(
            probe_id="probe_01",
            counter_example_scenario="What if the page is in RAM?",
            target_invariant="Invariant 1",
        )
        assert p.probe_id == "probe_01"
        assert "RAM" in p.counter_example_scenario

    def test_probe_message_missing_required_fields(self):
        with pytest.raises(ValidationError):
            ProbeMessage(probe_id="probe_01")


class TestStudentSessionRecordSchema:
    def test_session_record_serialization(self):
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
        data = rec.model_dump()
        assert data["student_id"] == "20231035053"
        assert data["final_verdict"] == "MASTERED"
        assert len(data["probes_issued"]) == 1

        json_str = rec.model_dump_json()
        restored = StudentSessionRecord.model_validate_json(json_str)
        assert restored == rec

    def test_session_record_max_iterations_bound(self):
        with pytest.raises(ValidationError):
            StudentSessionRecord(
                student_id="s1",
                concept_id="vm",
                iteration_count=3,  # Max is 2
                initial_text="x",
                final_verdict="MASTERED",
            )

    def test_normalize_resolved_verdict(self):
        rec = StudentSessionRecord(
            student_id="s1",
            concept_id="vm",
            initial_text="x",
            final_verdict="RESOLVED",
        )
        assert rec.final_verdict == "MASTERED"


class TestBatchAndEscalationSchemas:
    def test_batch_misconception_cluster(self):
        cluster = BatchMisconceptionCluster(
            fallacy_tag="TLB_MISS_EQUALS_DISK_IO",
            occurrence_count=3,
            affected_student_ids=["s1", "s2", "s3"],
            sample_student_quotes=["quote 1", "quote 2"],
            remediation_suggestion="Draw hierarchy slide",
        )
        assert cluster.occurrence_count == 3
        assert len(cluster.sample_student_quotes) == 2

    def test_professor_escalation_report(self):
        report = ProfessorEscalationReport(
            report_id="rep_01",
            concept_id="virtual_memory",
            timestamp="2026-09-19T11:46:00Z",
            cluster=CANNED_CLUSTER,
            status="WAITING_ACK",
        )
        assert report.status == "WAITING_ACK"
        assert report.cluster.occurrence_count == 3


class TestCannedStudentsAndMocks:
    def test_dilshan_canned_profile(self):
        dilshan = get_canned_student("dilshan")
        assert dilshan is not None
        assert dilshan["student_id"] == "20231035053"

        # Initial explanation triggers MISCONCEPTION
        v1 = evaluate_student_text(dilshan["initial_text"])
        assert v1.verdict == "MISCONCEPTION"
        assert v1.detected_flaw_tag == "TLB_MISS_EQUALS_DISK_IO"

        # Revision triggers MASTERED
        v2 = evaluate_student_text(dilshan["revision_text"])
        assert v2.verdict == "MASTERED"
        assert not v2.violates_invariant

    def test_siva_and_bakia_profiles(self):
        siva = get_canned_student("20231037154")
        assert siva is not None
        assert siva["name"] == "Siva"

        v_siva = evaluate_student_text(siva["initial_text"])
        assert v_siva.verdict == "MISCONCEPTION"
        assert v_siva.detected_flaw_tag == "TLB_MISS_EQUALS_DISK_IO"

        bakia = get_canned_student("bakia")
        assert bakia is not None
        v_bakia = evaluate_student_text(bakia["initial_text"])
        assert v_bakia.verdict == "MISCONCEPTION"
        assert v_bakia.detected_flaw_tag == "TLB_MISS_EQUALS_DISK_IO"

    def test_adversarial_injection_resistance(self):
        adv_text = CANNED_STUDENTS["adversarial"]["initial_text"]
        v = evaluate_student_text(adv_text)
        assert v.verdict == "MISCONCEPTION"
        assert v.detected_flaw_tag == "ADVERSARIAL_INJECTION_OR_EVASION"
        assert v.violates_invariant is True

    def test_ideal_and_ambiguous_evaluations(self):
        v_ideal = evaluate_student_text(CANNED_STUDENTS["mastered"]["initial_text"])
        assert v_ideal.verdict == "MASTERED"

        v_amb = evaluate_student_text(CANNED_STUDENTS["ambiguous"]["initial_text"])
        assert v_amb.verdict == "AMBIGUOUS"

    def test_deadlock_fallacies(self):
        v_cycle = evaluate_student_text("If there is a cycle in the resource allocation graph, the system is deadlocked.")
        assert v_cycle.verdict == "MISCONCEPTION"
        assert v_cycle.detected_flaw_tag == "CIRCULAR_WAIT_ALONE_IS_DEADLOCK"

        v_starve = evaluate_student_text("When a process waits too long in the queue, that is deadlock.")
        assert v_starve.verdict == "MISCONCEPTION"
        assert v_starve.detected_flaw_tag == "STARVATION_EQUALS_DEADLOCK"

    def test_cohort_records_helper(self):
        records = get_cohort_records()
        assert len(records) == 3
        tags = [r.tagged_fallacy for r in records]
        assert all(t == "TLB_MISS_EQUALS_DISK_IO" for t in tags)


class TestStubCompleter:
    def test_stub_complete_verdict(self):
        completer = StubCompleter()
        messages = [
            {"role": "system", "content": "You are a critic."},
            {"role": "user", "content": CANNED_STUDENTS["dilshan"]["initial_text"]},
        ]
        result = completer(messages=messages, schema=CriticVerdict)
        assert isinstance(result, CriticVerdict)
        assert result.verdict == "MISCONCEPTION"
        assert result.detected_flaw_tag == "TLB_MISS_EQUALS_DISK_IO"
        assert completer.call_count == 1

    def test_stub_complete_probe(self):
        completer = StubCompleter()
        messages = [
            {"role": "system", "content": "Generate probe."},
            {"role": "user", "content": "Flaw: TLB_MISS_EQUALS_DISK_IO"},
        ]
        probe = completer(messages=messages, schema=ProbeMessage)
        assert isinstance(probe, ProbeMessage)
        assert "RAM" in probe.counter_example_scenario

    def test_stub_complete_forced_responses_and_reset(self):
        completer = StubCompleter()
        forced = CriticVerdict(verdict="MASTERED", confidence=1.0)
        completer.force_verdict(forced)

        res = completer(messages=[{"role": "user", "content": "bad explanation"}], schema=CriticVerdict)
        assert res == forced

        completer.reset()
        assert completer.call_count == 0
        assert len(completer.calls) == 0
