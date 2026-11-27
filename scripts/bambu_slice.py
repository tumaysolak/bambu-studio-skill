#!/usr/bin/env python3
"""One-shot: model(s) -> Bambu Studio CLI slice -> GUI-safe 3MF + summary.

Examples
  bambu_slice.py part.stl
  bambu_slice.py a.stl b.stl --filament "Bambu PLA Basic @BBL A1M" --filament "Bambu PLA Matte @BBL A1M" --filament-ids 1,2
  bambu_slice.py part.stl --process "0.16mm Optimal @BBL A1M" --set sparse_infill_density=25% --set wall_loops=3 \
       --set enable_support=1 --set support_type="tree(auto)" --out ~/Desktop/part.gcode.3mf --open
  bambu_slice.py project.3mf --no-slice --out project_fixed.3mf     # just re-export (and repair)

Defaults target a Bambu Lab A1 mini 0.4 nozzle, 0.20mm Standard, Bambu PLA Basic.
Printer/process/filament can be any preset name visible in Bambu Studio
(see: bambu_profiles.py list process --filter A1M).
"""
import argparse, json, os, re, subprocess, sys, tempfile, zipfile, shutil

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bambu_profiles as bp  # noqa
from fix_3mf import fix_xml   # noqa

BIN = os.environ.get("BAMBU_BIN", "/Applications/BambuStudio.app/Contents/MacOS/BambuStudio")
MODEL_IDS = {"Bambu Lab A1 mini": "N1", "Bambu Lab A1": "N2S", "Bambu Lab P1S": "C12",
             "Bambu Lab P1P": "C11", "Bambu Lab X1 Carbon": "BL-P001", "Bambu Lab X1": "BL-P002"}


def repair(path, model_id):
    tmp = path + ".fix"
    with zipfile.ZipFile(path) as zin, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
        for it in zin.infolist():
            data = zin.read(it.filename)
            if it.filename.endswith(".config"):
                t = fix_xml(data.decode("utf-8"))
                if model_id and it.filename.endswith("slice_info.config"):
                    t = t.replace('key="printer_model_id" value=""', f'key="printer_model_id" value="{model_id}"')
                data = t.encode("utf-8")
            zout.writestr(it, data)
    shutil.move(tmp, path)


def gcode_header(path):
    info = {}
    try:
        with zipfile.ZipFile(path) as z:
            names = [n for n in z.namelist() if re.match(r"Metadata/plate_\d+\.gcode$", n)]
            for n in names:
                head = z.read(n)[:6000].decode("utf-8", "ignore")
                m = re.search(r"total estimated time: ([^\n;]+)", head)
                w = re.search(r"total filament weight \[g\] : ([\d.,]+)", head)
                L = re.search(r"total layer number: (\d+)", head)
                info[n] = {"time": m and m.group(1).strip(), "grams": w and w.group(1),
                           "layers": L and int(L.group(1))}
    except Exception as e:
        info["error"] = str(e)
    return info


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("models", nargs="+", help="STL/3MF/STEP/OBJ/AMF files")
    ap.add_argument("--printer", default="Bambu Lab A1 mini 0.4 nozzle")
    ap.add_argument("--process", default="0.20mm Standard @BBL A1M")
    ap.add_argument("--filament", action="append", help="repeat for multi-color (slot order)")
    ap.add_argument("--filament-ids", help='per-object (or per-part with --assemble) filament index, e.g. "1,2,2"')
    ap.add_argument("--color", action="append", help="hex color per --filament, e.g. #FFFFFF (same order)")
    ap.add_argument("--assemble", action="store_true",
                    help="merge all input models into ONE object as parts (keeps their coordinates); use for multi-color parts of one design")
    ap.add_argument("--set", action="append", default=[], help="process override key=value")
    ap.add_argument("--fset", action="append", default=[], help="filament override key=value (all filaments)")
    ap.add_argument("--mset", action="append", default=[], help="machine override key=value")
    ap.add_argument("--plate", default="Textured PEI Plate",
                    help='curr_bed_type: "Textured PEI Plate", "Cool Plate", "Engineering Plate", "High Temp Plate", "Supertack Plate"')
    ap.add_argument("--orient", type=int, default=0, help="1 = auto-orient (off by default, keeps your design orientation)")
    ap.add_argument("--no-arrange", action="store_true")
    ap.add_argument("--scale", type=float); ap.add_argument("--rotate", type=float)
    ap.add_argument("--rotate-x", type=float); ap.add_argument("--rotate-y", type=float)
    ap.add_argument("--copies", type=int, help="clone count for a single model")
    ap.add_argument("--no-slice", action="store_true", help="only build the project 3MF")
    ap.add_argument("--out", help="output .3mf (default: <first model>.gcode.3mf next to it)")
    ap.add_argument("--open", action="store_true", help="open result in the running Bambu Studio")
    a = ap.parse_args()

    models = [os.path.abspath(os.path.expanduser(m)) for m in a.models]
    first = os.path.splitext(os.path.basename(models[0]))[0]
    out = os.path.abspath(os.path.expanduser(a.out or os.path.join(
        os.path.dirname(models[0]), first + (".3mf" if a.no_slice else ".gcode.3mf"))))
    outdir = tempfile.mkdtemp(prefix="bambu_")
    filaments = a.filament or ["Bambu PLA Basic @BBL A1M"]

    mach = bp.flatten("machine", a.printer, a.mset)
    proc = bp.flatten("process", a.process, a.set)
    # Raft at the preset 0.1 mm contact distance welds to the part (Hallo Baby, Nov 2026).
    if str(proc.get("raft_layers", "0")) not in ("0", "") and not any(k.startswith("raft_contact_distance=") for k in a.set):
        proc["raft_contact_distance"] = "0.2"
    if a.plate:
        proc["curr_bed_type"] = a.plate
    n = len(filaments)
    palette = ["#00AE42", "#FFFFFF", "#000000", "#C12E1F", "#F4EE2A", "#0A2989", "#FF6A13", "#898989"]
    colors = (a.color or []) + palette[len(a.color or []):]
    # Without these vectors the CLI maps only filament 1 and silently drops the others.
    proc["filament_map"] = ["1"] * n
    proc["filament_nozzle_map"] = ["1"] * n
    proc["filament_volume_map"] = ["0"] * n
    fpaths = []
    for i, f in enumerate(filaments):
        fd = bp.flatten("filament", f, a.fset)
        fd["filament_colour"] = [colors[i]]
        fd["default_filament_colour"] = [colors[i]]
        p = os.path.join(outdir, f"filament_{i+1}.json"); json.dump(fd, open(p, "w"), indent=1); fpaths.append(p)
    mp = os.path.join(outdir, "machine.json"); json.dump(mach, open(mp, "w"), indent=1)
    pp = os.path.join(outdir, "process.json"); json.dump(proc, open(pp, "w"), indent=1)

    cmd = [BIN, "--debug", "2", "--load-settings", f"{mp};{pp}", "--load-filaments", ";".join(fpaths),
           "--orient", str(a.orient), "--arrange", "0" if a.no_arrange else "1",
           "--outputdir", outdir, "--export-3mf", "result.3mf"]
    if not a.no_slice:
        cmd += ["--slice", "0"]
    if a.filament_ids:
        cmd += ["--load-filament-ids", a.filament_ids]
    if a.scale: cmd += ["--scale", str(a.scale)]
    if a.rotate is not None: cmd += ["--rotate", str(a.rotate)]
    if a.rotate_x is not None: cmd += ["--rotate-x", str(a.rotate_x)]
    if a.rotate_y is not None: cmd += ["--rotate-y", str(a.rotate_y)]
    if a.copies and len(models) == 1: cmd += ["--clone-objects", str(a.copies)]
    if len(filaments) > 1: cmd += ["--allow-multicolor-oneplate"]
    if a.assemble: cmd += ["--assemble"]
    cmd += models
    r = subprocess.run(cmd, capture_output=True, text=True)
    log = (r.stdout or "") + (r.stderr or "")
    open(os.path.join(outdir, "cli.log"), "w").write(log)
    res_json = os.path.join(outdir, "result.json")
    result = json.load(open(res_json)) if os.path.exists(res_json) else {}
    produced = os.path.join(outdir, "result.3mf")
    summary = {"exit": r.returncode, "out": None, "workdir": outdir,
               "errors": [l.split("]")[-1].strip() for l in log.splitlines() if "[error]" in l and "parent path" not in l][-8:],
               "result": {k: result.get(k) for k in ("error_string", "return_code")}}
    if os.path.exists(produced):
        repair(produced, MODEL_IDS.get(mach.get("printer_model", ""), ""))
        os.makedirs(os.path.dirname(out), exist_ok=True)
        shutil.copy(produced, out)
        summary["out"] = out
        if not a.no_slice:
            summary["plates"] = gcode_header(out)
            for p in result.get("sliced_plates", []):
                summary.setdefault("plate_detail", []).append({
                    "id": p.get("id"),
                    "grams": sum(f.get("total_used_g", 0) for f in p.get("filaments", [])),
                    "objects": [o.get("name") for o in p.get("objects", [])],
                    "warnings": [w.get("msg") for w in p.get("warning_message", [])] if isinstance(p.get("warning_message"), list) else None})
        if a.open:
            subprocess.run(["osascript", "-e",
                f'tell application id "com.bambulab.bambu-studio" to open POSIX file "{out}"'])
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    sys.exit(0 if summary["out"] else 1)


if __name__ == "__main__":
    main()
