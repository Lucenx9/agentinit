"""Minimal FastAPI todo app backed by SQLite."""

import os
import sqlite3
from typing import List

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Todo API")


class TodoCreate(BaseModel):
    title: str


class Todo(BaseModel):
    id: int
    title: str


def _db_path() -> str:
    return os.environ.get("TODOS_DB_PATH", "todos.db")


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS todos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL
        )
        """
    )
    return conn


@app.get("/todos", response_model=List[Todo])
def list_todos() -> List[Todo]:
    with _get_conn() as conn:
        rows = conn.execute("SELECT id, title FROM todos ORDER BY id ASC").fetchall()
    return [Todo(id=row["id"], title=row["title"]) for row in rows]


@app.post("/todos", response_model=Todo, status_code=201)
def create_todo(payload: TodoCreate) -> Todo:
    with _get_conn() as conn:
        cursor = conn.execute("INSERT INTO todos(title) VALUES (?)", (payload.title,))
        conn.commit()
        todo_id = int(cursor.lastrowid)
    return Todo(id=todo_id, title=payload.title)
