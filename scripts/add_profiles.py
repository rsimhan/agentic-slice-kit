import os
from slice.store import Store

db_path = os.environ.get("SLICE_DB", "impactloop.db")
store = Store(db_path)

store.db.executescript("""
CREATE TABLE IF NOT EXISTS student_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER UNIQUE NOT NULL,
    skills TEXT NOT NULL DEFAULT '[]',
    interests TEXT NOT NULL DEFAULT '[]',
    availability TEXT NOT NULL DEFAULT '',
    preferred_role TEXT NOT NULL DEFAULT '',
    bio TEXT NOT NULL DEFAULT '',
    evidence_links TEXT NOT NULL DEFAULT '[]',
    created_at REAL NOT NULL
);
""")

print("student_profiles table is ready")
