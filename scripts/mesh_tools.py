#!/usr/bin/env python3
"""Mesh editing toolkit for remixing downloaded models before Bambu Studio.

Needs: trimesh, manifold3d, numpy (and openscad on PATH for text/preview).
All lengths in mm. Bambu Lab A1 mini build volume: 180 x 180 x 180.

  info     in.stl                                  size, volume, watertight, bed fit
  scale    in.stl out.stl --factor 1.2 | --size X,Y,Z | --fit 170   (uniform unless --size with 3 values)
  rotate   in.stl out.stl --x 90 --y 0 --z 45      then drops to bed
  mirror   in.stl out.stl --axis x
  flat     in.stl out.stl                          lay largest flat face on bed
  cut      in.stl out.stl --z 20 [--keep below|above|both]   (both -> out_a/out_b)
  hole     in.stl out.stl --at X,Y --d 5 [--z0 -1 --h 999] [--axis z]
  boolean  a.stl b.stl out.stl --op union|difference|intersection [--move-b X,Y,Z]
  text     in.stl out.stl --text "ABC" --size 8 --depth 1 --at X,Y --mode emboss|deboss [--font "Liberation Sans:style=Bold"] [--face top|bottom]
  textpart in.stl text.stl --text "ABC" ...         same, but writes the text as a separate part (for 2-color --assemble)
  split    in.stl outdir/                          one STL per disconnected body
  repair   in.stl out.stl                          merge verts, fix normals, fill holes
  convert  in.(obj|3mf|ply|off|step|stp) out.stl
  preview  in.stl out.png [--view iso|top|front]   OpenSCAD render for a quick visual check
"""
import argparse, os, subprocess, sys, tempfile
import numpy as np
import trimesh

BED = (180.0, 180.0, 180.0)


def load(p):
    ext = os.path.splitext(p)[1].lower()
    if ext in (".step", ".stp"):
        from build123d import import_step, export_stl
        t = tempfile.mktemp(suffix=".stl"); export_stl(import_step(p), t); p = t
    m = trimesh.load(p, force="mesh")
    return m


def save(m, p):
    os.makedirs(os.path.dirname(os.path.abspath(p)), exist_ok=True)
    m.export(p); print("wrote", p, fmt(m))


def fmt(m):
    e = m.extents
    return f"[{e[0]:.1f} x {e[1]:.1f} x {e[2]:.1f} mm, watertight={m.is_watertight}]"


def drop(m):
    b = m.bounds; m.apply_translation((-(b[0][0] + b[1][0]) / 2, -(b[0][1] + b[1][1]) / 2, -b[0][2])); return m


def bool_op(a, b, op):
    r = trimesh.boolean.boolean_manifold([a, b], op)
    return r


def text_mesh(text, size, depth, font):
    scad = f'linear_extrude({depth}) text("{text}", size={size}, font="{font}", halign="center", valign="center", $fn=48);'
    s = tempfile.mktemp(suffix=".scad"); o = tempfile.mktemp(suffix=".stl")
    open(s, "w").write(scad)
    subprocess.run(["openscad", "--backend=manifold", "-o", o, s], check=True, capture_output=True)
    return trimesh.load(o, force="mesh")


def place_text(m, a):
    t = text_mesh(a.text, a.size, a.depth + (0.4 if a.mode == "deboss" else 0), a.font)
    x, y = (float(v) for v in a.at.split(",")) if a.at else ((m.bounds[0][0] + m.bounds[1][0]) / 2, (m.bounds[0][1] + m.bounds[1][1]) / 2)
    if a.face == "bottom":
        t.apply_transform(trimesh.transformations.rotation_matrix(np.pi, (1, 0, 0)))
        zt = m.bounds[0][2] + (a.depth if a.mode == "deboss" else 0) - t.bounds[1][2]
    else:
        zt = m.bounds[1][2] - (a.depth if a.mode == "deboss" else 0) - t.bounds[0][2]
        if a.mode == "emboss":
            zt -= 0.01  # tiny overlap so union fuses
    t.apply_translation((x - (t.bounds[0][0] + t.bounds[1][0]) / 2, y - (t.bounds[0][1] + t.bounds[1][1]) / 2, zt))
    return t


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd"); ap.add_argument("paths", nargs="+")
    for k in ("--factor", "--fit", "--x", "--y", "--z", "--d", "--h", "--z0", "--size", "--depth"):
        ap.add_argument(k)
    ap.add_argument("--axis", default="z"); ap.add_argument("--keep", default="below")
    ap.add_argument("--at"); ap.add_argument("--op", default="union"); ap.add_argument("--move-b")
    ap.add_argument("--text"); ap.add_argument("--mode", default="emboss"); ap.add_argument("--face", default="top")
    ap.add_argument("--font", default="Liberation Sans:style=Bold"); ap.add_argument("--view", default="iso")
    a = ap.parse_args(); c = a.cmd; P = a.paths

    if c == "info":
        m = load(P[0]); e = m.extents
        fits = all(e[i] <= BED[i] for i in range(3))
        print(f"size: {e[0]:.2f} x {e[1]:.2f} x {e[2]:.2f} mm\nvolume: {m.volume/1000:.2f} cm3 (~{m.volume/1000*1.24:.1f} g PLA solid)\n"
              f"triangles: {len(m.faces)}\nwatertight: {m.is_watertight}\nbodies: {len(m.split(only_watertight=False))}\n"
              f"fits A1 mini (180^3): {fits}\nbounds: {m.bounds.tolist()}")
    elif c == "scale":
        m = load(P[0])
        if a.factor: m.apply_scale(float(a.factor))
        elif a.fit: m.apply_scale(float(a.fit) / max(m.extents))
        elif a.size:
            v = [float(x) for x in a.size.split(",")]
            if len(v) == 3: m.apply_scale(np.array(v) / m.extents)
            else: m.apply_scale(v[0] / max(m.extents))
        save(drop(m), P[1])
    elif c == "rotate":
        m = load(P[0])
        for ax, val in (((1, 0, 0), a.x), ((0, 1, 0), a.y), ((0, 0, 1), a.z)):
            if val: m.apply_transform(trimesh.transformations.rotation_matrix(np.radians(float(val)), ax))
        save(drop(m), P[1])
    elif c == "mirror":
        m = load(P[0]); s = {"x": (-1, 1, 1), "y": (1, -1, 1), "z": (1, 1, -1)}[a.axis]
        M = np.diag(list(s) + [1]); m.apply_transform(M)  # trimesh flips winding for det<0
        m.fix_normals(); save(drop(m), P[1])
    elif c == "flat":
        m = load(P[0]); T = trimesh.poses.compute_stable_poses(m, n_samples=1)[0][0]
        m.apply_transform(T); save(drop(m), P[1])
    elif c == "cut":
        m = load(P[0]); z = float(a.z); b = m.bounds; pad = 10
        def box(z0, z1):
            bx = trimesh.creation.box(extents=(b[1][0]-b[0][0]+2*pad, b[1][1]-b[0][1]+2*pad, z1-z0))
            bx.apply_translation(((b[0][0]+b[1][0])/2, (b[0][1]+b[1][1])/2, (z0+z1)/2)); return bx
        below = bool_op(m, box(b[0][2]-pad, z), "intersection")
        above = bool_op(m, box(z, b[1][2]+pad), "intersection")
        if a.keep == "below": save(below, P[1])
        elif a.keep == "above": save(drop(above), P[1])
        else:
            r, ext = os.path.splitext(P[1]); save(below, r + "_a" + ext); save(drop(above), r + "_b" + ext)
    elif c == "hole":
        m = load(P[0]); x, y = (float(v) for v in a.at.split(","))
        h = float(a.h) if a.h else 1000.0; z0 = float(a.z0) if a.z0 else m.bounds[0][2] - 1
        cyl = trimesh.creation.cylinder(radius=float(a.d) / 2, height=h, sections=64)
        cyl.apply_translation((x, y, z0 + h / 2))
        save(bool_op(m, cyl, "difference"), P[1])
    elif c == "boolean":
        A = load(P[0]); B = load(P[1])
        if a.move_b: B.apply_translation([float(v) for v in a.move_b.split(",")])
        save(bool_op(A, B, a.op), P[2])
    elif c in ("text", "textpart"):
        m = load(P[0]); a.size = float(a.size or 8); a.depth = float(a.depth or 1)
        t = place_text(m, a)
        if c == "textpart":
            save(t, P[1])
        else:
            save(bool_op(m, t, "union" if a.mode == "emboss" else "difference"), P[1])
    elif c == "split":
        m = load(P[0]); os.makedirs(P[1], exist_ok=True)
        for i, b in enumerate(m.split(only_watertight=False)): save(drop(b), os.path.join(P[1], f"body_{i+1}.stl"))
    elif c == "repair":
        m = load(P[0]); m.merge_vertices(); m.update_faces(m.nondegenerate_faces()); m.update_faces(m.unique_faces())
        trimesh.repair.fix_normals(m); trimesh.repair.fill_holes(m); save(m, P[1])
    elif c == "convert":
        save(load(P[0]), P[1])
    elif c == "preview":
        cams = {"iso": "--camera=0,0,0,55,0,25,0", "top": "--camera=0,0,0,0,0,0,0", "front": "--camera=0,0,0,90,0,0,0"}
        s = tempfile.mktemp(suffix=".scad"); src = os.path.abspath(P[0])
        if os.path.splitext(src)[1].lower() != ".stl":
            t = tempfile.mktemp(suffix=".stl"); load(src).export(t); src = t
        open(s, "w").write(f'color("#2ea44f") import("{src}");')
        subprocess.run(["openscad", "--backend=manifold", "-o", P[1], "--render", "--viewall", "--autocenter",
                        cams.get(a.view, cams["iso"]), "--imgsize=900,700", "--colorscheme=Tomorrow", s],
                       check=True, capture_output=True)
        print("wrote", P[1])
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
