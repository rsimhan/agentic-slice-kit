from models import DiagnosticRun, StudentState, Hypothesis, DiagnosticCheck
from store import save

MAX_ATTEMPTS = 6
MAX_REVISIONS = 3

VALID_RESULTS = {"supports", "contradicts", "uncertain"}
TERMINAL_STATES = {"STORE"}


class DiagnosticAgent:
    def __init__(self, student_id="S17", topic="recursion"):
        self.state = StudentState(student_id=student_id, topic=topic)
        self.run = DiagnosticRun(run_id="run-001", student_id=student_id)

    def load(self, state):
        # FIX: refuse to graft another learner's record onto this run.
        if state.student_id != self.run.student_id:
            raise ValueError(
                f"State belongs to {state.student_id}, run belongs to {self.run.student_id}"
            )
        self.state = state
        self.run.state = "OBSERVE"

    def choose_hypothesis(self, label, rationale):
        if self.run.state in TERMINAL_STATES:
            return None
        if self.run.attempts_used >= MAX_ATTEMPTS:
            self.safe_stop("attempt_limit")
            return None

        # FIX: the original loop used `continue`, so it never actually
        # prevented anything — a rejected cause could be re-proposed forever.
        for h in self.state.hypotheses:
            if h.label != label:
                continue
            if h.status == "rejected":
                return None          # already ruled out by evidence
            if h.status == "active":
                return h             # already under test; don't duplicate it

        hid = f"H{len(self.state.hypotheses) + 1}"
        h = Hypothesis(hid, label, rationale)
        self.state.hypotheses.append(h)
        self.run.state = "ASK_CHECK"
        return h

    def ask(self, hypothesis, question):
        # FIX: guard against a None hypothesis from a refused choose_hypothesis.
        if hypothesis is None:
            raise ValueError("Cannot ask a check without a hypothesis")
        if hypothesis.status != "active":
            raise ValueError(f"Hypothesis {hypothesis.id} is {hypothesis.status}, not active")
        if self.run.attempts_used >= MAX_ATTEMPTS:
            self.safe_stop("attempt_limit")
            return None

        cid = f"Q{len(self.state.checks) + 1}"
        check = DiagnosticCheck(cid, hypothesis.id, question)
        self.state.checks.append(check)
        self.run.attempts_used += 1
        self.run.state = "AWAIT_RESPONSE"
        return check

    def evaluate(self, check, response, result, evidence_note):
        # FIX: `ask` returns None at the attempt limit; the old code then blew up
        # with AttributeError deep inside evaluate.
        if check is None:
            raise ValueError("No check to evaluate (attempt limit may have been reached)")
        if result not in VALID_RESULTS:
            raise ValueError(f"Invalid evidence result: {result!r}")
        # FIX: an already-scored check could previously be re-scored, double-counting
        # revisions and flipping a hypothesis status.
        if check.result is not None:
            raise ValueError(f"Check {check.id} has already been evaluated")

        # FIX: unknown hypothesis_id raised a bare StopIteration instead of an error.
        h = next((x for x in self.state.hypotheses if x.id == check.hypothesis_id), None)
        if h is None:
            raise ValueError(f"No hypothesis {check.hypothesis_id} for check {check.id}")

        check.response = response
        check.result = result
        check.evidence_note = evidence_note
        h.evidence_ids.append(check.id)

        if result == "supports":
            h.status = "passed"
            self.state.current_gap = h.label
            self.state.confidence = "medium"
            self.run.state = "CONFIRM"

        elif result == "contradicts":
            h.status = "rejected"
            self.run.revisions_used += 1
            if self.run.revisions_used >= MAX_REVISIONS:
                self.safe_stop("revision_limit")
            else:
                self.run.state = "FORM_HYPOTHESIS"

        else:  # uncertain
            h.status = "uncertain"
            # FIX: ambiguous evidence must not name a gap. The old code set
            # current_gap here, so an "I'm not sure" answer produced a
            # diagnosis the evidence never supported.
            self.state.confidence = "low"
            self.run.state = "FORM_HYPOTHESIS"

        save(self.state)

    def confirm(self, answer):
        if self.run.state != "CONFIRM":
            raise ValueError("Confirmation is not currently allowed")

        if answer == "yes":
            self.state.confirmation_status = "confirmed"
            self.run.outcome = "confirmed_diagnosis"
            self.run.state = "STORE"
        elif answer == "no":
            self.state.confirmation_status = "rejected"
            # FIX: a rejected diagnosis must not remain the standing gap.
            self.state.current_gap = None
            self.state.confidence = "low"
            for h in self.state.hypotheses:
                if h.status == "passed":
                    h.status = "rejected"
            self.run.revisions_used += 1
            if self.run.revisions_used >= MAX_REVISIONS:
                self.safe_stop("revision_limit")
            else:
                self.run.state = "FORM_HYPOTHESIS"
        else:
            self.state.confirmation_status = "pending"
            self.run.state = "WAITING_FOR_CONFIRMATION"

        save(self.state)

    def safe_stop(self, reason):
        # FIX: guard against recursion — safe_stop is called from choose/ask,
        # which could otherwise re-enter it.
        if self.run.state in TERMINAL_STATES:
            return
        self.run.outcome = f"stopped:{reason}"
        self.run.state = "STORE"
        # FIX: don't downgrade an already-confirmed diagnosis back to "pending".
        if self.state.confirmation_status == "none":
            self.state.confirmation_status = "pending"
        save(self.state)
