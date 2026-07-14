"""Recovery imprints under CONDUCTOR_HOME/recovery — rebuild state from preserved patterns."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from conductor.agent.path_safety import is_write_denied
from conductor.paths import conductor_home

_MAX_MIRROR_BYTES = 2_000_000  # 2 MiB per file
_INDEX_NAME = "index.json"


def recovery_root() -> Path:
    root = conductor_home() / "recovery"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _safe_key(path: str) -> str:
    raw = str(path).encode("utf-8", errors="replace")
    return hashlib.sha256(raw).hexdigest()[:32]


def _index_path() -> Path:
    return recovery_root() / _INDEX_NAME


def _load_index() -> dict[str, Any]:
    p = _index_path()
    if not p.is_file():
        return {"files": {}}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(data, dict) and isinstance(data.get("files"), dict):
            return data
    except (OSError, json.JSONDecodeError):
        pass
    return {"files": {}}


def _save_index(data: dict[str, Any]) -> None:
    _index_path().write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def mirror_write(path: str, content: str, *, session_id: str = "") -> dict[str, Any]:
    """Store a recovery imprint of a successful write. Best-effort; never raises."""
    try:
        if is_write_denied(path):
            return {"ok": False, "error": "path denied"}
        data = content if isinstance(content, str) else str(content)
        raw = data.encode("utf-8", errors="replace")
        if len(raw) > _MAX_MIRROR_BYTES:
            return {"ok": False, "error": "content too large to mirror"}
        key = _safe_key(path)
        blob = recovery_root() / f"{key}.body"
        blob.write_bytes(raw)
        idx = _load_index()
        files = idx.setdefault("files", {})
        files[path] = {
            "key": key,
            "bytes": len(raw),
            "session_id": session_id,
            "path": path,
        }
        _save_index(idx)
        return {"ok": True, "path": path, "key": key, "bytes": len(raw)}
    except OSError as exc:
        return {"ok": False, "error": str(exc)}


def has_mirror(path: str) -> bool:
    idx = _load_index()
    entry = (idx.get("files") or {}).get(path)
    if not entry:
        return False
    key = str(entry.get("key") or "")
    return bool(key) and (recovery_root() / f"{key}.body").is_file()


def restore_path(path: str) -> dict[str, Any]:
    """Rebuild a path on disk from its recovery imprint. Respects write deny floors."""
    if is_write_denied(path):
        return {"ok": False, "error": "path denied by safety floors", "path": path}
    idx = _load_index()
    entry = (idx.get("files") or {}).get(path)
    if not entry:
        return {"ok": False, "error": "no recovery imprint", "path": path}
    key = str(entry.get("key") or "")
    blob = recovery_root() / f"{key}.body"
    if not blob.is_file():
        return {"ok": False, "error": "imprint blob missing", "path": path}
    try:
        content = blob.read_bytes()
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        return {"ok": True, "path": path, "bytes": len(content)}
    except OSError as exc:
        return {"ok": False, "error": str(exc), "path": path}


def ensure_parent_dirs(path: str) -> dict[str, Any]:
    if is_write_denied(path):
        return {"ok": False, "error": "path denied"}
    try:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        return {"ok": True, "path": str(Path(path).parent)}
    except OSError as exc:
        return {"ok": False, "error": str(exc)}


def path_exists(path: str) -> bool:
    try:
        return Path(path).exists()
    except OSError:
        return False
