import json
from pathlib import Path
from typing import Any

from .paths import data_dir

_SESSION_FILE = "session.json"


def session_path() -> Path:
    return data_dir() / _SESSION_FILE


def load_session() -> dict[str, Any]:
    p = session_path()
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def save_session(token: str | None, user: dict[str, Any] | None = None) -> None:
    data = load_session()
    if token:
        data["access_token"] = token
    if user is not None:
        data["user"] = user
    session_path().write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def clear_session() -> None:
    p = session_path()
    if p.exists():
        p.unlink()


def get_token() -> str | None:
    return load_session().get("access_token")
