import os
import re
import sys
from datetime import timedelta
from pathlib import Path
from dotenv import load_dotenv
from flask import Flask, Response, jsonify, request, send_from_directory, session
from flask_cors import CORS
from json import load as json_load
from groq import APIStatusError, Groq

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR / "frontend"

if hasattr(sys, "frozen"):
    ENV_PATH = Path(sys.executable).parent / "Development" / ".env"
else:
    ENV_PATH = BASE_DIR / "Development" / ".env"

load_dotenv(ENV_PATH)

import db
from auth import auth
from chats import chats

IS_RENDER = os.getenv("RENDER") == "true" or os.getenv("RENDER_SERVICE_ID") is not None
MAX_HISTORY = 20
MAX_TOTAL_CHARS = 16000

IGNORE_DIRS = {
    ".git",
    "node_modules",
    "__pycache__",
    "venv",
    "env",
    "dist",
    "build",
    ".idea",
    ".vscode"
}

CODE_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".html", ".css", ".json",
    ".cs", ".cpp", ".c", ".h", ".java", ".go", ".rs", ".sql",
    ".md", ".txt", ".yml", ".yaml", ".sh", ".bat"
}

MENTION_PATTERN = re.compile(r"@(\S+)")
EXCLUDE_PATTERN = re.compile(r"~(\S+)")

personality_path = BASE_DIR / "personality.txt"
personality = personality_path.read_text(encoding="utf-8") if personality_path.exists() else "You are Tev."

app = Flask(__name__)

# Safely load secret key from environment or config.json fallback
def get_secret_key():
    if os.getenv("FLASK_SECRET_KEY"):
        return os.getenv("FLASK_SECRET_KEY")
    config_path = BASE_DIR / "config.json"
    if config_path.exists():
        with config_path.open("r", encoding="utf-8") as f:
            return json_load(f).get("secret_key", "default-fallback-secret")
    return "default-fallback-secret"

app.secret_key = get_secret_key()
app.permanent_session_lifetime = timedelta(days=30)

app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SECURE=IS_RENDER,
    SESSION_COOKIE_SAMESITE="None" if IS_RENDER else "Lax"
)

CORS(
    app,
    supports_credentials=True,
    origins=[
        "https://cohendacool.github.io",
        "https://tev-web.onrender.com",
        "https://staging.d3j0llm8tu6dg3.amplifyapp.com/",
        "http://127.0.0.1:5500",
        "http://localhost:5500"
    ]
)

db.setup()
app.register_blueprint(auth)
app.register_blueprint(chats)

client = Groq(api_key=os.getenv("GROQ_API_KEY"))


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def static_files(path):
    if path:
        file_path = FRONTEND_DIR / path
        if file_path.is_file() and FRONTEND_DIR.resolve() in file_path.resolve().parents:
            return send_from_directory(FRONTEND_DIR, path)
    return send_from_directory(FRONTEND_DIR, "index.html")


def _is_ignored_project_path(relative_parts):
    return any(
        part in IGNORE_DIRS or part.startswith(".")
        for part in relative_parts
    )


def list_project_files(project_path):
    files = []
    if not project_path.exists() or not project_path.is_dir():
        return files

    for file_path in sorted(project_path.rglob("*")):
        if not file_path.is_file():
            continue
        relative_path = file_path.relative_to(project_path)
        if _is_ignored_project_path(relative_path.parts):
            continue
        if file_path.suffix.lower() not in CODE_EXTENSIONS:
            continue
        files.append(relative_path.as_posix())
    return files


def list_project_folders(project_path):
    folders = []
    if not project_path.exists() or not project_path.is_dir():
        return folders

    ignored_dirs = IGNORE_DIRS - {"node_modules"}

    for current_root, dirnames, filenames in os.walk(project_path):
        current_path = Path(current_root)
        relative_current = current_path.relative_to(project_path)

        if any(
            part.startswith(".") or part in ignored_dirs
            for part in relative_current.parts
        ):
            dirnames[:] = []
            continue

        for dirname in list(dirnames):
            if dirname.startswith(".") or dirname in ignored_dirs:
                dirnames.remove(dirname)
                continue

            folder_path = current_path / dirname
            relative_path = folder_path.relative_to(project_path)
            folders.append(str(relative_path).replace("\\", "/"))

            if dirname == "node_modules":
                dirnames.remove(dirname)

    return sorted(folders)


def extract_mentions(message):
    return MENTION_PATTERN.findall(message)


def strip_mentions(message):
    return MENTION_PATTERN.sub("", message).strip()


def extract_exclusions(message):
    return EXCLUDE_PATTERN.findall(message)


def strip_exclusions(message):
    return EXCLUDE_PATTERN.sub("", message).strip()


def exclude_project_paths(files, exclusions):
    excluded_paths = {
        exclusion.replace("\\", "/").strip("/")
        for exclusion in exclusions
        if exclusion.replace("\\", "/").strip("/")
    }
    return [
        file_path
        for file_path in files
        if not any(
            file_path == excluded or file_path.startswith(excluded + "/")
            for excluded in excluded_paths
        )
    ]


def build_project_context(project, relevant_files):
    project_path = Path(project["path"])
    file_contents = []
    total_chars = 0

    for relative in relevant_files:
        file_path = project_path / relative
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            if len(content) > 8000:
                content = content[:8000] + "\n... [File truncated]"

            file_block = f"--- FILE: {relative} ---\n{content}\n"
            if total_chars + len(file_block) > MAX_TOTAL_CHARS:
                file_contents.append("... [Remaining files omitted to fit the size limit]")
                break

            file_contents.append(file_block)
            total_chars += len(file_block)
        except Exception:
            pass

    files_text = "\n\n".join(file_contents) if file_contents else "No files found."

    return f"""

Connected Project Directory: {project['name']}
Project Files:
{files_text}

Strict Rule for this chat:
If the user's prompt is not about computers, programming, or anything to do with this project or its files, you must automatically and exclusively respond with: "Sorry, this prompt is not related to this project. Please try again." Do not include anything else in your response if it fails this check. Otherwise, search through the files above, find fixes for broken files or code, and answer them. If a file you need was not included above, say so instead of guessing at its contents.
"""


@app.route("/tev_response", methods=["POST"])
def call_function():
    if "user_id" not in session:
        return jsonify({"error": "Please log in."}), 401

    data = request.get_json(silent=True) or {}
    message = str(data.get("message", "")).strip()
    chat_id = data.get("chat_id")
    project_id = data.get("project_id")

    if not message:
        return jsonify({"error": "Message cannot be empty."}), 400

    if not project_id and not db.chat_belongs_to(chat_id, session["user_id"]):
        return jsonify({"error": "Chat not found."}), 404

    system_content = personality
    project = None

    if project_id:
        project = db.get_project(project_id, session["user_id"])
        if not project:
            return jsonify({"error": "Project not found."}), 404

        rows = db.get_project_messages(project_id)
        history = [{"role": row["role"], "content": row["content"]} for row in rows][-MAX_HISTORY:]
        db.add_project_message(project_id, "user", message)
    else:
        rows = db.get_messages(chat_id)
        history = [{"role": row["role"], "content": row["content"]} for row in rows][-MAX_HISTORY:]
        db.add_message(chat_id, "user", message)

        if not rows:
            db.rename_chat(chat_id, message[:40])

    def generate():
        nonlocal system_content
        try:
            if project:
                project_path = Path(project["path"]).resolve()
                mentions = extract_mentions(message)

                if "." in mentions:
                    exclusions = extract_exclusions(message)
                    all_files = list_project_files(project_path)
                    all_files = exclude_project_paths(all_files, exclusions)

                    yield "\x00STATUS\x00Reading the entire project, this may take a while...\x00"
                    system_content += build_project_context(project, all_files)
                    yield "\x00STATUS\x00\x00"

                    clean_message = strip_exclusions(strip_mentions(message))
                    messages = [{"role": "system", "content": system_content}] + history
                    messages.append({"role": "user", "content": clean_message})

                    response_content = ""
                    stream = client.chat.completions.create(
                        messages=messages,
                        model="openai/gpt-oss-120b",
                        temperature=1,
                        max_tokens=2056,
                        top_p=1,
                        stop=None,
                        stream=True
                    )

                    for chunk in stream:
                        content = chunk.choices[0].delta.content
                        if content:
                            response_content += content
                            yield content

                    db.add_project_message(project_id, "assistant", response_content)
                    return

                if not mentions:
                    warning = "I need at least one @file mention so I know what to read."
                    yield warning
                    db.add_project_message(project_id, "assistant", warning)
                    return

                missing = []
                valid_files = []

                for mention in mentions:
                    file_path = project_path / mention
                    try:
                        resolved = file_path.resolve()
                        resolved.relative_to(project_path)
                    except (ValueError, OSError):
                        missing.append(mention)
                        continue

                    if resolved.is_file():
                        valid_files.append(resolved.relative_to(project_path).as_posix())
                    else:
                        missing.append(mention)

                if missing:
                    warning = f"I couldn't find these files: {', '.join(missing)}."
                    yield warning
                    db.add_project_message(project_id, "assistant", warning)
                    return

                yield "\x00STATUS\x00Reading files...\x00"
                system_content += build_project_context(project, valid_files)

            yield "\x00STATUS\x00\x00"

            clean_message = strip_mentions(message) if project else message
            messages = [{"role": "system", "content": system_content}] + history
            messages.append({"role": "user", "content": clean_message})

            response_content = ""
            stream = client.chat.completions.create(
                messages=messages,
                model="openai/gpt-oss-120b",
                temperature=1,
                max_tokens=2056,
                top_p=1,
                stop=None,
                stream=True
            )

            for chunk in stream:
                content = chunk.choices[0].delta.content
                if content:
                    response_content += content
                    yield content

            if project_id:
                db.add_project_message(project_id, "assistant", response_content)
            else:
                db.add_message(chat_id, "assistant", response_content)

        except APIStatusError as error:
            err_msg = error.body.get('error', {}).get('message', 'The request was too large or rate-limited.')
            yield f"\n[Error: {err_msg}]"

    return Response(generate(), mimetype="text/plain")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=not IS_RENDER)
