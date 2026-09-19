from __future__ import annotations

from typing import Any, Type

from pydantic import BaseModel


# ---------------------------------------------------------
# Fake AI responses for the ImpactLoop MVP
# ---------------------------------------------------------

STUDENT_GOAL = """{
  "student_name": "Aarav",
  "goal": "I want to help improve how students discover campus events and opportunities.",
  "current_skills": [
    "Student research",
    "Communication",
    "Basic data organisation"
  ],
  "time_available": "6 hours per week",
  "desired_capability": "User Research and Opportunity Discovery"
}"""


PROJECT_BRIEF = """{
  "project_title": "Build a Unified Campus Opportunity Discovery Flow",
  "problem_to_solve": "Students miss useful campus events and opportunities because information is scattered across WhatsApp groups, posters, club pages, and separate channels.",
  "objective": "Understand how students currently discover events and design a simple unified flow that makes relevant opportunities easier to find.",
  "tasks": [
    "Interview students about how they currently find campus events",
    "Map the different channels where event information is shared",
    "Organise sample event information into a common format",
    "Design a simple unified opportunity-discovery flow",
    "Test the flow with students and record their feedback",
    "Write a short findings report"
  ],
  "deliverables": [
    "Student interview notes",
    "Campus event-channel map",
    "Structured event dataset",
    "Opportunity-discovery flow prototype",
    "Student walkthrough findings",
    "Short findings report"
  ],
  "required_capabilities": [
    "User research",
    "Data organisation",
    "UX and flow design",
    "Communication"
  ],
  "evidence_requirements": [
    "Interview notes",
    "Channel map",
    "Event dataset",
    "Prototype screenshot",
    "Walkthrough findings"
  ]
}"""


# Deliberately weak evidence.
# The verifier should reject this first submission.
WEAK_VERIFICATION = """{
  "status": "REVISION_REQUIRED",
  "reason": "The student submitted only a general claim and did not provide enough evidence of actual research, design, or testing.",
  "missing_evidence": [
    "Student interview notes",
    "Event-channel map",
    "Opportunity-discovery prototype",
    "Student walkthrough findings"
  ]
}"""


# Stronger evidence.
# The verifier should accept this second submission.
STRONG_VERIFICATION = """{
  "status": "PASS",
  "reason": "The submitted interview notes, channel map, prototype, and walkthrough findings provide evidence of the student's contribution to improving campus opportunity discovery.",
  "missing_evidence": []
}"""


PROOF = """{
  "capability": "User Research and Opportunity Discovery",
  "contribution": "Interviewed students, mapped fragmented campus-event channels, helped design a unified opportunity-discovery flow, and documented student walkthrough feedback.",
  "evidence": [
    "student_interview_notes.md",
    "event_channel_map.png",
    "opportunity_flow.png",
    "walkthrough_findings.md"
  ],
  "verification_status": "verified"
}"""


_SCRIPT: dict[str, list[str]] = {
    "intake": [STUDENT_GOAL],
    "decompose": [PROJECT_BRIEF],
    "verify": [WEAK_VERIFICATION, STRONG_VERIFICATION],
    "proof": [PROOF],
}


class Stub:
    """
    Fake replacement for slice.llm.complete.

    It gives us predictable AI responses so we can prove
    the workflow before using real API calls.
    """

    def __init__(self) -> None:
        self.calls: list[str] = []
        self._n: dict[str, int] = {}

    def __call__(
        self,
        *,
        settings,
        budget,
        messages,
        schema: Type[BaseModel] | None = None,
        model: str | None = None,
        step: str = "call",
        timeout: float = 120.0,
    ) -> Any:

        base = step.split(":")[0]

        i = self._n.get(base, 0)
        self._n[base] = i + 1

        self.calls.append(step)

        try:
            raw = _SCRIPT[base][i]
        except (KeyError, IndexError):
            raise AssertionError(
                f"Stub has no scripted reply {i} for step {step!r}."
            )

        # Simulate token usage.
        budget.record_tokens(len(raw) // 4)

        # Validate the fake response using the real Pydantic schema.
        return schema.model_validate_json(raw) if schema else raw


TEAM_PROPOSAL = """{
  "members": [
    {
      "student_name": "Aarav",
      "role": "Student researcher",
      "reason": "Can interview students and understand how they currently discover events.",
      "matched_capabilities": [
        "Student research",
        "Communication"
      ]
    },
    {
      "student_name": "Meera",
      "role": "UX flow designer",
      "reason": "Can convert research findings into a simple opportunity-discovery experience.",
      "matched_capabilities": [
        "UX and flow design",
        "Visual communication"
      ]
    },
    {
      "student_name": "Karthik",
      "role": "Event data organiser",
      "reason": "Can structure event information into a consistent and searchable format.",
      "matched_capabilities": [
        "Data organisation",
        "Attention to detail"
      ]
    }
  ],
  "unresolved_gaps": []
}"""


TASK_PLAN = """{
  "tasks": [
    "Interview students about how they find campus events",
    "Map the channels where event information is shared",
    "Organise sample event information into a common format",
    "Design a unified opportunity-discovery flow",
    "Test the flow with students",
    "Write the findings report"
  ],
  "owners": {
    "Interview students about how they find campus events": "Aarav",
    "Map the channels where event information is shared": "Aarav",
    "Organise sample event information into a common format": "Karthik",
    "Design a unified opportunity-discovery flow": "Meera",
    "Test the flow with students": "Aarav",
    "Write the findings report": "Aarav"
  },
  "acceptance_conditions": {
    "Interview students about how they find campus events": "At least three interview notes are recorded.",
    "Map the channels where event information is shared": "The main event-sharing channels are listed.",
    "Organise sample event information into a common format": "At least ten sample events use the same fields.",
    "Design a unified opportunity-discovery flow": "A clear flow or prototype is created.",
    "Test the flow with students": "Three student walkthroughs are recorded.",
    "Write the findings report": "The report summarises findings and suggested improvements."
  },
  "evidence_requirements": [
    "Student interview notes",
    "Event-channel map",
    "Structured event dataset",
    "Opportunity-discovery prototype",
    "Student walkthrough findings",
    "Short findings report"
  ]
}"""


MENTOR_DECISION = """{
  "question": "Which priority should guide the project if a unified discovery flow conflicts with existing club-channel preferences?",
  "decision": "Prioritise one unified student experience while keeping existing channels as input sources.",
  "priority": "One clear student discovery experience",
  "answered_by": "Student affairs mentor"
}"""


OPPORTUNITY_RECOMMENDATION = """{
  "opportunity_title": "Campus Innovation and Student Experience Project",
  "explanation": "The verified research, event-channel mapping, data organisation, and student testing experience match this opportunity.",
  "matched_evidence": [
    "student_interview_notes.md",
    "event_channel_map.png",
    "walkthrough_findings.md"
  ]
}"""


_SCRIPT.update(
    {
        "team": [TEAM_PROPOSAL],
        "plan": [TASK_PLAN],
        "mentor": [MENTOR_DECISION],
        "connector": [OPPORTUNITY_RECOMMENDATION],
    }
)
