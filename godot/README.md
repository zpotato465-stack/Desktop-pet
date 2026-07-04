# Duck Pet — Godot Edition 🦆✨

The **animation-first** duck. No AI, no API keys — a Godot 4.3 rewrite focused on
making the duck feel *alive*:

- **Squash & stretch** on every hop, landing, and throw impact
- **Waddle** — the duck bounces vertically, rocks, and leans into its walk
  in sync with its footsteps, kicking up dust on each footfall
- **Rich idle life** — weight-shifting sway, **feather shakes**, ground
  **pecks**, big yawny **stretches**, look-arounds and preening
- **Tricks** — in-place hops and full **backflips** with sparkle + dust landings
- **Throw physics** — grab the duck and yeet it: it tumbles with angular
  velocity, bounces off screen edges and the "floor" with damped impacts,
  and sees stars on a hard whack
- **Emotes** — pops `!`, `?`, `~` and more above its head to react
- **Petting** (double-click) — pixel-heart burst + wiggle of joy
- **Cursor chase** (optional) — waddles over to investigate your pointer
- **Sleeping** — dims and floats pixel Z's after ~90s idle
- Typewriter **speech bubbles** that pop out of the duck's head
- **Settings** (right-click → Settings): duck size, walk pace (incl. ZOOMIES),
  throw physics, chattiness, cursor-follow — persisted between runs

Transparent, borderless, always-on-top window; clicks outside the duck's body
pass through to whatever is underneath.

## Run from source

Open `godot/` with **Godot 4.3+** and press Play, or:

```bash
godot --path godot
```

## Builds

CI (`.github/workflows/godot-ci.yml`) tests the project headless, renders real
screenshots under xvfb, and exports Windows + macOS builds. See this branch's
GitHub Releases for downloads (tags `godot-v*`).

## Files

```
project.godot        window/transparency/render settings
main.tscn            root scene (everything is built in code)
main.gd              the whole duck: states, juice, FX, menu, physics
sprites/             idle, wave, walk_0..3 (pixel art)
tests/smoke.gd       headless state-machine test (CI gate)
tests/shots.gd       renders screenshots of live states (CI, xvfb)
export_presets.cfg   Windows + macOS export configs
```
