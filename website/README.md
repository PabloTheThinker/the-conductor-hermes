# The Conductor - official website

Premium marketing site for **The Conductor** (Hermes-ready skillset module).

## Preview

```bash
cd website
python3 -m http.server 8765
# open http://127.0.0.1:8765
```

## Design system (v2)

- **Vibe:** OLED dark ethereal glass + editorial luxury
- **Accent:** emerald (`#3d9a6a`) - no AI purple
- **Type:** Clash Display + Satoshi (Fontshare)
- **Nav:** floating glass island + mobile drawer
- **Cards:** double-bezel shells; bento pillars
- **New in v2:** scroll progress, skip link, focus rings, thin/full modes,
  combos A-H rail, install copy button, richer footer, OG meta, SVG favicon
- **Motion:** scroll reveal + progress bar; reduced-motion safe

## Assets

| File | Use |
|------|-----|
| `assets/hero.jpg` | Hero background |
| `assets/network.jpg` | Pillars visual tile |
| `assets/workspace.jpg` | Product story |

## Conductor flow (every section)

Each marketing region is a **remnant work pack**:

| Pack | Role | Anchor |
|------|------|--------|
| `sections/01-nav.json` | surface | `#top` |
| `sections/02-hero.json` | surface | `#top` |
| `sections/03-product.json` | product | `#product` |
| `sections/04-pillars.json` | product | `#pillars` |
| `sections/05-modes.json` | product | `#modes` |
| `sections/06-combos.json` | product | `#combos` |
| `sections/07-install.json` | docs | `#install` |
| `sections/08-close.json` | polish | `#close` |

```text
fanout ×8 objectives (2 batches of 4)
  work_root=website/
  report per remnant → merge
  meister implements HTML with data-conductor-section="…"
serve :8765  (evidence gate)
```

**Debug overlays:** open `http://127.0.0.1:8765/?conductor=1` to outline every Conductor-owned region.
