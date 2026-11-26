"""Persistent storage for 3.0 preview, isolated from the 2.x database.

The legacy diolino.sqlite3 is NEVER opened by this module. Calls are JSON-line
requests through a fixed, non-shell subprocess managed by Tauri.
"""
import json
import os
import sqlite3
import sys
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

ALLOWED = {
    "diolino-library", "diolino-health-entries", "diolino-health-goals",
    "diolino-bible-days", "diolino-preview-reviews",
    "diolino-habits-v1", "diolino-habit-marks-v1",
    "diolino-focus-settings", "diolino-focus-timer", "diolino-focus-sessions",
    "diolino-preview-agenda", "diolino-preview-tasks", "diolino-preview-studies",
}
MAX_BYTES = 2_000_000


def directory():
    # Separate preview app DB from the 2.x files.
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData/Local")
    else:
        base = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local/share")
    return base / "ProjetoDiolino" / "desktop-v3"


def db_path():
    return directory() / "preview.sqlite3"


def validate_key(key):
    if type(key) is not str or key not in ALLOWED:
        raise ValueError("Chave de armazenamento não permitida.")


def connect(path=None):
    path = Path(path) if path is not None else db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=10)
    connection.execute("PRAGMA busy_timeout=10000")
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("PRAGMA synchronous=FULL")
    connection.execute(
        "CREATE TABLE IF NOT EXISTS kv (key TEXT PRIMARY KEY, json TEXT NOT NULL, updated_at TEXT NOT NULL)"
    )
    return connection


def get(key, path=None):
    validate_key(key)
    with closing(connect(path)) as conn:
        row = conn.execute("SELECT json FROM kv WHERE key=?", (key,)).fetchone()
        return json.loads(row[0]) if row else None


def put(key, value, path=None):
    validate_key(key)
    payload = json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
    if len(payload.encode("utf-8")) > MAX_BYTES:
        raise ValueError("Registro muito grande.")
    with closing(connect(path)) as conn:
        with conn:
            conn.execute(
                "INSERT INTO kv(key,json,updated_at) VALUES(?,?,?) "
                "ON CONFLICT(key) DO UPDATE SET json=excluded.json, updated_at=excluded.updated_at",
                (key, payload, datetime.now(timezone.utc).isoformat()),
            )
    return True


def import_if_absent(key, value, path=None):
    """One-time import of existing WebView data; never overwrite SQLite."""
    validate_key(key)
    payload = json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
    if len(payload.encode("utf-8")) > MAX_BYTES:
        raise ValueError("Registro muito grande.")
    with closing(connect(path)) as conn:
        with conn:
            cursor = conn.execute(
                "INSERT OR IGNORE INTO kv(key,json,updated_at) VALUES(?,?,?)",
                (key, payload, datetime.now(timezone.utc).isoformat()),
            )
    return cursor.rowcount == 1


def backup(path=None):
    """SQLite online backup, atomic destination rename; never touches 2.x."""
    source = Path(path) if path is not None else db_path()
    if not source.is_file():
        raise FileNotFoundError("Banco da prévia inexistente.")
    folder = source.parent / "backups"
    folder.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    target = folder / f"preview-{stamp}.sqlite3"
    temp = folder / f".preview-{stamp}.tmp"
    try:
        with closing(connect(source)) as src, closing(sqlite3.connect(temp)) as dst:
            src.backup(dst)
            if dst.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise RuntimeError("Falha na verificação do backup.")
        os.replace(temp, target)
        return str(target)
    finally:
        temp.unlink(missing_ok=True)


def handle(request):
    if not isinstance(request, dict) or not isinstance(request.get("action"), str):
        raise ValueError("Requisição inválida.")
    action = request["action"]
    if action == "get":
        return get(request.get("key"))
    if action == "put":
        return put(request.get("key"), request.get("value"))
    if action == "import":
        return import_if_absent(request.get("key"), request.get("value"))
    if action == "backup":
        return backup()
    raise ValueError("Operação não permitida.")


def main():
    try:
        raw = sys.stdin.buffer.readline(MAX_BYTES + 2048)
        if not raw or len(raw) > MAX_BYTES + 1024:
            raise ValueError("Requisição muito grande ou vazia.")
        response = handle(json.loads(raw))
        print(json.dumps({"ok": True, "value": response}, ensure_ascii=False, allow_nan=False))
    except (OSError, sqlite3.Error, ValueError, TypeError, RuntimeError, KeyError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
