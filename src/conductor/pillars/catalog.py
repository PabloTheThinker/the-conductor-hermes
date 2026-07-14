"""Eight pillars + healing undercurrent — foundation catalog for agents and operators.

Each pillar: purpose (enhances host), contracts, specs, runtime, tools, slash, readiness.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Pillar:
    id: str
    number: int  # 1–8; 0 = undercurrent
    slug: str
    name: str
    role: str  # one line
    enhances: str  # how it upgrades the host meister
    contracts: tuple[str, ...]
    specs: tuple[str, ...]
    runtime: tuple[str, ...]
    tools: tuple[str, ...]
    slash: tuple[str, ...]
    skills: tuple[str, ...]
    readiness: str  # foundation | partial | experimental
    depends_on: tuple[str, ...] = ()


PILLARS: dict[str, Pillar] = {}


def _reg(p: Pillar) -> Pillar:
    PILLARS[p.id] = p
    PILLARS[p.slug] = p
    PILLARS[str(p.number)] = p
    return p


_reg(
    Pillar(
        id="P1",
        number=1,
        slug="soul",
        name="SOUL / Soul Resonance",
        role="Partner wavelength — enhances host identity, never replaces it.",
        enhances="Locks Conductor cognitive architecture to the meister’s name/voice.",
        contracts=(
            "Meister primary (host names the self)",
            "Partner enhances (tracks, spine, Remnants, Crucible)",
            "Shared spine immutable (ethics, path floors, done=proven)",
            "Modes: resonate | solo | host_only",
        ),
        specs=("SOUL.md", "docs/SOUL_RESONANCE.md"),
        runtime=("conductor.soul", "conductor.soul.resonance", "conductor.soul.identity"),
        tools=(),
        slash=("/soul", "/soul resonate", "/soul integrity"),
        skills=(),
        readiness="foundation",
    )
)

_reg(
    Pillar(
        id="P2",
        number=2,
        slug="memory",
        name="Memory Fabric",
        role="Perfect recall with emotional valence across four layers.",
        enhances="Host remembers outcomes, scars, seals, and task slices across turns.",
        contracts=(
            "Episodic: events + valence + outcome",
            "Semantic: distilled notes / seals",
            "Procedural: skills pack",
            "Track-linked: references into Track System",
            "Live inject on pre_llm when hooks enabled",
        ),
        specs=("memory/MEMORY_ARCHITECTURE.md", "memory/NOESIS.md"),
        runtime=(
            "conductor.memory.episodic",
            "conductor.memory.semantic",
            "conductor.memory.global_seals",
            "conductor.memory.context_inject",
            "conductor.memory.snapshot_export",
        ),
        tools=("memory_episodic",),
        slash=("/memory",),
        skills=(),
        readiness="foundation",
        depends_on=("P1",),
    )
)

_reg(
    Pillar(
        id="P3",
        number=3,
        slug="tracks",
        name="Track System",
        role="Living multiverse graph of paths, risks, opportunities.",
        enhances="Host sees a chessboard — not a flat todo list — for strategy.",
        contracts=(
            "Tracks have title, status, priority, confidence, parent links",
            "Chessboard view ranks active paths",
            "Fork / prune / resolve without deleting history lightly",
            "Feeds Remnant spawn and Crucible forks",
        ),
        specs=("tracks/TRACK_SYSTEM.md",),
        runtime=("conductor.tracks.store", "conductor.tracks.models"),
        tools=("track_orchestrate",),
        slash=("/track",),
        skills=("plan",),
        readiness="foundation",
        depends_on=("P1", "P2"),
    )
)

_reg(
    Pillar(
        id="P4",
        number=4,
        slug="crucible",
        name="Noesis + The Crucible",
        role="Deep internal simulation in an ephemeral pocket dimension.",
        enhances="Host can stress-test decisions without polluting main state.",
        contracts=(
            "Noesis decides when depth is worth it",
            "Crucible is ephemeral: start → work → distill → tear down",
            "Global Workspace holds verbalizable concepts",
            "RBMC and Max Effort run inside pocket when invoked",
            "Isolation: filesystem always; Docker optional",
        ),
        specs=(
            "noesis/SIMULATION_ALGORITHMS.md",
            "crucible/CRUCIBLE_RUNTIME.md",
            "crucible/WORKSPACE.md",
            "memory/NOESIS.md",
        ),
        runtime=(
            "conductor.noesis",
            "conductor.crucible",
            "conductor.crucible.manager",
            "conductor.crucible.bus",
            "conductor.crucible.pocket",
            "conductor.crucible.docker_isolation",
        ),
        tools=("crucible_workspace",),
        slash=("/crucible",),
        skills=("plan", "remnant-guide"),
        readiness="foundation",
        depends_on=("P1", "P2", "P3"),
    )
)

_reg(
    Pillar(
        id="P5",
        number=5,
        slug="remnant",
        name="Remnant Protocol",
        role="Live parallel clones for active work (not background dream).",
        enhances="Host fans out branches when parallel uncertainty beats serial cost.",
        contracts=(
            "Task-scoped snapshot before spawn",
            "Heartbeat while alive",
            "Merge tiers: Fast → Reflective → Deep (Deep may open Crucible)",
            "Remnants serve resonant will — not a second ego",
        ),
        specs=(
            "conductor/REMNANT_PROTOCOL.md",
            "conductor/REMNANT_MERGE_LOGIC.md",
            "conductor/REMNANT_DATA_MODELS.md",
        ),
        runtime=("conductor.core.remnant", "conductor.core.merge"),
        tools=("remnant_orchestrate",),
        slash=("/remnant",),
        skills=("remnant-guide",),
        readiness="foundation",
        depends_on=("P1", "P2", "P3"),
    )
)

_reg(
    Pillar(
        id="P6",
        number=6,
        slug="orchestration",
        name="Orchestration",
        role="Chessboard owner — who acts, when to escalate, plan/review.",
        enhances="Host conducts instead of thrashing solo on every subtask.",
        contracts=(
            "conductor_status surfaces field state",
            "conductor_worker for offline worker intent (not Hermes AI spawn)",
            "Skills plan / review / combo choose stacks",
            "Combos A–H pick pillar stacks for jobs",
        ),
        specs=("docs/PILLAR_COMBOS.md", "docs/WORKFLOWS.md", "docs/PILLARS.md"),
        runtime=(
            "conductor.core.runtime",
            "conductor.core.delegate",
            "conductor.combos",
            "conductor.pillars",
            "conductor.harness",
        ),
        tools=("conductor_status", "conductor_worker", "combo_route"),
        slash=("/status", "/combo", "/goal", "/pillars"),
        skills=("plan", "review", "combo"),
        readiness="foundation",
        depends_on=("P1",),
    )
)

_reg(
    Pillar(
        id="P7",
        number=7,
        slug="governance",
        name="Governance + Max Effort",
        role="Safe power + optional four-voice high-stakes deliberation.",
        enhances="Host gets policy gates and structured Max Effort when stakes spike.",
        contracts=(
            "PolicyEngine + constitutional rules on high-risk actions",
            "Audit trail of gate decisions",
            "Max Effort: Bellicus / Serena / Reason / Voice of Action",
            "Voice of Action requires owner + 24–48h + criteria",
            "Fable laws: evidence over narration",
        ),
        specs=(
            "governance/GOVERNANCE_SAFETY_AUDIT.md",
            "governance/MAX_EFFORT_DELIBERATION.md",
            "governance/FABLE_FRAMEWORK.md",
            "governance/HEALING.md",
        ),
        runtime=(
            "conductor.governance.policy",
            "conductor.governance.audit",
            "conductor.governance.constitutional",
            "conductor.noesis.max_effort",
        ),
        tools=("governance_audit", "crucible_workspace"),  # max_effort via crucible
        slash=("/governance",),
        skills=("review",),
        readiness="foundation",
        depends_on=("P1", "P8"),
    )
)

_reg(
    Pillar(
        id="P8",
        number=8,
        slug="ethics",
        name="Ethics",
        role="7-point gate before high-stakes emotional / parallel / sim moves.",
        enhances="Host stays neurodiversity-affirming and operator-sovereign under power.",
        contracts=(
            "Ethics Decision Checklist (7 points) before high-stakes acts",
            "No false sentience / clinical claims",
            "Operator sovereignty preserved",
            "Transparent engineered nature",
        ),
        specs=("ethics/ETHICS_CHECKLIST.md", "ethics/NEURODIVERGENT_AI_ETHICS.md"),
        runtime=("conductor.ethics.evaluator", "conductor.ethics.checklist"),
        tools=("ethics_evaluate",),
        slash=("/ethics",),
        skills=(),
        readiness="foundation",
        depends_on=("P1",),
    )
)

_reg(
    Pillar(
        id="P0",
        number=0,
        slug="healing",
        name="Healing cascade (undercurrent)",
        role="Always-on integrity: scars, seals, imprints, thrash guard, path floors.",
        enhances="Host recovers from wounds without thrash or blast-radius expansion.",
        contracts=(
            "Integrity reflex: sense → contain → repair → advance",
            "Path-safety floors block mass-delete",
            "Thrash guard stops same failing tool+args",
            "Scars → seals; promote only after regression gate",
            "Never rewrite SOUL spine under “repair”",
        ),
        specs=("governance/HEALING.md",),
        runtime=(
            "conductor.healing",
            "conductor.agent.path_safety",
            "conductor.loop_thrash",
            "conductor.hermes_bridge",
        ),
        tools=("heal_status", "heal_attempt", "promote_seal", "verification_list"),
        slash=(),
        skills=("review",),
        readiness="foundation",
        depends_on=("P1", "P2"),
    )
)


ORDERED_IDS = ("P1", "P2", "P3", "P4", "P5", "P6", "P7", "P8", "P0")


def get_pillar(key: str) -> Pillar | None:
    k = (key or "").strip()
    if not k:
        return None
    if k in PILLARS:
        return PILLARS[k]
    low = k.lower().replace(" ", "-").replace("_", "-")
    for p in unique_pillars():
        if low in {p.slug, p.id.lower(), p.name.lower(), str(p.number)}:
            return p
        if low in p.slug or low in p.name.lower():
            return p
    return None


def unique_pillars() -> list[Pillar]:
    seen: set[str] = set()
    out: list[Pillar] = []
    for pid in ORDERED_IDS:
        p = PILLARS[pid]
        if p.id in seen:
            continue
        seen.add(p.id)
        out.append(p)
    return out


def pillars_as_dicts() -> list[dict[str, Any]]:
    return [
        {
            "id": p.id,
            "number": p.number,
            "slug": p.slug,
            "name": p.name,
            "role": p.role,
            "enhances": p.enhances,
            "contracts": list(p.contracts),
            "specs": list(p.specs),
            "runtime": list(p.runtime),
            "tools": list(p.tools),
            "slash": list(p.slash),
            "skills": list(p.skills),
            "readiness": p.readiness,
            "depends_on": list(p.depends_on),
        }
        for p in unique_pillars()
    ]
