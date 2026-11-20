#!/usr/bin/env python3
"""Bambu Studio preset resolver.

Bambu Studio system presets use "inherits" and "include" chains. The CLI wants
complete (flattened) JSON files. This tool resolves a preset by name and writes
a self-contained JSON that `BambuStudio --load-settings/--load-filaments` accepts.

Usage:
  bambu_profiles.py list machine|process|filament [--filter A1M]
  bambu_profiles.py flatten machine "Bambu Lab A1 mini 0.4 nozzle" -o machine.json
  bambu_profiles.py flatten process "0.20mm Standard @BBL A1M" -o process.json [--set key=value ...]
  bambu_profiles.py flatten filament "Bambu PLA Basic @BBL A1M" -o filament.json
  bambu_profiles.py show process "0.20mm Standard @BBL A1M" sparse_infill_density
"""
import argparse, json, os, sys, glob

DATA = os.path.expanduser(os.environ.get(
    "BAMBU_DATADIR", "~/Library/Application Support/BambuStudio"))
KINDS = ("machine", "process", "filament")


def load_index(kind):
    idx = {}
    pats = [os.path.join(DATA, "system", "*", kind, "**", "*.json"),
            os.path.join(DATA, "user", "*", kind, "**", "*.json")]
    for pat in pats:
        for f in glob.glob(pat, recursive=True):
            try:
                d = json.load(open(f, encoding="utf-8"))
            except Exception:
                continue
            n = d.get("name")
            if n and n not in idx:   # system first, user can shadow only new names
                idx[n] = (f, d)
    return idx


def resolve(kind, name, idx=None, seen=None):
    idx = idx or load_index(kind)
    seen = seen or set()
    if name in seen:
        raise SystemExit(f"inheritance loop at {name}")
    seen.add(name)
    if name not in idx:
        raise SystemExit(f"preset not found: {kind}/{name}")
    _, d = idx[name]
    out = {}
    if d.get("inherits"):
        out.update(resolve(kind, d["inherits"], idx, seen))
    for inc in d.get("include", []) or []:
        out.update(resolve(kind, inc, idx, set(seen)))
    for k, v in d.items():
        if k in ("include",):
            continue
        out[k] = v
    return out


def flatten(kind, name, sets=()):
    d = resolve(kind, name)
    d.pop("inherits", None)
    d["name"] = name
    d["from"] = "system"
    d["instantiation"] = "true"
    for s in sets:
        k, v = s.split("=", 1)
        old = d.get(k)
        if isinstance(old, list):
            d[k] = [x for x in v.split(",")] if "," in v else [v] * max(1, len(old))
        else:
            d[k] = v
    return d


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    l = sub.add_parser("list"); l.add_argument("kind", choices=KINDS); l.add_argument("--filter", default="")
    f = sub.add_parser("flatten"); f.add_argument("kind", choices=KINDS); f.add_argument("name")
    f.add_argument("-o", "--out", required=True); f.add_argument("--set", action="append", default=[])
    s = sub.add_parser("show"); s.add_argument("kind", choices=KINDS); s.add_argument("name"); s.add_argument("keys", nargs="*")
    a = ap.parse_args()
    if a.cmd == "list":
        for n, (_, d) in sorted(load_index(a.kind).items()):
            if d.get("instantiation") == "true" and a.filter.lower() in n.lower():
                print(n)
    elif a.cmd == "flatten":
        d = flatten(a.kind, a.name, a.set)
        json.dump(d, open(a.out, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
        print(f"wrote {a.out} ({len(d)} keys)")
    else:
        d = resolve(a.kind, a.name)
        for k in (a.keys or sorted(d)):
            print(f"{k} = {d.get(k)}")

if __name__ == "__main__":
    main()
