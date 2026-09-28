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
import logging
import os
import re
import subprocess
import sys
import time
import warnings
import zipfile
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


class TestLoggingSinks:
    """A logging handler writes to stderr like print does; the values NLTK
    interpolates into its log records are neutralised at the call."""

    @staticmethod
    def _debug_log_of(logger_name, fn):
        buf = io.StringIO()
        logger = logging.getLogger(logger_name)
        handler = logging.StreamHandler(buf)
        old_level = logger.level
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
        try:
            fn()
        finally:
            logger.removeHandler(handler)
            logger.setLevel(old_level)
        return buf.getvalue()

    def test_nonprojective_parser_debug_log_neutralises_hostile_word(self):
        from nltk.parse.nonprojectivedependencyparser import (
            DemoScorer,
            ProbabilisticNonprojectiveParser,
        )

        parser = ProbabilisticNonprojectiveParser()
        parser.train([], DemoScorer())
        log = self._debug_log_of(
            "nltk.parse.nonprojectivedependencyparser",
            lambda: list(
                parser.parse(["v1", "v2", "v3", HOSTILE], ["a", "b", "c", "d"])
            ),
        )
        assert "evil" in log and not _live(log)
        assert "g_graph:" in log  # the guarded graph dump did run at DEBUG

    def test_nonprojective_parser_pays_nothing_for_graph_dumps_when_quiet(self):
        from nltk.parse.nonprojectivedependencyparser import (
            DemoScorer,
            ProbabilisticNonprojectiveParser,
        )

        parser = ProbabilisticNonprojectiveParser()
        parser.train([], DemoScorer())
        logger = logging.getLogger("nltk.parse.nonprojectivedependencyparser")
        assert not logger.isEnabledFor(logging.DEBUG)
        parses = list(parser.parse(["v1", "v2", "v3"], ["a", "b", "c"]))
        assert len(parses) == 1

    def test_agreement_debug_log_neutralises_hostile_coder(self):
        from nltk.metrics.agreement import AnnotationTask

        data = [
            (HOSTILE, "1", "a"),
            ("c2", "1", "a"),
            (HOSTILE, "2", "b"),
            ("c2", "2", "a"),
        ]
        task = AnnotationTask(data=data)
        log = self._debug_log_of(
            "nltk.metrics.agreement", lambda: (task.kappa(), task.alpha())
        )
        assert "evil" in log and not _live(log)

    def test_perceptron_training_progress_line_is_numeric_only(self):
        # captured on the module's own logger, like the parser and agreement
        # records above: the root logger belongs to the application, and on a
        # shared test worker its handlers and level are whatever the tests that
        # ran before left there (the line was seen going to stdout on one CI
        # cell while a handler added to the root logger for this test got nothing)
        from nltk.tag.perceptron import PerceptronTagger

        log = self._debug_log_of(
            "nltk.tag.perceptron",
            lambda: PerceptronTagger(load=False).train(
                [[(HOSTILE, "X"), ("b", "Y")]], nr_iter=1
            ),
        )
        line = log.strip()
        assert re.fullmatch(r"Iter 0: \d+/\d+=[0-9.]+", line), line
        assert "evil" not in log and not _live(log)

    def test_perceptron_progress_line_stays_out_of_the_root_logger_sinks(self):
        # the record still propagates to the root logger, so an application
        # handler sees it, but nothing is written to stdout or stderr by the
        # library itself while training
        from nltk.tag.perceptron import PerceptronTagger

        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            PerceptronTagger(load=False).train([[("a", "X"), ("b", "Y")]], nr_iter=1)
        assert out.getvalue() == "" and err.getvalue() == ""


class TestWarnExitAndExceptionSinks:
    """warnings.warn, sys.exit and a security refusal's exception text all end
    on stderr through the interpreter, not through print."""

    def test_langnames_unknown_tag_warning_is_clean(self):
        from nltk.langnames import langname

        try:
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                langname("zz-" + HOSTILE)
        except LookupError:
            pytest.skip("bcp47 corpus not installed")
        messages = [str(w.message) for w in caught]
        assert messages and all(not _live(m) for m in messages)
        assert any("evil" in m for m in messages)

    def test_bcp47_invalid_extension_warning_is_clean(self):
        from nltk.corpus import bcp47

        try:
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                bcp47.name("x-" + HOSTILE)
        except LookupError:
            pytest.skip("bcp47 corpus not installed")
        messages = [str(w.message) for w in caught]
        assert messages and all(not _live(m) for m in messages)
        assert any("evil" in m for m in messages)

    def test_chat80_unreadable_database_message_is_clean(self, tmp_path):
        from nltk.sem import chat80

        # inside the sandbox the missing file reaches sys.exit; outside it
        # pathsec refuses first. Both messages quote the name and both are clean.
        with pytest.raises((SystemExit, PermissionError)) as info:
            chat80.val_load(str(tmp_path / ("nonexistent_" + HOSTILE)))
        exc = info.value
        text = str(exc.code) if isinstance(exc, SystemExit) else str(exc)
        assert "evil" in text and not _live(text)

    def test_pathsec_unauthorized_path_exception_text_is_clean(self):
        from nltk.pathsec import validate_path

        with pytest.raises(PermissionError) as info:
            validate_path("nonexistent_" + HOSTILE, context="probe" + ESC + "[31m")
        assert "evil" in str(info.value) and not _live(str(info.value))

    def test_pathsec_zip_traversal_member_exception_text_is_clean(self, tmp_path):
        from nltk.pathsec import validate_zip_archive

        archive = tmp_path / "hostile.zip"
        with zipfile.ZipFile(archive, "w") as zf:
            zf.writestr("../" + HOSTILE + ".txt", "x")
        with pytest.raises(PermissionError) as info:
            validate_zip_archive(str(archive), str(tmp_path), context="probe")
        assert "evil" in str(info.value) and not _live(str(info.value))


class TestParserAndChunkerTraceSinks:
    @staticmethod
    def _grammar():
        from nltk.grammar import CFG, Nonterminal, Production

        S, NP = Nonterminal("S"), Nonterminal("NP")
        return CFG(S, [Production(S, [NP, "sat"]), Production(NP, [HOSTILE])])

    def test_recursive_descent_trace_neutralises_hostile_token(self):
        from nltk.parse import RecursiveDescentParser

        parser = RecursiveDescentParser(self._grammar(), trace=2)
        out = _stdout_of(lambda: list(parser.parse([HOSTILE, "sat"])))
        assert "evil" in out and not _live(out)

    def test_shift_reduce_trace_neutralises_hostile_token(self):
        from nltk.parse import ShiftReduceParser

        parser = ShiftReduceParser(self._grammar(), trace=2)
        out = _stdout_of(lambda: list(parser.parse([HOSTILE, "sat"])))
        assert "evil" in out and not _live(out)

    def test_chart_parser_trace_neutralises_hostile_token(self):
        from nltk.parse import ChartParser

        parser = ChartParser(self._grammar(), trace=2)
        out = _stdout_of(lambda: list(parser.parse([HOSTILE, "sat"])))
        assert "evil" in out and not _live(out)

    def test_regexp_chunk_parser_trace_neutralises_hostile_tag(self):
        from nltk.chunk import RegexpParser

        # the chunk trace prints the tag string, not the tokens: a tag is
        # tagger output over untrusted text, so it is the hostile channel here
        chunker = RegexpParser("NP: {<DT>?<NN>}", trace=2)
        out = _stdout_of(
            lambda: chunker.parse([("the", "DT"), ("cat", "NN"), ("x", HOSTILE)])
        )
        assert "# Input:" in out and "evil" in out and not _live(out)


class TestClusterSinks:
    def test_dendrogram_show_neutralises_hostile_leaf_label(self):
        from nltk.cluster.util import Dendrogram

        dendrogram = Dendrogram([1, 2, 3])
        dendrogram.merge(0, 1)
        out = _stdout_of(lambda: dendrogram.show(leaf_labels=["a", HOSTILE, "c"]))
        assert "evil" in out and not _live(out)
        assert "+" in out  # the ASCII art itself still renders


class TestDownloaderSinks:
    """The downloader index is network data: a package id or name from it is
    printed by list() and quoted in the error path of download()."""

    @staticmethod
    def _offline_downloader(tmp_path, packages):
        from nltk.downloader import Downloader

        downloader = Downloader(download_dir=str(tmp_path))
        downloader._index = object()  # an already-loaded index: no network
        downloader._index_timestamp = time.time()
        downloader._packages = {package.id: package for package in packages}
        downloader._collections = {}
        return downloader

    def test_list_renders_hostile_package_id_and_name_escaped(self, tmp_path):
        from nltk.downloader import Package

        package = Package(
            id="pkg_" + HOSTILE,
            url="http://example.invalid/pkg.zip",
            name="Name " + HOSTILE,
            subdir="corpora",
            size=100,
            unzipped_size=100,
            checksum="0",
        )
        downloader = self._offline_downloader(tmp_path, [package])
        out = _stdout_of(lambda: downloader.list(download_dir=str(tmp_path)))
        assert out.count("evil") >= 2 and not _live(out)
        assert "Packages:" in out

    def test_download_error_path_prints_hostile_id_escaped(self, tmp_path):
        downloader = self._offline_downloader(tmp_path, [])
        err = io.StringIO()
        result = downloader.download(
            "missing_" + HOSTILE, download_dir=str(tmp_path), print_error_to=err
        )
        assert result is False
        assert "evil" in err.getvalue() and not _live(err.getvalue())


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
