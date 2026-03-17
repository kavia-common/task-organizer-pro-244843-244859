from datetime import date
from typing import Any, Dict, List, Optional, Sequence, Tuple


class TasksRepo:
    def __init__(self, conn):
        self.conn = conn

    def create(
        self,
        *,
        user_id: str,
        title: str,
        description: Optional[str],
        status: str,
        priority: str,
        due_date: Optional[date],
    ) -> Dict[str, Any]:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO tasks (user_id, title, description, status, priority, due_date)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING *;
                """.strip(),
                (user_id, title, description, status, priority, due_date),
            )
            task = cur.fetchone()
        self.conn.commit()
        return task

    def get(self, *, user_id: str, task_id: str) -> Optional[Dict[str, Any]]:
        with self.conn.cursor() as cur:
            cur.execute("SELECT * FROM tasks WHERE id = %s AND user_id = %s;", (task_id, user_id))
            return cur.fetchone()

    def delete(self, *, user_id: str, task_id: str) -> bool:
        with self.conn.cursor() as cur:
            cur.execute("DELETE FROM tasks WHERE id = %s AND user_id = %s;", (task_id, user_id))
            deleted = cur.rowcount > 0
        self.conn.commit()
        return deleted

    def update(
        self,
        *,
        user_id: str,
        task_id: str,
        fields: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        if not fields:
            return self.get(user_id=user_id, task_id=task_id)

        allowed = {"title", "description", "status", "priority", "due_date"}
        set_parts: List[str] = []
        values: List[Any] = []
        for k, v in fields.items():
            if k not in allowed:
                continue
            set_parts.append(f"{k} = %s")
            values.append(v)

        if not set_parts:
            return self.get(user_id=user_id, task_id=task_id)

        values.extend([task_id, user_id])
        sql = f"""
            UPDATE tasks
            SET {", ".join(set_parts)}
            WHERE id = %s AND user_id = %s
            RETURNING *;
        """.strip()

        with self.conn.cursor() as cur:
            cur.execute(sql, tuple(values))
            task = cur.fetchone()

        self.conn.commit()
        return task

    def list(
        self,
        *,
        user_id: str,
        q: Optional[str],
        status: Optional[str],
        priority: Optional[str],
        due_from: Optional[date],
        due_to: Optional[date],
        sort: str,
        order: str,
        limit: int,
        offset: int,
    ) -> Tuple[List[Dict[str, Any]], int]:
        where = ["user_id = %s"]
        params: List[Any] = [user_id]

        if status:
            where.append("status = %s")
            params.append(status)
        if priority:
            where.append("priority = %s")
            params.append(priority)
        if due_from:
            where.append("due_date >= %s")
            params.append(due_from)
        if due_to:
            where.append("due_date <= %s")
            params.append(due_to)

        if q:
            where.append(
                "to_tsvector('english', coalesce(title,'') || ' ' || coalesce(description,'')) @@ plainto_tsquery('english', %s)"
            )
            params.append(q)

        sort_map = {
            "created_at": "created_at",
            "updated_at": "updated_at",
            "due_date": "due_date",
            "priority": "priority",
            "status": "status",
            "title": "title",
        }
        sort_col = sort_map.get(sort, "created_at")
        order_sql = "ASC" if order.lower() == "asc" else "DESC"

        where_sql = " AND ".join(where)

        with self.conn.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) AS cnt FROM tasks WHERE {where_sql};", tuple(params))
            total = int(cur.fetchone()["cnt"])

            cur.execute(
                f"""
                SELECT *
                FROM tasks
                WHERE {where_sql}
                ORDER BY {sort_col} {order_sql}
                LIMIT %s OFFSET %s;
                """.strip(),
                tuple(params + [limit, offset]),
            )
            rows: Sequence[Dict[str, Any]] = cur.fetchall()

        return list(rows), total
