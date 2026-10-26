import json
import os
import sqlite3
import urllib.error
import urllib.request
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / "Development" / ".env")

TURSO_URL = os.getenv("TURSO_DATABASE_URL")
TURSO_TOKEN = os.getenv("TURSO_AUTH_TOKEN")
USE_TURSO = bool(TURSO_URL)
DB_PATH = Path(__file__).resolve().parent / "tev.db"

TABLES = [
    """CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL COLLATE NOCASE,
        password_hash TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS chats (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        title TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id INTEGER,
        project_id INTEGER,
        role TEXT NOT NULL,
        content TEXT NOT NULL
    )""",
]

def to_arg(value):
    if value is None:
        return {"type": "null"}

    if isinstance(value, int):
        return {"type": "integer", "value": str(value)}

    if isinstance(value, float):
        return {"type": "float", "value": value}

    return {"type": "text", "value": str(value)}

def from_cell(cell):
    kind = cell["type"]

    if kind == "null":
        return None

    if kind == "integer":
        return int(cell["value"])

    if kind == "float":
        return float(cell["value"])

    return cell["value"]

def make_statement(sql, args):
    statement = {"sql": sql}

    if args:
        statement["args"] = [to_arg(value) for value in args]

    return statement

def run_turso(sql, args):
    body = {
        "requests": [
            {"type": "execute", "stmt": make_statement(sql, args)},
            {"type": "close"}
        ]
    }

    request = urllib.request.Request(
        TURSO_URL.replace("libsql://", "https://").rstrip("/") + "/v2/pipeline",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {TURSO_TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": "tev-backend"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            result = json.loads(response.read().decode("utf-8"))["results"][0]
    except urllib.error.HTTPError as error:
        raise RuntimeError(error.read().decode("utf-8"))

    if result["type"] == "error":
        raise RuntimeError(result["error"]["message"])

    return result["response"]["result"]

def local_execute(sql, args):
    db = sqlite3.connect(DB_PATH)
    cursor = db.execute(sql, args)
    db.commit()
    rowid = cursor.lastrowid
    db.close()
    return rowid

def local_fetch(sql, args):
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    rows = [dict(row) for row in db.execute(sql, args).fetchall()]
    db.close()
    return rows

def execute(sql, args=()):
    if not USE_TURSO:
        return local_execute(sql, args)

    rowid = run_turso(sql, args).get("last_insert_rowid")
    return int(rowid) if rowid else None

def fetch(sql, args=()):
    if not USE_TURSO:
        return local_fetch(sql, args)

    result = run_turso(sql, args)
    names = [col["name"] for col in result["cols"]]
    return [dict(zip(names, map(from_cell, row))) for row in result["rows"]]

def setup():
    for sql in TABLES:
        execute(sql)

def create_user(username, password_hash):
    return execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, password_hash))

def find_user(username):
    rows = fetch("SELECT * FROM users WHERE username = ?", (username,))
    return rows[0] if rows else None

def list_chats(user_id):
    return fetch("SELECT id, title FROM chats WHERE user_id = ? ORDER BY id DESC", (user_id,))

def create_chat(user_id):
    return execute("INSERT INTO chats (user_id, title) VALUES (?, ?)", (user_id, "New chat"))

def chat_belongs_to(chat_id, user_id):
    return bool(fetch("SELECT id FROM chats WHERE id = ? AND user_id = ?", (chat_id, user_id)))

def rename_chat(chat_id, title):
    execute("UPDATE chats SET title = ? WHERE id = ?", (title, chat_id))

def delete_chat(chat_id):
    execute("DELETE FROM messages WHERE chat_id = ?", (chat_id,))
    execute("DELETE FROM chats WHERE id = ?", (chat_id,))

def get_messages(chat_id):
    return fetch("SELECT role, content FROM messages WHERE chat_id = ? ORDER BY id", (chat_id,))

def add_message(chat_id, role, content):
    return execute("INSERT INTO messages (chat_id, role, content) VALUES (?, ?, ?)", (chat_id, role, content))
