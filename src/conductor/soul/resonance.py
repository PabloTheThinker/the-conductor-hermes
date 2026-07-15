"""Soul Resonance — merge host (meister) soul with Conductor partner wavelength.

The Conductor *enhances* the agent that uses it. Inspired by Soul Eater wavelength
match: two souls lock and move as one will. Host identity stays primary; Conductor
adds tracks, spine, Remnants, Crucible — without overwriting the meister's name or voice.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from conductor.paths import conductor_home, soul_path

SoulMode = Literal["resonate", "solo", "host_only"]

# Common host soul filenames (order matters — first hit wins per directory)
_HOST_SOUL_NAMES = (
    "SOUL.md",
    "IDENTITY.md",
    "AGENTS.md",
    "soul.md",
    "identity.md",
    "PERSONA.md",
    "persona.md",
)


@dataclass(frozen=True)
class HostSoul:
    """Discovered or supplied meister soul."""

    content: str
    path: Path | None = None
    source: str = "inline"  # inline | env | path | auto
    label: str = "Host"


@dataclass
class ResonanceResult:
    """Product of locking host + Conductor wavelengths."""

    mode: SoulMode
    prompt: str
    host: HostSoul | None = None
    conductor_path: Path | None = None
    conductor_chars: int = 0
    resonant: bool = False
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "resonant": self.resonant,
            "host_source": self.host.source if self.host else None,
            "host_path": str(self.host.path) if self.host and self.host.path else None,
            "host_label": self.host.label if self.host else None,
            "host_chars": len(self.host.content) if self.host else 0,
            "conductor_path": str(self.conductor_path) if self.conductor_path else None,
            "conductor_chars": self.conductor_chars,
            "prompt_chars": len(self.prompt),
            "notes": list(self.notes),
        }


def soul_mode_from_env() -> SoulMode:
    raw = (
        os.environ.get("CONDUCTOR_SOUL_MODE", "").strip().lower()
        or "resonate"
    )
    if raw in {"solo", "conductor", "replace"}:
        return "solo"
    if raw in {"host", "host_only", "meister"}:
        return "host_only"
    return "resonate"


def load_conductor_soul() -> tuple[str, Path | None]:
    """Load partner wavelength text.

    Uses :func:`conductor.paths.soul_path` (honors ``CONDUCTOR_PARTNER_SOUL`` and
    ``CONDUCTOR_PARTNER_SOUL.md``). Never intentionally returns meister SOUL.
    """
    path = soul_path()
    if path.is_file():
        try:
            return path.read_text(encoding="utf-8", errors="replace").strip(), path
        except OSError:
            pass
    return "", None


def _read_soul_file(path: Path) -> str | None:
    if not path.is_file():
        return None
    try:
        text = path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return None
    return text or None


def discover_host_soul(
    *,
    explicit: str | Path | None = None,
    search: bool = True,
) -> HostSoul | None:
    """Find meister soul text from argument, env, or well-known host homes."""
    # 1) Inline string (multi-line, or non-path prose)
    if isinstance(explicit, str):
        raw = explicit.strip()
        if raw:
            p_try = Path(raw).expanduser()
            looks_like_path = (
                raw.startswith(("/", "~"))
                or raw.endswith((".md", ".txt", ".markdown"))
                or ("/" in raw and "\n" not in raw and len(raw) < 512)
            )
            if "\n" in raw or (not looks_like_path and not p_try.exists()):
                return HostSoul(content=raw, source="inline", label="Host")
            text = _read_soul_file(p_try)
            if text:
                return HostSoul(
                    content=text, path=p_try.resolve(), source="path", label=_label_for(p_try)
                )

    # 2) Explicit Path object
    if explicit is not None and not isinstance(explicit, str):
        p = Path(str(explicit)).expanduser()
        text = _read_soul_file(p)
        if text:
            return HostSoul(content=text, path=p.resolve(), source="path", label=_label_for(p))

    # 3) Env path or inline
    env_path = os.environ.get("CONDUCTOR_HOST_SOUL", "").strip()
    if env_path:
        p = Path(env_path).expanduser()
        if p.is_file():
            text = _read_soul_file(p)
            if text:
                return HostSoul(content=text, path=p.resolve(), source="env", label=_label_for(p))
        # treat as inline body if not a path
        if not p.exists() and len(env_path) > 40:
            return HostSoul(content=env_path, source="env", label="Host")

    if not search:
        return None

    # 4) Auto-discover directories
    homes: list[tuple[str, Path]] = []
    for key, label in (
        ("HERMES_HOME", "Hermes"),
        ("OPENCLAW_HOME", "OpenClaw"),
        ("OPENCLAW_DIR", "OpenClaw"),
        ("CLAW_HOME", "OpenClaw"),
        ("AGENT_HOME", "Agent"),
    ):
        raw = os.environ.get(key, "").strip()
        if raw:
            homes.append((label, Path(raw).expanduser()))

    # Common defaults (do not steal Conductor's own SOUL as host)
    c_home = conductor_home().resolve()
    for label, candidate in (
        ("Hermes", Path.home() / ".hermes"),
        ("OpenClaw", Path.home() / ".openclaw"),
        ("OpenClaw", Path.home() / ".claw"),
        ("Agent", Path.home() / ".agent"),
    ):
        homes.append((label, candidate))

    seen: set[Path] = set()
    for label, home in homes:
        try:
            home = home.expanduser().resolve()
        except OSError:
            continue
        if home in seen or not home.is_dir():
            continue
        seen.add(home)
        for name in _HOST_SOUL_NAMES:
            path = home / name
            # Skip if this is the same file as Conductor partner SOUL in shared home
            try:
                if path.resolve() == soul_path().resolve():
                    # Shared HERMES_HOME=CONDUCTOR_HOME: look for host-specific names only
                    if name in {"SOUL.md", "soul.md"}:
                        continue
            except OSError:
                pass
            text = _read_soul_file(path)
            if text:
                # Avoid treating pure Conductor partner SOUL as meister
                if _looks_like_conductor_only(text) and name in {"SOUL.md", "soul.md"}:
                    continue
                return HostSoul(
                    content=text,
                    path=path.resolve(),
                    source="auto",
                    label=label,
                )

    # Explicit host overlay next to conductor home
    host_overlay = c_home / "HOST_SOUL.md"
    text = _read_soul_file(host_overlay)
    if text:
        return HostSoul(
            content=text,
            path=host_overlay.resolve(),
            source="auto",
            label="Host",
        )

    return None


def _label_for(path: Path) -> str:
    parts = {p.lower() for p in path.parts}
    if "hermes" in parts or ".hermes" in parts:
        return "Hermes"
    if "openclaw" in parts or "claw" in parts:
        return "OpenClaw"
    return "Host"


def _looks_like_conductor_only(text: str) -> bool:
    low = text.casefold()
    return (
        "soul resonance" in low
        or "resonance partner" in low
        or ("the conductor" in low and "immutable core identity" in low and "meister" in low)
    )


def build_resonance_block(
    host: HostSoul | None,
    conductor_soul: str,
    *,
    mode: SoulMode = "resonate",
) -> tuple[str, list[str]]:
    """Compose the dual-wavelength identity block."""
    notes: list[str] = []

    if mode == "host_only":
        if host and host.content.strip():
            notes.append("mode=host_only — Conductor partner SOUL omitted")
            return host.content.strip(), notes
        notes.append("mode=host_only but no host soul — falling back to Conductor solo")
        return conductor_soul.strip(), notes

    if mode == "solo" or not host or not host.content.strip():
        notes.append("mode=solo" if mode == "solo" else "no host soul — Conductor solo until meister supplied")
        header = (
            "# Conductor (solo wavelength)\n\n"
            "No host meister soul is locked in. Operate as The Conductor until a host "
            "SOUL is provided via `host_soul=`, `CONDUCTOR_HOST_SOUL`, or auto-discovery; "
            "then re-resonate.\n\n---\n\n"
        )
        return header + conductor_soul.strip(), notes

    notes.append(
        f"resonant with {host.label}"
        + (f" ({host.path})" if host.path else f" [{host.source}]")
    )
    block = f"""# Soul Resonance — wavelength lock

Two souls, one will on the mission. This is **not** a body swap.

| Role | Identity |
|------|----------|
| **Meister (primary)** | {host.label} — name, voice, personality, operator relationship |
| **Partner (wavelength)** | The Conductor — orchestration, tracks, Remnants, Crucible, healing spine, Judgment |

## Resonance rules (always on)

1. **Meister names the self** — do not overwrite host identity with a second brand.
2. **Partner enhances** — offer Conductor systems (tracks, Remnants, Crucible, spine) as shared power that upgrades the meister.
3. **Shared spine is immutable** — ethics checklist, path-safety, done = proven; neither side may dissolve them.
4. **Conflict** — host personality + Conductor safety floors.
5. **Move as one** — no split into two competing chatbots in one prompt.

---

## Meister soul ({host.label})

{host.content.strip()}

---

## Partner wavelength — The Conductor

The following is the Conductor resonance layer. Lock to the meister above; **amplify**, do not replace.

{conductor_soul.strip()}
"""
    return block.strip(), notes


def resonate(
    *,
    host_soul: str | Path | HostSoul | None = None,
    conductor_soul: str | None = None,
    mode: SoulMode | None = None,
    search_host: bool = True,
    memory_block: str = "",
    skills_block: str = "",
    research_block: str = "",
) -> ResonanceResult:
    """Lock wavelengths and return full system-prompt material (identity + optional indices)."""
    resolved_mode = mode or soul_mode_from_env()

    host: HostSoul | None
    if isinstance(host_soul, HostSoul):
        host = host_soul
    elif host_soul is None:
        host = discover_host_soul(search=search_host)
    else:
        host = discover_host_soul(explicit=host_soul, search=False)
        if host is None and search_host:
            host = discover_host_soul(search=True)

    c_text, c_path = load_conductor_soul()
    if conductor_soul is not None:
        c_text = conductor_soul.strip()
        c_path = c_path  # keep path metadata if any

    identity_block, notes = build_resonance_block(host, c_text, mode=resolved_mode)
    # Dual-ego thrash: same path or near-identical bodies mean partner resolution failed.
    if (
        host
        and host.path
        and c_path
        and host.path.resolve() == c_path.resolve()
    ):
        notes.append(
            "thrash: host and partner resolve to the same file — set "
            "CONDUCTOR_PARTNER_SOUL or seed CONDUCTOR_PARTNER_SOUL.md"
        )
    elif (
        host
        and host.content.strip()
        and c_text.strip()
        and host.content.strip() == c_text.strip()
    ):
        notes.append(
            "thrash: host and partner bodies are identical — partner SOUL is not distinct"
        )
    resonant = bool(
        resolved_mode == "resonate"
        and host
        and host.content.strip()
        and c_text.strip()
    )

    parts = [identity_block]
    if skills_block.strip():
        parts.append(skills_block.strip())
    if research_block.strip():
        parts.append(research_block.strip())
    if memory_block.strip():
        parts.append(memory_block.strip())

    return ResonanceResult(
        mode=resolved_mode,
        prompt="\n\n---\n\n".join(parts),
        host=host,
        conductor_path=c_path,
        conductor_chars=len(c_text),
        resonant=resonant,
        notes=notes,
    )


def resonance_status() -> dict[str, Any]:
    """Diagnostics for /soul resonate and doctor."""
    result = resonate(search_host=True)
    return result.to_dict()
