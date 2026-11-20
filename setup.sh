#!/usr/bin/env bash
# bambu-studio-skill setup for macOS
set -euo pipefail
cd "$(dirname "$0")"

BIN="${BAMBU_BIN:-/Applications/BambuStudio.app/Contents/MacOS/BambuStudio}"
[ -x "$BIN" ] || { echo "Bambu Studio not found at $BIN (set BAMBU_BIN)"; exit 1; }
echo "Bambu Studio: $($BIN --help 2>&1 | head -1)"

command -v brew >/dev/null || { echo "Homebrew required: https://brew.sh"; exit 1; }
if ! command -v openscad >/dev/null; then
  echo "Installing OpenSCAD (snapshot cask; the stable cask is disabled by Gatekeeper)"
  brew install --cask openscad@snapshot
fi
command -v uv >/dev/null || brew install uv

[ -d .venv ] || uv venv .venv --python 3.12
uv pip install --python .venv/bin/python -r requirements.txt

echo "Sanity slice..."
mkdir -p /tmp/bambu_skill_check
.venv/bin/python - <<'EOF'
import trimesh
m = trimesh.creation.box((20, 20, 5)); m.apply_translation((0, 0, 2.5)); m.export("/tmp/bambu_skill_check/cube.stl")
EOF
python3 scripts/bambu_slice.py /tmp/bambu_skill_check/cube.stl --out /tmp/bambu_skill_check/cube.gcode.3mf | head -20
echo "OK"
