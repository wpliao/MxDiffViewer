# PROTOTYPE - throwaway. Export one git revision of a Mendix project to one MDL file per document.
# usage: python export.py <repo> <rev> <outdir>
import json, os, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor

repo, rev, outdir = sys.argv[1], sys.argv[2], sys.argv[3]
sha = subprocess.check_output(["git", "-C", repo, "rev-parse", "--short", rev], text=True).strip()
wt = os.path.join(os.path.dirname(os.path.abspath(repo)), "wt", sha)
if not os.path.isdir(wt):
    subprocess.check_call(["git", "-C", repo, "worktree", "add", "-q", "--detach", wt, sha])
mpr = next(os.path.join(wt, f) for f in os.listdir(wt) if f.endswith(".mpr"))

TYPE_MAP = {"navprofile": "navigation"}
SKIP = {"navigation", "systemoverview"}

t0 = time.time()
tree = json.loads(subprocess.check_output(["mxcli", "project-tree", "-p", mpr], stderr=subprocess.DEVNULL))
items = []
def walk(n):
    ty = n.get("type")
    if n.get("describable") and ty not in SKIP:
        items.append((TYPE_MAP.get(ty, ty), n["qualifiedName"]))
    for ch in n.get("children", []):
        walk(ch)
for n in tree:
    walk(n)

def describe(item):
    ty, qn = item
    p = subprocess.run(["mxcli", "describe", "-p", mpr, ty, qn], capture_output=True, text=True, encoding="utf-8")
    path = os.path.join(outdir, ty, qn + ".mdl")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(p.stdout if p.returncode == 0 else f"-- DESCRIBE FAILED rc={p.returncode}\n{p.stderr}")
    return p.returncode

describe(items[0])  # warm the .mxcli catalog cache before going parallel
with ThreadPoolExecutor(8) as ex:
    rcs = list(ex.map(describe, items))
print(f"{sha}: {len(items)} documents, {sum(1 for r in rcs if r)} failed, {time.time()-t0:.0f}s -> {outdir}")
