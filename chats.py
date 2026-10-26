from functools import wraps

from flask import Blueprint, jsonify, session

import db

chats = Blueprint("chats", __name__)


def login_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({"error": "Please log in."}), 401

        return view(*args, **kwargs)

    return wrapper


@chats.get("/chats")
@login_required
def list_chats():
    return jsonify(db.list_chats(session["user_id"]))


@chats.post("/chats")
@login_required
def new_chat():
    return jsonify({"id": db.create_chat(session["user_id"])})


@chats.get("/chats/<int:chat_id>")
@login_required
def open_chat(chat_id):
    if not db.chat_belongs_to(chat_id, session["user_id"]):
        return jsonify({"error": "Chat not found."}), 404

    return jsonify(db.get_messages(chat_id))


@chats.delete("/chats/<int:chat_id>")
@login_required
def delete_chat(chat_id):
    if not db.chat_belongs_to(chat_id, session["user_id"]):
        return jsonify({"error": "Chat not found."}), 404

    db.delete_chat(chat_id)

    return jsonify({})