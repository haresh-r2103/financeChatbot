"""
Simple file-based auth. For production, replace with a proper database + JWT.
"""
import json
import hashlib
import uuid
from pathlib import Path

# Resolve relative to this file, not CWD
USERS_FILE = Path(__file__).parent / "users.json"
SESSIONS: dict[str, dict] = {}  # token -> user info (in-memory)


def _load_users() -> dict:
    if USERS_FILE.exists():
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    return {}


def _save_users(users: dict):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)


def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def register_user(name: str, email: str, password: str) -> dict:
    users = _load_users()
    email = email.lower().strip()

    if email in users:
        raise ValueError("An account with this email already exists.")

    if len(password) < 6:
        raise ValueError("Password must be at least 6 characters.")

    users[email] = {
        "name": name.strip(),
        "email": email,
        "password_hash": _hash_password(password),
    }
    _save_users(users)

    token = str(uuid.uuid4())
    SESSIONS[token] = {"email": email, "name": name.strip()}
    return {"token": token, "name": name.strip(), "email": email}


def login_user(email: str, password: str) -> dict:
    users = _load_users()
    email = email.lower().strip()

    user = users.get(email)
    if not user or user["password_hash"] != _hash_password(password):
        raise ValueError("Invalid email or password.")

    token = str(uuid.uuid4())
    SESSIONS[token] = {"email": email, "name": user["name"]}
    return {"token": token, "name": user["name"], "email": email}


def get_session(token: str) -> dict | None:
    return SESSIONS.get(token)
