#!/usr/bin/env python3
# Natural Language Toolkit: unsafe-print CI guard
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
"""Fail if a terminal sink can emit an unsanitised value.

A value an attacker can influence (a corpus token, a tool subprocess line, a
tweet, a user expression) written raw to a terminal can carry ANSI/OSC escape
sequences or Unicode bidi/invisibles that hijack or spoof the terminal
(CWE-150 / 1007 / 1236). ``nltk.termsec.safe_print`` / ``sanitize_terminal``
is the choke point that neutralises them.

This guard makes the policy structural, like ``no-unsandboxed-open`` for
pathsec. Every terminal SINK in the shipped tree must be one of:

  * ``safe_print(...)`` (sanitises every argument, ``sep`` and ``end``), or
  * a sink whose arguments are ALL provably harmless: string/number literals,
    or interpolations that are entirely ``repr``-escaped (``!r`` / ``!a`` /
    ``%r`` / ``%a``) or numeric-formatted (``%d`` / ``%.3f`` / ``{n:d}`` ...),
    which cannot carry a control byte, or an argument already wrapped in
    ``sanitize_terminal`` / ``sanitize_csv_field`` / ``repr`` / ``ascii``, or
  * a sink explicitly reviewed benign with a trailing
    ``# unsafe-print ok: <why>`` COMMENT on the statement's first or last
    line. The reason is mandatory, and the marker only counts inside a real
    comment token, never inside a string literal on that line.

A ``*args`` splat is never provably safe. The sinks held to this rule, each
of which writes its text to a terminal by default:

  * ``print(...)`` and ``builtins.print(...)`` (arguments, ``sep``, ``end``);
    the bare name ``print`` may not be aliased, passed, bound to a partial or
    fetched with ``getattr`` either, since that hides the sink from review;
  * ``sys.stdout.write`` / ``sys.stderr.write`` (also the ``sys.__stdout__``
    / ``sys.__stderr__`` originals and a ``from sys import stdout`` name),
    ``os.write(1 | 2, ...)`` and ``click.echo`` / ``click.secho``;
  * ``warnings.warn(message)`` / ``warn_explicit`` / a bare ``warn(message)``
    (the default ``showwarning`` prints the message to stderr);
  * every ``logging`` call on the ``logging`` module or a ``getLogger``
    logger: the message and its interpolation arguments (the last-resort and
    the usual handlers write to stderr);
  * ``sys.exit(message)`` / ``exit(message)`` / ``SystemExit(message)`` (the
    interpreter prints a non-integer argument to stderr at exit);
  * ``input(prompt)`` (the prompt is written to stdout).

Usage: ``python tools/check_unsafe_print.py`` (exit 1 on any violation).
"""

import ast
import io
import os
import re
import sys
import tokenize

GUARDED_PATHS = ["nltk"]
_EXEMPT_PREFIXES = (os.path.join("nltk", "test"),)
_EXEMPT_FILES = (os.path.join("nltk", "termsec.py"),)
# The marker must carry a reason: at least one non-blank character after the colon.
_MARKER = re.compile(r"#.*unsafe-print ok:\s*\S")
_SANITIZERS = {"safe_print", "sanitize_terminal", "sanitize_csv_field"}
_ESCAPERS = {"repr", "ascii"}
_LOG_METHODS = {
    "debug",
    "info",
    "warning",
    "warn",
    "error",
    "critical",
    "exception",
    "log",
}
_STREAM_NAMES = {"stdout", "stderr", "__stdout__", "__stderr__"}

# %-format conversion chars that cannot carry a control byte: repr/ascii-repr,
# every integer/float base, and the literal percent. 's' (str) and 'c' (chr of
# an int, which can be ESC) are deliberately excluded.
_SAFE_PERCENT = set("radiouxXeEfFgGn%")
_PERCENT_CONV = re.compile(r"%[-+ #0-9.*]*([a-zA-Z%])")
# f-string numeric type chars (the last char of a format spec like ``.3f``/``d``).
# 'c' is excluded here for the same reason as above, and 's' is not numeric.
_NUMERIC_SPEC_END = set("bdoxXneEfFgG%")


def _spec_is_numeric(fmtspec):
    if not isinstance(fmtspec, ast.JoinedStr):
        return False
    text = "".join(v.value for v in fmtspec.values if isinstance(v, ast.Constant))
    return bool(text) and text[-1] in _NUMERIC_SPEC_END


def _fvalue_is_safe(node):
    # An f-string ``{expr}`` field is harmless iff repr-converted, numeric-spec'd,
    # or itself a sanitised / repr'd expression.
    if node.conversion in (114, 97):  # !r , !a
        return True
    return _spec_is_numeric(node.format_spec) or _is_safe_arg(node.value)


def _percent_is_safe(fmt):
    convs = _PERCENT_CONV.findall(fmt)
    return bool(convs) and all(c in _SAFE_PERCENT for c in convs)


def _percent_values_safe(fmt, values):
    """``fmt % values``: each value is safe iff its own conversion is safe
    (``%d``, ``%r`` ...) or the value is itself sanitised / repr'd / literal.
    Pairing is positional; when the counts do not line up (a ``*`` width, a
    dict on the right) every value must be safe on its own."""
    if _percent_is_safe(fmt):
        return True
    convs = [c for c in _PERCENT_CONV.findall(fmt) if c != "%"]
    if len(convs) != len(values):
        return all(_is_safe_arg(v) for v in values)
    return all(c in _SAFE_PERCENT or _is_safe_arg(v) for c, v in zip(convs, values))


def _is_safe_arg(arg):
    if isinstance(arg, ast.Constant):
        return True
    if isinstance(arg, ast.JoinedStr):  # f-string
        return all(
            isinstance(v, ast.Constant) or _fvalue_is_safe(v) for v in arg.values
        )
    if isinstance(arg, ast.BinOp):
        if isinstance(arg.op, ast.Mod):
            # "...%r..." % value -> safe iff the format conversions are all safe,
            # or every interpolated value is itself sanitised / repr'd / literal
            if isinstance(arg.left, ast.Constant) and isinstance(arg.left.value, str):
                values = (
                    arg.right.elts if isinstance(arg.right, ast.Tuple) else [arg.right]
                )
                if isinstance(arg.right, (ast.Dict, ast.Starred)):
                    return False  # keyed / splatted values cannot be paired
                return _percent_values_safe(arg.left.value, values)
            return False
        if isinstance(arg.op, ast.Add):  # concatenation: safe iff both sides are
            return _is_safe_arg(arg.left) and _is_safe_arg(arg.right)
        return False
    if isinstance(arg, ast.Call) and isinstance(arg.func, ast.Name):
        # repr()/ascii() escape control bytes; the sanitisers neutralise them;
        # str() of an already-safe expression adds nothing unsafe.
        if arg.func.id == "str" and len(arg.args) == 1 and not arg.keywords:
            return _is_safe_arg(arg.args[0])
        return arg.func.id in _SANITIZERS or arg.func.id in _ESCAPERS
    if (
        isinstance(arg, ast.Call)
        and isinstance(arg.func, ast.Attribute)
        and arg.func.attr == "format"
        and isinstance(arg.func.value, ast.Constant)
        and isinstance(arg.func.value.value, str)
    ):
        # "...{}...".format(values): safe iff every interpolated value is
        return all(_is_safe_arg(a) for a in arg.args) and all(
            _is_safe_arg(k.value) for k in arg.keywords
        )
    return False


def _log_args_safe(args):
    """``logger.level(msg, *interp)``: safe iff the message cannot carry a raw
    value. A literal message whose %-conversions are all safe covers any
    arguments; otherwise the message and every interpolation argument must be
    safe on their own."""
    if not args:
        return True
    msg, interp = args[0], args[1:]
    if isinstance(msg, ast.Constant) and isinstance(msg.value, str):
        if not interp:
            return True
        if any(isinstance(a, ast.Starred) for a in interp):
            return False
        return _percent_values_safe(msg.value, interp)
    return _is_safe_arg(msg) and all(_is_safe_arg(a) for a in interp)


def _logger_names(tree):
    """``logging``, the conventional logger names, and every module-level name
    bound from ``getLogger(...)``. Only ``.debug(`` and friends on these names
    are sinks, so ``from math import log`` can never trip the rule."""
    names = {"logging", "logger", "_logger", "log", "_log", "LOG", "LOGGER"}
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Assign) and isinstance(node.value, ast.Call)):
            continue
        func = node.value.func
        if (isinstance(func, ast.Attribute) and func.attr == "getLogger") or (
            isinstance(func, ast.Name) and func.id == "getLogger"
        ):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    names.add(target.id)
    return names


def _classify_sink(node, logger_names):
    """Return ``(kind, checked_args)`` for a terminal-sink call, else ``None``.

    ``checked_args`` are the argument nodes that reach the terminal; for
    ``print`` that includes the ``sep`` and ``end`` keyword values.
    """
    func = node.func
    args = list(node.args)
    kwargs = {k.arg: k.value for k in node.keywords if k.arg}
    sep_end = [kwargs[k] for k in ("sep", "end") if k in kwargs]
    if isinstance(func, ast.Name):
        if func.id == "print":
            return "print", args + sep_end
        if func.id == "input":
            return "input", args[:1]
        if func.id in ("exit", "quit", "SystemExit"):
            return "exit", args[:1]
        if func.id == "warn":
            return "warn", args[:1]
        return None
    if not isinstance(func, ast.Attribute):
        return None
    recv = func.value
    recv_name = recv.id if isinstance(recv, ast.Name) else None
    if func.attr == "print" and recv_name == "builtins":
        return "print", args + sep_end
    if func.attr in ("echo", "secho") and recv_name == "click":
        return "print", args[:1]
    if func.attr in ("warn", "warn_explicit") and recv_name == "warnings":
        return "warn", args[:1]
    if func.attr == "exit" and recv_name == "sys":
        return "exit", args[:1]
    if func.attr == "write":
        if recv_name in _STREAM_NAMES:
            return "write", args
        if (
            isinstance(recv, ast.Attribute)
            and recv.attr in _STREAM_NAMES
            and getattr(recv.value, "id", "") == "sys"
        ):
            return "write", args
        if (
            recv_name == "os"
            and args
            and isinstance(args[0], ast.Constant)
            and args[0].value in (1, 2)
        ):
            return "write", args[1:2]
        return None
    if func.attr in _LOG_METHODS and recv_name in logger_names:
        return "log", (args[1:] if func.attr == "log" else args)
    return None


def _comment_lines(source):
    """Line number -> comment text, from the tokenizer, so a marker inside a
    string literal on the same line can never clear a violation."""
    comments = {}
    try:
        for tok in tokenize.generate_tokens(io.StringIO(source).readline):
            if tok.type == tokenize.COMMENT:
                comments[tok.start[0]] = tok.string
    except (tokenize.TokenError, SyntaxError):
        pass
    return comments


def _marker_clears(node, comments):
    first, last = node.lineno, getattr(node, "end_lineno", node.lineno)
    return any(_MARKER.search(comments.get(i, "")) for i in (first, last))


def check_source(source, filename="<string>"):
    """Return ``[(lineno, kind), ...]`` for every unsanitised sink in *source*."""
    try:
        tree = ast.parse(source, filename=filename)
    except SyntaxError:
        return []
    comments = _comment_lines(source)
    logger_names = _logger_names(tree)
    violations = []
    called = set()  # ids of Name nodes that are a Call's func
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Name):
            called.add(id(node.func))
        # getattr(anything, "print") fetches the sink by name: an alias.
        if (
            isinstance(node.func, ast.Name)
            and node.func.id == "getattr"
            and len(node.args) >= 2
            and isinstance(node.args[1], ast.Constant)
            and node.args[1].value == "print"
        ):
            violations.append((node.lineno, "print-alias"))
            continue
        classified = _classify_sink(node, logger_names)
        if classified is None:
            continue
        kind, checked = classified
        if kind == "log":
            if _log_args_safe(checked):
                continue
        elif all(_is_safe_arg(a) for a in checked):
            continue  # empty print() / literal / repr / numeric / already-sanitised
        if _marker_clears(node, comments):
            continue
        violations.append((node.lineno, kind))
    for node in ast.walk(tree):
        # The bare name ``print`` anywhere except as the callee is an alias
        # (``p = print``, ``partial(print)``, ``map(print, ...)``): the sink
        # then escapes review, so it is a violation with no marker escape.
        if (
            isinstance(node, ast.Name)
            and node.id == "print"
            and isinstance(node.ctx, ast.Load)
            and id(node) not in called
        ):
            violations.append((node.lineno, "print-alias"))
        if (
            isinstance(node, ast.Attribute)
            and node.attr == "print"
            and getattr(node.value, "id", "") == "builtins"
            and not any(
                isinstance(p, ast.Call) and p.func is node for p in ast.walk(tree)
            )
        ):
            violations.append((node.lineno, "print-alias"))
    return sorted(set(violations))


def check_file(path):
    with open(path, encoding="utf-8") as fh:
        return check_source(fh.read(), filename=path)


def main():
    root = os.getcwd()
    failures = []
    for guarded in GUARDED_PATHS:
        for dirpath, _dirs, files in os.walk(os.path.join(root, guarded)):
            for name in files:
                if not name.endswith(".py"):
                    continue
                path = os.path.join(dirpath, name)
                relpath = os.path.relpath(path, root)
                if relpath.startswith(_EXEMPT_PREFIXES) or relpath in _EXEMPT_FILES:
                    continue
                for lineno, kind in check_file(path):
                    failures.append((relpath, lineno, kind))
    if failures:
        print(
            f"{len(failures)} unsafe terminal sink(s) (CWE-150/1007/1236). Route "
            "through nltk.termsec.safe_print / sanitize_terminal, or add a "
            "trailing '# unsafe-print ok: <why>' comment:\n"
        )
        for relpath, lineno, kind in sorted(failures):
            what = "print aliased" if kind == "print-alias" else f"bare {kind}(<value>)"
            print(f"  {relpath}:{lineno}: {what}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
