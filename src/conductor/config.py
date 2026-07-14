"""Load CONDUCTOR_HOME configuration from config.yaml and .env."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from conductor.paths import conductor_home, config_path, env_path


def _load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


@dataclass
class ConductorConfig:
    provider: str = "openai"
    model: str = "gpt-4o-mini"
    base_url: str = "https://api.openai.com/v1"
    api_key: str = ""
    judge_model: str = ""
    goal_max_turns: int = 20
    goal_judge_max_turns: int = 20
    dashboard_host: str = "127.0.0.1"
    dashboard_port: int = 9119
    max_tool_rounds: int = 32
    keep_recent_messages: int = 24
    compress_after_messages: int = 40
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def effective_judge_model(self) -> str:
        return self.judge_model or self.model


def load_config() -> IloConfig:
    home = conductor_home()
    home.mkdir(parents=True, exist_ok=True)
    _load_dotenv(env_path())

    raw: dict[str, Any] = {}
    cfg_file = config_path()
    if cfg_file.exists():
        loaded = yaml.safe_load(cfg_file.read_text(encoding="utf-8")) or {}
        if isinstance(loaded, dict):
            raw = loaded

    model_section = raw.get("model", {}) if isinstance(raw.get("model"), dict) else {}
    agent_section = raw.get("agent", {}) if isinstance(raw.get("agent"), dict) else {}
    goal_section = raw.get("goal", {}) if isinstance(raw.get("goal"), dict) else {}
    dash_section = raw.get("dashboard", {}) if isinstance(raw.get("dashboard"), dict) else {}

    provider = (
        os.environ.get("CONDUCTOR_PROVIDER") or os.environ.get("CONDUCTOR_PROVIDER")
        or model_section.get("provider")
        or raw.get("provider")
        or "hermes"  # prefer Hermes OAuth/provider system by default
    )
    model = (
        os.environ.get("CONDUCTOR_MODEL") or os.environ.get("CONDUCTOR_MODEL")
        or model_section.get("default")
        or model_section.get("model")
        or "gpt-4o-mini"
    )
    base_url = (
        os.environ.get("CONDUCTOR_BASE_URL") or os.environ.get("CONDUCTOR_BASE_URL")
        or model_section.get("base_url")
        or "https://api.openai.com/v1"
    )
    api_key = (
        os.environ.get("OPENAI_API_KEY")
        or os.environ.get("CONDUCTOR_API_KEY") or os.environ.get("CONDUCTOR_API_KEY")
        or model_section.get("api_key")
        or ""
    )

    if str(provider).lower() == "test":
        api_key = api_key or "test-key"

    max_tool_rounds = int(
        os.environ.get("CONDUCTOR_MAX_TOOL_ROUNDS")
        or agent_section.get("max_tool_rounds")
        or raw.get("max_tool_rounds")
        or 32
    )
    keep_recent = int(
        agent_section.get("keep_recent_messages")
        or raw.get("keep_recent_messages")
        or 24
    )
    compress_after = int(
        agent_section.get("compress_after_messages")
        or raw.get("compress_after_messages")
        or 40
    )

    return IloConfig(
        provider=str(provider),
        model=str(model),
        base_url=str(base_url).rstrip("/"),
        api_key=str(api_key),
        judge_model=str(goal_section.get("judge_model", "") or ""),
        goal_max_turns=int(goal_section.get("max_turns", 20)),
        goal_judge_max_turns=int(goal_section.get("judge_max_turns", 20)),
        dashboard_host=str(dash_section.get("host", "127.0.0.1")),
        dashboard_port=int(dash_section.get("port", 9119)),
        max_tool_rounds=max(1, max_tool_rounds),
        keep_recent_messages=max(4, keep_recent),
        compress_after_messages=max(6, compress_after),
        extra=raw,
    )


def doctor_issues(cfg: IloConfig | None = None) -> list[str]:
    cfg = cfg or load_config()
    issues: list[str] = []
    known = {
        "test",
        "openai",
        "openrouter",
        "hermes",
        "auto",
        "xai",
        "xai-oauth",
        "copilot",
        "nous",
        "openai-api",
        "openai-codex",
        "anthropic",
        "qwen-oauth",
    }
    if cfg.provider.lower() not in known and not cfg.provider.lower().startswith("custom"):
        issues.append(
            f"Unknown provider '{cfg.provider}' — use hermes/auto (OAuth), test, openai, openrouter, xai, copilot, …"
        )
    if cfg.provider.lower() == "test":
        return issues
    # Hermes OAuth / pool may supply the key even if cfg.api_key empty
    has_key = bool(cfg.api_key)
    if not has_key:
        try:
            from conductor.agent.hermes_auth import resolve_hermes_runtime

            creds = resolve_hermes_runtime(
                requested=None if cfg.provider.lower() in {"hermes", "auto"} else cfg.provider
            )
            has_key = creds.ok()
            if has_key:
                return issues
        except Exception:  # noqa: BLE001
            pass
    if not has_key:
        issues.append(
            "No API key / OAuth credentials — run stock `hermes model` or "
            "`hermes auth add xai-oauth --type oauth` "
            "(HERMES_HOME=$CONDUCTOR_HOME), or set OPENAI_API_KEY / CONDUCTOR_PROVIDER=test"
        )
    return issues

# Back-compat alias
IloConfig = ConductorConfig
