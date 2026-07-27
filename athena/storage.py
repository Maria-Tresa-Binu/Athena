import sqlite3
import os
from datetime import datetime, timezone
from pathlib import Path


class Storage:
    def __init__(self, path: str | Path | None = None) -> None:
        database_path = Path(path or os.getenv("ATHENA_DB_PATH", ":memory:"))
        if database_path != Path(":memory:"):
            database_path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(str(database_path))
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY, title TEXT NOT NULL, completed INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL)")
        self.connection.execute("CREATE TABLE IF NOT EXISTS reminders (id INTEGER PRIMARY KEY, text TEXT NOT NULL, remind_at TEXT NOT NULL, completed INTEGER NOT NULL DEFAULT 0)")
        self.connection.commit()

    def add_task(self, title: str) -> int:
        cursor = self.connection.execute("INSERT INTO tasks(title, created_at) VALUES (?, ?)", (title, datetime.now(timezone.utc).isoformat()))
        self.connection.commit()
        return int(cursor.lastrowid)

    def list_tasks(self) -> list[dict]:
        return [dict(row) for row in self.connection.execute("SELECT id, title, completed FROM tasks ORDER BY completed, id").fetchall()]

    def complete_task(self, task_id: int) -> bool:
        cursor = self.connection.execute("UPDATE tasks SET completed=1 WHERE id=?", (task_id,))
        self.connection.commit()
        return cursor.rowcount == 1

    def add_reminder(self, text: str, remind_at: datetime) -> int:
        cursor = self.connection.execute("INSERT INTO reminders(text, remind_at) VALUES (?, ?)", (text, remind_at.isoformat()))
        self.connection.commit()
        return int(cursor.lastrowid)

    def list_reminders(self) -> list[dict]:
        return [dict(row) for row in self.connection.execute("SELECT id, text, remind_at, completed FROM reminders ORDER BY remind_at").fetchall()]
