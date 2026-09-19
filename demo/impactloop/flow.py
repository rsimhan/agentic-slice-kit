from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from slice import callback
from slice.llm import complete
from slice.records import RunState

from .schema import (
    StudentGoal,
    ProjectBrief,
    TeamProposal,
    TaskPlan,
    VerificationResult,
    ProofOfAbility,
    OpportunityRecommendation,
)


PROMPTS = Path(__file__).parent / "prompts"
OPPORTUNITIES = Path(__file__).parent / "opportunities.json"

# This is a domain revision limit, not an API-credit limit.
MAX_REVISIONS = 1


def load_prompt(name: str) -> str:
    return (PROMPTS / f"{name}.md").read_text(encoding="utf-8")


def load_opportunities() -> list[dict]:
    return json.loads(OPPORTUNITIES.read_text(encoding="utf-8"))


def rank_opportunities(proof: ProofOfAbility, limit: int = 3) -> list[dict]:
    """Retrieve a small candidate set from the local opportunity catalog.

    This is deliberately deterministic retrieval. The model may choose among
    retrieved records, but it is not allowed to invent an opportunity.
    """
    text = (
        f"{proof.capability} {proof.contribution} "
        + " ".join(proof.evidence)
    ).lower()

    scored = []
    for item in load_opportunities():
        score = 0
        for capability in item.get("required_capabilities", []):
            if capability.lower() in text:
                score += 2
            else:
                words = [w for w in capability.lower().split() if len(w) > 3]
                score += sum(1 for word in words if word in text)
        if item.get("type", "").lower() in text:
            score += 1
        scored.append((score, item))

    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [item for _, item in scored[:limit]]


def build_flow(call=complete):

    def handle_drafting(ctx) -> RunState:
        """
        Build the student goal, project brief, team proposal,
        and task plan.

        On a revision, wait for fresh evidence instead of silently
        regenerating the student's work.
        """

        previous_verification = ctx.latest("verification")

        if ctx.latest("student_goal") is not None:
            if (
                previous_verification
                and previous_verification.get("status") == "REVISION_REQUIRED"
            ):
                if ctx.latest("evidence_submission") is None:
                    pending = callback.pending(ctx.store, ctx.run_id)
                    evidence_pending = any(
                        q.context.get("kind") == "evidence" for q in pending
                    )
                    if not evidence_pending:
                        callback.ask(
                            ctx.store,
                            ctx.run_id,
                            (
                                "Verification found missing evidence. Submit the "
                                "links, file names, screenshots, or notes that "
                                "prove what you actually completed."
                            ),
                            {
                                "kind": "evidence",
                                "resume_state": RunState.DRAFTING.value,
                                "reason": (
                                    "The verifier rejected the first evidence "
                                    "submission and needs concrete proof before "
                                    "the capability can be verified."
                                ),
                            },
                            ctx.settings,
                        )
                    return RunState.AWAITING_EXPERT

                return RunState.GATING

            return RunState.PROBING

        run_input = ctx.latest("input") or {}
        student_profile = run_input.get("student_profile", {})
        candidates = run_input.get("candidate_profiles", [])

        # ---------------------------------------------------------
        # Agent 1: Intake
        # ---------------------------------------------------------
        student = call(
            settings=ctx.settings,
            budget=ctx.budget,
            messages=[
                {
                    "role": "system",
                    "content": load_prompt("intake"),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "challenge": {
                                "title": run_input.get("title", ""),
                                "description": run_input.get("text", ""),
                            },
                            "student_profile": student_profile,
                        },
                        indent=2,
                    ),
                },
            ],
            schema=StudentGoal,
            step="intake",
        )

        ctx.append(
            "student_goal",
            student.model_dump(),
            produced_by="agent:intake",
        )

        # ---------------------------------------------------------
        # Agent 2: Problem Decomposer
        # ---------------------------------------------------------
        project = call(
            settings=ctx.settings,
            budget=ctx.budget,
            messages=[
                {
                    "role": "system",
                    "content": load_prompt("decompose"),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "challenge": {
                                "title": run_input.get("title", ""),
                                "description": run_input.get("text", ""),
                            },
                            "student_goal": student.model_dump(),
                        },
                        indent=2,
                    ),
                },
            ],
            schema=ProjectBrief,
            step="decompose",
        )

        ctx.append(
            "project_brief",
            project.model_dump(),
            produced_by="agent:decomposer",
        )

        # ---------------------------------------------------------
        # Agent 3: Semantic Team Matcher
        # ---------------------------------------------------------
        team = call(
            settings=ctx.settings,
            budget=ctx.budget,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Match students to complementary roles using only the "
                        "candidate profiles provided. Never invent a skill, "
                        "experience, availability, or student. Explain the "
                        "capability evidence behind every match."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "project": project.model_dump(),
                            "candidate_profiles": candidates,
                        },
                        indent=2,
                    ),
                },
            ],
            schema=TeamProposal,
            step="team",
        )

        ctx.append(
            "team_proposal",
            team.model_dump(),
            produced_by="agent:team_matcher",
        )

        # ---------------------------------------------------------
        # Agent 4: Orchestrator
        # ---------------------------------------------------------
        plan = call(
            settings=ctx.settings,
            budget=ctx.budget,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Create a project plan with task owners, acceptance "
                        "conditions, and evidence requirements. Use only the "
                        "proposed team and project tasks."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "project": project.model_dump(),
                            "team": team.model_dump(),
                        },
                        indent=2,
                    ),
                },
            ],
            schema=TaskPlan,
            step="plan",
        )

        ctx.append(
            "task_plan",
            plan.model_dump(),
            produced_by="agent:orchestrator",
        )

        return RunState.PROBING

    def handle_probing(ctx) -> RunState:
        """
        Human-in-the-loop stage.

        The first time this stage runs, it creates a real persisted
        mentor question and suspends the workflow.

        After the mentor answers, the callback system wakes the run.
        The answer is then converted into a structured mentor_decision
        record that later agents can read.
        """

        if ctx.latest("mentor_decision") is not None:
            return RunState.GATING

        answers = ctx.history("expert_answer")

        if not answers:
            callback.ask(
                ctx.store,
                ctx.run_id,
                (
                    "Which priority should guide the project if a unified "
                    "discovery flow conflicts with existing club-channel "
                    "preferences?"
                ),
                {
                    "kind": "mentor",
                    "resume_state": RunState.PROBING.value,
                    "options": [
                        "Prioritise one unified student experience",
                        "Keep every existing channel unchanged",
                    ],
                    "reason": (
                        "The system detected a possible conflict between a "
                        "unified discovery experience and existing club channels."
                    ),
                },
                ctx.settings,
            )
            return RunState.AWAITING_EXPERT

        answer = answers[-1].payload

        ctx.append(
            "mentor_decision",
            {
                "question": answer["question"],
                "decision": answer.get("answer") or "No mentor response",
                "priority": answer.get("answer") or "Unresolved",
                "answered_by": answer.get("who") or "unresolved_no_expert",
            },
            produced_by="human:mentor",
        )

        return RunState.GATING

    def handle_gating(ctx) -> RunState:
        """
        Verify real submitted evidence, then create Proof-of-Ability and
        recommend an opportunity from the local opportunity catalog.
        """

        project = ctx.latest("project_brief")
        plan = ctx.latest("task_plan")
        mentor = ctx.latest("mentor_decision")
        evidence = ctx.latest("evidence_submission")

        result = call(
            settings=ctx.settings,
            budget=ctx.budget,
            messages=[
                {
                    "role": "system",
                    "content": load_prompt("verify"),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "project": project,
                            "task_plan": plan,
                            "mentor_decision": mentor,
                            "evidence_submission": evidence,
                        },
                        indent=2,
                    ),
                },
            ],
            schema=VerificationResult,
            step="verify",
        )

        ctx.append(
            "verification",
            result.model_dump(),
            produced_by="agent:verifier",
        )

        if result.status == "REVISION_REQUIRED":
            attempts = len(ctx.history("verification"))

            if attempts > MAX_REVISIONS:
                ctx.append(
                    "failure",
                    {
                        "kind": "verification_exhausted",
                        "detail": (
                            "The project did not pass verification within "
                            "the revision limit."
                        ),
                    },
                    produced_by="system",
                )
                return RunState.FAILED

            return RunState.DRAFTING

        # ---------------------------------------------------------
        # Agent 7: Proof-of-Ability Generator
        # ---------------------------------------------------------
        proof = call(
            settings=ctx.settings,
            budget=ctx.budget,
            messages=[
                {
                    "role": "system",
                    "content": load_prompt("proof"),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "project": project,
                            "task_plan": plan,
                            "mentor_decision": mentor,
                            "verification": result.model_dump(),
                            "evidence_submission": evidence,
                        },
                        indent=2,
                    ),
                },
            ],
            schema=ProofOfAbility,
            step="proof",
        )

        ctx.append(
            "proof_of_ability",
            proof.model_dump(),
            produced_by="agent:proof",
        )

        # ---------------------------------------------------------
        # Agent 8: Connector
        # ---------------------------------------------------------
        candidates = rank_opportunities(proof)

        recommendation = call(
            settings=ctx.settings,
            budget=ctx.budget,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are the ImpactLoop Connector. Recommend exactly "
                        "one next opportunity from the candidate catalog below. "
                        "Do not invent an opportunity, organisation, or "
                        "requirement. Explain the match using only the verified "
                        "Proof-of-Ability record."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "proof_of_ability": proof.model_dump(),
                            "candidate_opportunities": candidates,
                        },
                        indent=2,
                    ),
                },
            ],
            schema=OpportunityRecommendation,
            step="connector",
        )

        ctx.append(
            "opportunity_recommendation",
            recommendation.model_dump(),
            produced_by="agent:connector",
        )

        return RunState.COMPLETE

    return SimpleNamespace(
        name="impactloop",
        handlers={
            RunState.DRAFTING: handle_drafting,
            RunState.PROBING: handle_probing,
            RunState.GATING: handle_gating,
        },
    )
