# bambu-studio-skill

An agent skill (Claude / any coding agent with a macOS shell) that turns a plain-language request into a print-ready Bambu Studio project:

- **Design from scratch** with parametric OpenSCAD or build123d
- **Remix models you like** (scale, cut, holes, embossed/debossed text, booleans, repair)
- **Slice headlessly** with the Bambu Studio CLI using the real system presets (A1 mini by default, any Bambu printer works)
- **Multi-color** (AMS / AMS lite) parts from separate STLs
- **Open the result in the running Bambu Studio** for a final check and send-to-printer

Everything was verified on macOS with Bambu Studio 02.09.01.70 and a Bambu Lab A1 mini.

## Why this exists

The Bambu Studio CLI works, but several undocumented behaviours make naive automation fail:

| Problem | Fix in this repo |
|---|---|
| System presets use `inherits`/`include` chains; the CLI wants complete JSON | `scripts/bambu_profiles.py flatten` |
| CLI-written 3MFs fail to open in the GUI (unescaped quotes in `Metadata/model_settings.config`) | `scripts/fix_3mf.py` (auto-applied by `bambu_slice.py`) |
| Emptying `compatible_printers` makes the CLI reject the process (exit 239) | keep the list, repair the 3MF afterwards |
| Extra filaments are silently dropped in multi-color slices | `bambu_slice.py` fills `filament_map`, `filament_nozzle_map`, `filament_volume_map`, `filament_colour` |
| `--export-3mf` with a path writes to `outputdir//abs/path` (exit 243) | pass a file name, absolute `--outputdir` |
| `open -a BambuStudio file` starts a new instance every time | AppleScript `open POSIX file` into the running app |

## Install

```bash
git clone https://github.com/tumaysolak/bambu-studio-skill ~/bambu-studio-skill
cd ~/bambu-studio-skill && ./setup.sh
```

Requirements: macOS, Bambu Studio in `/Applications`, Homebrew, `uv` (installed by setup if missing).

To use it as a Claude skill, copy `SKILL.md` into your skills folder (or upload it as a skill); it calls the scripts in `~/bambu-studio-skill`.

## Quick start

```bash
cd ~/bambu-studio-skill
# slice an STL for an A1 mini (0.20mm Standard, Bambu PLA Basic) and open it in Bambu Studio
python3 scripts/bambu_slice.py ~/Downloads/model.stl --open

# two-color name tag from a template
openscad --backend=manifold -D 'name="HELLO"' -D 'part="base"' -o /tmp/base.stl templates/name_tag.scad
openscad --backend=manifold -D 'name="HELLO"' -D 'part="text"' -o /tmp/text.stl templates/name_tag.scad
python3 scripts/bambu_slice.py /tmp/base.stl /tmp/text.stl --assemble \
  --filament "Bambu PLA Basic @BBL A1M" --filament "Bambu PLA Basic @BBL A1M" \
  --color "#FFFFFF" --color "#C12E1F" --filament-ids 1,2 --out ~/Desktop/tag.gcode.3mf --open

# remix: fit a downloaded model to 150 mm and add a 5.2 mm hole
.venv/bin/python scripts/mesh_tools.py scale model.stl big.stl --fit 150
.venv/bin/python scripts/mesh_tools.py hole big.stl final.stl --at 0,0 --d 5.2
```

Other printers: `--printer "Bambu Lab P1S 0.4 nozzle" --process "0.20mm Standard @BBL P1S" --filament "Bambu PLA Basic @BBL P1S"` (list names with `scripts/bambu_profiles.py list`).

## Layout

```
SKILL.md                         agent instructions
docs/Bambu-Studio-Uzman-Rehberi.md   full expert guide (Turkish)
scripts/bambu_slice.py           model(s) -> sliced, GUI-safe .gcode.3mf + JSON report
scripts/bambu_profiles.py        list / show / flatten Bambu Studio presets
scripts/fix_3mf.py               repair CLI-written 3MF for the GUI
scripts/mesh_tools.py            remix toolkit (trimesh + manifold3d, OpenSCAD for text/preview)
                                 + `firstlayer`: pre-print adhesion check (thin tips -> brim advice)
templates/*.scad                 verified parametric starting points
setup.sh                         dependencies + sanity slice
```

## Safety

The skill never sends, pauses or stops a print without explicit user approval, and never stores printer access codes or account data.

## Türkçe özet

Bambu Studio'yu Mac üzerinden otomatik kullanan açık kaynak bir skill: beğendiğin modeli değiştirir, sıfırdan parametrik tasarım yapar, A1 mini için dilimler ve sonucu Bambu Studio'da açar. Ayrıntılı rehber: `docs/Bambu-Studio-Uzman-Rehberi.md`.

## License

MIT. Contact: [linkedin.com/in/tumaysolak](https://linkedin.com/in/tumaysolak)
