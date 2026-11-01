"""Store lifetime analysis limits by Telegram user ID."""

import sqlite3
from contextlib import closing
from pathlib import Path

FREE_ANALYSIS_LIMIT = 3


def _connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.execute(
        "CREATE TABLE IF NOT EXISTS user_usage ("
        "user_id INTEGER PRIMARY KEY, completed INTEGER NOT NULL DEFAULT 0 "
        f"CHECK (completed BETWEEN 0 AND {FREE_ANALYSIS_LIMIT}))"
    )
    return connection


def remaining_analyses(user_id: int, path: Path) -> int:
    with closing(_connect(path)) as connection:
        row = connection.execute(
            "SELECT completed FROM user_usage WHERE user_id = ?", (user_id,)
        ).fetchone()
    return FREE_ANALYSIS_LIMIT - (row[0] if row else 0)


def record_success(user_id: int, path: Path) -> int:
    with closing(_connect(path)) as connection, connection:
        connection.execute(
            "INSERT INTO user_usage (user_id, completed) VALUES (?, 1) "
            "ON CONFLICT(user_id) DO UPDATE SET completed = completed + 1",
            (user_id,),
        )
        completed = connection.execute(
            "SELECT completed FROM user_usage WHERE user_id = ?", (user_id,)
        ).fetchone()[0]
    return FREE_ANALYSIS_LIMIT - completed
