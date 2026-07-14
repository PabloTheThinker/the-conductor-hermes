"""SOUL identity — load, integrity, and Soul Resonance with host meisters."""

from conductor.soul.identity import SoulIdentity, load_soul_identity
from conductor.soul.resonance import (
    HostSoul,
    ResonanceResult,
    discover_host_soul,
    resonate,
    resonance_status,
    soul_mode_from_env,
)

__all__ = [
    "HostSoul",
    "ResonanceResult",
    "SoulIdentity",
    "discover_host_soul",
    "load_soul_identity",
    "resonate",
    "resonance_status",
    "soul_mode_from_env",
]
