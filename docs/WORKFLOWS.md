# Combo workflows

Operational flows for combos **A–H**. Catalog + decision tree: [PILLAR_COMBOS.md](PILLAR_COMBOS.md).  
Runtime: `conductor.combos` · skill `/combo` · slash `/combo` · tool `combo_route`.

---

## Decision tree

```mermaid
flowchart TD
  start[Intent] --> stakes{High-stakes / irreversible?}
  stakes -->|yes| E[E Max Effort + Ethics]
  stakes -->|no| parallel{Multi-branch uncertainty worth parallel cost?}
  parallel -->|yes| C[C Remnant fan-out]
  C --> deep{Deep merge needed?}
  deep -->|yes| D[D Crucible forge]
  deep -->|no| merge[Merge + Memory + Tracks]
  parallel -->|no| wound{Chronic / unique wound?}
  wound -->|yes| F[F Integrity cascade]
  F --> maybeD{Needs deep recon?}
  maybeD -->|yes| D
  maybeD -->|no| advance[Advance step]
  wound -->|no| map{Need strategic map?}
  map -->|yes| B[B Chessboard]
  map -->|no| A[A Daily driver]
  E --> G
  merge --> G
  D --> G
  advance --> G
  B --> G
  A --> G[G Evidence before done]
```

---

## A — Daily driver

```mermaid
flowchart LR
  soul[SOUL + skills] --> tools[Host tools + spine]
  tools --> mem[Optional memory_episodic]
  mem --> judge[Judgment: evidence]
```

1. Load SOUL + skills index  
2. Work under path-safety / thrash guard  
3. Optional episodic write  
4. Done only with proof  

**Tools:** host loop · `conductor_status` · `memory_episodic`  
**Skills:** `plan`, `review`

---

## B — Chessboard

```mermaid
flowchart LR
  list[track list/chessboard] --> create[create/update tracks]
  create --> bind[memory bind outcomes]
  bind --> move[Orchestrate next move]
```

1. `track_orchestrate` chessboard/list  
2. Create/update risks & opportunities  
3. `memory_episodic` bind  
4. Act from priority  

**Tools:** `track_orchestrate`, `memory_episodic`  
**Skills:** `plan`

---

## C — Parallel push (Remnant)

```mermaid
flowchart TD
  tracks[Name branches on tracks] --> ethics{High-stakes merge?}
  ethics -->|yes| eth[ethics_evaluate]
  ethics -->|no| spawn
  eth --> spawn[remnant spawn/fanout]
  spawn --> hb[heartbeats]
  hb --> m1[Fast merge]
  m1 --> m2[Reflective merge]
  m2 --> m3{Need Deep?}
  m3 -->|yes| D[Combo D Crucible]
  m3 -->|no| out[Memory + track update]
  D --> out
```

1. Light Combo B — name branches  
2. Ethics if merge is heavy  
3. `remnant_orchestrate` spawn/fanout  
4. Heartbeats  
5. Merge Fast → Reflective → Deep  
6. Memory + track artifact  

**Tools:** `remnant_orchestrate`, `track_orchestrate`  
**Skills:** `remnant-guide`, `plan`

---

## D — Deep forge (Crucible)

```mermaid
flowchart TD
  start[crucible start] --> clones[register/fork clones]
  clones --> post[post workspace concepts]
  post --> run[rbmc / max_effort / distill]
  run --> iso[pocket isolate]
  iso --> promote[promote to tracks + memory]
```

1. `crucible_workspace start`  
2. Clones + birth moments  
3. Post Global Workspace concepts  
4. RBMC / max_effort / distill  
5. Isolate; promote insights  
6. Audit + memory  

**Tools:** `crucible_workspace`, `track_orchestrate`  
**Skills:** `plan`, `remnant-guide`

---

## E — Max Effort decision

```mermaid
flowchart TD
  eth[ethics_evaluate] --> voices[max_effort four voices]
  voices --> action[Voice of Action 24-48h]
  action --> audit[governance_audit + track]
  audit --> step[Smallest verifiable step]
```

1. Ethics 7-point  
2. Four voices in Crucible  
3. Owner + deadline + criteria  
4. Audit + track  
5. Execute + evidence  

**Tools:** `ethics_evaluate`, `crucible_workspace`, `governance_audit`  
**Skills:** `review`, `plan`

---

## F — Integrity cascade

```mermaid
flowchart TD
  sense[Sense wound] --> stop[Stop thrash]
  stop --> contain[Contain blast radius]
  contain --> repair[Field repair / imprint]
  repair --> scar[Scar + optional seal]
  scar --> advance[Advance alternate step]
```

1. Sense — do not re-run same failure  
2. Contain (spine floors)  
3. Repair from imprint  
4. Scar / seal  
5. Promote seal only after gate  
6. Advance  

**Tools:** `memory_episodic`, `conductor_status`  
**Skills:** `review`

---

## G — Evidence gate

```mermaid
flowchart LR
  plan[plan skill] --> work[Execute A/B/C…]
  work --> review[review skill]
  review --> art[Artifacts: tests/logs/paths]
  art --> judge[Judgment: done?]
```

1. Plan with verification surfaces  
2. Execute under the right combo  
3. Review for gaps / drift  
4. Collect proof  
5. Claim done only if proven  

**Skills:** `plan`, `review`  
**Always fold into shipping paths.**

---

## H — Full stack

```mermaid
flowchart TD
  soul[SOUL] --> eth[Ethics if needed]
  eth --> tracks[Chessboard B]
  tracks --> mem[Memory inject]
  mem --> pick{Path}
  pick --> a[A tools]
  pick --> c[C Remnants]
  pick --> d[D/E deep]
  a --> merge[Merge/distill]
  c --> merge
  d --> merge
  merge --> g[G Evidence + audit]
  g --> go[Advance]
```

Rare high-leverage day. Prefer naming the real primary (C/D/E) and using H only when all layers fire.

---

## Runtime wiring

| Surface | How |
|---------|-----|
| Skill `/combo` | Recommend + workflow text |
| Slash `/combo` | `list` · `recommend <text>` · `workflow <id>` · `<id>` |
| Tool `combo_route` | Same actions for host agent loops |
| Skills plan / review / remnant-guide | Reference combos in output structure |
| Module | `from conductor.combos import recommend_combo, format_workflow` |
