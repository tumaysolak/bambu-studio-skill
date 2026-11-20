---
name: bambu-studio
description: Design, remix, slice and prepare 3D prints with Bambu Studio on macOS (Bambu Lab A1 mini by default). Use when the user wants to modify a model they liked, design a part from scratch, slice an STL/3MF, or print on their Bambu printer; Turkish triggers: "3D baskı", "bunu bas", "tasarla", "Bambu Studio".
---

# Bambu Studio: design, remix, slice, print

Toolkit repo: https://github.com/tumaysolak/bambu-studio-skill (local clone: `~/bambu-studio-skill`).
Full Turkish expert guide with every verified detail: `docs/Bambu-Studio-Uzman-Rehberi.md`. Read it when anything below is unclear.

## How to reach the Mac

- Run Mac commands with the local macOS shell tool (e.g. `MacOS-MCP__Shell` / Desktop Commander), not the Linux sandbox. Keep long jobs under the tool timeout or run them with `nohup` and poll.
- To look at images (previews), grant the session `~/bambu-studio-skill` as a folder, stage the PNG and Read it.
- Use computer use only for the final GUI check and the send-to-printer dialog.

## First run check

```bash
test -d ~/bambu-studio-skill || git clone https://github.com/tumaysolak/bambu-studio-skill ~/bambu-studio-skill
cd ~/bambu-studio-skill && ./setup.sh     # openscad@snapshot, uv venv (trimesh, manifold3d, build123d), sanity slice
```

Paths: `B=/Applications/BambuStudio.app/Contents/MacOS/BambuStudio`, `PY=~/bambu-studio-skill/.venv/bin/python`, scripts in `~/bambu-studio-skill/scripts`.

## Pipeline

1. **Understand the request in millimetres.** Size, what it holds/fits, material, colors, strength. Ask only for a missing critical dimension; otherwise pick sensible defaults and state them.
2. **Get geometry**
   - From scratch: write parametric OpenSCAD (`openscad --backend=manifold -o out.stl file.scad`), start from `templates/` when one fits (`name_tag.scad` two-color tag, `box_lid.scad` slip-fit box, `phone_stand.scad`). Use build123d for fillets/STEP-grade mechanical parts.
   - Remix: convert to STL and edit with `$PY scripts/mesh_tools.py` (`info`, `scale --fit/--factor`, `rotate`, `flat`, `cut --z`, `hole --at --d`, `text|textpart`, `boolean`, `repair`, `convert`).
3. **Verify geometry**: `mesh_tools.py info` (fits 180x180x180, watertight) and `mesh_tools.py preview x.stl x.png`, then look at the PNG. Fix before slicing.
4. **Slice**: `python3 scripts/bambu_slice.py model.stl [--process ...] [--set key=value ...] --out <path>.gcode.3mf --open`
   - Multi-color single design: export each color as its own STL in the same coordinates, then `--assemble --filament F --filament F --color #FFFFFF --color #C12E1F --filament-ids 1,2`.
   - Presets: `python3 scripts/bambu_profiles.py list process --filter A1M` / `list filament --filter A1M`.
5. **Report** to the user: dimensions, material, print time, grams, layers, any warnings, and the 3MF path. The 3MF is already open in Bambu Studio via AppleScript.
6. **Print only on explicit approval.** In the GUI: Hazırla tab → "Baskı tablasını dilimle" → "Baskı tablasını yazdır" → check printer, AMS slot mapping (match colors to loaded spools in the Cihaz tab), bed leveling → "Gönder". Screenshot each step. If the Cihaz tab shows a print in progress, do not send and never touch pause/stop.

## Hard-won rules (do not relearn these)

- System presets use `inherits`/`include`; always pass flattened JSON (`bambu_profiles.py flatten`, done inside `bambu_slice.py`).
- `--export-3mf` takes a file NAME; `--outputdir` must be absolute.
- CLI-written 3MFs break the GUI (unescaped quotes in `model_settings.config`). `bambu_slice.py` repairs automatically; for other 3MFs run `scripts/fix_3mf.py file.3mf --model-id N1`.
- Never empty `compatible_printers` (CLI then refuses: exit 239).
- Multi-color needs `filament_map`/`filament_nozzle_map`/`filament_volume_map` sized to the filament count and `filament_colour` in each filament JSON, or extra colors are silently dropped (handled by `bambu_slice.py`).
- `--arrange 0` with origin-centred meshes = object off the 0..180 bed (exit 206).
- Open files in the running app with `osascript -e 'tell application id "com.bambulab.bambu-studio" to open POSIX file "/abs/path"'`; `open -a` spawns extra instances.
- Keep `--orient 0` when you designed the print orientation yourself.

## A1 mini design rules (0.4 nozzle)

Walls ≥0.8 mm (1.6 for strong parts) · overhangs ≤45° without support · bridges ≤25 mm · vertical holes +0.2 mm (M3 → 3.2) · fits: 0.1 press, 0.2 slide, 0.3-0.4 loose · raised text ≥5 mm tall, 0.6-1.2 mm high · largest flat face down · split parts >180 mm with `cut` and add pin holes · open frame: PLA/PETG/TPU yes, ABS/ASA no · color changes cost ~30 s each plus a prime tower.

Defaults (`0.20mm Standard @BBL A1M`): wall_loops 2, sparse_infill_density 15%, grid, top/bottom 5/3, support off, tree(auto) when enabled, brim None, Textured PEI Plate. Useful overrides: `wall_loops=3`, `sparse_infill_density=25%`, `sparse_infill_pattern=gyroid`, `enable_support=1`, `support_on_build_plate_only=1`, `brim_type=outer_only`, `ironing_type=top`, `spiral_mode=1`, `elefant_foot_compensation=0.15`, `xy_hole_compensation=0.1`, `curr_bed_type="Cool Plate"` (via `--plate`).

## Safety

- Sending, pausing, stopping a print or starting calibration needs the user's explicit go-ahead each time.
- Never write the printer access code, serial or account data into files, logs shown to the user, or the repo.
- Respect model licenses; credit the original designer when publishing a remix.
