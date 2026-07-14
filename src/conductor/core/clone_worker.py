"""Local shadow-clone worker — real parallel work unit for a remnant.

Naruto metaphor: a clone that actually does a mission, then returns a scroll
(result) to the parent. This worker is offline/CPU-bound; host backends
(Grok spawn_subagent, Hermes subagents, Claude Task) run the same brief shape
outside the process.
"""

from __future__ import annotations

import os
import re
import time
from pathlib import Path
from typing import Any


def _tokens(text: str) -> list[str]:
    raw = re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{2,}", text or "")
    stop = {
        "the",
        "and",
        "for",
        "with",
        "from",
        "this",
        "that",
        "into",
        "using",
        "build",
        "implement",
        "create",
    }
    out: list[str] = []
    seen: set[str] = set()
    for t in raw:
        low = t.lower()
        if low in stop or low in seen:
            continue
        seen.add(low)
        out.append(low)
        if len(out) >= 10:
            break
    return out


_SOURCE_SUFFIXES = (
    ".py",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".html",
    ".css",
    ".json",
    ".md",
    ".vue",
    ".svelte",
)


def _scan_root(root: Path, tokens: list[str], *, limit: int = 24) -> list[dict[str, str]]:
    """Score paths by name tokens; also peek file content so js/game.js matches combat.

    Self-loop lesson (stellar-codex): path-only scoring missed game.js when
    tokens were combat/enemy but filenames were generic.
    """
    if not root.is_dir():
        return []
    skip_dirs = {
        ".git",
        "node_modules",
        ".venv",
        "venv",
        "__pycache__",
        ".pytest_cache",
        "dist",
        "build",
        ".ruff_cache",
        "upload_queue",
    }
    hits: list[dict[str, str]] = []
    try:
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in skip_dirs and not d.startswith(".")]
            rel_dir = Path(dirpath).relative_to(root)
            for name in filenames:
                if name.startswith("."):
                    continue
                path = Path(dirpath) / name
                rel = str(path.relative_to(root))
                low = rel.lower()
                score = sum(1 for t in tokens if t in low)
                # Content peek for source files when path score is weak
                if tokens and score == 0 and name.lower().endswith(_SOURCE_SUFFIXES):
                    try:
                        size = path.stat().st_size
                    except OSError:
                        continue
                    if size <= 250_000:
                        try:
                            head = path.read_text(encoding="utf-8", errors="replace")[:8000].lower()
                        except OSError:
                            head = ""
                        score = sum(1 for t in tokens if t in head)
                        if score:
                            score = max(1, score // 2)  # path matches rank higher
                if score <= 0 and tokens:
                    # Fallback: always surface shallow entrypoints for greenfield demos
                    if name.lower() in {
                        "index.html",
                        "main.js",
                        "app.js",
                        "game.js",
                        "main.py",
                        "app.py",
                    } or (len(rel_dir.parts) <= 1 and name.lower().endswith((".html", ".js", ".css", ".py"))):
                        score = 1
                    else:
                        continue
                if not tokens:
                    if len(rel_dir.parts) > 2:
                        continue
                try:
                    size = path.stat().st_size
                except OSError:
                    continue
                if size > 400_000:
                    continue
                hits.append({"path": rel, "score": str(score), "bytes": str(size)})
                if len(hits) >= limit * 3:
                    break
            if len(hits) >= limit * 3:
                break
    except OSError:
        return []
    hits.sort(key=lambda h: (-int(h["score"]), h["path"]))
    return hits[:limit]


def _read_snippets(root: Path, files: list[dict[str, str]], *, max_files: int = 6) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for item in files[:max_files]:
        path = root / item["path"]
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        lines = text.splitlines()
        head = "\n".join(lines[:40])
        out.append(
            {
                "path": item["path"],
                "lines": str(min(len(lines), 40)),
                "preview": head[:1200],
            }
        )
    return out


def _greenfield_findings(*, role: str, objective: str, steps: list[Any]) -> list[str]:
    """When no work_root, still return parent-usable lane plan (website live-run lesson)."""
    obj = (objective or "")[:100]
    out = [
        f"Greenfield lane ({role}): no work_root scan — emitting deliverable plan for «{obj}»",
        "Parent should set work_root/CONDUCTOR_CLONE_ROOT next fanout for file-aware clones",
    ]
    for i, s in enumerate(steps[:4], 1):
        out.append(f"step {i}: {str(s)[:140]}")
    if role in {"surface", "product", "docs", "polish"}:
        out.append(
            f"Suggested site path: website/ (index.html section for role={role})"
        )
    if role in {"rules", "combat", "world", "character", "meta"}:
        out.append(
            f"Suggested game path: demos/stellar-codex/js/game.js (role={role})"
        )
    return out


def _greenfield_suggested_edits(*, role: str, objective: str) -> list[dict[str, str]]:
    obj = (objective or "").lower()
    if role in {"surface", "product", "docs", "polish"} or any(
        t in obj for t in ("website", "landing", "hero", "ui", "ux", "marketing")
    ):
        path_map = {
            "surface": "website/index.html#hero-nav",
            "product": "website/index.html#product-pillars",
            "docs": "website/index.html#install-hermes",
            "polish": "website/assets + responsive/a11y pass",
        }
        path = path_map.get(role, "website/index.html")
        return [
            {
                "path": path,
                "action": "create_or_extend",
                "why": f"greenfield marketing lane role={role}",
            }
        ]
    if role in {"rules", "combat", "world", "character", "meta"} or any(
        t in obj for t in ("game", "d20", "rpg", "combat", "quest", "d&d")
    ):
        path_map = {
            "surface": "demos/stellar-codex/index.html + css/game.css",
            "rules": "demos/stellar-codex/js/game.js#rules",
            "combat": "demos/stellar-codex/js/game.js#combat",
            "world": "demos/stellar-codex/js/game.js#world",
            "character": "demos/stellar-codex/js/game.js#create",
            "meta": "demos/stellar-codex/js/game.js#save",
            "polish": "demos/stellar-codex/css/game.css",
            "implement": "demos/stellar-codex/js/game.js",
        }
        path = path_map.get(role, "demos/stellar-codex/js/game.js")
        return [
            {
                "path": path,
                "action": "create_or_extend",
                "why": f"greenfield game lane role={role}",
            }
        ]
    return [
        {
            "path": f"src/{role}/module.py",
            "action": "create_or_extend",
            "why": f"no existing matches; start vertical slice for {objective[:60]}",
        }
    ]


def run_clone_mission(
    *,
    remnant_id: str,
    objective: str,
    strategy: str = "",
    work_pack: dict[str, Any] | None = None,
    work_root: str | Path | None = None,
    parent_goal: str = "",
) -> dict[str, Any]:
    """Execute a local shadow-clone mission and return a scroll (result dict)."""
    started = time.time()
    pack = dict(work_pack or {})
    obj = (objective or pack.get("objective") or "").strip() or "unspecified"
    role = str(pack.get("role") or "implement")
    tokens = _tokens(f"{obj} {strategy} {parent_goal}")

    root_env = (
        str(work_root or "").strip()
        or os.environ.get("CONDUCTOR_CLONE_ROOT", "").strip()
        or os.environ.get("CONDUCTOR_WORKSPACE", "").strip()
    )
    root = Path(root_env).expanduser() if root_env else None

    files: list[dict[str, str]] = []
    snippets: list[dict[str, str]] = []
    if root and root.is_dir():
        files = _scan_root(root, tokens)
        snippets = _read_snippets(root, files)

    steps = list(pack.get("steps") or [])
    acceptance = list(pack.get("acceptance") or [])
    findings: list[str] = [
        f"Clone mission for «{obj[:100]}» as role={role}",
        f"Token focus: {', '.join(tokens[:6]) or '(none)'}",
    ]
    if files:
        findings.append(f"Examined {len(files)} path(s) under {root}")
        for f in files[:5]:
            findings.append(f"touch candidate: {f['path']} (score={f['score']})")
    else:
        # Greenfield / marketing: deliver a real lane plan, not empty theater
        findings.extend(_greenfield_findings(role=role, objective=obj, steps=steps))

    suggested_edits: list[dict[str, str]] = []
    for f in files[:8]:
        suggested_edits.append(
            {
                "path": f["path"],
                "action": "review_or_edit",
                "why": f"matches objective tokens (score={f['score']})",
            }
        )
    if not suggested_edits:
        suggested_edits.extend(_greenfield_suggested_edits(role=role, objective=obj))

    # Scaffold writer (1.18.6): local clones leave real files under work_root
    # so they are not pure scouts. Opt-out: CONDUCTOR_LOCAL_SCAFFOLD=0
    scaffolded: list[str] = []
    if root and root.is_dir() and _scaffold_enabled():
        scaffolded = _write_lane_scaffolds(
            root=root,
            remnant_id=remnant_id,
            role=role,
            objective=obj,
            steps=steps,
            acceptance=acceptance,
            suggested_edits=suggested_edits,
            files_exist=bool(files),
        )
        for p in scaffolded:
            findings.append(f"scaffold wrote: {p}")
            suggested_edits.insert(
                0,
                {
                    "path": p,
                    "action": "created_scaffold",
                    "why": "local clone built lane stub for parent deepen",
                },
            )

    checklist_done = [
        f"scoped: {obj[:80]}",
        f"role locked: {role}",
        f"candidates: {len(files)}",
    ]
    if steps:
        checklist_done.append(f"first step: {steps[0][:100]}")
    if not files:
        checklist_done.append("greenfield plan: deliverable paths named for parent")
    if scaffolded:
        checklist_done.append(f"scaffolds written: {len(scaffolded)}")

    insights = [
        f"[clone:{role}] {obj[:140]}",
        f"[clone:{role}] files={len(files)} suggested_edits={len(suggested_edits)}",
    ]
    if files:
        insights.append(f"[clone:{role}] top={files[0]['path']}")
    else:
        # Actionable, not filler "plan-only (no root)" that polluted merges
        dest = suggested_edits[0]["path"] if suggested_edits else f"{role}/deliverable"
        insights.append(f"[clone:{role}] greenfield deliverable: {dest}")
    for p in scaffolded[:3]:
        insights.append(f"[clone:{role}] scaffold wrote: {p}")

    for a in acceptance[:2]:
        if "ready for parent merge" in str(a).lower():
            continue  # pack chrome
        insights.append(f"[clone:accept] {str(a)[:120]}")

    elapsed_ms = int((time.time() - started) * 1000)
    return {
        "ok": True,
        "kind": "shadow_clone_result",
        "backend": "local",
        "remnant_id": remnant_id,
        "objective": obj,
        "role": role,
        "strategy": strategy,
        "parent_goal": parent_goal,
        "findings": findings,
        "suggested_edits": suggested_edits,
        "files_examined": [f["path"] for f in files] + scaffolded,
        "files_written": scaffolded,
        "snippets": snippets,
        "checklist_done": checklist_done,
        "acceptance": acceptance,
        "steps": steps,
        "insights": insights,
        "key_decisions": list(pack.get("key_decisions") or [])
        or ["parallel branches: execute each work pack then merge once"],
        "progress_percent": 100.0 if (files or scaffolded) else 85.0,
        "elapsed_ms": elapsed_ms,
        "work_root": str(root) if root else None,
        "scaffold_count": len(scaffolded),
        "host_instruction": pack.get("host_instruction")
        or f"Integrate clone results for: {obj[:100]}",
    }


def _scaffold_enabled() -> bool:
    raw = os.environ.get("CONDUCTOR_LOCAL_SCAFFOLD", "1").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def _safe_rel_path(path: str) -> str | None:
    """Strip anchors/fragments and reject path traversal."""
    raw = (path or "").split("#")[0].split("?")[0].strip()
    if not raw or raw.startswith("/") or ".." in raw.split("/"):
        return None
    # Keep simple file-ish paths
    if raw.endswith("/"):
        return None
    return raw


def _write_lane_scaffolds(
    *,
    root: Path,
    remnant_id: str,
    role: str,
    objective: str,
    steps: list[Any],
    acceptance: list[Any],
    suggested_edits: list[dict[str, str]],
    files_exist: bool,
) -> list[str]:
    """Write lane plan + optional stub module under work_root (local builder, not pure scout)."""
    written: list[str] = []
    scrolls = root / ".conductor" / "clone_scrolls"
    try:
        scrolls.mkdir(parents=True, exist_ok=True)
    except OSError:
        return written

    rid_short = (remnant_id or "clone")[:12]
    plan_name = f"{rid_short}_{role or 'lane'}.md"
    plan_path = scrolls / plan_name
    body_lines = [
        f"# Clone scroll — {role}",
        "",
        f"- remnant_id: `{remnant_id}`",
        f"- objective: {objective[:200]}",
        "",
        "## Steps",
    ]
    for s in steps[:8]:
        body_lines.append(f"- {s}")
    if not steps:
        body_lines.append("- (no pack steps)")
    body_lines.extend(["", "## Acceptance"])
    for a in acceptance[:6]:
        body_lines.append(f"- {a}")
    body_lines.extend(
        [
            "",
            "## Suggested paths",
        ]
    )
    for e in suggested_edits[:6]:
        body_lines.append(f"- `{e.get('path')}` — {e.get('action')}: {e.get('why')}")
    body_lines.extend(
        [
            "",
            "_Written by Conductor local shadow clone. Parent host deepens implementation._",
            "",
        ]
    )
    try:
        if not plan_path.is_file():
            plan_path.write_text("\n".join(body_lines), encoding="utf-8")
            written.append(str(plan_path.relative_to(root)))
        else:
            written.append(str(plan_path.relative_to(root)))  # already present
    except OSError:
        pass

    # Greenfield only: create a minimal stub at first concrete file path
    if not files_exist:
        for e in suggested_edits[:3]:
            rel = _safe_rel_path(str(e.get("path") or ""))
            if not rel:
                continue
            # Only create plain source-like files
            if not rel.endswith(
                (".py", ".js", ".ts", ".tsx", ".jsx", ".html", ".css", ".md", ".json")
            ):
                continue
            dest = root / rel
            try:
                dest.parent.mkdir(parents=True, exist_ok=True)
            except OSError:
                continue
            if dest.is_file():
                continue
            stub = _stub_content(rel, role=role, objective=objective)
            try:
                dest.write_text(stub, encoding="utf-8")
                written.append(rel)
                break  # one stub per clone is enough
            except OSError:
                continue
    return written


def _stub_content(rel: str, *, role: str, objective: str) -> str:
    """Minimal non-empty scaffold so host/hybrid has a real file to deepen."""
    obj = (objective or "lane")[:100]
    if rel.endswith(".py"):
        return (
            f'"""Conductor local scaffold — role={role}.\n\n{obj}\n"""\n\n'
            f"# TODO(clone): implement {role} lane\n"
            f"ROLE = {role!r}\n"
            f"OBJECTIVE = {obj!r}\n\n"
            f"def main() -> None:\n"
            f"    raise NotImplementedError({obj!r})\n\n"
            f"if __name__ == '__main__':\n"
            f"    main()\n"
        )
    if rel.endswith((".js", ".ts", ".tsx", ".jsx")):
        return (
            f"// Conductor local scaffold — role={role}\n"
            f"// {obj}\n"
            f"export const ROLE = {role!r};\n"
            f"export const OBJECTIVE = {obj!r};\n"
            f"export function stub() {{\n"
            f"  throw new Error('TODO(clone): implement ' + ROLE);\n"
            f"}}\n"
        )
    if rel.endswith(".html"):
        return (
            f"<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n"
            f"  <meta charset=\"utf-8\" />\n"
            f"  <title>{role} — Conductor scaffold</title>\n"
            f"</head>\n<body>\n"
            f"  <main data-conductor-role=\"{role}\">\n"
            f"    <h1>{role}</h1>\n"
            f"    <p>{obj}</p>\n"
            f"    <p>Local clone scaffold — parent deepens.</p>\n"
            f"  </main>\n</body>\n</html>\n"
        )
    if rel.endswith(".css"):
        return (
            f"/* Conductor scaffold role={role} */\n"
            f"[data-conductor-role=\"{role}\"] {{ /* TODO */ }}\n"
        )
    if rel.endswith(".json"):
        import json

        return json.dumps(
            {"role": role, "objective": obj, "scaffold": True, "conductor": True},
            indent=2,
        ) + "\n"
    return f"# Conductor scaffold — {role}\n\n{obj}\n\nTODO: implement this lane.\n"


def _role_to_host_spawn(
    role: str,
    objective: str = "",
    pack: dict[str, Any] | None = None,
) -> tuple[str, str]:
    """Return (subagent_type, capability_mode) for host spawn.

    verify → general-purpose/all so clones can run pytest/shell (1.14 lesson).
    explore/scout stay read-only explore. work_pack may override both fields.
    """
    pack = dict(pack or {})
    if pack.get("host_subagent_type") and pack.get("host_capability_mode"):
        return (
            str(pack["host_subagent_type"]),
            str(pack["host_capability_mode"]),
        )
    r = (role or "implement").strip().lower()
    text = f"{objective} {pack.get('objective') or ''}".lower()
    if r in {"architect", "plan"}:
        return "plan", "read-only"
    if r in {"explore", "scout"}:
        return "explore", "read-only"
    if r == "verify":
        # Always write/shell capable — evidence requires real commands
        return "general-purpose", "all"
    if r in {
        "surface",
        "backend",
        "rules",
        "graph",
        "implement",
        "safety",
        "integrate",
        "ai",
        "combat",
        "world",
        "character",
        "product",
        "docs",
        "polish",
        "meta",
    }:
        return "general-purpose", "all"
    # Objective hints: pure research without "test/verify" can stay explore
    if any(k in text for k in ("read-only", "research only", "no edits")):
        return "explore", "read-only"
    return "general-purpose", "all"


def build_host_spawn_request(
    *,
    remnant_id: str,
    objective: str,
    strategy: str = "",
    work_pack: dict[str, Any] | None = None,
    parent_goal: str = "",
    session_id: str = "",
    host: str = "generic",
) -> dict[str, Any]:
    """Build a host-native subagent spawn request (Grok / Claude / Hermes / Codex)."""
    pack = dict(work_pack or {})
    role = str(pack.get("role") or "implement")
    steps = pack.get("steps") or []
    acceptance = pack.get("acceptance") or []
    prompt_lines = [
        "You are a Conductor shadow clone (subagent) of the parent agent.",
        "You share the parent's will — complete ONLY your branch, then return a structured result.",
        f"remnant_id: {remnant_id}",
        f"session_id: {session_id}",
        f"role: {role}",
        f"objective: {objective}",
    ]
    if parent_goal:
        prompt_lines.append(f"parent_goal: {parent_goal}")
    if strategy:
        prompt_lines.append(f"strategy: {strategy}")
    if steps:
        prompt_lines.append("steps:")
        prompt_lines.extend(f"  - {s}" for s in steps)
    if acceptance:
        prompt_lines.append("acceptance:")
        prompt_lines.extend(f"  - {a}" for a in acceptance)
    prompt_lines.extend(
        [
            "",
            "Return JSON-ish summary with: findings[], suggested_edits[], files_touched[], "
            "insights[], blockers[], done: bool",
            "Do not expand into sibling remnant territory.",
        ]
    )
    prompt = "\n".join(prompt_lines)

    # Map role → Grok subagent_type / capability (work_pack may override)
    # Live lesson (1.14): verify-as-explore/read-only cannot run pytest — useless.
    sub_type, cap = _role_to_host_spawn(role, objective, pack)

    desc = f"clone {role}: {objective[:48]}"
    # Exact Grok spawn_subagent tool_call (parent MUST invoke this)
    prompt_tail = (
        "\n\nWhen done, the PARENT will call remnant_orchestrate action=report "
        f"with remnant_id={remnant_id}. Your final message must be structured JSON "
        "with REAL findings (commands run, paths, pass/fail) — not work-pack templates."
    )
    if role == "verify" or cap == "all":
        prompt_tail += (
            "\nYou have shell/file tools when capability_mode allows — use them. "
            "For verify lanes: run tests/CLI and paste evidence into findings[]."
        )
    grok_tool_call = {
        "tool": "spawn_subagent",
        "arguments": {
            "prompt": prompt + prompt_tail,
            "description": desc[:80],
            "subagent_type": sub_type,
            "background": True,
            "capability_mode": cap,
            "isolation": "none",
        },
    }

    if host in {"grok", "xai"}:
        return {
            "host": "grok",
            "api": "spawn_subagent",
            "remnant_id": remnant_id,
            "session_id": session_id,
            "description": desc,
            "subagent_type": sub_type,
            "prompt": prompt,
            "capability_mode": cap,
            "background": True,
            "isolation": "none",
            "tool_call": grok_tool_call,
            "after_complete": {
                "tool": "remnant_orchestrate",
                "arguments": {
                    "action": "report",
                    "remnant_id": remnant_id,
                    "session_id": session_id,
                    "result": {
                        "ok": True,
                        "reported_by_host": True,
                        "findings": ["…from clone…"],
                        "insights": ["…"],
                        "done": True,
                    },
                },
            },
        }
    if host in {"claude", "anthropic"}:
        return {
            "host": "claude",
            "api": "Task",
            "remnant_id": remnant_id,
            "session_id": session_id,
            "description": f"clone:{role}",
            "prompt": prompt,
            "subagent_type": "general-purpose",
            "tool_call": {
                "tool": "Task",
                "arguments": {
                    "description": desc[:80],
                    "prompt": prompt,
                    "subagent_type": "general-purpose",
                },
            },
            "after_complete": {
                "action": "report",
                "remnant_id": remnant_id,
            },
        }
    if host in {"hermes", "ilo"}:
        # Real Hermes tool is delegate_task(goal, context) — NOT delegate_or_subagent.
        # Batch path prefers hermes_batch.tasks[] (one call); per-remnant tool_call
        # is the single-task fallback. See docs/HERMES_SUBAGENT_FANOUT.md.
        hermes_context = (
            prompt
            + "\n\nWhen done, return structured JSON: findings[], insights[], "
            "files_touched[], done: bool. The PARENT will call remnant_orchestrate "
            f"action=report with remnant_id={remnant_id}."
        )
        return {
            "host": "hermes",
            "api": "delegate_task",
            "remnant_id": remnant_id,
            "session_id": session_id,
            "goal": objective,
            "context": hermes_context,
            "prompt": hermes_context,  # alias for hybrid preflight injection
            "description": desc,
            "kind": "conductor_shadow_clone",
            "role": role,
            "tool_call": {
                "tool": "delegate_task",
                "arguments": {
                    "goal": objective,
                    "context": hermes_context,
                },
            },
            "after_complete": {
                "tool": "remnant_orchestrate",
                "arguments": {
                    "action": "report",
                    "remnant_id": remnant_id,
                    "session_id": session_id,
                    "result": {
                        "ok": True,
                        "reported_by_host": True,
                        "findings": ["…from clone…"],
                        "insights": ["…"],
                        "done": True,
                    },
                },
            },
        }
    return {
        "host": host or "generic",
        "api": "subagent",
        "remnant_id": remnant_id,
        "session_id": session_id,
        "prompt": prompt,
        "description": desc,
        "objective": objective,
        "role": role,
        "tool_call": grok_tool_call,
        "after_complete": {
            "tool": "remnant_orchestrate",
            "arguments": {
                "action": "report",
                "remnant_id": remnant_id,
                "session_id": session_id,
                "result": {
                    "ok": True,
                    "reported_by_host": True,
                    "findings": ["…from clone…"],
                    "insights": ["…"],
                    "done": True,
                },
            },
        },
    }
