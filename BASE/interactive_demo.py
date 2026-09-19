"""
Interactive mode: YOU play the student.

No API key, no internet, no LLM. Instead of a real model reading your
answer, this uses a small keyword-matching function (see `judge_answer`
below) to decide supports / contradicts / uncertain. It's not smart -
it's just checking for a few telltale words - but it's real code making
a real decision based on what you actually type, and it feeds straight
into the same DiagnosticAgent controller that demo.py uses.

Run it with:
    python interactive_demo.py
"""

from state_machine import DiagnosticAgent
from store import reset

# One scripted question per candidate cause. In the full version, an LLM
# would write these dynamically. Here they're fixed so the keyword judge
# below has a fighting chance of understanding your answer.
QUESTIONS = {
    "base_case": "For factorial(3), when should the recursion stop, and what value should it return at that point?",
    "call_stack": "Trace factorial(3) step by step. After factorial(0) returns, what happens to all the calls that were waiting?",
    "parameter_state": "If you forget to update the parameter you pass in the recursive call, what goes wrong?",
}

# Very rough keyword hints. This is deliberately simple - the point is to
# show the controller reacting to real input, not to build a real NLP model.
GOOD_KEYWORDS = {
    "base_case": ["n=0", "n == 0", "return 1", "stop", "base case"],
    "call_stack": ["stack", "unwind", "return chain", "waiting", "pop", "resume"],
    "parameter_state": ["decrement", "n-1", "update", "shrink", "smaller"],
}
UNSURE_PHRASES = ["not sure", "don't know", "maybe", "no idea", "?", "dunno", "idk"]


def judge_answer(cause: str, answer: str) -> tuple[str, str]:
    """Return (result, evidence_note) using simple keyword matching."""
    text = answer.lower().strip()

    if not text or any(p in text for p in UNSURE_PHRASES):
        return "uncertain", "Learner expressed uncertainty."

    hits = [kw for kw in GOOD_KEYWORDS[cause] if kw in text]
    if hits:
        return "supports", f"Answer mentioned: {', '.join(hits)}."

    return "contradicts", "Answer did not reference the expected concept."


def next_cause(tried_labels: set[str]) -> str | None:
    for cause in QUESTIONS:
        if cause not in tried_labels:
            return cause
    return None


def main():
    print("=== COGNIX Diagnostic Agent - interactive mode ===")
    print("You're playing the student. Answer honestly, or try to fool it -")
    print("either way you'll see the controller's real decisions.\n")

    student_id = input("Pick a student id (e.g. YOU): ").strip() or "YOU"
    reset(student_id)  # start clean each run
    agent = DiagnosticAgent(student_id)

    tried = set()
    while agent.run.state not in ("STORE",):
        cause = next_cause(tried)
        if cause is None:
            print("\nRan out of candidate causes to try. Stopping.")
            agent.safe_stop("no_more_hypotheses")
            break

        tried.add(cause)
        h = agent.choose_hypothesis(
            cause, f"Trying '{cause}' as the next candidate cause."
        )
        if h is None:
            print("\nAttempt limit reached. Stopping safely.")
            break

        print(f"\n--- Testing hypothesis: {cause} ---")
        question = QUESTIONS[cause]
        print(f"Q: {question}")
        answer = input("Your answer: ")

        q = agent.ask(h, question)
        result, note = judge_answer(cause, answer)
        agent.evaluate(q, answer, result, note)

        print(f"-> judged as: {result} ({note})")

        if agent.run.state == "CONFIRM":
            print(f"\nBased on that, the likely gap is: {agent.state.current_gap}")
            reply = input("Does that sound right to you? (yes/no): ").strip().lower()
            agent.confirm("yes" if reply.startswith("y") else "no")

    print("\n=== RUN SUMMARY ===")
    print("Outcome:", agent.run.outcome)
    print("Final state:", agent.run.state)
    print("Confirmed gap:", agent.state.current_gap)
    print("Confirmation status:", agent.state.confirmation_status)
    print(f"\n(Saved to state/{student_id}.json - run again with the same id to see it reload.)")


if __name__ == "__main__":
    main()
