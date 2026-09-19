# agent_runtime/store.py
# SQLite persistence for runs, history, checkpoints, concepts, and graphs

import sqlite3
import json
import threading
from pathlib import Path
from typing import Optional, List
from datetime import datetime
from contextlib import contextmanager

from contracts.schemas import (
    RunRecord, StepRecord, RunState, ConceptNode, GraphEdge, NoteVersion,
    MAX_TEST_GENERATION_RETRIES
)


# Database schema version - increment when schema changes
SCHEMA_VERSION = 3


class RunStore:
    """Thread-safe SQLite store for agent runs, steps, concepts, and graphs."""

    def __init__(self, db_path: str = "synapse.db"):
        self.db_path = db_path
        self._lock = threading.RLock()
        self._init_db()
        self._run_migrations()

    def _init_db(self) -> None:
        """Initialize database tables. Called on first connection."""
        with self._conn() as conn:
            # Schema version table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS schema_version (
                    version INTEGER PRIMARY KEY,
                    applied_at TEXT NOT NULL
                )
            """)
            
            # Runs table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY,
                    concept_id TEXT NOT NULL,
                    student_id TEXT,
                    teacher_id TEXT,
                    state TEXT NOT NULL,
                    current_cycle INTEGER NOT NULL DEFAULT 1,
                    revision_count INTEGER NOT NULL DEFAULT 0,
                    model_call_count INTEGER NOT NULL DEFAULT 0,
                    test_generation_retry_count INTEGER NOT NULL DEFAULT 0,
                    test_generation_error TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    completed_at TEXT,
                    error TEXT
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_runs_concept_student
                ON runs(concept_id, student_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_runs_state
                ON runs(state)
            """)

            # Steps table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS steps (
                    id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    step_name TEXT NOT NULL,
                    input_data TEXT NOT NULL,
                    output_data TEXT,
                    state_before TEXT NOT NULL,
                    state_after TEXT,
                    started_at TEXT NOT NULL,
                    completed_at TEXT,
                    error TEXT,
                    retry_count INTEGER NOT NULL DEFAULT 0,
                    FOREIGN KEY (run_id) REFERENCES runs(run_id)
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_steps_run_id
                ON steps(run_id)
            """)

            # Concepts table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS concepts (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    prerequisites TEXT NOT NULL DEFAULT '[]',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_concepts_name
                ON concepts(name)
            """)

            # Graph edges table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS graph_edges (
                    id TEXT PRIMARY KEY,
                    from_concept_id TEXT NOT NULL,
                    to_concept_id TEXT NOT NULL,
                    edge_type TEXT NOT NULL DEFAULT 'prerequisite',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (from_concept_id) REFERENCES concepts(id),
                    FOREIGN KEY (to_concept_id) REFERENCES concepts(id),
                    UNIQUE(from_concept_id, to_concept_id, edge_type)
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_graph_edges_from
                ON graph_edges(from_concept_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_graph_edges_to
                ON graph_edges(to_concept_id)
            """)

            # Note versions table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS note_versions (
                    id TEXT PRIMARY KEY,
                    student_id TEXT NOT NULL,
                    concept_id TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    markdown TEXT NOT NULL,
                    diagnosis_id TEXT,
                    review_id TEXT,
                    run_id TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (concept_id) REFERENCES concepts(id),
                    FOREIGN KEY (run_id) REFERENCES runs(run_id),
                    UNIQUE(student_id, concept_id, version)
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_note_versions_student_concept
                ON note_versions(student_id, concept_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_note_versions_run
                ON note_versions(run_id)
            """)

    def _run_migrations(self) -> None:
        """Run pending migrations to bring schema to current version."""
        with self._lock, self._conn() as conn:
            # Get current version
            row = conn.execute("SELECT version FROM schema_version ORDER BY version DESC LIMIT 1").fetchone()
            current_version = row["version"] if row else 0

            # Migration 1: Initial schema (runs, steps)
            if current_version < 1:
                # Tables already created in _init_db
                conn.execute(
                    "INSERT INTO schema_version (version, applied_at) VALUES (?, ?)",
                    (1, datetime.utcnow().isoformat())
                )
                current_version = 1

            # Migration 2: Add concepts, graph_edges, note_versions
            if current_version < 2:
                # Tables already created in _init_db
                conn.execute(
                    "INSERT INTO schema_version (version, applied_at) VALUES (?, ?)",
                    (2, datetime.utcnow().isoformat())
                )
                current_version = 2

            # Migration 3: Add test_generation_retry_count and test_generation_error to runs
            if current_version < 3:
                # Check if columns exist
                cursor = conn.execute("PRAGMA table_info(runs)")
                columns = [row["name"] for row in cursor.fetchall()]
                
                if "test_generation_retry_count" not in columns:
                    conn.execute("ALTER TABLE runs ADD COLUMN test_generation_retry_count INTEGER NOT NULL DEFAULT 0")
                if "test_generation_error" not in columns:
                    conn.execute("ALTER TABLE runs ADD COLUMN test_generation_error TEXT")
                
                conn.execute(
                    "INSERT INTO schema_version (version, applied_at) VALUES (?, ?)",
                    (3, datetime.utcnow().isoformat())
                )
                current_version = 3

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    # ─── Run operations ────────────────────────────────────────────────

    def create_run(self, run: RunRecord) -> None:
        with self._lock, self._conn() as conn:
            conn.execute("""
                INSERT INTO runs (
                    run_id, concept_id, student_id, teacher_id, state,
                    current_cycle, revision_count, model_call_count,
                    test_generation_retry_count, test_generation_error,
                    created_at, updated_at, completed_at, error
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                run.run_id, run.concept_id, run.student_id, run.teacher_id,
                run.state.value, run.current_cycle, run.revision_count,
                run.model_call_count, run.test_generation_retry_count,
                run.test_generation_error,
                run.created_at.isoformat(), run.updated_at.isoformat(),
                run.completed_at.isoformat() if run.completed_at else None,
                run.error
            ))

    def get_run(self, run_id: str) -> Optional[RunRecord]:
        with self._lock, self._conn() as conn:
            row = conn.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,)).fetchone()
            if not row:
                return None
            return self._row_to_run(row)

    def update_run(self, run: RunRecord) -> None:
        with self._lock, self._conn() as conn:
            run.updated_at = datetime.utcnow()
            conn.execute("""
                UPDATE runs SET
                    concept_id = ?, student_id = ?, teacher_id = ?, state = ?,
                    current_cycle = ?, revision_count = ?, model_call_count = ?,
                    test_generation_retry_count = ?, test_generation_error = ?,
                    updated_at = ?, completed_at = ?, error = ?
                WHERE run_id = ?
            """, (
                run.concept_id, run.student_id, run.teacher_id, run.state.value,
                run.current_cycle, run.revision_count, run.model_call_count,
                run.test_generation_retry_count, run.test_generation_error,
                run.updated_at.isoformat(),
                run.completed_at.isoformat() if run.completed_at else None,
                run.error, run.run_id
            ))

    def get_runs_by_concept_and_student(self, concept_id: str, student_id: Optional[str] = None) -> List[RunRecord]:
        with self._lock, self._conn() as conn:
            if student_id:
                rows = conn.execute(
                    "SELECT * FROM runs WHERE concept_id = ? AND student_id = ? ORDER BY created_at DESC",
                    (concept_id, student_id)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM runs WHERE concept_id = ? ORDER BY created_at DESC",
                    (concept_id,)
                ).fetchall()
            return [self._row_to_run(row) for row in rows]

    def get_latest_run(self, concept_id: str, student_id: str) -> Optional[RunRecord]:
        with self._lock, self._conn() as conn:
            row = conn.execute("""
                SELECT * FROM runs
                WHERE concept_id = ? AND student_id = ?
                ORDER BY created_at DESC LIMIT 1
            """, (concept_id, student_id)).fetchone()
            if not row:
                return None
            return self._row_to_run(row)

    # ─── Step operations ──────────────────────────────────────────────

    def create_step(self, step: StepRecord) -> None:
        with self._lock, self._conn() as conn:
            conn.execute("""
                INSERT INTO steps (
                    id, run_id, step_name, input_data, output_data,
                    state_before, state_after, started_at, completed_at, error, retry_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                step.id, step.run_id, step.step_name,
                json.dumps(step.input_data), json.dumps(step.output_data) if step.output_data else None,
                step.state_before.value, step.state_after.value if step.state_after else None,
                step.started_at.isoformat(),
                step.completed_at.isoformat() if step.completed_at else None,
                step.error, step.retry_count
            ))

    def update_step(self, step: StepRecord) -> None:
        with self._lock, self._conn() as conn:
            conn.execute("""
                UPDATE steps SET
                    output_data = ?, state_after = ?, completed_at = ?, error = ?, retry_count = ?
                WHERE id = ?
            """, (
                json.dumps(step.output_data) if step.output_data else None,
                step.state_after.value if step.state_after else None,
                step.completed_at.isoformat() if step.completed_at else None,
                step.error, step.retry_count, step.id
            ))

    def get_steps(self, run_id: str) -> List[StepRecord]:
        with self._lock, self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM steps WHERE run_id = ? ORDER BY started_at",
                (run_id,)
            ).fetchall()
            return [self._row_to_step(row) for row in rows]

    # ─── Concept operations ───────────────────────────────────────────

    def create_concept(self, concept: ConceptNode) -> None:
        """Create a new concept."""
        with self._lock, self._conn() as conn:
            conn.execute("""
                INSERT INTO concepts (id, name, summary, prerequisites, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                concept.id, concept.name, concept.summary,
                json.dumps(concept.prerequisites),
                concept.created_at.isoformat(), concept.updated_at.isoformat()
            ))

    def get_concept(self, concept_id: str) -> Optional[ConceptNode]:
        """Get a concept by ID."""
        with self._lock, self._conn() as conn:
            row = conn.execute("SELECT * FROM concepts WHERE id = ?", (concept_id,)).fetchone()
            if not row:
                return None
            return ConceptNode(
                id=row["id"],
                name=row["name"],
                summary=row["summary"],
                prerequisites=json.loads(row["prerequisites"]),
                created_at=datetime.fromisoformat(row["created_at"]),
                updated_at=datetime.fromisoformat(row["updated_at"])
            )

    def get_concepts(self, concept_ids: Optional[List[str]] = None) -> List[ConceptNode]:
        """Get all concepts or filter by IDs."""
        with self._lock, self._conn() as conn:
            if concept_ids:
                placeholders = ",".join("?" for _ in concept_ids)
                rows = conn.execute(
                    f"SELECT * FROM concepts WHERE id IN ({placeholders})",
                    concept_ids
                ).fetchall()
            else:
                rows = conn.execute("SELECT * FROM concepts").fetchall()
            return [
                ConceptNode(
                    id=row["id"],
                    name=row["name"],
                    summary=row["summary"],
                    prerequisites=json.loads(row["prerequisites"]),
                    created_at=datetime.fromisoformat(row["created_at"]),
                    updated_at=datetime.fromisoformat(row["updated_at"])
                )
                for row in rows
            ]

    def update_concept(self, concept: ConceptNode) -> None:
        """Update an existing concept."""
        with self._lock, self._conn() as conn:
            concept.updated_at = datetime.utcnow()
            conn.execute("""
                UPDATE concepts SET
                    name = ?, summary = ?, prerequisites = ?, updated_at = ?
                WHERE id = ?
            """, (
                concept.name, concept.summary,
                json.dumps(concept.prerequisites),
                concept.updated_at.isoformat(), concept.id
            ))

    def delete_concept(self, concept_id: str) -> None:
        """Delete a concept and its associated edges."""
        with self._lock, self._conn() as conn:
            # Delete edges first (foreign key constraint)
            conn.execute("DELETE FROM graph_edges WHERE from_concept_id = ? OR to_concept_id = ?",
                        (concept_id, concept_id))
            conn.execute("DELETE FROM concepts WHERE id = ?", (concept_id,))

    # ─── Graph edge operations ────────────────────────────────────────

    def create_edge(self, edge: GraphEdge) -> None:
        """Create a new graph edge."""
        with self._lock, self._conn() as conn:
            edge_id = f"{edge.from_concept_id}->{edge.to_concept_id}:{edge.edge_type}"
            conn.execute("""
                INSERT INTO graph_edges (id, from_concept_id, to_concept_id, edge_type, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (
                edge_id, edge.from_concept_id, edge.to_concept_id,
                edge.edge_type, datetime.utcnow().isoformat()
            ))

    def get_edges(self, concept_id: Optional[str] = None) -> List[GraphEdge]:
        """Get all edges, optionally filtered by concept."""
        with self._lock, self._conn() as conn:
            if concept_id:
                rows = conn.execute("""
                    SELECT * FROM graph_edges 
                    WHERE from_concept_id = ? OR to_concept_id = ?
                """, (concept_id, concept_id)).fetchall()
            else:
                rows = conn.execute("SELECT * FROM graph_edges").fetchall()
            return [
                GraphEdge(
                    from_concept_id=row["from_concept_id"],
                    to_concept_id=row["to_concept_id"],
                    edge_type=row["edge_type"]
                )
                for row in rows
            ]

    def delete_edge(self, from_concept_id: str, to_concept_id: str, edge_type: str = "prerequisite") -> None:
        """Delete a graph edge."""
        with self._lock, self._conn() as conn:
            edge_id = f"{from_concept_id}->{to_concept_id}:{edge_type}"
            conn.execute("DELETE FROM graph_edges WHERE id = ?", (edge_id,))

    # ─── Note version operations ──────────────────────────────────────

    def create_note_version(self, note: NoteVersion) -> None:
        """Create a new note version."""
        with self._lock, self._conn() as conn:
            conn.execute("""
                INSERT INTO note_versions (
                    id, student_id, concept_id, version, markdown,
                    diagnosis_id, review_id, run_id, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                f"{note.student_id}:{note.concept_id}:v{note.version}",
                note.student_id, note.concept_id, note.version,
                note.markdown, note.diagnosis_id, note.review_id,
                note.run_id, note.created_at.isoformat()
            ))

    def get_note_version(self, student_id: str, concept_id: str, version: int) -> Optional[NoteVersion]:
        """Get a specific note version."""
        with self._lock, self._conn() as conn:
            row = conn.execute("""
                SELECT * FROM note_versions 
                WHERE student_id = ? AND concept_id = ? AND version = ?
            """, (student_id, concept_id, version)).fetchone()
            if not row:
                return None
            return NoteVersion(
                student_id=row["student_id"],
                concept_id=row["concept_id"],
                version=row["version"],
                markdown=row["markdown"],
                diagnosis_id=row["diagnosis_id"],
                review_id=row["review_id"],
                run_id=row["run_id"],
                created_at=datetime.fromisoformat(row["created_at"])
            )

    def get_latest_note_version(self, student_id: str, concept_id: str) -> Optional[NoteVersion]:
        """Get the latest note version for a student/concept."""
        with self._lock, self._conn() as conn:
            row = conn.execute("""
                SELECT * FROM note_versions 
                WHERE student_id = ? AND concept_id = ?
                ORDER BY version DESC LIMIT 1
            """, (student_id, concept_id)).fetchone()
            if not row:
                return None
            return NoteVersion(
                student_id=row["student_id"],
                concept_id=row["concept_id"],
                version=row["version"],
                markdown=row["markdown"],
                diagnosis_id=row["diagnosis_id"],
                review_id=row["review_id"],
                run_id=row["run_id"],
                created_at=datetime.fromisoformat(row["created_at"])
            )

    def get_note_versions(self, student_id: str, concept_id: str) -> List[NoteVersion]:
        """Get all note versions for a student/concept."""
        with self._lock, self._conn() as conn:
            rows = conn.execute("""
                SELECT * FROM note_versions 
                WHERE student_id = ? AND concept_id = ?
                ORDER BY version
            """, (student_id, concept_id)).fetchall()
            return [
                NoteVersion(
                    student_id=row["student_id"],
                    concept_id=row["concept_id"],
                    version=row["version"],
                    markdown=row["markdown"],
                    diagnosis_id=row["diagnosis_id"],
                    review_id=row["review_id"],
                    run_id=row["run_id"],
                    created_at=datetime.fromisoformat(row["created_at"])
                )
                for row in rows
            ]

    # ─── Graph operations ─────────────────────────────────────────────

    def get_concept_graph(self, student_id: str) -> Optional["ConceptGraph"]:
        """Get the concept graph for a student (based on their note versions)."""
        from contracts.schemas import ConceptGraph
        with self._lock, self._conn() as conn:
            # Get all concepts the student has notes for
            rows = conn.execute("""
                SELECT DISTINCT c.* FROM concepts c
                JOIN note_versions nv ON c.id = nv.concept_id
                WHERE nv.student_id = ?
            """, (student_id,)).fetchall()
            
            if not rows:
                return None
            
            nodes = [
                ConceptNode(
                    id=row["id"],
                    name=row["name"],
                    summary=row["summary"],
                    prerequisites=json.loads(row["prerequisites"]),
                    created_at=datetime.fromisoformat(row["created_at"]),
                    updated_at=datetime.fromisoformat(row["updated_at"])
                )
                for row in rows
            ]
            
            # Get edges between these concepts
            node_ids = {n.id for n in nodes}
            edge_rows = conn.execute("""
                SELECT * FROM graph_edges 
                WHERE from_concept_id IN ({}) AND to_concept_id IN ({})
            """.format(",".join("?" for _ in node_ids), ",".join("?" for _ in node_ids)),
                list(node_ids) + list(node_ids)
            ).fetchall()
            
            edges = [
                GraphEdge(
                    from_concept_id=row["from_concept_id"],
                    to_concept_id=row["to_concept_id"],
                    edge_type=row["edge_type"]
                )
                for row in edge_rows
            ]
            
            return ConceptGraph(nodes=nodes, edges=edges)

    # ─── Row conversion helpers ───────────────────────────────────────

    def _row_to_run(self, row: sqlite3.Row) -> RunRecord:
        return RunRecord(
            run_id=row["run_id"],
            concept_id=row["concept_id"],
            student_id=row["student_id"],
            teacher_id=row["teacher_id"],
            state=RunState(row["state"]),
            current_cycle=row["current_cycle"],
            revision_count=row["revision_count"],
            model_call_count=row["model_call_count"],
            test_generation_retry_count=row["test_generation_retry_count"],
            test_generation_error=row["test_generation_error"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
            error=row["error"]
        )

    def _row_to_step(self, row: sqlite3.Row) -> StepRecord:
        return StepRecord(
            id=row["id"],
            run_id=row["run_id"],
            step_name=row["step_name"],
            input_data=json.loads(row["input_data"]),
            output_data=json.loads(row["output_data"]) if row["output_data"] else None,
            state_before=RunState(row["state_before"]),
            state_after=RunState(row["state_after"]) if row["state_after"] else None,
            started_at=datetime.fromisoformat(row["started_at"]),
            completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
            error=row["error"],
            retry_count=row["retry_count"]
        )


# Global store instance
_store: Optional[RunStore] = None


def get_store(db_path: str = "synapse.db") -> RunStore:
    global _store
    if _store is None:
        _store = RunStore(db_path)
    return _store


def set_store(store: RunStore) -> None:
    global _store
    _store = store