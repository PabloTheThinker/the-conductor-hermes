/**
 * Stellar Codex — D&D-style sci-fi browser RPG
 * Conducted under Combo-full multi-lane plan (rules / combat / world / UI / meta)
 */
(() => {
  "use strict";

  const SAVE_KEY = "stellar-codex-v1";
  const $ = (sel, el = document) => el.querySelector(sel);
  const $$ = (sel, el = document) => [...el.querySelectorAll(sel)];

  // --- Rules engine (d20) ---
  const STATS = ["STR", "DEX", "CON", "INT", "WIS", "CHA"];
  const mod = (score) => Math.floor((score - 10) / 2);
  const d = (sides) => 1 + Math.floor(Math.random() * sides);
  const d20 = () => d(20);
  function roll(modVal = 0, advantage = 0) {
    let a = d20(), b = d20();
    let raw = a;
    if (advantage > 0) raw = Math.max(a, b);
    if (advantage < 0) raw = Math.min(a, b);
    const total = raw + modVal;
    return { raw, total, mod: modVal, advantage, a, b };
  }

  const ARCHETYPES = {
    voidblade: {
      name: "Voidblade",
      blurb: "Melee tank. Hard light edge and station-forged plate.",
      bonuses: { STR: 2, CON: 1 },
      hp: 12,
      ac: 15,
      weapon: { name: "Phase Saber", dmg: 8, stat: "STR" },
      skill: "Intimidation",
    },
    pulse: {
      name: "Pulse Runner",
      blurb: "Speed and guns. Zero-G parkour specialist.",
      bonuses: { DEX: 2, CHA: 1 },
      hp: 10,
      ac: 14,
      weapon: { name: "Coil Pistol", dmg: 6, stat: "DEX" },
      skill: "Acrobatics",
    },
    astromancer: {
      name: "Astromancer",
      blurb: "Psi-math caster. Bends probability and plasma.",
      bonuses: { INT: 2, WIS: 1 },
      hp: 8,
      ac: 12,
      weapon: { name: "Starbrand Focus", dmg: 8, stat: "INT" },
      skill: "Arcana",
    },
    rigsmith: {
      name: "Rig-Smith",
      blurb: "Engineer and drone wrangler. Fixes what war breaks.",
      bonuses: { INT: 1, CON: 1, WIS: 1 },
      hp: 11,
      ac: 13,
      weapon: { name: "Servo Hammer", dmg: 6, stat: "STR" },
      skill: "Engineering",
    },
    courier: {
      name: "Shadow Courier",
      blurb: "Infiltration, smuggling, and whispered deals.",
      bonuses: { DEX: 1, CHA: 2 },
      hp: 9,
      ac: 13,
      weapon: { name: "Mono-Knife", dmg: 6, stat: "DEX" },
      skill: "Stealth",
    },
  };

  const LOCATIONS = {
    airlock: {
      id: "airlock",
      name: "Airlock Theta-9",
      desc: "Frost crawls the viewport. The Shattered Corridor hangs outside like a broken crown.",
      exits: ["market", "cryo"],
      actions: ["scout", "rest"],
    },
    market: {
      id: "market",
      name: "Black Market Deck",
      desc: "Neon stalls sell illegal jump cores and bad coffee. A broker watches you.",
      exits: ["airlock", "reactor", "bridge"],
      npc: "nyx",
      actions: ["shop", "talk"],
    },
    reactor: {
      id: "reactor",
      name: "Reactor Spine",
      desc: "The heart of the station thrums. Heat and radiation warnings blink amber.",
      exits: ["market", "bridge"],
      encounter: "spark_drone",
      actions: ["fight", "sabotage"],
    },
    cryo: {
      id: "cryo",
      name: "Cryo Vault",
      desc: "Rows of pods. One is cracked open. Something left footprints in the frost.",
      exits: ["airlock", "bridge"],
      encounter: "frost_reaver",
      actions: ["search", "fight"],
    },
    bridge: {
      id: "bridge",
      name: "Command Bridge",
      desc: "Captain's chair is empty. The nav-core still holds a sealed jump vector.",
      exits: ["market", "reactor", "cryo"],
      encounter: "captain_wraith",
      actions: ["finale", "talk"],
      npc: "echo",
    },
  };

  const ENEMIES = {
    spark_drone: {
      id: "spark_drone",
      name: "Spark Drone",
      hp: 18,
      ac: 13,
      atk: 4,
      dmg: 5,
      xp: 40,
      loot: { name: "Power Cell", value: 15 },
    },
    frost_reaver: {
      id: "frost_reaver",
      name: "Frost Reaver",
      hp: 28,
      ac: 14,
      atk: 5,
      dmg: 7,
      xp: 70,
      loot: { name: "Cryo Shard", value: 30 },
    },
    captain_wraith: {
      id: "captain_wraith",
      name: "Captain's Wraith",
      hp: 45,
      ac: 15,
      atk: 6,
      dmg: 9,
      xp: 150,
      loot: { name: "Jump Cipher", value: 100 },
      boss: true,
    },
  };

  const NPCS = {
    nyx: {
      name: "Nyx the Broker",
      lines: [
        "Credits or blood, Runner. The Corridor doesn't care which you spend.",
        "Word is the Bridge still holds a live jump cipher. Guarded. Always guarded.",
      ],
      choices: [
        { t: "Ask about work", effect: "quest_cipher" },
        { t: "Buy medkit (20c)", effect: "buy_med" },
        { t: "Leave", effect: "close" },
      ],
    },
    echo: {
      name: "Echo (AI remnant)",
      lines: [
        "I am what remains of the station AI. The Captain did not leave. She was unmade.",
        "Defeat her wraith. Restore the nav-core. Then the Corridor can sleep.",
      ],
      choices: [
        { t: "Accept the charge", effect: "quest_finale" },
        { t: "Ask for a blessing", effect: "buff" },
        { t: "Step back", effect: "close" },
      ],
    },
  };

  // --- State ---
  let state = null;

  function baseStats() {
    return { STR: 10, DEX: 10, CON: 10, INT: 10, WIS: 10, CHA: 10 };
  }

  function newDraft() {
    return {
      name: "",
      arch: "voidblade",
      stats: baseStats(),
      points: 12,
    };
  }

  function createHero(draft) {
    const a = ARCHETYPES[draft.arch];
    const stats = { ...draft.stats };
    for (const [k, v] of Object.entries(a.bonuses)) stats[k] = (stats[k] || 10) + v;
    const maxHp = a.hp + mod(stats.CON) * 2 + 4;
    return {
      name: draft.name.trim() || "Runner",
      arch: draft.arch,
      archName: a.name,
      stats,
      hp: maxHp,
      maxHp,
      ac: a.ac + Math.max(0, mod(stats.DEX)),
      level: 1,
      xp: 0,
      nextXp: 100,
      credits: 40,
      weapon: { ...a.weapon },
      inventory: [
        { name: "Ration Pack", type: "consumable", heal: 6, qty: 2 },
        { name: "Station Map Fragment", type: "quest", qty: 1 },
      ],
      skill: a.skill,
    };
  }

  function freshGame(hero) {
    return {
      hero,
      loc: "airlock",
      log: [],
      combat: null,
      dialogue: null,
      flags: {
        questCipher: false,
        questFinale: false,
        defeated: {},
        win: false,
      },
      buffs: { atk: 0, turns: 0 },
      draft: null,
      screen: "play",
    };
  }

  // --- Log / UI helpers ---
  function pushLog(msg, cls = "") {
    if (!state) return;
    if (!Array.isArray(state.log)) state.log = [];
    state.log.unshift({ t: Date.now(), msg, cls });
    state.log = state.log.slice(0, 80);
  }

  function toast(msg) {
    const el = $("#toast");
    el.textContent = msg;
    el.classList.add("show");
    clearTimeout(toast._t);
    toast._t = setTimeout(() => el.classList.remove("show"), 1800);
  }

  function showScreen(id) {
    $$(".screen").forEach((s) => s.classList.toggle("active", s.id === `screen-${id}`));
  }

  // --- Combat ---
  function startCombat(enemyId) {
    if (state.flags.defeated[enemyId]) {
      pushLog("Only scrap remains here.", "ok");
      render();
      return;
    }
    const base = ENEMIES[enemyId];
    state.combat = {
      id: enemyId,
      name: base.name,
      hp: base.hp,
      maxHp: base.hp,
      ac: base.ac,
      atk: base.atk,
      dmg: base.dmg,
      xp: base.xp,
      loot: base.loot,
      boss: !!base.boss,
    };
    state.dialogue = null;
    pushLog(`Combat: ${base.name} engages!`, "combat");
    render();
  }

  function playerAttack() {
    const h = state.hero;
    const e = state.combat;
    if (!e) return;
    const w = h.weapon;
    const m = mod(h.stats[w.stat]) + (state.buffs.atk || 0);
    const r = roll(m);
    pushLog(`You attack with ${w.name}: d20 ${r.raw}${m >= 0 ? "+" : ""}${m} = ${r.total} vs AC ${e.ac}`, "roll");
    if (r.raw === 20 || r.total >= e.ac) {
      const dmg = d(w.dmg) + Math.max(0, mod(h.stats[w.stat]));
      const crit = r.raw === 20 ? 2 : 1;
      const total = dmg * crit;
      e.hp -= total;
      pushLog(`${crit > 1 ? "Critical! " : ""}Hit for ${total} damage.`, "combat");
    } else {
      pushLog("Miss.", "combat");
    }
    if (e.hp <= 0) return endCombat(true);
    enemyTurn();
    render();
  }

  function playerSkill() {
    const h = state.hero;
    const e = state.combat;
    if (!e) return;
    const r = roll(mod(h.stats.INT) + mod(h.stats.WIS));
    pushLog(`Tactical exploit (${h.skill}): ${r.total}`, "roll");
    if (r.total >= 14) {
      const dmg = d(6) + mod(h.stats.INT);
      e.hp -= Math.max(2, dmg);
      pushLog(`You exploit a weak point for ${Math.max(2, dmg)} damage.`, "ok");
    } else {
      pushLog("The pattern slips. No opening.", "combat");
    }
    if (e.hp <= 0) return endCombat(true);
    enemyTurn();
    render();
  }

  function playerDefend() {
    state._defend = true;
    pushLog("You brace behind hard-light plating.", "ok");
    enemyTurn();
    state._defend = false;
    render();
  }

  function enemyTurn() {
    const h = state.hero;
    const e = state.combat;
    if (!e || e.hp <= 0) return;
    const r = roll(e.atk);
    pushLog(`${e.name} attacks: ${r.total} vs your AC ${h.ac}`, "roll");
    if (r.total >= h.ac) {
      let dmg = d(e.dmg) + 1;
      if (state._defend) dmg = Math.max(1, Math.floor(dmg / 2));
      h.hp -= dmg;
      pushLog(`${e.name} hits for ${dmg}.`, "combat");
    } else {
      pushLog(`${e.name} misses.`, "ok");
    }
    if (h.hp <= 0) {
      h.hp = 0;
      endCombat(false);
    }
    if (state.buffs.turns > 0) {
      state.buffs.turns -= 1;
      if (state.buffs.turns <= 0) state.buffs.atk = 0;
    }
  }

  function endCombat(won) {
    const e = state.combat;
    if (!e) return;
    if (won) {
      pushLog(`${e.name} destroyed.`, "ok");
      state.flags.defeated[e.id] = true;
      state.hero.xp += e.xp;
      state.hero.credits += Math.floor(e.xp / 2);
      if (e.loot) {
        addItem({ name: e.loot.name, type: "loot", value: e.loot.value, qty: 1 });
        pushLog(`Loot: ${e.loot.name}`, "loot");
      }
      checkLevel();
      if (e.boss) {
        state.flags.win = true;
        pushLog("The nav-core unlocks. Jump vector stable. You saved the Corridor.", "quest");
        toast("Victory: Shattered Corridor cleared");
      }
    } else {
      pushLog("You drop. Emergency medfoam saves you at 1 HP. Retreat to Airlock.", "combat");
      state.hero.hp = 1;
      state.loc = "airlock";
    }
    state.combat = null;
    render();
  }

  function checkLevel() {
    const h = state.hero;
    while (h.xp >= h.nextXp) {
      h.xp -= h.nextXp;
      h.level += 1;
      h.nextXp = 80 + h.level * 40;
      h.maxHp += 4 + Math.max(0, mod(h.stats.CON));
      h.hp = h.maxHp;
      h.ac += h.level % 2 === 0 ? 1 : 0;
      pushLog(`Level up! You are level ${h.level}.`, "quest");
      toast(`Level ${h.level}`);
    }
  }

  function addItem(item) {
    const inv = state.hero.inventory;
    const existing = inv.find((i) => i.name === item.name && i.type === item.type);
    if (existing) existing.qty += item.qty || 1;
    else inv.push({ ...item, qty: item.qty || 1 });
  }

  function useItem(name) {
    const inv = state.hero.inventory;
    const item = inv.find((i) => i.name === name);
    if (!item) return;
    if (item.type === "consumable" && item.heal) {
      const heal = item.heal + mod(state.hero.stats.CON);
      state.hero.hp = Math.min(state.hero.maxHp, state.hero.hp + heal);
      pushLog(`Used ${name}: recovered ${heal} HP.`, "ok");
      item.qty -= 1;
      if (item.qty <= 0) state.hero.inventory = inv.filter((i) => i !== item);
      render();
    } else {
      toast("Can't use that now");
    }
  }

  // --- World ---
  function travel(to) {
    if (state.combat) return toast("Finish combat first");
    const loc = LOCATIONS[state.loc];
    if (!loc.exits.includes(to)) return;
    state.loc = to;
    state.dialogue = null;
    const dest = LOCATIONS[to];
    pushLog(`You move to ${dest.name}.`, "");
    pushLog(dest.desc, "");
    // ambush chance
    if (dest.encounter && !state.flags.defeated[dest.encounter] && Math.random() < 0.35) {
      pushLog("Sensors spike. Contact!", "combat");
      startCombat(dest.encounter);
      return;
    }
    render();
  }

  function rest() {
    if (state.combat) return;
    if (state.loc !== "airlock") {
      toast("Only safe at Airlock");
      return;
    }
    state.hero.hp = state.hero.maxHp;
    pushLog("You rest in the airlock foam-bunk. HP restored.", "ok");
    render();
  }

  function openDialogue(npcId) {
    const n = NPCS[npcId];
    if (!n) return;
    state.dialogue = {
      id: npcId,
      name: n.name,
      line: n.lines[Math.floor(Math.random() * n.lines.length)],
      choices: n.choices,
    };
    render();
  }

  function dialogueChoice(effect) {
    if (effect === "close") {
      state.dialogue = null;
    } else if (effect === "quest_cipher") {
      state.flags.questCipher = true;
      pushLog("Quest: Retrieve the Jump Cipher from the Bridge.", "quest");
      toast("Quest accepted");
      state.dialogue = null;
    } else if (effect === "quest_finale") {
      state.flags.questFinale = true;
      pushLog("Quest: Defeat the Captain's Wraith.", "quest");
      toast("Charge accepted");
      state.dialogue = null;
    } else if (effect === "buy_med") {
      if (state.hero.credits >= 20) {
        state.hero.credits -= 20;
        addItem({ name: "Medkit", type: "consumable", heal: 14, qty: 1 });
        pushLog("Bought Medkit (-20 credits).", "loot");
      } else toast("Not enough credits");
      state.dialogue = null;
    } else if (effect === "buff") {
      state.buffs = { atk: 2, turns: 5 };
      pushLog("Echo threads a +2 attack blessing for 5 exchanges.", "ok");
      state.dialogue = null;
    }
    render();
  }

  function locationAction(act) {
    const loc = LOCATIONS[state.loc];
    if (act === "rest") return rest();
    if (act === "scout") {
      const r = roll(mod(state.hero.stats.WIS));
      pushLog(`Scout check: ${r.total}`, "roll");
      if (r.total >= 12) {
        pushLog("You map a safe route toward the Market Deck vents.", "ok");
        state.hero.credits += 5;
      } else pushLog("Static. Nothing useful.", "");
      render();
      return;
    }
    if (act === "shop" || act === "talk") {
      if (loc.npc) openDialogue(loc.npc);
      else toast("No one to talk to");
      return;
    }
    if (act === "fight" || act === "finale") {
      if (loc.encounter) startCombat(loc.encounter);
      else toast("No hostiles");
      return;
    }
    if (act === "search") {
      const r = roll(mod(state.hero.stats.INT));
      pushLog(`Search: ${r.total}`, "roll");
      if (r.total >= 13) {
        addItem({ name: "Data Chip", type: "loot", value: 20, qty: 1 });
        pushLog("You pry a Data Chip from a frozen console.", "loot");
      } else pushLog("Frost and empty shells.", "");
      render();
      return;
    }
    if (act === "sabotage") {
      const r = roll(mod(state.hero.stats.INT));
      pushLog(`Sabotage: ${r.total}`, "roll");
      if (r.total >= 14) {
        pushLog("You vent coolant. Drones nearby will be weakened next fight.", "ok");
        state.flags.sabotage = true;
      } else {
        pushLog("Alarm! A Spark Drone drops from the rafters.", "combat");
        startCombat("spark_drone");
        return;
      }
      render();
    }
  }

  // --- Save ---
  function save() {
    if (!state || !state.hero) return toast("Nothing to save — start a New Run first");
    try {
      localStorage.setItem(SAVE_KEY, JSON.stringify(state));
      toast("Game saved");
    } catch {
      toast("Could not save (private mode?)");
    }
  }
  function load() {
    let raw;
    try {
      raw = localStorage.getItem(SAVE_KEY);
    } catch {
      return toast("Storage blocked in this browser");
    }
    if (!raw) return toast("No save found — start a New Run");
    try {
      const data = JSON.parse(raw);
      if (!data.hero || !data.loc) throw new Error("incomplete save");
      state = data;
      if (!Array.isArray(state.log)) state.log = [];
      if (!state.flags) state.flags = { questCipher: false, questFinale: false, defeated: {}, win: false };
      if (!state.buffs) state.buffs = { atk: 0, turns: 0 };
      state.screen = "play";
      state.combat = state.combat || null;
      state.dialogue = null;
      pushLog("Save loaded.", "ok");
      render();
      toast("Loaded");
    } catch (e) {
      console.error(e);
      toast("Corrupt save — use New Run");
    }
  }

  // --- Create UI state ---
  let draft = newDraft();

  function renderCreate() {
    showScreen("create");
    $("#hero-name").value = draft.name;
    $$(".arch").forEach((el) => {
      el.classList.toggle("selected", el.dataset.id === draft.arch);
    });
    const box = $("#stats-box");
    box.innerHTML = STATS.map((s) => {
      const v = draft.stats[s];
      return `<div class="stat" data-stat="${s}">
        <small>${s}</small>
        <b>${v}</b>
        <div class="stat-ctrl">
          <button type="button" data-d="-1" data-s="${s}" aria-label="Decrease ${s}">−</button>
          <button type="button" data-d="1" data-s="${s}" aria-label="Increase ${s}">+</button>
        </div>
        <small>mod ${mod(v) >= 0 ? "+" : ""}${mod(v)}</small>
      </div>`;
    }).join("");
    $("#points-left").textContent = `Point-buy remaining: ${draft.points}`;
    const a = ARCHETYPES[draft.arch];
    $("#arch-preview").innerHTML = `<strong>${a.name}</strong><p class="muted">${a.blurb}</p>
      <p class="faint">Weapon: ${a.weapon.name} · Base AC ${a.ac} · Skill ${a.skill}</p>`;
  }

  function render() {
    try {
      _renderInner();
    } catch (err) {
      console.error(err);
      showBootError(err);
    }
  }

  function showBootError(err) {
    let box = document.getElementById("boot-error");
    if (!box) {
      box = document.createElement("div");
      box.id = "boot-error";
      box.style.cssText =
        "position:fixed;inset:auto 1rem 1rem 1rem;z-index:99;background:#3a1020;color:#ffd0d8;border:1px solid #ff5d7a;padding:1rem;border-radius:12px;font:14px/1.4 system-ui";
      document.body.appendChild(box);
    }
    box.textContent = "Game error: " + (err && err.message ? err.message : String(err));
  }

  function _renderInner() {
    if (!state || state.screen === "title") {
      showScreen("title");
      return;
    }
    // Only use explicit screen — do not trap on create via draft object truthiness
    if (state.screen === "create") {
      renderCreate();
      return;
    }
    if (!state.hero || !state.loc) {
      showScreen("title");
      return;
    }
    showScreen("play");
    const h = state.hero;
    const loc = LOCATIONS[state.loc];
    if (!loc) {
      pushLog("Invalid location; returning to airlock.", "combat");
      state.loc = "airlock";
      return _renderInner();
    }

    $("#hud-name").textContent = `${h.name} · ${h.archName} L${h.level}`;
    $("#hud-credits").textContent = `${h.credits}c`;
    $("#hp-label").textContent = `HP ${h.hp}/${h.maxHp}`;
    $("#hp-bar").style.width = `${Math.max(0, (h.hp / h.maxHp) * 100)}%`;
    $("#xp-label").textContent = `XP ${h.xp}/${h.nextXp}`;
    $("#xp-bar").style.width = `${Math.max(0, (h.xp / h.nextXp) * 100)}%`;
    $("#hud-ac").textContent = `AC ${h.ac}`;
    $("#hud-weapon").textContent = h.weapon.name;

    $("#loc-name").textContent = loc.name;
    $("#loc-desc").textContent = loc.desc;

    const exits = $("#exits");
    exits.innerHTML = loc.exits
      .map((id) => {
        const L = LOCATIONS[id];
        return `<li><button type="button" data-go="${id}">→ ${L.name}</button></li>`;
      })
      .join("");

    const acts = $("#loc-actions");
    acts.innerHTML = (loc.actions || [])
      .map((a) => `<button type="button" class="btn btn-ghost" data-act="${a}">${labelAct(a)}</button>`)
      .join("");

    // inventory
    $("#inv").innerHTML = h.inventory
      .map(
        (i) =>
          `<li><button type="button" data-use="${escapeAttr(i.name)}">${i.name} ×${i.qty}${
            i.heal ? " (heal)" : i.value ? ` (${i.value}c)` : ""
          }</button></li>`
      )
      .join("");

    // quests
    const q = [];
    if (state.flags.questCipher && !state.flags.win)
      q.push({ t: "Retrieve the Jump Cipher (Bridge)", done: !!state.flags.defeated.captain_wraith });
    if (state.flags.questFinale && !state.flags.win)
      q.push({ t: "Defeat the Captain's Wraith", done: !!state.flags.defeated.captain_wraith });
    if (!q.length) q.push({ t: "Explore the Shattered Corridor", done: false });
    if (state.flags.win) q.push({ t: "Corridor secured", done: true });
    $("#quests").innerHTML = q
      .map((x) => `<li class="${x.done ? "done" : ""}">${x.t}</li>`)
      .join("");

    // log
    $("#log").innerHTML = state.log
      .map((l) => `<div class="log-line ${l.cls || ""}">${escapeHtml(l.msg)}</div>`)
      .join("");

    // combat
    const cbox = $("#combat");
    if (state.combat) {
      const e = state.combat;
      cbox.hidden = false;
      cbox.innerHTML = `
        <h3>Combat</h3>
        <div class="enemy-row"><span>${escapeHtml(e.name)}</span><span>HP ${Math.max(0, e.hp)}/${e.maxHp} · AC ${e.ac}</span></div>
        <div class="bar"><i style="width:${Math.max(0, (e.hp / e.maxHp) * 100)}%"></i></div>
        <div class="actions">
          <button type="button" class="btn btn-primary" data-combat="attack">Attack</button>
          <button type="button" class="btn btn-ghost" data-combat="skill">Exploit</button>
          <button type="button" class="btn btn-ghost" data-combat="defend">Defend</button>
        </div>`;
    } else {
      cbox.hidden = true;
      cbox.innerHTML = "";
    }

    // dialogue
    const dbox = $("#dialogue");
    if (state.dialogue) {
      const d = state.dialogue;
      dbox.hidden = false;
      dbox.innerHTML = `
        <div class="who">${escapeHtml(d.name)}</div>
        <p>${escapeHtml(d.line)}</p>
        <div class="choices">
          ${d.choices.map((c) => `<button type="button" data-dlg="${c.effect}">${escapeHtml(c.t)}</button>`).join("")}
        </div>`;
    } else {
      dbox.hidden = true;
      dbox.innerHTML = "";
    }

    if (state.flags.win) {
      $("#win-banner").hidden = false;
    } else {
      $("#win-banner").hidden = true;
    }
  }

  function labelAct(a) {
    return (
      {
        scout: "Scout",
        rest: "Rest (full HP)",
        shop: "Browse stalls",
        talk: "Talk",
        fight: "Engage hostiles",
        search: "Search",
        sabotage: "Sabotage systems",
        finale: "Confront the Wraith",
      }[a] || a
    );
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }
  function escapeAttr(s) {
    return escapeHtml(s).replace(/'/g, "&#39;");
  }

  // --- Events ---
  function bind() {
    $("#btn-new").addEventListener("click", () => {
      draft = newDraft();
      state = { screen: "create", hero: null, log: [] };
      renderCreate();
    });
    $("#btn-continue").addEventListener("click", load);
    $("#btn-save").addEventListener("click", save);
    $("#btn-load").addEventListener("click", load);
    $("#btn-title").addEventListener("click", () => {
      state = { screen: "title" };
      showScreen("title");
    });

    $("#hero-name").addEventListener("input", (e) => {
      draft.name = e.target.value;
    });

    $("#arch-list").addEventListener("click", (e) => {
      const btn = e.target.closest(".arch");
      if (!btn) return;
      draft.arch = btn.dataset.id;
      renderCreate();
    });

    $("#stats-box").addEventListener("click", (e) => {
      const b = e.target.closest("button[data-s]");
      if (!b) return;
      const s = b.dataset.s;
      const dlt = Number(b.dataset.d);
      const cur = draft.stats[s];
      if (dlt > 0) {
        if (draft.points <= 0 || cur >= 15) return;
        draft.stats[s] = cur + 1;
        draft.points -= 1;
      } else {
        if (cur <= 8) return;
        draft.stats[s] = cur - 1;
        draft.points += 1;
      }
      renderCreate();
    });

    $("#btn-start").addEventListener("click", () => {
      if (draft.points > 0) {
        toast(`Spend remaining ${draft.points} points or leave them`);
      }
      const hero = createHero(draft);
      state = freshGame(hero);
      pushLog(`Welcome aboard, ${hero.name} the ${hero.archName}.`, "quest");
      pushLog(LOCATIONS.airlock.desc, "");
      pushLog("Hint: Rest at Airlock. Talk to Nyx on the Market Deck.", "quest");
      render();
    });

    $("#btn-roll-stats").addEventListener("click", () => {
      draft.points = 0;
      for (const s of STATS) {
        // 4d6 drop lowest vibe simplified: 2d6+4
        draft.stats[s] = Math.min(15, Math.max(8, d(6) + d(6) + 4));
      }
      renderCreate();
      toast("Stats rolled");
    });

    document.body.addEventListener("click", (e) => {
      const go = e.target.closest("[data-go]");
      if (go) return travel(go.dataset.go);
      const act = e.target.closest("[data-act]");
      if (act) return locationAction(act.dataset.act);
      const use = e.target.closest("[data-use]");
      if (use) return useItem(use.dataset.use);
      const combat = e.target.closest("[data-combat]");
      if (combat) {
        if (combat.dataset.combat === "attack") return playerAttack();
        if (combat.dataset.combat === "skill") return playerSkill();
        if (combat.dataset.combat === "defend") return playerDefend();
      }
      const dlg = e.target.closest("[data-dlg]");
      if (dlg) return dialogueChoice(dlg.dataset.dlg);
    });
  }

  // boot
  function init() {
    try {
      const list = $("#arch-list");
      if (!list) throw new Error("Missing #arch-list — wrong page/path?");
      list.innerHTML = Object.entries(ARCHETYPES)
        .map(
          ([id, a]) =>
            `<button type="button" class="arch" data-id="${id}"><strong>${a.name}</strong><span>${a.blurb}</span></button>`
        )
        .join("");
      bind();
      state = { screen: "title", log: [] };
      showScreen("title");
      const meta = $("#conductor-meta");
      if (meta) {
        meta.textContent =
          "Conductor lanes: UI · rules · combat · world · character · meta — use New Run to start";
      }
      // prove UI is live
      const badge = document.createElement("div");
      badge.id = "js-live";
      badge.style.cssText =
        "position:fixed;top:0;right:0;background:#0a2;color:#041018;font:11px/1 system-ui;padding:4px 8px;z-index:100;border-radius:0 0 0 8px";
      badge.textContent = "JS OK";
      document.body.appendChild(badge);
      setTimeout(() => badge.remove(), 2500);
    } catch (err) {
      console.error(err);
      showBootError(err);
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
