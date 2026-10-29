# Import every nltk module in its own subprocess on this interpreter; group the errors.
from __future__ import print_function
import os, subprocess, sys, collections
root = "nltk"
mods = []
for dp, dn, fn in os.walk(root):
    dn[:] = [d for d in dn if d != "test" and not d.startswith("__")]
    for f in fn:
        if f.endswith(".py"):
            m = os.path.join(dp, f)[:-3].replace(os.sep, ".")
            if m.endswith(".__init__"): m = m[:-9]
            mods.append(m)
errs = collections.defaultdict(list); ok = 0
for m in sorted(mods):
    p = subprocess.Popen([sys.executable, "-c", "import %s" % m], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate()
    if p.returncode == 0: ok += 1; continue
    last = err.decode("utf-8", "replace").strip().splitlines()
    msg = last[-1] if last else "?"
    where = [l for l in last if l.strip().startswith("File \"nltk")]
    loc = where[-1].strip().split(",")[0].replace("File ", "") if where else "?"
    errs[msg].append((m, loc))
print("modules: %d, import OK: %d, failing: %d" % (len(mods), ok, len(mods) - ok))
for msg, ms in sorted(errs.items(), key=lambda kv: -len(kv[1])):
    print("%4d  %s" % (len(ms), msg[:110]))
    print("        e.g. %s at %s" % (ms[0][0], ms[0][1]))
