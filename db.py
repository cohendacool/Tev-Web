import sqlite3
from pathlib import Path

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
        chat_id INTEGER NOT NULL,
        role TEXT NOT NULL,
        content TEXT NOT NULL
    )"""
]

def execute(sql, args=()):
    db = sqlite3.connect(DB_PATH)
    cursor = db.execute(sql, args)
    db.commit()
    rowid = cursor.lastrowid
    db.close()
    return rowid

def fetch(sql, args=()):
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    rows = [dict(row) for row in db.execute(sql, args).fetchall()]
    db.close()
    return rows

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
