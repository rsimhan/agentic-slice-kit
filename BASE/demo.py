from state_machine import DiagnosticAgent, MAX_ATTEMPTS
from store import load, reset


def case_revision():
    print("\n=== CASE: WRONG FIRST HYPOTHESIS -> REVISION ===")
    # FIX: the demo replayed on top of whatever was left on disk, so hypothesis
    # ids grew (H3, H5, ...) on every run and output was not reproducible.
    reset("S17")

    agent = DiagnosticAgent("S17")
    agent.load(load("S17"))

    h1 = agent.choose_hypothesis(
        "base_case",
        "Student reports recursion continues unexpectedly."
    )
    q1 = agent.ask(
        h1,
        "For factorial(3), when should recursion stop and what value should be returned?"
    )
    agent.evaluate(
        q1,
        "At n=0; return 1.",
        "contradicts",
        "Student demonstrated base-case understanding."
    )
    print("H1 rejected:", h1.label)

    # The rejected cause is now genuinely blocked from being re-proposed.
    print("re-propose base_case ->", agent.choose_hypothesis("base_case", "retry"))

    h2 = agent.choose_hypothesis(
        "call_stack",
        "Base case passed; call-stack tracing is a distinct candidate."
    )
    q2 = agent.ask(
        h2,
        "Trace factorial(3). What calls are waiting, and what happens after factorial(0) returns?"
    )
    agent.evaluate(
        q2,
        "I don't know what happens to the waiting calls.",
        "supports",
        "Student cannot explain the return chain."
    )

    print("H2 supported:", h2.label)
    print("State:", agent.run.state)
    print("Current gap:", agent.state.current_gap)
    print("Confidence:", agent.state.confidence)

    agent.confirm("yes")
    print("Confirmation:", agent.state.confirmation_status)


def case_insufficient():
    print("\n=== CASE: INSUFFICIENT EVIDENCE -> SAFE STOP ===")
    reset("S18")
    agent = DiagnosticAgent("S18")
    h = agent.choose_hypothesis("base_case", "Possible stopping-condition issue.")
    q = agent.ask(h, "What is the base case for this recursive function?")
    agent.evaluate(q, "Maybe? I'm not sure.", "uncertain", "Answer is ambiguous.")
    print("Gap after ambiguous evidence:", agent.state.current_gap)  # stays None
    agent.safe_stop("insufficient_evidence")
    print("Outcome:", agent.run.outcome)


def case_rejection():
    print("\n=== CASE: LEARNER REJECTS DIAGNOSIS ===")
    reset("S19")
    agent = DiagnosticAgent("S19")
    h = agent.choose_hypothesis("call_stack", "Possible tracing issue.")
    q = agent.ask(h, "Trace the recursive calls and returns.")
    agent.evaluate(q, "I can trace them correctly.", "supports", "Response supports the check.")
    agent.confirm("no")
    print("Confirmation:", agent.state.confirmation_status)
    print("Gap cleared:", agent.state.current_gap)
    print("Next state:", agent.run.state)


def case_attempt_limit():
    print("\n=== CASE: ATTEMPT LIMIT -> SAFE STOP ===")
    reset("S20")
    agent = DiagnosticAgent("S20")
    labels = ["base_case", "call_stack", "parameter_state"]
    for i in range(MAX_ATTEMPTS + 2):
        h = agent.choose_hypothesis(f"{labels[i % 3]}_{i}", "probing")
        if h is None:
            break
        q = agent.ask(h, "discriminating question?")
        if q is None:
            break
        agent.evaluate(q, "unclear", "uncertain", "ambiguous")
    print("Attempts used:", agent.run.attempts_used)
    print("Outcome:", agent.run.outcome)
    print("State:", agent.run.state)


if __name__ == "__main__":
    case_revision()
    case_insufficient()
    case_rejection()
    case_attempt_limit()
