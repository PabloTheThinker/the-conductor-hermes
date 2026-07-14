# Stellar Codex

**Full D&D-style sci-fi browser RPG** built under **The Conductor** multi-lane plan.

## Play

```bash
cd demos/stellar-codex
python3 -m http.server 8770
# open http://127.0.0.1:8770
```

## Conductor plan

See `CONDUCTOR_PLAN.json` (session lanes):

| Lane | Focus |
|------|--------|
| surface | Shell UI, HUD, dark sci-fi panels |
| rules | d20, mods, HP, levels, point-buy |
| combat | Turns, enemies, loot, boss |
| world | Map, NPCs, dialogue, quests |
| character | Archetypes, inventory start |
| meta | Save/load, help, a11y basics |

**Combo:** full multi-axis mission · **Mode:** full  

## How to play

1. **New Run** → pick archetype, spend point-buy (or roll), launch  
2. Explore **Airlock → Market → Reactor / Cryo → Bridge**  
3. Talk to **Nyx**, accept the Jump Cipher quest  
4. Fight drones/reavers, rest at Airlock, level up  
5. Defeat **Captain's Wraith** on the Bridge  

## Stack

Static HTML + CSS + vanilla JS (no build). Save in `localStorage` key `stellar-codex-v1`.
