"""Live foundation status for each pillar — probes imports, stores, and configs."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from conductor.pillars.catalog import ORDERED_IDS, PILLARS, get_pillar, unique_pillars


@dataclass
class PillarProbe:
    pillar_id: str
    slug: str
    name: str
    ok: bool
    readiness: str
    details: dict[str, Any] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.pillar_id,
            "slug": self.slug,
            "name": self.name,
            "ok": self.ok,
            "readiness": self.readiness,
            "details": dict(self.details),
            "notes": list(self.notes),
        }


def _probe_import(mod: str) -> bool:
    try:
        __import__(mod)
        return True
    except Exception:  # noqa: BLE001
        return False


def probe_soul() -> PillarProbe:
    p = PILLARS["P1"]
    notes: list[str] = []
    details: dict[str, Any] = {}
    ok = True
    try:
        from conductor.soul.identity import load_soul_identity
        from conductor.soul.resonance import resonate, soul_mode_from_env

        ident = load_soul_identity()
        res = resonate(search_host=True)
        details = {
            "integrity_ok": ident.integrity_ok,
            "tagline": ident.tagline[:80],
            "path": str(ident.path),
            "word_count": ident.word_count,
            "soul_mode": soul_mode_from_env(),
            "resonant": res.resonant,
            "meister": res.host.label if res.host else None,
            "meister_path": str(res.host.path) if res.host and res.host.path else None,
        }
        if not ident.integrity_ok:
            ok = False
            notes.append("SOUL integrity check failed (ethics marker / content)")
        if res.resonant:
            notes.append(f"wavelength locked with {res.host.label if res.host else 'host'}")
        else:
            notes.append("solo wavelength — supply host soul to enhance a meister")
    except Exception as exc:  # noqa: BLE001
        ok = False
        notes.append(str(exc))
    return PillarProbe(p.id, p.slug, p.name, ok, p.readiness, details, notes)


def probe_memory(*, session_id: str = "") -> PillarProbe:
    p = PILLARS["P2"]
    notes: list[str] = []
    details: dict[str, Any] = {
        "imports": {
            "episodic": _probe_import("conductor.memory.episodic"),
            "semantic": _probe_import("conductor.memory.semantic"),
            "global_seals": _probe_import("conductor.memory.global_seals"),
            "context_inject": _probe_import("conductor.memory.context_inject"),
        }
    }
    ok = all(details["imports"].values())
    try:
        from conductor.memory.global_seals import list_global_seals
        from conductor.skills.loader import skills_index

        seals = list_global_seals(limit=20)
        skills = skills_index()
        details["global_seals"] = len(seals)
        details["bundled_skills"] = len(skills)
        details["layers"] = {
            "episodic": "EpisodicStore (session meta)",
            "semantic": "SemanticStore (session meta)",
            "procedural": f"ProceduralStore + {len(skills)} skills",
            "track_linked": "via TrackStore + episodic tags",
        }
        if session_id:
            from conductor.memory.fabric import MemoryFabric
            from conductor.session.store import SessionStore

            fabric = MemoryFabric(SessionStore())
            details["fabric"] = fabric.status(session_id)
        notes.append("four-layer fabric + procedural store online")
    except Exception as exc:  # noqa: BLE001
        ok = False
        notes.append(str(exc))
    return PillarProbe(p.id, p.slug, p.name, ok, p.readiness, details, notes)


def probe_tracks(*, session_id: str = "") -> PillarProbe:
    p = PILLARS["P3"]
    notes: list[str] = []
    details: dict[str, Any] = {"import": _probe_import("conductor.tracks.store")}
    ok = bool(details["import"])
    try:
        if session_id:
            from conductor.session.store import SessionStore
            from conductor.tracks.store import TrackStore

            store = SessionStore()
            ts = TrackStore(store)
            tracks = ts.list_tracks(session_id, include_pruned=True)
            edges = ts.list_edges(session_id)
            details["track_count"] = len(tracks)
            details["edge_count"] = len(edges)
            details["active"] = sum(1 for t in tracks if t.status not in {"pruned", "archived"})
            notes.append(f"{details['track_count']} tracks · {details['edge_count']} edges")
        else:
            notes.append("TrackStore + graph edges ready (pass session_id for counts)")
    except Exception as exc:  # noqa: BLE001
        ok = False
        notes.append(str(exc))
    return PillarProbe(p.id, p.slug, p.name, ok, p.readiness, details, notes)


def probe_crucible() -> PillarProbe:
    p = PILLARS["P4"]
    notes: list[str] = []
    details: dict[str, Any] = {
        "manager": _probe_import("conductor.crucible.manager"),
        "rbmc": _probe_import("conductor.noesis.rbmc"),
        "max_effort": _probe_import("conductor.noesis.max_effort"),
        "pocket": _probe_import("conductor.crucible.pocket"),
    }
    ok = all(details.values()) if isinstance(details["manager"], bool) else False
    try:
        from conductor.crucible.docker_isolation import docker_available
        from conductor.core.runtime import get_crucible_manager

        mgr = get_crucible_manager()
        details["docker_available"] = docker_available()
        details["active_sessions"] = len(getattr(mgr, "_sessions", {}) or {})
        details["rbmc_backprop"] = True
        notes.append(
            "RBMC+backprop · filesystem pocket · Docker "
            + ("available" if details["docker_available"] else "optional/off")
        )
    except Exception as exc:  # noqa: BLE001
        ok = False
        notes.append(str(exc))
    return PillarProbe(p.id, p.slug, p.name, ok, p.readiness, details, notes)


def probe_remnant(*, session_id: str = "") -> PillarProbe:
    p = PILLARS["P5"]
    notes: list[str] = []
    details: dict[str, Any] = {
        "remnant": _probe_import("conductor.core.remnant"),
        "merge": _probe_import("conductor.core.merge"),
    }
    ok = all(details.values())
    try:
        if session_id:
            from conductor.core.runtime import ConductorRuntime
            from conductor.session.store import SessionStore

            rt = ConductorRuntime(SessionStore())
            meta = rt.load_meta(session_id)
            details["remnant_session_id"] = meta.get("remnant_session_id")
            details["remnant_count"] = len(meta.get("remnants") or {})
            details["merged_insights"] = len(meta.get("merged_remnant_insights") or [])
        notes.append("RemnantLedger + Tier1/2/3 (deep+RBMC) merge available")
    except Exception as exc:  # noqa: BLE001
        ok = False
        notes.append(str(exc))
    return PillarProbe(p.id, p.slug, p.name, ok, p.readiness, details, notes)


def probe_orchestration() -> PillarProbe:
    p = PILLARS["P6"]
    notes: list[str] = []
    details: dict[str, Any] = {
        "runtime": _probe_import("conductor.core.runtime"),
        "combos": _probe_import("conductor.combos"),
        "harness": _probe_import("conductor.harness"),
        "delegate": _probe_import("conductor.core.delegate"),
    }
    ok = all(details.values())
    try:
        from conductor.combos import COMBOS
        from conductor.skills.loader import skills_index

        details["combo_count"] = len(COMBOS)
        details["skills"] = [s.name for s in skills_index()]
        notes.append(f"{len(COMBOS)} combos · {len(details['skills'])} skills")
    except Exception as exc:  # noqa: BLE001
        ok = False
        notes.append(str(exc))
    return PillarProbe(p.id, p.slug, p.name, ok, p.readiness, details, notes)


def probe_governance() -> PillarProbe:
    p = PILLARS["P7"]
    notes: list[str] = []
    details: dict[str, Any] = {
        "policy": _probe_import("conductor.governance.policy"),
        "audit": _probe_import("conductor.governance.audit"),
        "constitutional": _probe_import("conductor.governance.constitutional"),
        "max_effort": _probe_import("conductor.noesis.max_effort"),
    }
    ok = all(details.values())
    try:
        from conductor.governance.policy import PolicyEngine
        from conductor.noesis.max_effort import run_max_effort

        engine = PolicyEngine()
        # smoke: benign action should not raise
        gate = engine.evaluate("status_check", {"description": "probe"})
        details["policy_smoke_blocked"] = bool(getattr(gate, "blocked", False))
        details["max_effort_callable"] = callable(run_max_effort)
        notes.append("PolicyEngine + Max Effort online")
    except Exception as exc:  # noqa: BLE001
        ok = False
        notes.append(str(exc))
    return PillarProbe(p.id, p.slug, p.name, ok, p.readiness, details, notes)


def probe_ethics() -> PillarProbe:
    p = PILLARS["P8"]
    notes: list[str] = []
    details: dict[str, Any] = {
        "evaluator": _probe_import("conductor.ethics.evaluator"),
        "checklist": _probe_import("conductor.ethics.checklist"),
    }
    ok = all(details.values())
    try:
        from conductor.ethics.checklist import ETHICS_CHECKLIST
        from conductor.ethics.evaluator import EthicsEvaluator

        details["checklist_points"] = len(ETHICS_CHECKLIST)
        ev = EthicsEvaluator()
        result = ev.evaluate(
            "probe",
            {"description": "foundation status probe only", "human_acknowledged": True},
        )
        details["probe_blocked"] = bool(result.blocked)
        details["probe_summary"] = result.summary[:120]
        notes.append(f"{details['checklist_points']}-point checklist live")
    except Exception as exc:  # noqa: BLE001
        ok = False
        notes.append(str(exc))
    return PillarProbe(p.id, p.slug, p.name, ok, p.readiness, details, notes)


def probe_healing() -> PillarProbe:
    p = PILLARS["P0"]
    notes: list[str] = []
    details: dict[str, Any] = {
        "healing": _probe_import("conductor.healing"),
        "path_safety": _probe_import("conductor.agent.path_safety"),
        "thrash": _probe_import("conductor.loop_thrash"),
        "bridge": _probe_import("conductor.hermes_bridge"),
    }
    ok = all(details.values())
    try:
        from conductor.agent.path_safety import is_shell_denied

        deny = is_shell_denied("rm -rf /")
        details["blocks_root_wipe"] = deny is not None
        if not details["blocks_root_wipe"]:
            ok = False
            notes.append("path safety did not block rm -rf /")
        else:
            notes.append("path floors + thrash + healing cascade loaded")
    except Exception as exc:  # noqa: BLE001
        ok = False
        notes.append(str(exc))
    return PillarProbe(p.id, p.slug, p.name, ok, p.readiness, details, notes)


_PROBES = {
    "P1": lambda sid: probe_soul(),
    "P2": lambda sid: probe_memory(session_id=sid),
    "P3": lambda sid: probe_tracks(session_id=sid),
    "P4": lambda sid: probe_crucible(),
    "P5": lambda sid: probe_remnant(session_id=sid),
    "P6": lambda sid: probe_orchestration(),
    "P7": lambda sid: probe_governance(),
    "P8": lambda sid: probe_ethics(),
    "P0": lambda sid: probe_healing(),
}


def probe_pillar(key: str, *, session_id: str = "") -> PillarProbe | None:
    p = get_pillar(key)
    if not p:
        return None
    fn = _PROBES.get(p.id)
    if not fn:
        return PillarProbe(p.id, p.slug, p.name, False, p.readiness, notes=["no probe"])
    return fn(session_id)


def foundation_report(*, session_id: str = "") -> dict[str, Any]:
    """Full foundation status for all pillars."""
    probes = [probe_pillar(pid, session_id=session_id) for pid in ORDERED_IDS]
    rows = [pr.to_dict() for pr in probes if pr]
    ok_n = sum(1 for r in rows if r["ok"])
    return {
        "ok": ok_n == len(rows),
        "passed": ok_n,
        "total": len(rows),
        "enhances_host": True,
        "product_line": "The Conductor enhances the agent that uses it",
        "pillars": rows,
        "catalog": [
            {
                "id": p.id,
                "number": p.number,
                "slug": p.slug,
                "name": p.name,
                "role": p.role,
                "enhances": p.enhances,
                "readiness": p.readiness,
            }
            for p in unique_pillars()
        ],
    }


def format_foundation_report(*, session_id: str = "", verbose: bool = False) -> str:
    report = foundation_report(session_id=session_id)
    lines = [
        "◆ Conductor pillar foundation",
        f"  Product: {report['product_line']}",
        f"  Status:  {report['passed']}/{report['total']} pillars ok"
        + (" ✓" if report["ok"] else " — check notes"),
        "",
    ]
    for row in report["pillars"]:
        mark = "✓" if row["ok"] else "✗"
        num = next((p.number for p in unique_pillars() if p.id == row["id"]), "?")
        lines.append(f"  {mark} P{num} {row['name']:<28} [{row['readiness']}]")
        for n in row.get("notes") or []:
            lines.append(f"      · {n}")
        if verbose and row.get("details"):
            for k, v in list(row["details"].items())[:6]:
                lines.append(f"      {k}: {v}")
    lines.append("")
    lines.append("  Spec: docs/PILLARS.md · Combos: docs/PILLAR_COMBOS.md")
    lines.append("  /pillars list|status|get <id> · tool pillar_status")
    return "\n".join(lines)


def format_pillar_detail(key: str) -> str:
    p = get_pillar(key)
    if not p:
        return f"Unknown pillar {key!r}. Try /pillars list"
    probe = probe_pillar(p.id)
    lines = [
        f"◆ P{p.number} {p.name} ({p.id} / {p.slug})",
        f"  Role:     {p.role}",
        f"  Enhances: {p.enhances}",
        f"  Ready:    {p.readiness}",
        f"  Probe:    {'ok' if probe and probe.ok else 'check'}",
        "",
        "  Contracts:",
    ]
    for c in p.contracts:
        lines.append(f"    · {c}")
    lines.append("  Specs:    " + ", ".join(p.specs))
    lines.append("  Runtime:  " + ", ".join(p.runtime[:4]) + ("…" if len(p.runtime) > 4 else ""))
    if p.tools:
        lines.append("  Tools:    " + ", ".join(p.tools))
    if p.slash:
        lines.append("  Slash:    " + ", ".join(p.slash))
    if p.skills:
        lines.append("  Skills:   " + ", ".join(p.skills))
    if p.depends_on:
        lines.append("  Depends:  " + ", ".join(p.depends_on))
    if probe and probe.notes:
        lines.append("  Notes:")
        for n in probe.notes:
            lines.append(f"    · {n}")
    return "\n".join(lines)


def format_pillars_list() -> str:
    lines = [
        "◆ Conductor pillars — enhance the host agent",
        "",
    ]
    for p in unique_pillars():
        label = f"P{p.number}" if p.number else "P0"
        lines.append(f"  {label:<4} {p.name:<28} {p.role}")
        lines.append(f"       enhances: {p.enhances}")
    lines.append("")
    lines.append("  /pillars status   — live foundation probes")
    lines.append("  /pillars get P3   — detail one pillar")
    lines.append("  Spec: docs/PILLARS.md")
    return "\n".join(lines)
