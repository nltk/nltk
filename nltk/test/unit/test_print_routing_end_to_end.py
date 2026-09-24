# Natural Language Toolkit: end-to-end terminal-output routing tests
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
"""Drive REAL NLTK functions that print or warn, feed them hostile data, and
read what actually reached the captured stdout / stderr / warnings: no mocked
print, no patched sink. Two properties for every site: no live control byte or
bidi override survives (CWE-150 / CVE-2021-42574), and clean data prints
exactly as before, so the routing is a true drop-in.

Untrusted text enters NLTK as corpus tokens, tree leaves, graph nodes,
resource names and user input; each test below feeds one such channel."""

import contextlib
import io
import os
import subprocess
import sys
import warnings
from pathlib import Path

import pytest

ESC = "\x1b"
RLO = chr(0x202E)  # never a literal: the tool layer decodes escapes
HOSTILE = "evil" + ESC + "[2J" + RLO + "x"


def _live(text):
    return ESC in text or RLO in text or "\x07" in text


def _stdout_of(fn):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        fn()
    return buf.getvalue()


class TestTextSinks:
    def _text(self):
        from nltk.text import Text

        tokens = ("the cat sat on the mat and the " + HOSTILE + " sat too").split()
        return Text(tokens)

    def test_concordance_neutralises_a_hostile_token(self):
        out = _stdout_of(lambda: self._text().concordance("sat"))
        assert "sat" in out and not _live(out)
        assert "\\x1b" in out  # the escape is visible, not executed

    def test_similar_and_collocations_run_clean(self):
        text = self._text()
        for fn in (lambda: text.similar("cat"), lambda: text.collocations()):
            assert not _live(_stdout_of(fn))

    def test_clean_concordance_output_unchanged(self):
        from nltk.text import Text

        text = Text("the cat sat on the mat".split())
        out = _stdout_of(lambda: text.concordance("sat"))
        assert "Displaying 1 of 1 matches" in out and "the cat sat on the mat" in out


class TestProbabilitySinks:
    def test_freqdist_tabulate_with_hostile_sample(self):
        from nltk.probability import FreqDist

        fd = FreqDist(["a", "a", HOSTILE, "b"])
        out = _stdout_of(lambda: fd.tabulate())
        assert not _live(out) and "evil" in out

    def test_conditional_freqdist_tabulate(self):
        from nltk.probability import ConditionalFreqDist

        cfd = ConditionalFreqDist([(HOSTILE, "x"), ("cond", HOSTILE)])
        out = _stdout_of(lambda: cfd.tabulate())
        assert not _live(out)

    def test_freqdist_pprint_clean_unchanged(self):
        from nltk.probability import FreqDist

        out = _stdout_of(lambda: FreqDist(["a", "b", "a"]).pprint())
        assert "'a': 2" in out


class TestTreeSinks:
    def test_pretty_print_with_hostile_leaf_and_label(self):
        from nltk.tree import Tree

        tree = Tree("S", [Tree(HOSTILE, ["leaf"]), Tree("NP", [HOSTILE])])
        for fn in (tree.pretty_print, tree.pprint):
            out = _stdout_of(fn)
            assert not _live(out) and "evil" in out

    def test_clean_tree_pretty_print_unchanged(self):
        from nltk.tree import Tree

        out = _stdout_of(Tree.fromstring("(S (NP I) (VP saw))").pretty_print)
        assert "S" in out and "saw" in out and "NP" in out


class TestWarningSinks:
    def test_graph_search_warning_neutralises_node_text(self):
        from nltk.util import acyclic_breadth_first

        # the hostile node is visited first, then rediscovered from "a", so
        # the "redundant search" warning quotes it as the discarded child
        graph = {"root": [HOSTILE, "a"], HOSTILE: [], "a": [HOSTILE]}
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            list(
                acyclic_breadth_first("root", lambda n: graph.get(n, []), verbose=True)
            )
        messages = [str(w.message) for w in caught]
        assert messages and all(not _live(m) for m in messages)
        assert any("evil" in m for m in messages)

    def test_sonority_unknown_character_warning_neutralised(self):
        from nltk.tokenize.sonority_sequencing import SyllableTokenizer

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            SyllableTokenizer().tokenize(
                "ba" + ESC + "nana"
            )  # two vowels: past the early return
        messages = [str(w.message) for w in caught]
        assert messages and all(not _live(m) for m in messages)


class TestUtilityAndCliSinks:
    def test_util_pr_and_print_string(self):
        from nltk.util import pr, print_string

        assert not _live(_stdout_of(lambda: pr([HOSTILE])))
        assert not _live(_stdout_of(lambda: print_string(HOSTILE * 3, 20)))

    def test_cli_tokenize_stream_escapes_control_characters(self):
        # nltk.cli tokenises stdin to stdout through the same sink, so a
        # control byte inside a token is emitted as its visible escape: a
        # documented, deliberate change from the raw byte
        pytest.importorskip("click")
        # the console entry point (nltk=nltk.cli:cli) as a real process, since
        # the command closes its stdout stream, which click's in-process runner
        # cannot survive
        root = Path(__file__).resolve().parents[3]
        # CI runs with safe path enabled, so the child's cwd is not on sys.path;
        # PYTHONPATH is honoured there and makes this checkout importable
        env = dict(os.environ, PYTHONPATH=str(root))
        proc = subprocess.run(
            [sys.executable, "-c", "from nltk.cli import cli; cli()", "tokenize"],
            input="hello " + ESC + "[2Jworld\nplain line\n",
            capture_output=True,
            text=True,
            cwd=root,
            env=env,
        )
        assert proc.returncode == 0, proc.stderr
        assert not _live(proc.stdout)
        assert "hello" in proc.stdout and "world" in proc.stdout
        assert "plain line" in proc.stdout


def test_unsafe_print_guard_passes_on_the_tree():
    root = Path(__file__).resolve().parents[3]
    tool = root / "tools" / "check_unsafe_print.py"
    if not tool.exists():
        pytest.skip("guard not present in this checkout")
    proc = subprocess.run(
        [sys.executable, str(tool)], cwd=root, capture_output=True, text=True
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_no_bare_print_reference_remains_in_library_code():
    import ast

    root = Path(__file__).resolve().parents[3] / "nltk"
    offenders = []
    for path in root.rglob("*.py"):
        if "test" in path.relative_to(root).parts[:1]:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Name)
                and node.id == "print"
                and isinstance(node.ctx, ast.Load)
            ):
                if path.name != "termsec.py":
                    offenders.append(f"{path.relative_to(root)}:{node.lineno}")
            if (
                isinstance(node, ast.Attribute)
                and node.attr == "print"
                and getattr(node.value, "id", "") == "builtins"
            ):
                offenders.append(
                    f"{path.relative_to(root)}:{node.lineno} (builtins.print)"
                )
    assert not offenders, offenders
