"""SQLite-backed question storage for the portal prototype.

A question = title + prompt text + the teacher's reference diagram
(stored as the editor's JSON export). No auth in v1 — the frontend's
role picker decides which endpoints a client uses.
"""
import json
import os
import sqlite3
import time
from pathlib import Path

DB_PATH = Path(os.environ.get(
    'PORTAL_DB', Path(__file__).resolve().parents[1] / 'portal.db'))


def _conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def init_db():
    with _conn() as c:
        c.execute(
            'CREATE TABLE IF NOT EXISTS questions ('
            ' id INTEGER PRIMARY KEY AUTOINCREMENT,'
            ' title TEXT NOT NULL,'
            ' prompt TEXT NOT NULL,'
            ' reference TEXT NOT NULL,'
            ' created_at REAL NOT NULL)'
        )


def list_questions():
    with _conn() as c:
        rows = c.execute(
            'SELECT id, title, created_at FROM questions ORDER BY id DESC').fetchall()
    return [dict(r) for r in rows]


def get_question(qid):
    with _conn() as c:
        row = c.execute('SELECT * FROM questions WHERE id = ?', (qid,)).fetchone()
    if not row:
        return None
    q = dict(row)
    q['reference'] = json.loads(q['reference'])
    return q


def create_question(title, prompt, reference):
    with _conn() as c:
        cur = c.execute(
            'INSERT INTO questions (title, prompt, reference, created_at) VALUES (?,?,?,?)',
            (title, prompt, json.dumps(reference), time.time()))
        return cur.lastrowid


def delete_question(qid):
    with _conn() as c:
        cur = c.execute('DELETE FROM questions WHERE id = ?', (qid,))
        return cur.rowcount > 0
