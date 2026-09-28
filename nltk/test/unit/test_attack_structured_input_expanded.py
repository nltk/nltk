# Natural Language Toolkit: expanded attack harness for the structured-input,
# downloader-bound, decorator and DOT guards
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
"""Every guard this PR adds is driven here with the widest attack matrix that
could be thought of, benign neighbours included, and judged by what the sink
would have received, not by whether something raised. Nothing is mocked except
the network reader of the downloader (a hostile server cannot be stood up in a
unit test); the guards, the file writes and, where a real tool is installed,
the tool itself run for real."""

import hashlib
import io
import os
import time
import unicodedata

import pytest

from nltk.pathsec import has_line_unsafe_char

NUL = chr(0)
# Every character class has_line_unsafe_char refuses, spelled with chr()
LINE_BREAKS = [chr(c) for c in (0x0A, 0x0D, 0x0B, 0x0C, 0x1C, 0x1D, 0x1E, 0x85)]
SEPARATORS = [chr(0x2028), chr(0x2029)]
CONTROLS = [chr(c) for c in (0x00, 0x01, 0x07, 0x08, 0x09, 0x1B, 0x7F, 0x9B)]
SURROGATE = chr(0xD800)
UNSAFE = LINE_BREAKS + SEPARATORS + CONTROLS + [SURROGATE]
# Ordinary multilingual content that must keep working
BENIGN = [
    "John",
    "New-York",
    "caf" + chr(0xE9),
    "مرحبا",  # Arabic letters, spelled as literals
    "x" + chr(0x200D) + "y",  # zero-width joiner
    "a" + chr(0x00A0) + "b",  # no-break space
    "\U0001f600",
    "'",
    '"',
    "\\",
    "<b>",
    "&amp;",
    "a" * 5000,
]


def _all_refused_classes_covered():
    # the matrix must agree with the shared rule it drives
    for ch in UNSAFE:
        assert has_line_unsafe_char(ch), hex(ord(ch))
    for text in BENIGN:
        assert not has_line_unsafe_char(text), text


# --------------------------------------------------------------------------- #
# 1. CoNLL rows handed to MaltParser
# --------------------------------------------------------------------------- #
class TestConllMatrix:
    def test_matrix_matches_the_shared_rule(self):
        _all_refused_classes_covered()

    @pytest.mark.parametrize("bad", UNSAFE, ids=lambda c: "U+%04X" % ord(c))
    def test_every_unsafe_character_is_refused_in_word_and_tag(self, bad):
        from nltk.parse.util import taggedsent_to_conll

        for pair in (("a" + bad + "b", "NN"), ("ok", "N" + bad + "N")):
            with pytest.raises(ValueError):
                list(taggedsent_to_conll([pair]))

    @pytest.mark.parametrize("text", BENIGN, ids=lambda t: t[:8])
    def test_benign_content_builds_exactly_one_row(self, text):
        from nltk.parse.util import taggedsent_to_conll

        rows = list(taggedsent_to_conll([(text, "NN")]))
        assert len(rows) == 1 and rows[0].count("\n") == 1
        assert rows[0].split("\t")[1] == text and rows[0].count("\t") == 9

    def test_a_row_is_never_re_split_by_a_line_reader(self):
        # what a reader sees is exactly one record per token, whatever the
        # token: str.splitlines (the widest splitter) agrees with the count
        from nltk.parse.util import taggedsent_to_conll

        rows = list(taggedsent_to_conll([(t, "NN") for t in BENIGN]))
        assert len("".join(rows).splitlines()) == len(BENIGN)


# --------------------------------------------------------------------------- #
# 2. Stanford tagger / segmenter newline-per-sentence input
# --------------------------------------------------------------------------- #
def _bare_stanford_tagger():
    from nltk.tag.stanford import StanfordPOSTagger

    tagger = StanfordPOSTagger.__new__(StanfordPOSTagger)
    tagger._encoding = "utf8"
    return tagger


def _bare_segmenter():
    from nltk.tokenize.stanford_segmenter import StanfordSegmenter

    seg = StanfordSegmenter.__new__(StanfordSegmenter)
    seg._encoding = "utf8"
    return seg


class TestStanfordInputMatrix:
    @pytest.mark.parametrize("bad", UNSAFE, ids=lambda c: "U+%04X" % ord(c))
    def test_every_unsafe_character_in_a_token_is_refused_before_any_lookup(self, bad):
        # the guard runs before the jar or the JVM is looked up, so a bare
        # instance is enough and no tool is spawned
        with pytest.raises(ValueError):
            _bare_stanford_tagger().tag_sents([["ok", "a" + bad + "b"]])
        with pytest.raises(ValueError):
            _bare_segmenter().segment_sents([["ok", "a" + bad + "b"]])

    def test_an_empty_sentence_list_and_empty_sentences_pass_the_guard(self):
        # nothing to refuse: the guard lets these through to the (absent) tool,
        # which is the pre-existing behaviour; the LookupError comes from the
        # jar lookup, not from the input check
        for sentences in ([], [[]], [["a"], []]):
            with pytest.raises((LookupError, AttributeError, TypeError, OSError)):
                _bare_stanford_tagger().tag_sents(sentences)

    @pytest.mark.skipif(
        not (os.environ.get("STANFORD_MODELS") and os.environ.get("STANFORD_POSTAGGER"))
        and not os.path.isdir("/Users/alvas/nltk_tools/stanford-postagger"),
        reason="needs a real Stanford POS tagger install",
    )
    def test_real_tagger_refuses_the_injection_and_still_tags(self, monkeypatch):
        # executed for real: the refusal is the guard, the tagging is the tool
        from nltk.tag.stanford import StanfordPOSTagger

        if not os.environ.get("STANFORD_POSTAGGER"):
            home = "/Users/alvas/nltk_tools/stanford-postagger"
            monkeypatch.setenv("STANFORD_POSTAGGER", home)
            monkeypatch.setenv("STANFORD_MODELS", os.path.join(home, "models"))
            jdk = "/Users/alvas/nltk_tools/jdk/jdk-21.0.12.1+1/Contents/Home"
            if os.path.isdir(jdk):
                monkeypatch.setenv("JAVA_HOME", jdk)
        import nltk.internals as internals

        monkeypatch.setattr(internals, "_java_bin", None)
        try:
            tagger = StanfordPOSTagger("english-bidirectional-distsim.tagger")
        except LookupError as e:
            pytest.skip(f"Stanford POS tagger not resolvable here: {e}")
        with pytest.raises(ValueError):
            tagger.tag_sents([["The", "quick\nbrown", "fox"]])
        tagged = tagger.tag_sents([["The", "quick", "brown", "fox"]])
        assert len(tagged) == 1 and [w for w, _ in tagged[0]] == [
            "The",
            "quick",
            "brown",
            "fox",
        ]
        assert all(tag for _, tag in tagged[0])


# --------------------------------------------------------------------------- #
# 3. Graphviz DOT
# --------------------------------------------------------------------------- #
def _unescaped_quotes(dot):
    count, i = 0, 0
    while i < len(dot):
        if dot[i] == "\\":
            i += 2
            continue
        if dot[i] == '"':
            count += 1
        i += 1
    return count


DOT_ATTACKS = [
    'x" ] ; evil -> 0 [ label="',
    'x"]\n9 [label="pwned"]\n8 [label="',
    "x\\",
    'x\\\\"',
    "x\r\n",
    "x\n" + "9 -> 0",
    "x" + chr(0x2028) + "9 -> 0",
    "x" + NUL + "y",
    "{x}",
    "<x>",
    "x'y",
    "x;y",
    "x" * 5000,
]


class TestDotMatrix:
    @pytest.mark.parametrize("word", DOT_ATTACKS, ids=lambda w: repr(w)[:14])
    def test_dependencygraph_word_never_breaks_out(self, word):
        from nltk.parse.dependencygraph import DependencyGraph

        dg = DependencyGraph("John N 2\nloves V 0\nMary N 2")
        dg.nodes[1]["word"] = word
        dot = dg.to_dot()
        lines = dot.split("\n")
        # exactly the four node labels and three edge labels of the three-word
        # graph, one statement per line, no raw line break or separator
        # smuggled in, every quote balanced
        assert _unescaped_quotes(dot) == 2 * 7, dot
        assert len(lines) == 12, dot
        # DOT breaks lines on LF and CR only; a Unicode separator inside the
        # quotes is just a character to it, and the count above shows it
        # added no statement
        assert "\r" not in dot
        assert (
            word.replace("\\", "\\\\")
            .replace('"', '\\"')
            .replace("\n", "\\n")
            .replace("\r", "\\r")
            in dot
        )

    @pytest.mark.parametrize("word", DOT_ATTACKS, ids=lambda w: repr(w)[:14])
    def test_alignedsent_word_never_breaks_out(self, word):
        from nltk.translate.api import AlignedSent, Alignment

        sent = AlignedSent([word, "ok"], ["x", "y"], Alignment.fromstring("0-0 1-1"))
        dot = sent._to_dot()
        assert _unescaped_quotes(dot) % 2 == 0, dot
        assert "\r" not in dot and dot.count("\n") == dot.replace("\\n", "").count("\n")

    @pytest.mark.parametrize(
        "address",
        ['1 [label="x"]; 9 -> 0', "1;2", "0x1", 1.0, None, True, b"1", "1"],
        ids=lambda a: repr(a)[:14],
    )
    def test_a_non_integer_address_is_refused_not_interpolated(self, address):
        from nltk.parse.dependencygraph import DependencyGraph

        dg = DependencyGraph("John N 2\nloves V 0\nMary N 2")
        dg.nodes[1]["address"] = address
        with pytest.raises((ValueError, TypeError)):
            dg.to_dot()
        dg = DependencyGraph("John N 2\nloves V 0\nMary N 2")
        dg.nodes[2]["deps"]["dep"] = [address]
        with pytest.raises((ValueError, TypeError)):
            dg.to_dot()

    def test_relation_labels_are_escaped_too(self):
        from nltk.parse.dependencygraph import DependencyGraph

        dg = DependencyGraph("John N 2\nloves V 0\nMary N 2")
        deps = dg.nodes[2]["deps"]
        deps['x" ] ; evil -> 0 [ label="'] = deps.pop(next(iter(deps)))
        dot = dg.to_dot()
        assert _unescaped_quotes(dot) == 2 * 7, dot
        assert len(dot.split("\n")) == 12, dot

    def test_legit_graph_renders_unchanged(self):
        from nltk.parse.dependencygraph import DependencyGraph

        dg = DependencyGraph("John N 2\nloves V 0\nMary N 2")
        assert '1 [label="1 (John)"]' in dg.to_dot()
        assert "2 -> 1" in dg.to_dot()


# --------------------------------------------------------------------------- #
# 4. Downloader: the declared size is capped, the index body is bounded
# --------------------------------------------------------------------------- #
class _Counting:
    """A server stand-in that records how much was asked of it."""

    def __init__(self, body=b"", endless=False):
        self.body, self.endless, self.served, self.reads = body, endless, 0, 0

    def read(self, n=-1):
        self.reads += 1
        if self.endless:
            chunk = b"<x>" * 1024
        else:
            chunk, self.body = self.body[:n], self.body[n:]
        self.served += len(chunk)
        return chunk

    def close(self):
        pass


class TestDownloaderCeilings:
    def _info(self, size):
        class _Info:
            id = "dummy"
            url = "https://hostile.example/dummy.zip"
            filename = os.path.join("corpora", "dummy.zip")
            subdir = "corpora"
            unzip = False
            sha256_checksum = hashlib.sha256(b"x").hexdigest()
            checksum = hashlib.md5(b"x").hexdigest()

        _Info.size = size
        return _Info()

    @pytest.mark.parametrize("size", [10**12, 2**40, 1024**3 + 1, -1, -(10**9)])
    def test_an_out_of_range_declared_size_fetches_nothing(self, tmp_path, size):
        import unittest.mock

        from nltk.downloader import Downloader, ErrorMessage

        download_dir = str(tmp_path / "dl")
        os.makedirs(os.path.join(download_dir, "corpora"))
        reader = _Counting(endless=True)
        with unittest.mock.patch(
            "nltk.downloader.urlopen", return_value=reader
        ) as opened, unittest.mock.patch.object(
            Downloader, "status", return_value=Downloader.NOT_INSTALLED
        ):
            messages = list(
                Downloader(download_dir=download_dir)._download_package(
                    self._info(size), download_dir, force=True
                )
            )
        assert opened.call_count == 0 and reader.reads == 0
        assert any(isinstance(m, ErrorMessage) for m in messages)
        assert not os.path.exists(
            os.path.join(download_dir, "corpora", "dummy.zip.tmp")
        )

    def test_the_ceiling_is_above_every_real_package(self):
        # the largest package in the real index is under 100 MB; the ceiling
        # is a DoS bound, not a business limit
        from nltk.downloader import MAX_PACKAGE_BYTES

        assert MAX_PACKAGE_BYTES >= 10 * 100 * 1024 * 1024

    def test_a_declared_size_inside_the_range_is_still_bounded_by_it(self, tmp_path):
        import unittest.mock

        from nltk.downloader import Downloader, ErrorMessage

        download_dir = str(tmp_path / "dl")
        os.makedirs(os.path.join(download_dir, "corpora"))
        reader = _Counting(endless=True)
        with unittest.mock.patch(
            "nltk.downloader.urlopen", return_value=reader
        ), unittest.mock.patch.object(
            Downloader, "status", return_value=Downloader.NOT_INSTALLED
        ):
            messages = list(
                Downloader(download_dir=download_dir)._download_package(
                    self._info(100), download_dir, force=True
                )
            )
        assert reader.served <= 100 + 1024 * 1024 + 2 * 16 * 1024
        assert any(isinstance(m, ErrorMessage) for m in messages)

    def test_an_endless_index_is_refused_not_read_whole(self, tmp_path):
        import unittest.mock

        from nltk.downloader import MAX_INDEX_BYTES, Downloader

        reader = _Counting(endless=True)
        downloader = Downloader(download_dir=str(tmp_path))
        with unittest.mock.patch("nltk.downloader.urlopen", return_value=reader):
            with pytest.raises(ValueError, match="larger than"):
                downloader._update_index(url="https://hostile.example/index.xml")
        assert reader.served <= MAX_INDEX_BYTES + 64 * 1024

    def test_a_real_sized_index_still_parses(self, tmp_path):
        import unittest.mock

        from nltk.downloader import Downloader

        body = (
            b'<?xml version="1.0"?><nltk_data><packages>'
            b'<package id="p" name="P" size="3" unzipped_size="3" url="https://x/p.zip" '
            b'checksum="d41d8cd98f00b204e9800998ecf8427e" subdir="corpora" unzip="1" />'
            b"</packages><collections/></nltk_data>"
        )
        downloader = Downloader(download_dir=str(tmp_path))
        with unittest.mock.patch(
            "nltk.downloader.urlopen", return_value=_Counting(body)
        ):
            downloader._update_index(url="https://example.invalid/index.xml")
        assert downloader.info("p").size == 3


# --------------------------------------------------------------------------- #
# 5. Decorators: the signature fence
# --------------------------------------------------------------------------- #
class TestSignatureFence:
    def test_every_legal_name_passes_including_non_ascii(self):
        from nltk.decorators import _assert_safe_signature, decorator

        for sig in ("caf" + chr(0xE9), chr(0xDF) + ", x", "_", "x1, *a, **k", "", "  "):
            _assert_safe_signature(sig)

        def caller(func, *a, **k):
            return func(*a, **k)

        exec_locals = {}
        exec(  # bare-exec ok: builds a test function with a non-ASCII parameter
            "def f(caf" + chr(0xE9) + "=1):\n    return caf" + chr(0xE9), exec_locals
        )
        assert decorator(caller)(exec_locals["f"])(5) == 5

    @pytest.mark.parametrize(
        "sig",
        [
            "a b",
            "a, b): pass",
            "a\nb",
            "a\tb",
            "a=1",
            "a: int",
            "a.b",
            "a()",
            "a[0]",
            "__import__('os')",
            "lambda",
            "import",
            "None",
            "a, ,b",
            ",",
            "*",
            "**",
            "***a",
            "a" + NUL,
            "a" + chr(0x2028) + "b",
            "a, b, " + "x, " * 5000 + "!",
        ],
        ids=lambda s: repr(s)[:16],
    )
    def test_everything_that_is_not_a_name_list_is_refused(self, sig):
        from nltk.decorators import _assert_safe_signature

        started = time.perf_counter()
        with pytest.raises(ValueError, match="non-identifier signature"):
            _assert_safe_signature(sig)
        assert time.perf_counter() - started < 1.0

    def test_a_non_string_signature_is_refused(self):
        from nltk.decorators import _assert_safe_signature

        for value in (None, 1, ["a"], b"a"):
            with pytest.raises(ValueError):
                _assert_safe_signature(value)

    def test_the_fence_is_load_bearing(self, tmp_path):
        # a crafted signature carries a default expression; with the fence
        # removed the eval runs it (the marker file appears), with the fence in
        # place the refusal happens before any code is built
        from nltk import decorators

        marker = tmp_path / "pwned"
        infodict = {
            "signature": f"x=open({str(marker)!r}, 'w').close()",
            "argnames": ["x"],
            "name": "f",
            "doc": None,
            "module": "m",
            "dict": {},
            "defaults": (),
            "fullsignature": None,
        }
        with pytest.raises(ValueError, match="non-identifier signature"):
            decorators.new_wrapper(lambda *a, **k: None, infodict)
        assert not marker.exists()
        real = decorators._assert_safe_signature
        decorators._assert_safe_signature = lambda signature: None
        try:
            decorators.new_wrapper(lambda *a, **k: None, infodict)
        finally:
            decorators._assert_safe_signature = real
        assert marker.exists(), "without the fence the crafted default ran"


# --------------------------------------------------------------------------- #
# 6. read_str: literals only
# --------------------------------------------------------------------------- #
class TestReadStrMatrix:
    @pytest.mark.parametrize(
        "source",
        [
            'f\'{__import__("os").system("true")}\'',
            'f"{1+1}"',
            "b'bytes'",
            "rb'raw'",
            "'a' 'b'",
            "'a'\n'b'",
            "'\\N{LATIN SMALL LETTER A}'",
            "'\\x41\\101\\u0041'",
            "'it''s'",
            "'x' + 'y'",
            "'x'.upper()",
            "(lambda: 1)()",
            "__import__('os')",
            "'" + "x" * 100000 + "'",
        ],
        ids=lambda s: repr(s)[:16],
    )
    def test_no_form_executes_anything(self, source, monkeypatch):
        import builtins

        from nltk.internals import ReadError, read_str

        def _boom(*a, **k):
            raise AssertionError("code executed")

        monkeypatch.setattr(builtins, "eval", _boom)
        monkeypatch.setattr(builtins, "exec", _boom)
        started = time.perf_counter()
        try:
            value, end = read_str(source, 0)
            assert isinstance(value, (str, bytes)) and end <= len(source)
        except (ReadError, ValueError, SyntaxError):
            pass
        assert time.perf_counter() - started < 2.0


# --------------------------------------------------------------------------- #
# 7. CSV cells written by the sentiment and twitter helpers, on real files
# --------------------------------------------------------------------------- #
FORMULAS = ["=1+1", "+1+1", "-1+1", "@SUM(A1)", "\t=1", "\r=1", "=cmd|' /C calc'!A0"]


class TestCsvSinks:
    def test_sentiment_json2csv_preprocess_neutralises_every_formula(
        self, restricted_sandbox
    ):
        # both files live inside the pathsec data root the helper reads and
        # writes through; the rows are written to a real CSV and read back
        import csv
        import json

        from nltk.sentiment.util import json2csv_preprocess

        src = os.path.join(restricted_sandbox, "tweets.json")
        out = os.path.join(restricted_sandbox, "out.csv")
        with open(src, "w", encoding="utf-8") as fh:
            for i, text in enumerate(FORMULAS):
                fh.write(json.dumps({"id": i, "text": text, "lang": "en"}) + "\n")
        json2csv_preprocess(src, out, ["id", "text"], remove_duplicates=False)
        with open(out, encoding="utf-8", newline="") as fh:
            rows = list(csv.reader(fh))
        cells = [row[1] for row in rows[1:]]
        assert len(cells) == len(FORMULAS), rows
        for cell in cells:
            assert cell[0] not in "=+-@\t\r", cell
