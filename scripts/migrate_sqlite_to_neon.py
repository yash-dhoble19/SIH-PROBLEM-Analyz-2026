"""
Fast Batch Migration script to transfer all 226 SIH problem statements from local SQLite into Neon PostgreSQL with pgvector embeddings.
"""

import sys
import os
import json
import sqlite3
from pathlib import Path

# Force UTF-8 stdout
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from platform_core.database.connection import init_db, SessionLocal, engine
from platform_core.database.models import ProblemStatement, Organization, Theme
from platform_core.ai.embeddings import EmbeddingProvider

SQLITE_PATH = BASE_DIR / "data" / "sih_2026.db"


def run_migration():
    print("========================================", flush=True)
    print("Starting SQLite to Neon PostgreSQL Migration", flush=True)
    print(f"Source SQLite: {SQLITE_PATH}", flush=True)
    print("========================================", flush=True)

    if not SQLITE_PATH.exists():
        print(f"Error: SQLite source database not found at {SQLITE_PATH}", flush=True)
        sys.exit(1)

    # 1. Initialize schema in Neon PostgreSQL
    print("[1/4] Initializing PostgreSQL Schema and pgvector extension...", flush=True)
    init_db()
    print("[OK] Schema initialized successfully.", flush=True)

    # 2. Read records from SQLite
    print("[2/4] Reading problem statements from SQLite...", flush=True)
    conn = sqlite3.connect(str(SQLITE_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM problem_statements ORDER BY serial_number ASC;")
    sqlite_rows = cursor.fetchall()
    conn.close()

    print(f"[OK] Found {len(sqlite_rows)} problem statements in SQLite.", flush=True)

    # 3. Process and populate Neon DB
    print("[3/4] Generating embeddings and inserting into Neon PostgreSQL...", flush=True)
    embedder = EmbeddingProvider()
    db = SessionLocal()

    try:
        # Pre-fetch existing orgs and themes in one go
        existing_orgs = {o.name: o.id for o in db.query(Organization).all()}
        existing_themes = {t.name: t.id for t in db.query(Theme).all()}
        
        # Insert any missing orgs and themes
        for r in sqlite_rows:
            org_name = r["organization"]
            theme_name = r["theme"]
            if org_name and org_name not in existing_orgs:
                org = Organization(name=org_name)
                db.add(org)
                db.flush()
                existing_orgs[org_name] = org.id
            if theme_name and theme_name not in existing_themes:
                theme = Theme(name=theme_name, slug=theme_name.lower().replace(" ", "-"))
                db.add(theme)
                db.flush()
                existing_themes[theme_name] = theme.id

        # Pre-fetch all existing problem statements into memory in ONE query
        existing_ps_map = {ps.id: ps for ps in db.query(ProblemStatement).all()}
        
        inserted_count = 0
        updated_count = 0

        for r in sqlite_rows:
            ps_id = r["problem_statement_id"]
            search_text = r["search_text"]
            embedding_vec = embedder.get_embedding(search_text)

            extra_fields = {}
            if r["extra_fields"]:
                try:
                    extra_fields = json.loads(r["extra_fields"])
                except Exception:
                    extra_fields = {}

            if ps_id in existing_ps_map:
                ps = existing_ps_map[ps_id]
                ps.serial_number = r["serial_number"]
                ps.problem_statement_number = r["problem_statement_number"]
                ps.title = r["title"]
                ps.organization = r["organization"]
                ps.organization_id = existing_orgs.get(r["organization"])
                ps.department = r["department"]
                ps.category = r["category"]
                ps.theme = r["theme"]
                ps.theme_id = existing_themes.get(r["theme"])
                ps.submitted_ideas_count = r["submitted_ideas_count"]
                ps.deadline_for_idea_submission = r["deadline_for_idea_submission"]
                ps.background = r["background"]
                ps.description = r["description"]
                ps.expected_solution = r["expected_solution"]
                ps.youtube_link = r["youtube_link"]
                ps.dataset_link = r["dataset_link"]
                ps.contact_info = r["contact_info"]
                ps.source_url = r["source_url"]
                ps.search_text = search_text
                ps.embedding = embedding_vec
                ps.extra_fields = extra_fields
                updated_count += 1
            else:
                ps = ProblemStatement(
                    id=ps_id,
                    serial_number=r["serial_number"],
                    problem_statement_number=r["problem_statement_number"],
                    title=r["title"],
                    organization=r["organization"],
                    organization_id=existing_orgs.get(r["organization"]),
                    department=r["department"],
                    category=r["category"],
                    theme=r["theme"],
                    theme_id=existing_themes.get(r["theme"]),
                    submitted_ideas_count=r["submitted_ideas_count"],
                    deadline_for_idea_submission=r["deadline_for_idea_submission"],
                    background=r["background"],
                    description=r["description"],
                    expected_solution=r["expected_solution"],
                    youtube_link=r["youtube_link"],
                    dataset_link=r["dataset_link"],
                    contact_info=r["contact_info"],
                    source_url=r["source_url"],
                    search_text=search_text,
                    embedding=embedding_vec,
                    extra_fields=extra_fields
                )
                db.add(ps)
                inserted_count += 1

        db.commit()
        print(f"[OK] Migration committed: {inserted_count} inserted, {updated_count} updated.", flush=True)

    except Exception as e:
        db.rollback()
        print(f"Migration error: {e}", flush=True)
        raise
    finally:
        db.close()

    # 4. Verify in PostgreSQL
    print("[4/4] Verifying migrated records in Neon PostgreSQL...", flush=True)
    db = SessionLocal()
    total_pg = db.query(ProblemStatement).count()
    software_pg = db.query(ProblemStatement).filter(ProblemStatement.category == "Software").count()
    hardware_pg = db.query(ProblemStatement).filter(ProblemStatement.category == "Hardware").count()
    db.close()

    print("========================================", flush=True)
    print("MIGRATION COMPLETED SUCCESSFULLY", flush=True)
    print(f"Total in Neon DB: {total_pg} (Target: 226)", flush=True)
    print(f"Software Track:   {software_pg} (Target: 172)", flush=True)
    print(f"Hardware Track:   {hardware_pg} (Target: 54)", flush=True)
    print("========================================", flush=True)


if __name__ == "__main__":
    run_migration()
