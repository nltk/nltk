"""Mechanical Python 3 to 2.7-compatible source rewrites, comments preserved:
f-strings to str.format, ``raise X from Y`` to six.raise_from, ``yield from``
to a loop, annotations stripped, bare ``super()`` qualified, the future header
and the six imports added. Usage: py2pass.py <in.py> <out.py>"""
import ast
import re
import sys

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from defstring import convert as defstring


def _offsets(src):
    lines = src.splitlines(keepends=True)
    offs = [0]
    for ln in lines:
        offs.append(offs[-1] + len(ln))
    return lines, offs


def _pos(lines, offs, lineno, col):
    line = lines[lineno - 1]
    return offs[lineno - 1] + len(line.encode("utf-8")[:col].decode("utf-8", "ignore"))


def _apply(src, edits):
    for start, end, rep in sorted(edits, reverse=True):
        src = src[:start] + rep + src[end:]
    return src


def strip_annotations(src):
    tree = ast.parse(src)
    lines, offs = _offsets(src)
    edits = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.returns is not None:
                # from the end of the ')' to the end of the annotation
                start = _pos(lines, offs, node.returns.lineno, node.returns.col_offset)
                end = _pos(lines, offs, node.returns.end_lineno, node.returns.end_col_offset)
                head = src[:start]
                arrow = head.rfind("->")
                edits.append((arrow, end, ""))
            args = node.args
            for a in args.posonlyargs + args.args + args.kwonlyargs + [x for x in (args.vararg, args.kwarg) if x]:
                if a.annotation is not None:
                    start = _pos(lines, offs, a.lineno, a.col_offset) + len(a.arg)
                    end = _pos(lines, offs, a.annotation.end_lineno, a.annotation.end_col_offset)
                    edits.append((start, end, ""))
        elif isinstance(node, ast.AnnAssign):
            start = _pos(lines, offs, node.target.end_lineno, node.target.end_col_offset)
            end = _pos(lines, offs, node.annotation.end_lineno, node.annotation.end_col_offset)
            if node.value is None:
                s0 = _pos(lines, offs, node.lineno, node.col_offset)
                e0 = _pos(lines, offs, node.end_lineno, node.end_col_offset)
                edits.append((s0, e0, "%s = None" % src[s0:start]))
            else:
                edits.append((start, end, ""))
    return _apply(src, edits), len(edits)


def raise_from(src):
    tree = ast.parse(src)
    lines, offs = _offsets(src)
    edits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Raise) and node.cause is not None:
            s = _pos(lines, offs, node.lineno, node.col_offset)
            e = _pos(lines, offs, node.end_lineno, node.end_col_offset)
            exc = ast.get_source_segment(src, node.exc)
            if isinstance(node.cause, ast.Constant) and node.cause.value is None:
                edits.append((s, e, "raise %s" % exc))
            else:
                edits.append((s, e, "six.raise_from(%s, %s)" % (exc, ast.get_source_segment(src, node.cause))))
    return _apply(src, edits), len(edits)


def yield_from(src):
    tree = ast.parse(src)
    lines, offs = _offsets(src)
    edits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.YieldFrom):
            s = _pos(lines, offs, node.lineno, node.col_offset)
            e = _pos(lines, offs, node.end_lineno, node.end_col_offset)
            indent = " " * node.col_offset
            inner = ast.get_source_segment(src, node.value.value)
            edits.append((s, e, "for _yf_item in %s:\n%s    yield _yf_item" % (inner, indent)))
    return _apply(src, edits), len(edits)


def qualify_super(src):
    tree = ast.parse(src)
    lines, offs = _offsets(src)
    edits = []
    stack = []

    def visit(node, cls, func):
        if isinstance(node, ast.ClassDef):
            cls = node.name
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            func = node
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == "super" and not node.args and cls and func and func.args.args):
            s = _pos(lines, offs, node.lineno, node.col_offset)
            e = _pos(lines, offs, node.end_lineno, node.end_col_offset)
            edits.append((s, e, "super(%s, %s)" % (cls, func.args.args[0].arg)))
        for child in ast.iter_child_nodes(node):
            visit(child, cls, func)

    visit(tree, None, None)
    return _apply(src, edits), len(edits)


FUTURE = "from __future__ import absolute_import, division, print_function, unicode_literals\n"


def header(src):
    """Insert the future import and ``import six`` after the module docstring."""
    tree = ast.parse(src)
    lines, offs = _offsets(src)
    body = tree.body
    at = 0
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str):
        at = _pos(lines, offs, body[0].end_lineno, body[0].end_col_offset)
        at = src.index("\n", at) + 1
    block = FUTURE
    if "import six" not in src:
        block += "import six\n"
    if "# -*- coding" not in src[:200]:
        src = "# -*- coding: utf-8 -*-\n" + src
        at += len("# -*- coding: utf-8 -*-\n")
    return src[:at] + block + src[at:], 1


def run(src):
    report = {}
    for name, fn in (("fstrings", defstring), ("annotations", strip_annotations), ("raise_from", raise_from),
                     ("yield_from", yield_from), ("super", qualify_super), ("header", header)):
        src, n = fn(src)
        report[name] = n
        ast.parse(src)
    return src, report


if __name__ == "__main__" and len(sys.argv) == 3:
    src = open(sys.argv[1], encoding="utf-8").read()
    out, report = run(src)
    open(sys.argv[2], "w", encoding="utf-8").write(out)
    print("%s: %s" % (sys.argv[1].rsplit("/", 1)[-1], ", ".join("%s=%d" % kv for kv in report.items())))


def numeric_underscores(src):
    import tokenize, io
    edits = []
    lines, offs = _offsets(src)
    for tok in tokenize.generate_tokens(io.StringIO(src).readline):
        if tok.type == tokenize.NUMBER and "_" in tok.string:
            s = _pos(lines, offs, tok.start[0], len(lines[tok.start[0] - 1][: tok.start[1]].encode("utf-8")))
            e = s + len(tok.string)
            edits.append((s, e, tok.string.replace("_", "")))
    return _apply(src, edits), len(edits)


def starred(src):
    """``[a, *b]`` / ``(a, *b)`` / ``f(a, *b, c)`` with a star not in last
    position: rewrite literals as concatenations, calls as ``*(...)``."""
    tree = ast.parse(src)
    lines, offs = _offsets(src)
    edits = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.List, ast.Tuple, ast.Set)) and any(isinstance(e, ast.Starred) for e in node.elts):
            s = _pos(lines, offs, node.lineno, node.col_offset)
            e = _pos(lines, offs, node.end_lineno, node.end_col_offset)
            parts, run = [], []
            for el in node.elts:
                if isinstance(el, ast.Starred):
                    if run:
                        parts.append("[%s]" % ", ".join(run)); run = []
                    parts.append("list(%s)" % ast.get_source_segment(src, el.value))
                else:
                    run.append(ast.get_source_segment(src, el))
            if run:
                parts.append("[%s]" % ", ".join(run))
            joined = " + ".join(parts)
            wrap = {ast.List: "%s", ast.Tuple: "tuple(%s)", ast.Set: "set(%s)"}[type(node)]
            edits.append((s, e, wrap % joined))
        elif isinstance(node, ast.Call):
            stars = [i for i, a in enumerate(node.args) if isinstance(a, ast.Starred)]
            if stars and (len(stars) > 1 or stars[0] != len(node.args) - 1):
                # py2 allows one *args only in last position: fold into one list
                first = node.args[0]
                last = node.args[-1]
                s = _pos(lines, offs, first.lineno, first.col_offset)
                e = _pos(lines, offs, last.end_lineno, last.end_col_offset)
                parts, run = [], []
                for a in node.args:
                    if isinstance(a, ast.Starred):
                        if run:
                            parts.append("[%s]" % ", ".join(run)); run = []
                        parts.append("list(%s)" % ast.get_source_segment(src, a.value))
                    else:
                        run.append(ast.get_source_segment(src, a))
                if run:
                    parts.append("[%s]" % ", ".join(run))
                edits.append((s, e, "*(%s)" % " + ".join(parts)))
    return _apply(src, edits), len(edits)


def kwonly(src):
    """``def f(a, *, b=1)`` becomes ``def f(a, **_kw)`` with the keyword-only
    names popped from ``_kw`` at the top of the body (unknown names raise)."""
    tree = ast.parse(src)
    lines, offs = _offsets(src)
    edits = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.args.kwonlyargs:
            a = node.args
            if a.vararg is not None:
                continue  # def f(*args, b=1): handled by hand
            names = [k.arg for k in a.kwonlyargs]
            defaults = [ast.get_source_segment(src, d) if d is not None else None for d in a.kw_defaults]
            # the span from after the last positional arg to the end of the kwonly list
            star_tok_start = None
            if a.args:
                prev = a.args[-1]
                after = _pos(lines, offs, prev.end_lineno, prev.end_col_offset)
                if a.defaults and len(a.defaults) >= 1:
                    d = a.defaults[-1]
                    after = max(after, _pos(lines, offs, d.end_lineno, d.end_col_offset))
            else:
                after = src.index("(", _pos(lines, offs, node.lineno, node.col_offset)) + 1
            last = a.kwonlyargs[-1]
            end = _pos(lines, offs, last.end_lineno, last.end_col_offset)
            if a.kw_defaults[-1] is not None:
                d = a.kw_defaults[-1]
                end = max(end, _pos(lines, offs, d.end_lineno, d.end_col_offset))
            sep = ", " if a.args else ""
            kw_name = "_kw" if a.kwarg is None else a.kwarg.arg
            new_sig = "%s**%s" % (sep, kw_name) if a.kwarg is None else sep.rstrip(", ") and ""
            if a.kwarg is None:
                edits.append((after, end, new_sig))
            else:
                # drop the kwonly list; the existing **kwargs catches them
                kwarg_start = _pos(lines, offs, a.kwarg.lineno, a.kwarg.col_offset)
                star_pos = src.rfind("**", after, kwarg_start)
                edits.append((after, star_pos, sep if a.args else ""))
            body0 = node.body[0]
            indent = " " * body0.col_offset
            ins = _pos(lines, offs, body0.lineno, body0.col_offset)
            # keep a docstring first
            if isinstance(body0, ast.Expr) and isinstance(body0.value, ast.Constant) and isinstance(body0.value.value, str):
                ins = _pos(lines, offs, body0.end_lineno, body0.end_col_offset)
                ins = src.index("\n", ins) + 1
                pre = indent
            else:
                pre = ""
            stmts = []
            for n, d in zip(names, defaults):
                if d is None:
                    stmts.append("%s = %s.pop(%r)" % (n, kw_name, n))
                else:
                    stmts.append("%s = %s.pop(%r, %s)" % (n, kw_name, n, d))
            if a.kwarg is None:
                stmts.append("if %s:\n%s    raise TypeError(\"unexpected keyword argument(s): %%s\" %% \", \".join(sorted(%s)))" % (kw_name, indent, kw_name))
            text = "".join(("%s%s\n" % (indent, s)) for s in stmts)
            if pre:
                edits.append((ins, ins, text))
            else:
                edits.append((ins, ins, text.lstrip(" ") if False else text[len(indent):] ))
    return _apply(src, edits), len(edits)


def run2(src):
    src, report = run(src)
    for name, fn in (("underscores", numeric_underscores), ("starred", starred), ("kwonly", kwonly)):
        src, n = fn(src)
        report[name] = n
        ast.parse(src)
    return src, report


if __name__ == "__main__" and len(sys.argv) > 3 and sys.argv[3] == "--full":
    src = open(sys.argv[1], encoding="utf-8").read()
    out, report = run2(src)
    open(sys.argv[2], "w", encoding="utf-8").write(out)
    print("FULL %s: %s" % (sys.argv[1].rsplit("/", 1)[-1], ", ".join("%s=%d" % kv for kv in report.items())))


if __name__ == "__main__" and len(sys.argv) > 3 and sys.argv[3] == "--basic":
    src = open(sys.argv[1], encoding="utf-8").read()
    out, report = run(src)
    out, n = numeric_underscores(out)
    report["underscores"] = n
    ast.parse(out)
    open(sys.argv[2], "w", encoding="utf-8").write(out)
    print("BASIC %s: %s" % (sys.argv[1].rsplit("/", 1)[-1], ", ".join("%s=%d" % kv for kv in report.items())))


def kwonly_decorator(src):
    """Keyword-only parameters without ``*args``: drop the ``*`` separator and
    guard the positional count with ``@keyword_only(n)`` from nltk.compat."""
    tree = ast.parse(src)
    lines, offs = _offsets(src)
    edits = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.args.kwonlyargs and node.args.vararg is None:
            n_pos = len(node.args.posonlyargs) + len(node.args.args)
            first_kw = node.args.kwonlyargs[0]
            kw_start = _pos(lines, offs, first_kw.lineno, first_kw.col_offset)
            def_start = _pos(lines, offs, node.lineno, node.col_offset)
            sig = src[def_start:kw_start]
            m = re.search(r"\n[ \t]*\*,[ \t]*\n(?=[ \t]*$)", sig)
            if m:
                edits.append((def_start + m.start(), def_start + m.end() - 1, ""))
            else:
                m = list(re.finditer(r"\*,\s*", sig))[-1]
                edits.append((def_start + m.start(), def_start + m.end(), ""))
            indent = " " * node.col_offset
            edits.append((def_start, def_start, "@keyword_only(%d)\n%s" % (n_pos, indent)))
    out = _apply(src, edits)
    if edits and "from nltk.compat import keyword_only" not in out:
        out = out.replace("import six\n", "import six\nfrom nltk.compat import keyword_only\n", 1)
    return out, len(edits) // 2


if __name__ == "__main__" and len(sys.argv) > 3 and sys.argv[3] == "--deco":
    src = open(sys.argv[1], encoding="utf-8").read()
    out, n = kwonly_decorator(src)
    ast.parse(out)
    open(sys.argv[2], "w", encoding="utf-8").write(out)
    print("DECO %s: kwonly=%d" % (sys.argv[1].rsplit("/", 1)[-1], n))


def vararg_kwonly(src):
    """``def f(a, *args, k=1, **kw)``: 2.7 cannot name a parameter after
    ``*args``, so the keyword-only ones are popped from ``**kw`` (added when
    absent) right after the docstring."""
    tree = ast.parse(src)
    lines, offs = _offsets(src)
    edits = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) or not node.args.kwonlyargs or node.args.vararg is None:
            continue
        a = node.args
        first_kw = a.kwonlyargs[0]
        last_kw = a.kwonlyargs[-1]
        start = _pos(lines, offs, first_kw.lineno, first_kw.col_offset)
        end = _pos(lines, offs, last_kw.end_lineno, last_kw.end_col_offset)
        if a.kw_defaults[-1] is not None:
            end = max(end, _pos(lines, offs, a.kw_defaults[-1].end_lineno, a.kw_defaults[-1].end_col_offset))
        # remove ", kw1=..., kwN=..." (the comma before the first kwonly)
        pre = src.rfind(",", 0, start)
        kw_name = a.kwarg.arg if a.kwarg is not None else "_kw"
        if a.kwarg is None:
            edits.append((pre, end, ", **%s" % kw_name))
        else:
            edits.append((pre, end, ""))
        body0 = node.body[0]
        indent = " " * body0.col_offset
        if isinstance(body0, ast.Expr) and isinstance(body0.value, ast.Constant) and isinstance(body0.value.value, str):
            ins = _pos(lines, offs, body0.end_lineno, body0.end_col_offset)
            ins = src.index("\n", ins) + 1
            lead = indent
        else:
            ins = _pos(lines, offs, body0.lineno, body0.col_offset)
            lead = ""
        stmts = []
        for k, d in zip(a.kwonlyargs, a.kw_defaults):
            dsrc = ast.get_source_segment(src, d) if d is not None else None
            stmts.append("%s = %s.pop(%r%s)" % (k.arg, kw_name, k.arg, (", " + dsrc) if dsrc is not None else ""))
        if a.kwarg is None:
            stmts.append("if %s:\n%s    raise TypeError(\"unexpected keyword argument(s): %%s\" %% \", \".join(sorted(%s)))" % (kw_name, indent, kw_name))
        text = "".join(("%s%s\n" % (indent, st)) for st in stmts)
        if not lead:
            text = text[len(indent):]
        edits.append((ins, ins, text))
    return _apply(src, edits), len(edits) // 2


if __name__ == "__main__" and len(sys.argv) > 3 and sys.argv[3] == "--vararg":
    src = open(sys.argv[1], encoding="utf-8").read()
    out, n = vararg_kwonly(src)
    ast.parse(out)
    open(sys.argv[2], "w", encoding="utf-8").write(out)
    print("VARARG %s: %d" % (sys.argv[1].rsplit("/", 1)[-1], n))
