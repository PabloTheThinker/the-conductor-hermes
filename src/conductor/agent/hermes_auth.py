"""Use Hermes OAuth + provider/credential system for Conductor inference.

Hermes owns auth.json, credential pools, device-code OAuth (xAI, Nous, Codex,
Anthropic, …) and provider resolution. Conductor does not reimplement login —
it binds HERMES_HOME to CONDUCTOR_HOME (shared state) and resolves runtime
credentials via the Hermes modules when the Relay is on PYTHONPATH / disk.
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class HermesRuntimeCreds:
    provider: str
    api_key: str
    base_url: str
    model: str = ""
    source: str = ""  # hermes_pool | hermes_oauth | env | none
    detail: str = ""

    def ok(self) -> bool:
        return bool(self.api_key and self.base_url)

    def to_status(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "base_url": self.base_url,
            "model": self.model,
            "source": self.source,
            "has_key": bool(self.api_key),
            "key_len": len(self.api_key) if self.api_key else 0,
            "detail": self.detail,
            "ok": self.ok(),
        }


# OpenAI-compatible defaults per Hermes provider id
_PROVIDER_BASE: dict[str, str] = {
    "openrouter": "https://openrouter.ai/api/v1",
    "openai": "https://api.openai.com/v1",
    "openai-api": "https://api.openai.com/v1",
    "xai": "https://api.x.ai/v1",
    "xai-oauth": "https://api.x.ai/v1",
    "copilot": "https://api.githubcopilot.com",
    "nous": "https://inference-api.nousresearch.com/v1",
    "qwen-oauth": "https://portal.qwen.ai/v1",
    "lmstudio": "http://127.0.0.1:1234/v1",
    "gemini": "https://generativelanguage.googleapis.com/v1beta/openai",
    "kimi-coding": "https://api.moonshot.ai/v1",
    "zai": "https://api.z.ai/api/paas/v4",
}

_DEFAULT_MODELS: dict[str, str] = {
    "openrouter": "openrouter/auto",
    "openai": "gpt-4o-mini",
    "openai-api": "gpt-4o-mini",
    "xai": "grok-3",
    "xai-oauth": "grok-3",
    "copilot": "gpt-4.1",
    "nous": "hermes-3-llama-3.1-70b",
}


def ensure_hermes_home() -> Path:
    """Share Hermes auth/config with CONDUCTOR_HOME when unset."""
    from conductor.paths import conductor_home

    home = conductor_home()
    os.environ.setdefault("HERMES_HOME", str(home))
    # Hermes also reads ~/.hermes for some globals — prefer explicit HERMES_HOME
    return Path(os.environ["HERMES_HOME"]).expanduser()


def hermes_relay_on_path() -> Path | None:
    """Find hermes-agent root and ensure it is importable (optional)."""
    from conductor.paths import relay_root

    root = relay_root()
    if root is None:
        return None
    s = str(root)
    if s not in sys.path:
        sys.path.insert(0, s)
    return root


def _auth_json_path() -> Path:
    ensure_hermes_home()
    return Path(os.environ["HERMES_HOME"]).expanduser() / "auth.json"


def _read_auth_store() -> dict[str, Any]:
    path = _auth_json_path()
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _hermes_config_model() -> tuple[str, str, str]:
    """Return (provider, model, base_url) from Hermes/Conductor config.yaml when present."""
    ensure_hermes_home()
    cfg_path = Path(os.environ["HERMES_HOME"]).expanduser() / "config.yaml"
    if not cfg_path.is_file():
        # also try Conductor home config
        from conductor.paths import config_path

        cfg_path = config_path()
    if not cfg_path.is_file():
        return "", "", ""
    try:
        import yaml

        raw = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    except Exception:  # noqa: BLE001
        return "", "", ""
    if not isinstance(raw, dict):
        return "", "", ""
    model_sec = raw.get("model") if isinstance(raw.get("model"), dict) else {}
    provider = str(
        model_sec.get("provider") or raw.get("provider") or ""
    ).strip()
    model = str(
        model_sec.get("default") or model_sec.get("model") or ""
    ).strip()
    base = str(model_sec.get("base_url") or "").strip()
    return provider, model, base


def _pool_first_entry(provider: str) -> tuple[str, str, str] | None:
    """(api_key, base_url, source) from Hermes credential pool."""
    hermes_relay_on_path()
    try:
        from agent.credential_pool import load_pool

        pool = load_pool(provider)
        entries = pool.entries() if hasattr(pool, "entries") else []
        for e in entries:
            key = ""
            if hasattr(e, "runtime_api_key"):
                key = str(e.runtime_api_key or "")
            if not key:
                key = str(getattr(e, "access_token", "") or "")
            if not key:
                continue
            base = (
                str(getattr(e, "runtime_base_url", "") or "")
                or str(getattr(e, "base_url", "") or "")
                or str(getattr(e, "inference_base_url", "") or "")
                or _PROVIDER_BASE.get(provider, "")
            )
            return key, base.rstrip("/"), f"hermes_pool:{provider}"
    except Exception:  # noqa: BLE001
        pass
    # Fallback: raw auth.json pool (no hermes import)
    store = _read_auth_store()
    pool = store.get("credential_pool") if isinstance(store, dict) else None
    if not isinstance(pool, dict):
        return None
    rows = pool.get(provider) or []
    if not isinstance(rows, list):
        return None
    for row in rows:
        if not isinstance(row, dict):
            continue
        # secrets may be externalized; fingerprint-only rows won't work
        key = str(
            row.get("access_token")
            or row.get("api_key")
            or row.get("token")
            or ""
        ).strip()
        if not key:
            continue
        base = str(row.get("base_url") or _PROVIDER_BASE.get(provider, "")).rstrip("/")
        return key, base, f"auth_json_pool:{provider}"
    return None


def _oauth_runtime(provider: str) -> tuple[str, str, str] | None:
    """Try Hermes OAuth runtime resolvers for known OAuth providers."""
    hermes_relay_on_path()
    resolvers = {
        "xai-oauth": "resolve_xai_oauth_runtime_credentials",
        "nous": "resolve_nous_runtime_credentials",
        "openai-codex": "resolve_codex_runtime_credentials",
        "qwen-oauth": "resolve_qwen_runtime_credentials",
        "minimax-oauth": "resolve_minimax_oauth_runtime_credentials",
    }
    fn_name = resolvers.get(provider)
    if not fn_name:
        return None
    try:
        import hermes_cli.auth as auth_mod

        fn = getattr(auth_mod, fn_name, None)
        if not callable(fn):
            return None
        data = fn()
        if not isinstance(data, dict):
            return None
        tokens = data.get("tokens") if isinstance(data.get("tokens"), dict) else data
        key = str(
            data.get("api_key")
            or data.get("access_token")
            or (tokens or {}).get("access_token")
            or ""
        ).strip()
        if not key:
            return None
        base = str(
            data.get("base_url")
            or data.get("inference_base_url")
            or _PROVIDER_BASE.get(provider, "")
        ).rstrip("/")
        return key, base, f"hermes_oauth:{provider}"
    except Exception:  # noqa: BLE001
        return None


def _env_key_for(provider: str) -> tuple[str, str, str] | None:
    env_map: dict[str, tuple[tuple[str, ...], str]] = {
        "openrouter": (("OPENROUTER_API_KEY", "OPENAI_API_KEY"), _PROVIDER_BASE["openrouter"]),
        "openai": (("OPENAI_API_KEY", "CONDUCTOR_API_KEY"), _PROVIDER_BASE["openai"]),
        "openai-api": (("OPENAI_API_KEY", "CONDUCTOR_API_KEY"), _PROVIDER_BASE["openai"]),
        "xai": (("XAI_API_KEY", "GROK_API_KEY"), _PROVIDER_BASE["xai"]),
        "copilot": (("COPILOT_GITHUB_TOKEN", "GH_TOKEN", "GITHUB_TOKEN"), _PROVIDER_BASE["copilot"]),
        "gemini": (("GOOGLE_API_KEY", "GEMINI_API_KEY"), _PROVIDER_BASE["gemini"]),
    }
    # also generic
    if provider in env_map:
        keys, base = env_map[provider]
        for k in keys:
            v = os.environ.get(k, "").strip()
            if v:
                return v, base, f"env:{k}"
    # generic openai-compatible
    for k in ("OPENROUTER_API_KEY", "OPENAI_API_KEY", "CONDUCTOR_API_KEY", "XAI_API_KEY"):
        v = os.environ.get(k, "").strip()
        if v:
            base = os.environ.get("CONDUCTOR_BASE_URL") or (
                _PROVIDER_BASE["openrouter"] if "OPENROUTER" in k else _PROVIDER_BASE["openai"]
            )
            if "XAI" in k:
                base = _PROVIDER_BASE["xai"]
            return v, str(base).rstrip("/"), f"env:{k}"
    return None


def list_auth_providers() -> list[str]:
    """Provider ids present in auth.json pools or active_provider."""
    store = _read_auth_store()
    found: list[str] = []
    active = str(store.get("active_provider") or "").strip()
    if active:
        found.append(active)
    pool = store.get("credential_pool")
    if isinstance(pool, dict):
        for k, rows in pool.items():
            if rows and k not in found:
                found.append(str(k))
    providers = store.get("providers")
    if isinstance(providers, dict):
        for k in providers:
            if k not in found:
                found.append(str(k))
    return found


def resolve_hermes_runtime(
    *,
    requested: str | None = None,
) -> HermesRuntimeCreds:
    """Resolve provider + OpenAI-compatible credentials via Hermes system.

    Order:
    1. Explicit requested provider (or config model.provider / CONDUCTOR_PROVIDER)
    2. Hermes resolve_provider('auto') when importable
    3. First non-empty credential pool
    4. Env API keys
    """
    ensure_hermes_home()
    hermes_relay_on_path()

    cfg_provider, cfg_model, cfg_base = _hermes_config_model()
    req = (requested or os.environ.get("CONDUCTOR_PROVIDER") or cfg_provider or "auto").strip()
    if req.lower() in {"test", "mock"}:
        return HermesRuntimeCreds(
            provider="test",
            api_key="test-key",
            base_url="http://localhost/test",
            model="test",
            source="test",
            detail="offline test provider",
        )

    provider = req
    if provider.lower() in {"auto", "hermes", "hermes-auto", ""}:
        provider = "auto"

    # Try Hermes resolve_provider
    if provider == "auto":
        try:
            from hermes_cli.auth import resolve_provider

            provider = resolve_provider("auto")
        except Exception:  # noqa: BLE001
            # pick first pool with entries
            pools = list_auth_providers()
            provider = pools[0] if pools else "openrouter"

    provider = provider.strip().lower()
    # aliases
    aliases = {
        "grok": "xai",
        "x-ai": "xai",
        "openai": "openai-api",
        "github": "copilot",
        "github-copilot": "copilot",
    }
    provider = aliases.get(provider, provider)

    # OAuth runtime first for oauth ids
    if provider.endswith("-oauth") or provider in {"nous", "openai-codex"}:
        hit = _oauth_runtime(provider)
        if hit:
            key, base, src = hit
            if cfg_base:
                base = cfg_base.rstrip("/")
            model = cfg_model or _DEFAULT_MODELS.get(provider, "")
            return HermesRuntimeCreds(provider, key, base, model, src, "oauth runtime")

    # credential pool
    hit = _pool_first_entry(provider)
    if hit:
        key, base, src = hit
        if cfg_base:
            base = cfg_base.rstrip("/")
        model = cfg_model or _DEFAULT_MODELS.get(provider, "")
        return HermesRuntimeCreds(provider, key, base or _PROVIDER_BASE.get(provider, ""), model, src, "pool")

    # env
    hit = _env_key_for(provider if provider != "auto" else "openrouter")
    if not hit and provider != "openrouter":
        hit = _env_key_for("openrouter") or _env_key_for("openai") or _env_key_for("xai")
    if hit:
        key, base, src = hit
        if cfg_base:
            base = cfg_base.rstrip("/")
        model = cfg_model or os.environ.get("CONDUCTOR_MODEL") or _DEFAULT_MODELS.get(provider, "gpt-4o-mini")
        return HermesRuntimeCreds(provider, key, base, model, src, "environment")

    # last resort: empty
    return HermesRuntimeCreds(
        provider=provider or "none",
        api_key="",
        base_url=cfg_base or _PROVIDER_BASE.get(provider, ""),
        model=cfg_model,
        source="none",
        detail=(
            "No Hermes OAuth/API credentials. Run stock Hermes: "
            "hermes model  or  hermes auth add xai-oauth --type oauth  "
            "(HERMES_HOME=$CONDUCTOR_HOME). "
        ),
    )


def hermes_auth_status() -> dict[str, Any]:
    ensure_hermes_home()
    creds = resolve_hermes_runtime()
    return {
        "hermes_home": os.environ.get("HERMES_HOME", ""),
        "auth_json": str(_auth_json_path()),
        "auth_json_exists": _auth_json_path().is_file(),
        "relay_root": str(hermes_relay_on_path() or ""),
        "providers_in_store": list_auth_providers(),
        "runtime": creds.to_status(),
        "oauth_capable": [
            "anthropic",
            "nous",
            "openai-codex",
            "xai-oauth",
            "qwen-oauth",
            "minimax-oauth",
        ],
        "login_hint": "hermes model  # or: hermes auth add xai-oauth --type oauth",
    }
