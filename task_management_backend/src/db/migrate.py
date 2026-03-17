"""Idempotent migration runner for PostgreSQL schema.

Run:
    python -m src.db.migrate
"""

from src.db.connection import get_db_conn


def _exec(conn, sql: str) -> None:
    with conn.cursor() as cur:
        cur.execute(sql)


# PUBLIC_INTERFACE
def run_migrations() -> None:
    """Create core tables and indexes if they do not exist."""
    with get_db_conn() as conn:
        _exec(conn, 'CREATE EXTENSION IF NOT EXISTS "pgcrypto";')

        _exec(
            conn,
            """
            CREATE TABLE IF NOT EXISTS users (
                id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
                email text NOT NULL UNIQUE,
                password_hash text NOT NULL,
                created_at timestamptz NOT NULL DEFAULT now()
            );
            """.strip(),
        )

        _exec(
            conn,
            """
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'task_status') THEN
                    CREATE TYPE task_status AS ENUM ('todo', 'in_progress', 'done');
                END IF;
                IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'task_priority') THEN
                    CREATE TYPE task_priority AS ENUM ('low', 'medium', 'high');
                END IF;
            END $$;
            """.strip(),
        )

        _exec(
            conn,
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                title text NOT NULL,
                description text NULL,
                status task_status NOT NULL DEFAULT 'todo',
                priority task_priority NOT NULL DEFAULT 'medium',
                due_date date NULL,
                created_at timestamptz NOT NULL DEFAULT now(),
                updated_at timestamptz NOT NULL DEFAULT now()
            );
            """.strip(),
        )

        _exec(
            conn,
            """
            CREATE OR REPLACE FUNCTION set_updated_at()
            RETURNS trigger AS $$
            BEGIN
                NEW.updated_at = now();
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
            """.strip(),
        )

        _exec(
            conn,
            """
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_trigger WHERE tgname = 'trg_tasks_set_updated_at'
                ) THEN
                    CREATE TRIGGER trg_tasks_set_updated_at
                    BEFORE UPDATE ON tasks
                    FOR EACH ROW
                    EXECUTE FUNCTION set_updated_at();
                END IF;
            END $$;
            """.strip(),
        )

        _exec(conn, "CREATE INDEX IF NOT EXISTS idx_tasks_user_status ON tasks (user_id, status);")
        _exec(conn, "CREATE INDEX IF NOT EXISTS idx_tasks_user_due_date ON tasks (user_id, due_date);")
        _exec(conn, "CREATE INDEX IF NOT EXISTS idx_tasks_user_priority ON tasks (user_id, priority);")
        _exec(conn, "CREATE INDEX IF NOT EXISTS idx_tasks_user_created_at ON tasks (user_id, created_at DESC);")

        _exec(
            conn,
            """
            CREATE INDEX IF NOT EXISTS idx_tasks_search
            ON tasks
            USING GIN (
                to_tsvector('english', coalesce(title,'') || ' ' || coalesce(description,''))
            );
            """.strip(),
        )

        conn.commit()


if __name__ == "__main__":
    run_migrations()
    print("Migrations applied successfully.")
