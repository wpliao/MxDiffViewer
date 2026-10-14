# PROTOTYPE - throwaway. Diff two per-document MDL exports and write a self-contained HTML report.
# usage: python diff.py <old-export-dir> <new-export-dir> <report.html> [title]
import difflib, html, os, re, sys

old_dir, new_dir, out = sys.argv[1], sys.argv[2], sys.argv[3]
title = sys.argv[4] if len(sys.argv) > 4 else f"{os.path.basename(old_dir)} → {os.path.basename(new_dir)}"

LAYOUT_LINE = re.compile(r"^\s*@(position|curve|merge|anchor|start)\(.*\)\s*$", re.I)
LAYOUT_ARG = re.compile(r",?\s*(position|size):\s*\(-?\d+,\s*-?\d+\)")

def normalise(text):
    lines = []
    for line in text.splitlines():
        if LAYOUT_LINE.match(line):
            continue
        if line.lstrip().startswith("@annotation("):
            line = LAYOUT_ARG.sub("", line)
        lines.append(line)
    return lines

def load(root):
    docs = {}
    for dirpath, _, files in os.walk(root):
        for f in files:
            p = os.path.join(dirpath, f)
            key = os.path.relpath(p, root).replace("\\", "/")[:-4]  # type/Qualified.Name
            docs[key] = open(p, encoding="utf-8").read()
    return docs

old, new = load(old_dir), load(new_dir)
rows = []  # (kind, type, name, diff_lines)
layout_only = []
for key in sorted(old.keys() | new.keys()):
    ty, name = key.split("/", 1)
    a, b = old.get(key), new.get(key)
    if a == b:
        continue
    na, nb = normalise(a or ""), normalise(b or "")
    if a is not None and b is not None and na == nb:
        layout_only.append(key)
        continue
    kind = "added" if a is None else "removed" if b is None else "modified"
    diff = list(difflib.unified_diff(na, nb, lineterm="", n=3))[2:]
    rows.append((kind, ty, name, diff))

def module(name):
    return name.split(".", 1)[0] if "." in name else "(project)"

counts = {k: sum(1 for r in rows if r[0] == k) for k in ("added", "modified", "removed")}
parts = []
for kind, ty, name, diff in sorted(rows, key=lambda r: (module(r[2]), r[1], r[2])):
    plus = sum(1 for l in diff if l.startswith("+"))
    minus = sum(1 for l in diff if l.startswith("-"))
    body = []
    for l in diff:
        cls = "add" if l.startswith("+") else "del" if l.startswith("-") else "hunk" if l.startswith("@@") else "ctx"
        body.append(f'<div class="{cls}">{html.escape(l) or "&nbsp;"}</div>')
    parts.append(
        f'<details class="doc {kind}" data-module="{html.escape(module(name))}"><summary>'
        f'<span class="badge {kind}">{kind}</span> <span class="ty">{ty}</span> <b>{html.escape(name)}</b>'
        f' <span class="stat"><span class="p">+{plus}</span> <span class="m">−{minus}</span></span></summary>'
        f'<pre>{"".join(body)}</pre></details>')

doc = f"""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>MDL diff prototype</title><style>
:root{{--bg:#fff;--fg:#1d1d1f;--mut:#6b6b70;--line:#e3e3e6;--add:#e6f6ea;--addfg:#116329;--del:#fdecec;--delfg:#a40e26;--hunk:#eef3fb}}
@media (prefers-color-scheme:dark){{:root{{--bg:#16171a;--fg:#e8e8ea;--mut:#9a9aa1;--line:#2c2d31;--add:#12301c;--addfg:#7ee2a0;--del:#3a1518;--delfg:#ff9aa5;--hunk:#1c2433}}}}
body{{background:var(--bg);color:var(--fg);font:14px/1.45 system-ui,sans-serif;margin:0 auto;max-width:1100px;padding:16px}}
h1{{font-size:20px;margin:0 0 4px}} .sub{{color:var(--mut);margin-bottom:16px}}
.doc{{border:1px solid var(--line);border-radius:8px;margin:6px 0}} summary{{cursor:pointer;padding:8px 10px}}
.badge{{font-size:11px;padding:1px 6px;border-radius:4px;text-transform:uppercase}} .badge.added{{background:var(--add);color:var(--addfg)}}
.badge.removed{{background:var(--del);color:var(--delfg)}} .badge.modified{{background:var(--hunk)}}
.ty{{color:var(--mut);font-size:12px}} .stat{{float:right;font-family:ui-monospace,monospace}} .p{{color:var(--addfg)}} .m{{color:var(--delfg)}}
pre{{margin:0;overflow-x:auto;font:12px/1.5 ui-monospace,Consolas,monospace;border-top:1px solid var(--line)}}
pre div{{padding:0 10px;white-space:pre}} .add{{background:var(--add)}} .del{{background:var(--del)}} .hunk{{background:var(--hunk);color:var(--mut)}}
.note{{color:var(--mut);font-size:13px}}
</style></head><body>
<h1>{html.escape(title)}</h1>
<div class="sub">PROTOTYPE · {counts['added']} added · {counts['modified']} modified · {counts['removed']} removed · {len(layout_only)} layout-only changes hidden</div>
{''.join(parts) or '<p>No model changes.</p>'}
<p class="note">Layout-only: {html.escape(', '.join(layout_only)) or 'none'}</p>
</body></html>"""
open(out, "w", encoding="utf-8").write(doc)
print(f"{title}: +{counts['added']} ~{counts['modified']} -{counts['removed']}, layout-only {len(layout_only)} -> {out}")
