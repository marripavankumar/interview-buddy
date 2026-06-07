from __future__ import annotations

import hashlib
import json
from pathlib import Path

import gradio as gr


ROOT = Path(__file__).resolve().parent
USERS_FILE = ROOT / "interview_users.json"


def _load_users() -> dict[str, str]:
    if not USERS_FILE.exists():
        return {}
    try:
        data = json.loads(USERS_FILE.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return {str(k): str(v) for k, v in data.items()}
    except Exception:
        return {}
    return {}


def _save_users(users: dict[str, str]) -> None:
    USERS_FILE.write_text(json.dumps(users, indent=2), encoding="utf-8")


def _password_hash(username: str, password: str) -> str:
    return hashlib.sha256(f"{username}:{password}".encode("utf-8")).hexdigest()


def _login_user(username: str, password: str):
    username = (username or "").strip()
    password = (password or "").strip()
    if not username or not password:
        return (
            "Username and password are required.",
            gr.update(visible=True),
            gr.update(visible=False),
            None,
            "",
            gr.update(value="Login"),
            gr.update(value="Log In"),
        )

    users = _load_users()
    stored = users.get(username)
    if not stored:
        return (
            "User not found. Please sign up first.",
            gr.update(visible=True),
            gr.update(visible=False),
            None,
            "",
            gr.update(value="Login"),
            gr.update(value="Log In"),
        )
    if stored != _password_hash(username, password):
        return (
            "Invalid password. Please try again.",
            gr.update(visible=True),
            gr.update(visible=False),
            None,
            "",
            gr.update(value="Login"),
            gr.update(value="Log In"),
        )
    return (
        f"Welcome back, {username}.",
        gr.update(visible=False),
        gr.update(visible=True),
        True,
        username,
        gr.update(value="Login"),
        gr.update(value="Log In"),
    )


def _signup_user(username: str, password: str):
    username = (username or "").strip()
    password = (password or "").strip()
    if not username or not password:
        return (
            "Username and password are required.",
            gr.update(visible=True),
            gr.update(visible=False),
            None,
            "",
            gr.update(value="Sign Up"),
            gr.update(value="Sign Up"),
        )

    users = _load_users()
    if username in users:
        return (
            "User already exists. Please log in.",
            gr.update(visible=True),
            gr.update(visible=False),
            None,
            "",
            gr.update(value="Login"),
            gr.update(value="Log In"),
        )

    users[username] = _password_hash(username, password)
    _save_users(users)
    return (
        "Account created successfully. Please log in.",
        gr.update(visible=True),
        gr.update(visible=False),
        None,
        "",
        gr.update(value="Login"),
        gr.update(value="Log In"),
    )
