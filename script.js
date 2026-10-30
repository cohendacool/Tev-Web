import os
import secrets
import sys
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, Response, jsonify, request, send_from_directory, session
from flask_cors import CORS
from openai import OpenAI, APIError

if hasattr(sys, "frozen"):
    env_dir = Path(sys.executable).parent
else:
    env_dir = Path(__file__).resolve().parent.parent / "Development"

load_dotenv(env_dir / ".env")

import db
from auth import auth
from chats import chats

MAX_HISTORY = 10

personality = (
    Path(__file__).resolve().parent / "personality.txt"
).read_text(encoding="utf-8")

client = OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama",
    timeout=30.0
)

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY") or secrets.token_hex(32)
app.permanent_session_lifetime = timedelta(days=30)

app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_SAMESITE="None"
)

CORS(
    app,
    supports_credentials=True,
    origins=["https://cohendacool.github.io"]
)

db.setup()
app.register_blueprint(auth)
app.register_blueprint(chats)


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def static_files(path):
    if path != "" and os.path.exists(os.path.join("frontend", path)):
        return send_from_directory("frontend", path)

    return send_from_directory("frontend", "index.html")


@app.route("/tev_response", methods=["POST"])
def call_function():
    if "user_id" not in session:
        return jsonify({"error": "Please log in."}), 401

    data = request.get_json(silent=True) or {}
    message = str(data.get("message", "")).strip()
    chat_id = data.get("chat_id")

    if not message:
        return jsonify({"error": "Message cannot be empty."}), 400

    if not db.chat_belongs_to(chat_id, session["user_id"]):
        return jsonify({"error": "Chat not found."}), 404

    rows = db.get_messages(chat_id)
    history = [
        {"role": row["role"], "content": row["content"]}
        for row in rows
    ][-MAX_HISTORY:]

    db.add_message(chat_id, "user", message)
    if not rows:
        db.rename_chat(chat_id, message[:40])

    def generate():
        messages = [{"role": "system", "content": personality}] + history
        messages.append({"role": "user", "content": message})

        response_content = ""

        try:
            stream = client.chat.completions.create(
                messages=messages,
                model="qwen2.5:0.5b",
                temperature=0.7,
                max_tokens=4096,
                stream=True
            )

            for chunk in stream:
                content = chunk.choices[0].delta.content
                if content:
                    response_content += content
                    yield content

            db.add_message(chat_id, "assistant", response_content)

        except APIError as error:
            yield f"\n[Error: Ollama API Error - {str(error)}]"
        except Exception as error:
            yield f"\n[Error: Could not connect to Ollama. Make sure Ollama is running (`ollama serve`). Details: {str(error)}]"

    return Response(generate(), mimetype="text/plain")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
