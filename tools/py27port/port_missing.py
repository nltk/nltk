"""Port every nltk module the tree imports but lacks, from the 3.10 tree, until none is missing."""
import os, re, subprocess, sys, glob
A = "/Users/alvas/git-stuff/nltk-devsec-merge/nltk"
PORT = os.path.join(os.path.dirname(__file__), "port_file.py")
def exists(mod):
    rel = mod.replace(".", "/")
    return os.path.exists("nltk/%s.py" % rel) or os.path.isdir("nltk/%s" % rel)
def in3(mod):
    rel = mod.replace(".", "/")
    if os.path.exists("%s/%s.py" % (A, rel)): return "%s/%s.py" % (A, rel), "nltk/%s.py" % rel
    if os.path.isdir("%s/%s" % (A, rel)): return "%s/%s" % (A, rel), "nltk/%s" % rel
    return None
for rnd in range(6):
    missing = set()
    for f in glob.glob("nltk/**/*.py", recursive=True):
        if "/test/" in f: continue
        pkg = f[len("nltk/"):].rsplit("/", 1)[0].replace("/", ".") if "/" in f[len("nltk/"):] else ""
        for line in open(f, encoding="utf-8"):
            m = re.match(r"\s*from nltk\.([\w.]+) import", line) or re.match(r"\s*import nltk\.([\w.]+)", line)
            if m:
                mod = m.group(1)
                if not exists(mod):
                    # 'from nltk.a import b' may name a submodule b
                    parts = mod.split(".")
                    if not exists(".".join(parts[:-1])) or not in3(mod) and len(parts) > 1 and exists(".".join(parts[:-1])):
                        pass
                    missing.add(mod)
            m = re.match(r"\s*from \.([\w.]*) import ([\w, ]+)", line)
            if m and pkg:
                base = (pkg + "." + m.group(1)).strip(".") if m.group(1) else pkg
                if m.group(1) and not exists(base): missing.add(base)
                if not m.group(1):
                    for name in m.group(2).replace(" ", "").split(","):
                        if name and in3(base + "." + name) and not exists(base + "." + name): missing.add(base + "." + name)
    missing = {m for m in missing if in3(m)}
    if not missing:
        print("round %d: nothing missing" % rnd); break
    print("round %d: porting %d missing modules: %s" % (rnd, len(missing), ", ".join(sorted(missing))[:300]))
    for mod in sorted(missing):
        src, dst = in3(mod)
        if os.path.isdir(src):
            os.makedirs(dst, exist_ok=True)
            for sf in glob.glob(src + "/*.py"):
                subprocess.run([sys.executable, PORT, sf, os.path.join(dst, os.path.basename(sf))], capture_output=True)
        else:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            r = subprocess.run([sys.executable, PORT, src, dst], capture_output=True, text=True)
            if r.returncode: print("  PORT FAIL", mod, r.stderr.strip().splitlines()[-1][:100] if r.stderr else "")
