---
name: bambu-studio
description: Design, remix, slice and prepare 3D prints with Bambu Studio on macOS (Bambu Lab A1 mini by default). Use when the user wants to modify a model they liked, design a part from scratch, slice an STL/3MF, or print on their Bambu printer; Turkish triggers: "3D baskı", "bunu bas", "tasarla", "Bambu Studio".
---

# Bambu Studio: design, remix, slice, print

Toolkit repo: https://github.com/tumaysolak/bambu-studio-skill (local clone: `~/bambu-studio-skill`).
Full Turkish expert guide with every verified detail: `docs/Bambu-Studio-Uzman-Rehberi.md` (copy also on the Desktop). Read it when anything below is unclear.

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
   Then **always** run `$PY scripts/mesh_tools.py firstlayer model.(stl|3mf)` (also for downloaded 3MFs you only re-slice) and apply every ADVICE line (brim/raft, slow first layer, fan/plate `--fset`, tree support); checklist item 4 has the rules.
4. **Slice**: `python3 scripts/bambu_slice.py model.stl [--process ...] [--set key=value ...] --out <path>.gcode.3mf --open`
   - Multi-color single design: export each color as its own STL in the same coordinates, then `--assemble --filament F --filament F --color #FFFFFF --color #C12E1F --filament-ids 1,2`.
   - Presets: `python3 scripts/bambu_profiles.py list process --filter A1M` / `list filament --filter A1M`.
5. **Report** to the user: dimensions, material, print time, grams, layers, any warnings, and the 3MF path. The 3MF is already open in Bambu Studio via AppleScript.
6. **Print only on explicit approval, and before EVERY send ask the user: "Tablayı sildin mi?"** (dish soap or IPA, dry, no fingers on the surface). Send only after they confirm; a "bas"/"gönder" alone is not that confirmation. Then: In the GUI: Hazırla tab → "Baskı tablasını dilimle" → "Baskı tablasını yazdır" → check printer, AMS slot mapping (match colors to loaded spools in the Cihaz tab), bed leveling → "Gönder". Screenshot each step. If the Cihaz tab shows a print in progress, do not send and never touch pause/stop.
7. **After sending**: tell the user to watch the first 3 layers. The A1 mini does NOT detect a lifted/curled tip (it only senses flow and collisions), so "machine found no problem" means nothing for adhesion.

## Pre-print checklist (from a real failed leaf tip, Nov 2026)

1. **Which design is "open"?** Several BambuStudio processes may run. Read `recent_projects` in `~/Library/Application Support/BambuStudio/BambuStudio.conf` and the file's mtime, then confirm with a screenshot. The window title can belong to an older instance.
2. **Read the designer's 3MF settings** (`Metadata/project_settings.config`, `slice_info.config` for their grams/time) before changing anything; keep their layer height and orientation unless there is a reason.
3. **Strength** for functional parts (door stopper, hook, bracket): `wall_loops=4`, `sparse_infill_density=25%`, `sparse_infill_pattern=gyroid`, `top_shell_layers=6`, `bottom_shell_layers=5`. Usually only +10-20 % grams; report designer vs new grams/time in a table.
4. **Adhesion and support are mandatory decisions, never left on auto.** Two real failures: a leaf tip curled (thin tip) and a 173 mm ball holder lifted at a corner and was stopped (large footprint, designer had no raft/support). Before every print, from the `firstlayer` output:
   - thin tips → `brim_type=outer_only` (`auto_brim` often prints NO brim for PLA on Textured PEI);
   - footprint span >120 mm or contact >3000 mm² → `raft_layers=3` (or `brim_type=outer_only`, `brim_width=8` when raft marks matter) and leave ≥8 mm free around the part (scale down a few % if needed);
   - always with either of the above: `initial_layer_speed=30`, `initial_layer_infill_speed=50`, and filament overrides `--fset close_fan_the_first_x_layers=3 --fset textured_plate_temp_initial_layer=70` (PLA on Textured PEI: fan off for the first 3 layers, plate +5 °C on the first layer only; verified in G-code: `M190 S70` then `M140 S65`). PETG: plate +5 °C over its preset, fan off 3 layers;
   - overhang >50 mm² → `enable_support=1`, `support_type=tree(auto)`, `support_on_build_plate_only=1`; skip only if the designer printed it support-free and the overhang is a low lip;
   - functional parts near the bed limits: prefer raft + support over saving 10 minutes.
   Tell the user to watch the first layers and corners.
5. **GUI did not keep all CLI `--set` values** (support, raft and first-layer speeds included) when the re-sliced 3MF was reopened (wall_loops, bottom shells, infill density/pattern fell back). After opening, check the Dayanıklılık tab, fix fields by hand, re-slice in the GUI and compare its grams with the CLI result. Save (cmd+S).
6. **Send dialog**: confirm the AMS slot the user named (e.g. A3 = green), keep bed leveling on, turn timelapse OFF if the "surface defects" warning appears (unless the user wants a timelapse).
7. **Computer use**: resolve the app as "BambuStudio" (not "Bambu Studio"). Another app's window (e.g. Word) can sit on top and block a click; take a fresh screenshot and retry.

## Hard-won rules (do not relearn these)

- System presets use `inherits`/`include`; always pass flattened JSON (`bambu_profiles.py flatten`, done inside `bambu_slice.py`).
- `--export-3mf` takes a file NAME; `--outputdir` must be absolute.
- CLI-written 3MFs break the GUI (unescaped quotes in `model_settings.config`). `bambu_slice.py` repairs automatically; for other 3MFs run `scripts/fix_3mf.py file.3mf --model-id N1`.
- Never empty `compatible_printers` (CLI then refuses: exit 239).
- Multi-color needs `filament_map`/`filament_nozzle_map`/`filament_volume_map` sized to the filament count and `filament_colour` in each filament JSON, or extra colors are silently dropped (handled by `bambu_slice.py`).
- `--arrange 0` with origin-centred meshes = object off the 0..180 bed (exit 206).
- Open files in the running app with `osascript -e 'tell application id "com.bambulab.bambu-studio" to open POSIX file "/abs/path"'`; `open -a` spawns extra instances.
- Keep `--orient 0` when you designed the print orientation yourself.
- GUI paths: support = Destek tab ("Desteği etkinleştir", "Sadece baskı tablasında", "Raft katmanları"); first-layer speed = Hız tab ("İlk katman", "İlk katman dolgusu"); outer wall = Hız tab ("Dış duvar" speed, and "Dış duvar" again under İvme); print order = Diğerleri → Özel mod → "Yazdırma sırası"; fan and plate temperature are FILAMENT settings, so set them with `--fset` in the CLI slice (the GUI may drop them on reopen: check the plate temperature shown in the send dialog/G-code); use the search box (magnifier) instead of scrolling. Raft expansion is not exposed in the GUI. The gear icon next to "Proje Filamentleri" opens the filament PICKER, not filament settings; cancel it.
- Separate objects in different colors (e.g. one green heart, one white heart): set `print_sequence="by object"` and `enable_prime_tower=0`, or the slicer swaps color every layer (real case: 108 swaps, 4h25m, 68 g vs 58 min, 18 g by object). The GUI may reset it to "Katmana göre" on reopen; check before slicing. By object, the CLI may spread objects over several plates; in the GUI press `a` (arrange) on the 3D view to fit them on one plate.
- GUI quirks: some dropdowns (e.g. "Yazdırma sırası") open off-screen; click the field, then press Down to step through options. Never type into the window unless a text field has focus: single keys are 3D-view shortcuts (`a` arranges all objects).
- Several BambuStudio windows/instances may exist and a downloaded 3MF can replace the project in the window you were using; after any pause, confirm the window title before clicking.
- Reopened CLI-sliced 3MFs can show preset values instead of your `--set` overrides in the GUI; verify in the GUI before printing (checklist item 5).

## Smooth outer surface (verified Nov 2026)

When the user wants a smoother/cleaner visible surface ("daha pürüzsüz dış yüzey"), slow only the outer wall; inner walls and infill stay fast.

- GUI: Hazırla → İşlem → **Hız** → "Diğer katmanların hızı" → **Dış duvar** (A1M presets: 200 mm/s) → 60-100 mm/s; same tab further down → **İvme** → **Dış duvar** (5000 mm/s²) → 2500.
- CLI: `--set outer_wall_speed=60 --set outer_wall_acceleration=2500` (balanced: 100 / 3000). Keep "Çıkıntılar için yavaşla" (`enable_overhang_speed=1`) on.
- Measured on a 35 mm heart (0.20 Standard A1M, PLA): 200/5000 = 24m18s, 100/3000 = 24m37s, 60/2500 = 25m11s (+4 %, same grams). G-code check: outer-wall moves go from F12000 to F3600 and `M204 S2500` appears before each outer wall. Small parts cost little because the filament's 6 s minimum layer time already slows them; large parts pay more.
- Further options, mention as trade-offs: Kalite → Gelişmiş → Duvar sırası "dış/iç" gives a crisper surface but weaker overhangs (keep "iç/dış" for overhang-heavy models); 0.16 or 0.12 mm layers reduce visible layer lines; `ironing_type=top` only smooths flat tops; `seam_position=back` hides the seam.
- After reopening a CLI-sliced 3MF, confirm both Dış duvar fields in the GUI (checklist item 5).

## A1 mini design rules (0.4 nozzle)

Walls ≥0.8 mm (1.6 for strong parts) · overhangs ≤45° without support · bridges ≤25 mm · vertical holes +0.2 mm (M3 → 3.2) · fits: 0.1 press, 0.2 slide, 0.3-0.4 loose · raised text ≥5 mm tall, 0.6-1.2 mm high · first-layer features narrower than 5 mm (leaf tips, spikes) need a brim · footprint >120 mm needs a raft or 8 mm brim plus 30 mm/s first layer · largest flat face down · split parts >180 mm with `cut` and add pin holes · open frame: PLA/PETG/TPU yes, ABS/ASA no · color changes cost ~30 s each plus a prime tower.

Defaults (`0.20mm Standard @BBL A1M`): wall_loops 2, sparse_infill_density 15%, grid, top/bottom 5/3, support off, tree(auto) when enabled, brim None, Textured PEI Plate. Useful overrides: `wall_loops=3`, `sparse_infill_density=25%`, `sparse_infill_pattern=gyroid`, `enable_support=1`, `support_on_build_plate_only=1`, `brim_type=outer_only`, `ironing_type=top`, `spiral_mode=1`, `elefant_foot_compensation=0.15`, `xy_hole_compensation=0.1`, `curr_bed_type="Cool Plate"` (via `--plate`).

## Safety

- Sending, pausing, stopping a print or starting calibration needs the user's explicit go-ahead each time.
- Never write the printer access code, serial or account data into files, logs shown to the user, or the repo.
- Respect model licenses; credit the original designer when publishing a remix.
