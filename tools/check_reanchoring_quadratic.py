#!/usr/bin/env python3
# Natural Language Toolkit: re-anchoring quadratic CI guard
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
"""Fail if a re-anchoring regex operation runs an UNBOUNDED wide scan.

A re-anchoring op -- ``redos.sub``/``subn``/``finditer``/``findall``/``split``/
``search`` -- retries its match at O(n) positions in the input. If the pattern
pairs a repeatable anchor with an unbounded "wide" run (``[^X]*``/``[^X]+``,
``.*``/``.*?``, ``\\S*``/``\\D*``/``\\W*``) that scans toward a terminator the
attacker can omit, every anchor position triggers an O(n) forward scan -> O(n**2)
(CWE-400/407). The ``nltk.redos`` wall-clock timeout is only a BACKSTOP for this
shape (it still burns a full timeout window per malicious call AND raises
``TimeoutError`` on legitimately-large VALID input), so it is NOT a fix -- the fix
is a ``{0,N}`` bound on the run (e.g. ``[^)]*`` -> ``[^)]{0,400}``).

This is the class that let the YCOE reader (``(CODE|ID)[^)]*`` under ``sub``, PR
#3896) and several corpus readers slip past the "catastrophic-backtracking only"
review. This guard makes the policy structural: every re-anchoring op with an
unbounded wide run must either bound the run (``{0,N}``) or be listed in
``_REVIEWED`` below with a one-line reason. A new unbounded site fails CI.

Usage: ``python tools/check_reanchoring_quadratic.py`` (exit 1 on violation).
"""

import ast
import os
import re
import sys

GUARDED_PATHS = ["nltk"]
_EXEMPT_PREFIXES = (os.path.join("nltk", "test"),)
_EXEMPT_FILES = (os.path.join("nltk", "redos.py"),)

# Ops that retry the match at O(n) positions (so a per-match O(n) scan is O(n**2)).
# match/fullmatch anchor once and are excluded.
_REANCHOR_OPS = frozenset({"sub", "subn", "finditer", "findall", "split", "search"})

# The dangerous unbounded "wide" runs: a negated class, dot, or a wide category
# escape carrying a ``*``/``+`` (no upper bound). A bounded ``{0,N}`` run has no
# ``*``/``+`` and so does not match -- that is exactly the fix.
_WIDE_RUN = re.compile(
    r"""
      \[\^[^\]]*\][*+]        # [^...]* or [^...]+   (negated class)
    | (?<!\\)\.[*+]           # .*  .+   (unescaped dot)
    | \\[SDW][*+]             # \S* \D+ \W* ...      (wide category escapes)
    """,
    re.VERBOSE,
)

# Sites reviewed and judged safe DESPITE an unbounded wide run (the anchor cannot
# repeat O(n) times, the run cannot re-scan, or the input is not attacker length).
# Keyed by (relpath, pattern) -> reason. Fixed sites carry a ``{0,N}`` bound and
# are NOT listed here (they no longer match _WIDE_RUN). Populate deliberately:
# the O(n**2) shape needs a repeatable anchor whose inner class does NOT contain
# the run's terminator, so a run whose anchor re-introduces the terminator, or a
# run with no terminator to re-scan, or one fed only short code-built input, is
# linear/benign.
_REVIEWED: dict[tuple[str, str], str] = {
    ("nltk/app/chunkparser_app.py", "((\\\\.|[^#])*)(#.*)?"): (
        "GUI grammar input; the .* is an optional trailing group with no repeating "
        "anchor, engine-linear"
    ),
    (
        "nltk/app/chunkparser_app.py",
        "^\\# Regexp Chunk Parsing Grammar[\\s\\S]*F-score:.*\n",
    ): "GUI status text, one greedy match, not attacker corpus input",
    ("nltk/chunk/util.py", "<[^>]{1,400}>|[^\\s<]+"): (
        "tag body is bounded; the [^\\s<]+ alt matches one token per pass with no "
        "terminator to re-scan"
    ),
    ("nltk/classify/textcat.py", "[^\\P{P}\\']+"): (
        "matches punctuation runs; each match advances, O(n) total"
    ),
    (
        "nltk/corpus/reader/bracket_parse.py",
        "\\(([^\\s()]+) ([^\\s()]+) [^\\s()]+\\)",
    ): "inner [^\\s()]+ excludes the ( anchor, so a scan cannot cross an anchor",
    ("nltk/corpus/reader/childes.py", "(?i)/childes(?:/data-xml)?/(.*)\\.xml"): (
        "runs on a bounded file-path string, not corpus bytes"
    ),
    ("nltk/corpus/reader/childes.py", "/(?i)Eng-USA/(.*)\\.xml"): (
        "runs on a bounded file-path string, not corpus bytes"
    ),
    ("nltk/corpus/reader/framenet.py", '<fex name="[^"]+">'): (
        'anchor ends in the " terminator, so [^"]+ is bounded per repetition'
    ),
    (
        "nltk/corpus/reader/senseval.py",
        '(?<![ \\t])[ \\t]*+([^<>\\s]++)[ \\t]*+<p="([^"]*+"?)"/>',
    ): "possessive quantifiers (*+/++) are atomic, no backtracking; already hardened",
    ("nltk/corpus/reader/senseval.py", "<\\&frasl>\\s*<p[^>]*>"): (
        "repeated <&frasl> re-introduces >, so [^>]* is bounded per repetition"
    ),
    ("nltk/corpus/reader/senseval.py", "item=(\"[^\"]+\"|'[^']+')"): (
        "search; anchor ends in a quote terminator, bounded per repetition"
    ),
    ("nltk/corpus/reader/wordnet.py", '"([^"]*)"'): (
        'anchor " equals the terminator, so [^"]* is bounded per repetition'
    ),
    ("nltk/corpus/reader/wordnet.py", '[\\"].*?[\\"]'): (
        'anchor " equals the terminator, so .*? matches an empty body immediately'
    ),
    ("nltk/corpus/util.py", "(([^/]+)(/.*)?)"): (
        "runs on a short code-supplied corpus zip name, not attacker-sized input"
    ),
    ("nltk/data.py", "(^\\w+:)?.*/"): (
        "runs on a short code-supplied resource URL, not attacker-sized input"
    ),
}


def _pattern_literal(node: ast.AST):
    """Return the static pattern string of a Call's first arg, or None if the
    pattern is built at runtime (dynamic) and cannot be statically bounded."""
    if not node.args:
        return None
    arg = node.args[0]
    if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
        return arg.value
    # r"a" + r"b" style concatenation of string literals.
    if isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.Add):
        left = _const_str(arg.left)
        right = _const_str(arg.right)
        if left is not None and right is not None:
            return left + right
    return None


def _const_str(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _iter_reanchor_calls(tree):
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if (
            isinstance(func, ast.Attribute)
            and func.attr in _REANCHOR_OPS
            and isinstance(func.value, ast.Name)
            and func.value.id == "redos"
        ):
            yield node


def check_file(path, relpath):
    with open(path, encoding="utf-8") as fh:
        try:
            tree = ast.parse(fh.read(), filename=path)
        except SyntaxError:
            return []
    violations = []
    for call in _iter_reanchor_calls(tree):
        pattern = _pattern_literal(call)
        if pattern is None:
            continue  # dynamic pattern: cannot statically bound; relies on redos
        if not _WIDE_RUN.search(pattern):
            continue  # bounded / narrow run -> not this class
        if (relpath, pattern) in _REVIEWED:
            continue
        violations.append((call.lineno, call.func.attr, pattern))
    return violations


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
                for lineno, op, pattern in check_file(path, relpath):
                    failures.append((relpath, lineno, op, pattern))

    if failures:
        print(
            "Unbounded re-anchoring quadratic regex(es) found (CWE-400/407).\n"
            "Bound the wide run with {0,N}, or add (relpath, pattern) to _REVIEWED "
            "in tools/check_reanchoring_quadratic.py with a reason:\n"
        )
        for relpath, lineno, op, pattern in sorted(failures):
            print(f"  {relpath}:{lineno}: redos.{op}(  {pattern!r}  )")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
