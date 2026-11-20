#!/usr/bin/env python3
"""Repair a 3MF written by the Bambu Studio CLI so the GUI can open it.

CLI 02.0x writes list values such as compatible_printers into
Metadata/model_settings.config as value=""Bambu Lab A1 mini 0.4 nozzle"" (unescaped
quotes). The GUI then reports "Model dosyasinin yuklenmesi basarisiz oldu".
This escapes inner quotes and, optionally, sets printer_model_id in slice_info.

Usage: fix_3mf.py in.3mf [out.3mf] [--model-id N1]
"""
import re, sys, zipfile, shutil, os, tempfile

ATTR = re.compile(r'(value=")(.*)("\s*/>)')

def fix_xml(text):
    out = []
    for line in text.splitlines(keepends=True):
        m = ATTR.search(line)
        if m and '"' in m.group(2):
            inner = m.group(2).replace('&', '&amp;').replace('"', '&quot;')
            inner = inner.replace('&amp;quot;', '&quot;').replace('&amp;amp;', '&amp;')
            line = line[:m.start(2)] + inner + line[m.end(2):]
        out.append(line)
    return ''.join(out)

def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    model_id = None
    if '--model-id' in sys.argv:
        model_id = sys.argv[sys.argv.index('--model-id') + 1]
        args = [a for a in args if a != model_id]
    src = args[0]; dst = args[1] if len(args) > 1 else src
    tmp = tempfile.mktemp(suffix='.3mf')
    changed = 0
    with zipfile.ZipFile(src) as zin, zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename.endswith('.config'):
                t = data.decode('utf-8')
                n = fix_xml(t)
                if model_id and item.filename.endswith('slice_info.config'):
                    n = n.replace('key="printer_model_id" value=""', f'key="printer_model_id" value="{model_id}"')
                if n != t:
                    changed += 1
                data = n.encode('utf-8')
            zout.writestr(item, data)
    shutil.move(tmp, dst)
    print(f"fixed {changed} config file(s) -> {dst}")

if __name__ == '__main__':
    main()
