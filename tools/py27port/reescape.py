"""Re-escape raw control, format and invisible characters inside string
literals of an already converted file (tokenize-based; raw-prefixed literals
are reported, not changed). Usage: reescape.py <file> [<file>...]"""
import io, sys, tokenize, unicodedata

def esc(ch):
    cp = ord(ch)
    if ch in "\t\n\r" or (0x20 <= cp < 0x7F):
        return ch
    if cp < 0x100:
        return "\\x%02x" % cp
    if unicodedata.category(ch)[0] in "CZ" and ch != " ":
        return "\\u%04x" % cp if cp <= 0xFFFF else "\\U%08x" % cp
    return ch

for path in sys.argv[1:]:
    src = open(path, encoding="utf-8").read()
    toks = list(tokenize.generate_tokens(io.StringIO(src).readline))
    lines = src.splitlines(keepends=True)
    offs = [0]
    for ln in lines: offs.append(offs[-1] + len(ln))
    edits, raw_hits = [], 0
    for t in toks:
        if t.type != tokenize.STRING: continue
        body = t.string
        if not any(esc(c) != c for c in body): continue
        prefix = body[: len(body) - len(body.lstrip("rRbBuUfF"))]
        if "r" in prefix.lower():
            raw_hits += 1; continue
        new = "".join(esc(c) for c in body)
        s = offs[t.start[0] - 1] + t.start[1]; e = offs[t.end[0] - 1] + t.end[1]
        edits.append((s, e, new))
    for s, e, new in sorted(edits, reverse=True):
        src = src[:s] + new + src[e:]
    if edits: open(path, "w", encoding="utf-8").write(src)
    print("%s: %d literals re-escaped%s" % (path.rsplit("/", 1)[-1], len(edits), ", RAW-STRING HITS %d" % raw_hits if raw_hits else ""))
