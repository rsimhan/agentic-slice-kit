import json
import os
from pathlib import Path
from dataclasses import asdict, fields
from datetime import datetime, timezone

from models import StudentState, Hypothesis, DiagnosticCheck

# FIX: one file per learner instead of a single shared student_state.json,
# which previously let each learner overwrite the previous learner's record.
STATE_DIR = Path(os.environ.get("COGNIX_STATE_DIR", "state"))


def _path(student_id: str) -> Path:
    safe = "".join(c for c in student_id if c.isalnum() or c in "-_")
    if not safe:
        raise ValueError(f"Unusable student_id: {student_id!r}")
    return STATE_DIR / f"{safe}.json"


def save(state: StudentState) -> None:
    # FIX: refresh updated_at so the timestamp reflects the last write,
    # not the moment the object happened to be constructed.
    state.updated_at = datetime.now(timezone.utc).isoformat()
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    path = _path(state.student_id)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(asdict(state), indent=2))
    tmp.replace(path)  # atomic: a crash mid-write can't truncate the record


def load(student_id: str, topic: str = "recursion") -> StudentState:
    path = _path(student_id)
    if not path.exists():
        return StudentState(student_id=student_id, topic=topic)

    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        # FIX: a corrupt or unreadable file used to crash the whole run.
        return StudentState(student_id=student_id, topic=topic)

    if not isinstance(data, dict) or data.get("student_id") != student_id:
        return StudentState(student_id=student_id, topic=topic)

    try:
        data["hypotheses"] = [Hypothesis(**h) for h in data.get("hypotheses", [])]
        data["checks"] = [DiagnosticCheck(**c) for c in data.get("checks", [])]
        # FIX: drop unknown keys so an older/newer schema doesn't raise TypeError.
        known = {f.name for f in fields(StudentState)}
        return StudentState(**{k: v for k, v in data.items() if k in known})
    except TypeError:
        return StudentState(student_id=student_id, topic=topic)


def reset(student_id: str) -> None:
    """Delete a learner's stored record. Used by the demo for repeatable runs."""
    _path(student_id).unlink(missing_ok=True)
