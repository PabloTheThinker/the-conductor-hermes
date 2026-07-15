"""Path resolution for The Conductor skillset module."""

from __future__ import annotations

import os
from pathlib import Path


def conductor_home() -> Path:
    """Durable home for Conductor state (skills, SOUL, sessions, config).

    Resolution order:
      CONDUCTOR_HOME → HERMES_HOME (if set) → existing ~/.conductor →
      existing ~/.hermes → create ~/.conductor

    When used as a Hermes plugin, set CONDUCTOR_HOME=HERMES_HOME so state is shared.
    """
    from conductor.bootstrap import shared_home_default

    return shared_home_default()


def state_db_path() -> Path:
    """SQLite path for Conductor sessions/meta.

    Uses ``conductor_state.db`` (not Hermes ``state.db``) so sharing
    ``CONDUCTOR_HOME=HERMES_HOME`` never collides with Hermes session schema.
    Override with ``CONDUCTOR_STATE_DB``.
    """
    explicit = os.environ.get("CONDUCTOR_STATE_DB", "").strip()
    if explicit:
        return Path(explicit).expanduser().resolve()
    return conductor_home() / "conductor_state.db"


def config_path() -> Path:
    return conductor_home() / "config.yaml"


def env_path() -> Path:
    return conductor_home() / ".env"


def skills_dir() -> Path:
    return conductor_home() / "skills"


def _package_dir() -> Path:
    return Path(__file__).resolve().parent


def _is_native_brain_package() -> bool:
    pkg = _package_dir()
    if (pkg / "_NATIVE_BRAIN").is_file():
        return True
    if (pkg / "_RELAY_BRAIN").is_file():
        return False
    layout = os.environ.get("CONDUCTOR_PACKAGE_LAYOUT", "").strip().lower()
    if layout == "native":
        return True
    if layout == "relay":
        return False
    return True


def relay_root() -> Path | None:
    """Optional hermes-agent checkout (Hermes adapter only)."""
    if _is_native_brain_package():
        return None
    explicit = os.environ.get("HERMES_AGENT_ROOT", "").strip()
    if not explicit:
        return None
    return Path(explicit).expanduser().resolve()


def _bundle_root() -> Path | None:
    bundled = _package_dir() / "_bundle"
    if bundled.is_dir() and (bundled / "SOUL.md").is_file():
        return bundled.resolve()
    return None


def _dev_native_root() -> Path | None:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "src" / "conductor" / "_NATIVE_BRAIN").is_file():
            return parent
        if (parent / "hermes_plugin" / "conductor" / "plugin.yaml").is_file() and (
            parent / "SOUL.md"
        ).is_file():
            return parent
        if (parent / "skills" / "conductor").is_dir() and (parent / "SOUL.md").is_file():
            return parent
    return None


def _repo_root() -> Path:
    relay = relay_root()
    if relay is not None:
        return relay
    explicit = os.environ.get("CONDUCTOR_ROOT", "").strip()
    if explicit:
        root = Path(explicit).expanduser().resolve()
        if not root.is_dir():
            raise RuntimeError(f"CONDUCTOR_ROOT is not a directory: {root}")
        return root
    bundle = _bundle_root()
    if bundle is not None:
        return bundle
    dev = _dev_native_root()
    if dev is not None:
        return dev
    raise RuntimeError(
        "Cannot resolve The Conductor repo root. Set CONDUCTOR_ROOT, install "
        "the-conductor, or run from a Conductor checkout."
    )


def canonical_soul_path() -> Path:
    try:
        repo_soul = _repo_root() / "SOUL.md"
        if repo_soul.exists():
            return repo_soul
    except RuntimeError:
        pass
    return conductor_home() / "SOUL.md"


def _text_looks_like_partner_soul(text: str) -> bool:
    """True when body is Conductor partner wavelength (not a host meister SOUL)."""
    lower = text.casefold()
    if "enhance the host" in lower and "conductor" in lower:
        return True
    if "soul resonance" in lower and ("partner" in lower or "meister" in lower):
        return True
    if "you are the conductor" in lower or "you are **the conductor**" in lower:
        return True
    if "immutable core identity for the conductor" in lower:
        return True
    return False


def soul_path() -> Path:
    """Runtime path to the Conductor *partner* SOUL (wavelength), never the meister.

    Shared Hermes homes keep the host identity in ``SOUL.md`` and the partner in
    ``CONDUCTOR_PARTNER_SOUL.md`` (see docs/HERMES.md, docs/SOUL_RESONANCE.md).
    Older installs that only had partner text in ``$HOME/SOUL.md`` still work.

    Resolution order:
      1. ``CONDUCTOR_PARTNER_SOUL`` env (file path)
      2. ``$CONDUCTOR_HOME/CONDUCTOR_PARTNER_SOUL.md``
      3. ``$CONDUCTOR_HOME/SOUL.md`` only if partner-shaped and not the meister path
      4. package/canonical ``SOUL.md``
    """
    explicit = os.environ.get("CONDUCTOR_PARTNER_SOUL", "").strip()
    if explicit:
        p = Path(explicit).expanduser()
        if p.is_file():
            return p.resolve()

    home = conductor_home()
    partner_file = home / "CONDUCTOR_PARTNER_SOUL.md"
    if partner_file.is_file():
        return partner_file.resolve()

    home_soul = home / "SOUL.md"
    if home_soul.is_file():
        host_env = os.environ.get("CONDUCTOR_HOST_SOUL", "").strip()
        if host_env:
            try:
                host_p = Path(host_env).expanduser()
                if host_p.is_file() and host_p.resolve() == home_soul.resolve():
                    # Shared-home meister file — do not treat as partner.
                    return canonical_soul_path()
            except OSError:
                pass
        try:
            body = home_soul.read_text(encoding="utf-8", errors="replace")
        except OSError:
            body = ""
        if _text_looks_like_partner_soul(body):
            return home_soul.resolve()
        # Host-shaped SOUL with no partner file → package partner wavelength.
        return canonical_soul_path()

    return canonical_soul_path()


def research_root() -> Path:
    return _repo_root()


def bundled_skills_roots() -> list[Path]:
    try:
        root = _repo_root()
    except RuntimeError:
        return []
    skills_root = root / "skills"
    roots: list[Path] = []
    native_conductor = skills_root / "conductor"
    if native_conductor.is_dir():
        roots.append(native_conductor)
    return roots or ([skills_root] if skills_root.is_dir() else [])


def bundled_skills_dir() -> Path:
    roots = bundled_skills_roots()
    if not roots:
        return skills_dir()
    return roots[0]
