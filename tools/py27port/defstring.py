"""Rewrite every f-string in a Python 3 source file as a str.format call so the
file parses on Python 2.7. Usage: defstring.py <in.py> <out.py>"""
import ast
import sys


import unicodedata


def _escape_char(ch):
    cp = ord(ch)
    if ch == "\n":
        return "\\n"
    if ch == "\r":
        return "\\r"
    if ch == "\t" or (0x20 <= cp < 0x7F):
        return ch
    if cp < 0x100:
        return "\\x%02x" % cp
    if unicodedata.category(ch)[0] in "CZ" and ch != " ":
        return "\\u%04x" % cp if cp <= 0xFFFF else "\\U%08x" % cp
    return ch


def _lit(text):
    text = "".join(_escape_char(c) for c in text)
    return text.replace("{", "{{").replace("}", "}}")


def _format_call(node, src):
    parts = []
    args = []
    for v in node.values:
        if isinstance(v, ast.Constant):
            parts.append(_lit(v.value))
        else:
            expr = ast.get_source_segment(src, v.value)
            conv = {-1: "", 115: "!s", 114: "!r", 97: "!a"}[v.conversion]
            spec = ""
            if v.format_spec is not None:
                spec = ":" + "".join(
                    s.value if isinstance(s, ast.Constant)
                    else "{" + str(len(args) + _spec_args(v.format_spec, args, src)) + "}"
                    for s in v.format_spec.values
                )
            parts.append("{%d%s%s}" % (len(args), conv, spec))
            args.append(expr)
    template = "".join(parts)
    quote = '"' if '"' not in template or "'" in template else "'"
    if "\n" in template:
        body = template.replace("\\", "\\\\").replace(quote, "\\" + quote).replace("\n", "\\n")
    else:
        body = template.replace("\\", "\\\\").replace(quote, "\\" + quote)
    return "%s%s%s.format(%s)" % (quote, body, quote, ", ".join(args))


def _spec_args(spec_node, args, src):
    added = 0
    for s in spec_node.values:
        if isinstance(s, ast.FormattedValue):
            args.append(ast.get_source_segment(src, s.value))
            added += 1
    return added - 1


def convert(src):
    tree = ast.parse(src)
    lines = src.splitlines(keepends=True)
    offsets = [0]
    for ln in lines:
        offsets.append(offsets[-1] + len(ln))
    spans = []
    for node in ast.walk(tree):
        if isinstance(node, ast.JoinedStr):
            spans.append(node)
    # outermost first: drop any JoinedStr nested inside another one's span
    spans.sort(key=lambda n: (n.lineno, n.col_offset))
    kept = []
    for n in spans:
        if kept and (n.lineno, n.col_offset) < (kept[-1].end_lineno, kept[-1].end_col_offset) and (n.lineno, n.col_offset) >= (kept[-1].lineno, kept[-1].col_offset):
            continue
        kept.append(n)
    out = src
    for n in reversed(kept):
        start = offsets[n.lineno - 1] + len(lines[n.lineno - 1][: n.col_offset].encode("utf-8").decode("utf-8", "ignore"))
        start = offsets[n.lineno - 1] + _col(lines[n.lineno - 1], n.col_offset)
        end = offsets[n.end_lineno - 1] + _col(lines[n.end_lineno - 1], n.end_col_offset)
        out = out[:start] + _format_call(n, src) + out[end:]
    return out, len(kept)


def _col(line, byte_col):
    return len(line.encode("utf-8")[:byte_col].decode("utf-8", "ignore"))


if __name__ == "__main__":
    src = open(sys.argv[1], encoding="utf-8").read()
    out, n = convert(src)
    ast.parse(out)
    open(sys.argv[2], "w", encoding="utf-8").write(out)
    print("%s: %d f-strings rewritten" % (sys.argv[1], n))
