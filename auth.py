from flask import Blueprint, jsonify, request, session
from werkzeug.security import check_password_hash, generate_password_hash

import db

auth = Blueprint("auth", __name__)


def fail(message, status):
    return jsonify({"success": False, "message": message}), status


def start_session(user_id, username):
    session.clear()
    session["user_id"] = user_id
    session["username"] = username
    session.permanent = True


def read_credentials():
    data = request.get_json(silent=True) or {}
    return str(data.get("username", "")).strip(), data.get("password", "")


@auth.route("/register", methods=["POST"])
def register():
    username, password = read_credentials()

    if not username or not isinstance(password, str) or not password:
        return fail("Username and password are required.", 400)

    if len(username) > 32 or len(password) < 8:
        return fail("Username must be at most 32 characters and password must be at least 8 characters.", 400)

    if db.find_user(username):
        return fail("Username already exists.", 409)

    user_id = db.create_user(username, generate_password_hash(password))
    start_session(user_id, username)

    return jsonify({"success": True, "message": "Registration successful!", "username": username}), 201


@auth.route("/login", methods=["POST"])
def login():
    username, password = read_credentials()

    if not username or not isinstance(password, str) or not password:
        return fail("Username and password are required.", 400)

    user = db.find_user(username)

    if not user or not check_password_hash(user["password_hash"], password):
        return fail("Invalid username or password.", 401)

    start_session(user["id"], user["username"])

    return jsonify({"success": True, "message": "Login successful!", "username": user["username"]})


@auth.route("/session", methods=["GET"])
def check_session():
    if "user_id" not in session:
        return jsonify({"success": False}), 401

    return jsonify({"success": True, "username": session["username"]})


@auth.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"success": True, "message": "Logged out."})