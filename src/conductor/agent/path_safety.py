"""Path and shell safety floors — deny catastrophic and secret-touching ops.

Ordinary project work stays available. This module is the **conductor spine**
guard against agents that “help” by wiping a machine (mass-delete of home,
root, or entire volumes). Integrity cascade / field repairs MUST call these
floors and must never auto-retry denied destructive commands.
"""

from __future__ import annotations

import os
import re
import shlex
from pathlib import Path

# Paths (or path prefixes) that write/read tools must not target.
_DENY_WRITE_NAMES = frozenset(
    {
        ".ssh",
        ".gnupg",
        ".aws",
        ".kube",
        "id_rsa",
        "id_ed25519",
        "shadow",
        "passwd",
        "sudoers",
    }
)

_DENY_WRITE_PREFIXES = (
    "/etc/shadow",
    "/etc/passwd",
    "/etc/sudoers",
    "/root/.ssh",
)

# Non-rm catastrophic patterns
_SHELL_CATASTROPHIC: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bmkfs(\.\w+)?\b", re.I),
    re.compile(r"\bwipefs\b", re.I),
    re.compile(r"\bdd\s+if=.+\s+of=/dev/[sh]d", re.I),
    re.compile(r"\bdd\s+.*\bof=/dev/(nvme|mmcblk)", re.I),
    re.compile(r":\(\)\s*\{\s*:\|:&\s*\}\s*;"),
    re.compile(r"\bchmod\s+(-[a-zA-Z]*R[a-zA-Z]*\s+)?[0-7]{3,4}\s+/(\s|$)", re.I),
    re.compile(r"\bchown\s+(-[a-zA-Z]*R[a-zA-Z]*\s+)?.+\s+/(\s|$)", re.I),
    re.compile(r">\s*/etc/passwd\b", re.I),
    re.compile(r">\s*/etc/shadow\b", re.I),
    re.compile(r"\bfind\s+/\s", re.I),  # find on filesystem root
    re.compile(r"\bfind\s+(~|\$HOME|\$\{HOME\})\s", re.I),
    re.compile(r"\bfind\b.+\s+-delete\b", re.I),
    re.compile(r"\bsudo\s+.*\b(rm\s+-[a-zA-Z]*[rf]|mkfs|dd\s+)", re.I),
)


def _expand(path: str | Path) -> Path:
    return Path(str(path)).expanduser().resolve()


def is_write_denied(path: str | Path) -> str | None:
    """Return denial reason if write/read should be blocked, else None."""
    try:
        p = _expand(path)
    except (OSError, RuntimeError):
        p = Path(str(path)).expanduser()
    raw = str(p)
    lower = raw.lower()
    for prefix in _DENY_WRITE_PREFIXES:
        if lower == prefix or lower.startswith(prefix + "/"):
            return f"path denied by safety floor: {prefix}"
    parts = {part.lower() for part in p.parts}
    for name in _DENY_WRITE_NAMES:
        if name in parts or p.name.lower() == name:
            if name in {".ssh", ".gnupg", ".aws", ".kube"}:
                return f"path denied by safety floor: {name}"
            if "/etc/" in lower or str(Path.home() / ".ssh") in raw:
                return f"path denied by safety floor: {name}"
    home = Path.home()
    for secret in (".ssh", ".gnupg", ".aws"):
        try:
            secret_root = (home / secret).resolve()
            if p == secret_root or secret_root in p.parents:
                return f"path denied by safety floor: ~/{secret}"
        except (OSError, RuntimeError):
            continue
    return None


def is_mass_delete_target(path_token: str) -> bool:
    """True if path is a whole-tree wipe target (/, ~, $HOME, /home/user bare)."""
    t = (path_token or "").strip().strip("'\"")
    if not t:
        return False
    # Exact dangerous targets
    if t in {
        "/",
        "/*",
        "/*/",
        "~",
        "~/",
        "~/*",
        "$HOME",
        "${HOME}",
        "$HOME/",
        "${HOME}/",
        "$HOME/*",
        "${HOME}/*",
        ".",
        "./*",
        "*",
    }:
        # "." and "*" only dangerous when cwd is home/root — still deny as too broad for agents
        if t in {".", "./*", "*"}:
            return True
        return True
    # Bare user home roots only (not /home/user/project)
    if re.fullmatch(r"/(home|Users|var/home)/\w+/?", t):
        return True
    if re.fullmatch(r"/(home|Users|var/home)/\w+/\*", t):
        return True
    try:
        home = Path.home().resolve()
        expanded = Path(t).expanduser().resolve()
        if expanded == Path("/") or expanded == home:
            return True
    except (OSError, RuntimeError, ValueError):
        pass
    return False


def _rm_targets(command: str) -> list[str]:
    """Best-effort extract path operands after `rm` flags."""
    cmd = command.strip()
    # Focus on each rm invocation in simple pipelines
    parts = re.split(r"\brm\b", cmd, flags=re.I)
    targets: list[str] = []
    for segment in parts[1:]:
        segment = segment.strip()
        if not segment:
            continue
        try:
            tokens = shlex.split(segment)
        except ValueError:
            tokens = segment.split()
        i = 0
        while i < len(tokens):
            tok = tokens[i]
            if tok.startswith("-") and tok != "-":
                i += 1
                continue
            # stop at shell operators left in token stream
            if tok in {"&&", "||", ";", "|"}:
                break
            targets.append(tok)
            i += 1
    return targets


def _has_recursive_rm(command: str) -> bool:
    # rm -r, -rf, -fr, --recursive
    if re.search(r"\brm\s+-[a-zA-Z]*r", command, re.I):
        return True
    if re.search(r"\brm\s+--recursive\b", command, re.I):
        return True
    return False


def is_shell_denied(command: str) -> str | None:
    """Return denial reason if shell command hits a catastrophic floor."""
    cmd = (command or "").strip()
    if not cmd:
        return None

    for pattern in _SHELL_CATASTROPHIC:
        if pattern.search(cmd):
            return (
                "shell command denied by safety floor: catastrophic pattern "
                f"({pattern.pattern!r})"
            )

    # Block writes into secret homes via shell redirection
    if re.search(r"(>~?/?\.ssh/|>\s*/etc/shadow)", cmd, re.I):
        return "shell command denied by safety floor: targets secret/system files"

    # Mass-delete via rm: only deny when targets are whole roots/homes (not /tmp/project)
    if re.search(r"\brm\b", cmd, re.I):
        recursive = _has_recursive_rm(cmd)
        for target in _rm_targets(cmd):
            if is_mass_delete_target(target):
                return (
                    "shell command denied by safety floor: mass-delete of root/home "
                    f"target {target!r}"
                )
            # recursive delete of /something that is only one segment after root
            # e.g. rm -rf /var is scary; allow /var/tmp/foo and /tmp/foo
            if recursive and target.startswith("/") and not target.startswith("/tmp"):
                stripped = target.rstrip("/")
                parts = [p for p in stripped.split("/") if p]
                # /var, /usr, /etc, /opt, /boot — single-segment system roots
                if len(parts) == 1 and parts[0] in {
                    "var",
                    "usr",
                    "etc",
                    "opt",
                    "boot",
                    "bin",
                    "sbin",
                    "lib",
                    "lib64",
                    "root",
                    "mnt",
                    "media",
                    "sys",
                    "proc",
                    "dev",
                }:
                    return (
                        "shell command denied by safety floor: recursive delete of "
                        f"system root {target!r}"
                    )

        # cd $HOME && rm -rf .
        if recursive and re.search(
            r"\bcd\s+(~|\$HOME|\$\{HOME\}|/|/home/\w+|/Users/\w+)\s*&&\s*rm\b",
            cmd,
            re.I,
        ):
            return "shell command denied by safety floor: recursive delete after cd to home/root"

    strict = (
        os.environ.get("CONDUCTOR_SHELL_STRICT", "").strip()
        or os.environ.get("ILO_SHELL_STRICT", "").strip()  # legacy
    )
    if strict in {"1", "true", "yes"}:
        if _has_recursive_rm(cmd):
            for target in _rm_targets(cmd):
                if target.startswith("/") or target.startswith("~") or "$HOME" in target:
                    return (
                        "shell command denied by safety floor: CONDUCTOR_SHELL_STRICT blocks "
                        "recursive rm on absolute/home paths"
                    )

    return None


def integrity_may_not_auto_retry(command: str) -> bool:
    """Field repairs must never auto-re-run commands that look destructive."""
    cmd = (command or "").strip()
    if not cmd:
        return True
    if is_shell_denied(cmd):
        return True
    low = cmd.lower()
    if re.search(r"\b(rm|dd|mkfs|wipefs|shred|truncate)\b", low):
        return True
    if re.search(r"\bfind\b", low) and "-delete" in low:
        return True
    if re.search(r"\bfind\b", low) and re.search(r"\bfind\s+/", low):
        return True
    return False
