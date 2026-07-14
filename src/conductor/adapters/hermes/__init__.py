"""Hermes adapter — package The Conductor as a Hermes plugin + shared home.

Stock Hermes is one supported harness. Other harnesses use
``conductor.harness`` directly without this adapter.
"""

from __future__ import annotations

from conductor.hermes_host import (
    hermes_available,
    hermes_bin,
    hermes_host_status,
    launch_hermes,
)

__all__ = [
    "hermes_available",
    "hermes_bin",
    "hermes_host_status",
    "launch_hermes",
    "install_for_hermes",
    "register",
    "hermes_ready_report",
]


def install_for_hermes(*, home=None, force: bool = True, install_pip: bool | None = None):
    """Install plugin + skills for stock Hermes (shared HERMES_HOME)."""
    from conductor.setup_ext import setup_extension

    return setup_extension(home=home, force=force, harness="hermes", install_pip=install_pip)


def register(ctx):
    """Hermes plugin entry (also exposed via pip entry-point)."""
    from conductor.adapters.hermes.plugin import register as _register

    return _register(ctx)


def hermes_ready_report(*, home=None):
    from conductor.adapters.hermes.ready import hermes_ready_report as _report

    return _report(home=home)
