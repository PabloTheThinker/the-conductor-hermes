"""Harness integration surface — any agent host can load The Conductor as a module.

Public API
----------
- :func:`conductor.harness.module_info`
- :func:`conductor.harness.install`
- :func:`conductor.harness.get_system_prompt`
- :func:`conductor.harness.list_skills`
- :func:`conductor.harness.tool_schemas`
- :func:`conductor.harness.hooks`  (pre_tool / post_tool / pre_llm)

Adapters (optional host-specific packaging)
------------------------------------------
- ``conductor.adapters.hermes`` — install plugin into Hermes home + launch helpers
"""

from conductor.harness.api import (
    HarnessHooks,
    execute_tool,
    get_system_prompt,
    hooks,
    install,
    list_skills,
    module_info,
    resonate_souls,
    tool_schemas,
)

__all__ = [
    "HarnessHooks",
    "execute_tool",
    "get_system_prompt",
    "hooks",
    "install",
    "list_skills",
    "module_info",
    "resonate_souls",
    "tool_schemas",
]
