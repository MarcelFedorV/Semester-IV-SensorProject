from sqlalchemy import create_engine, Column, Integer, String, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./users.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def run_migrations(engine):
    """Add any missing columns to existing tables so the schema stays in sync."""
    inspector = inspect(engine)

    # Only run if the users table already exists
    if "users" not in inspector.get_table_names():
        return

    existing = {col["name"] for col in inspector.get_columns("users")}

    # (column_name, SQLite column definition)
    migrations = [
        ("email",         "VARCHAR"),
        ("bio",           "VARCHAR"),
        ("age",           "INTEGER"),
        ("favorite_game", "VARCHAR"),
        ("role",          "VARCHAR NOT NULL DEFAULT 'user'"),
        ("language",      "VARCHAR NOT NULL DEFAULT 'en'"),
    ]

    with engine.connect() as conn:
        for col_name, col_def in migrations:
            if col_name not in existing:
                print(f"[DB migration] Adding missing column: users.{col_name}")
                conn.execute(text(f"ALTER TABLE users ADD COLUMN {col_name} {col_def}"))
        conn.commit()

    # Backfill spacefunk_stats from existing spacefunk_runs for any users who
    # played before this migration was introduced.
    tables = inspector.get_table_names()
    if "spacefunk_runs" in tables and "spacefunk_stats" in tables:
        with engine.connect() as conn:
            existing_stats = {
                row[0] for row in conn.execute(text("SELECT user_id FROM spacefunk_stats"))
            }
            users_with_runs = conn.execute(text("SELECT DISTINCT user_id FROM spacefunk_runs")).fetchall()
            for (uid,) in users_with_runs:
                if uid not in existing_stats:
                    print(f"[DB migration] Backfilling spacefunk_stats for user_id={uid}")
                    conn.execute(text("""
                        INSERT INTO spacefunk_stats (user_id, total_runs, total_distance_m, best_score)
                        SELECT user_id, COUNT(*), SUM(distance_m), MAX(score)
                        FROM spacefunk_runs
                        WHERE user_id = :uid
                        GROUP BY user_id
                    """), {"uid": uid})
            conn.commit()