# Natural Language Toolkit: expanded attack harness for the readline guard
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
"""SeekableUnicodeStreamReader.readline driven with the widest matrix, judged
against Python's own line splitting on the same bytes: every line boundary at
every block edge, encodings and decode errors, seek and tell around long lines,
a single oversized line and a flood of tiny ones in bounded time and memory,
and the real corpora read back byte for byte. Nothing is mocked."""

import hashlib
import io
import os
import random
import time
import tracemalloc

import pytest

from nltk.data import SeekableUnicodeStreamReader
from nltk.test.unit.test_quadratic_dos import _assert_subquadratic

MiB = 1024 * 1024
BOUNDARIES = ["\n", "\r", "\r\n", "\v", "\f", "\x1c", "\x1d", "\x1e", "\x85", " ", " "]


def _reader(data, encoding="utf-8", errors="strict"):
    return SeekableUnicodeStreamReader(io.BytesIO(data), encoding, errors)


class TestReadlineReparse:  # GHSA-j8g8: the grow-and-reparse of a long line
    def test_correctness_preserved(self):
        r = _reader(b"line1\nline2\nline3\n")
        assert [r.readline(), r.readline(), r.readline()] == [
            "line1\n",
            "line2\n",
            "line3\n",
        ]
        assert _reader(b"a\r\nb\r\n").readlines() == ["a\r\n", "b\r\n"]

    def test_unterminated_line_is_linear(self):
        def op(n):
            _reader(b"a" * n).readline()

        _assert_subquadratic(op, 200_000, 800_000)


class TestAgainstPythonsOwnSplit:
    @pytest.mark.parametrize("boundary", BOUNDARIES, ids=lambda b: repr(b))
    @pytest.mark.parametrize(
        "offset", [0, 1, 70, 71, 72, 73, 143, 144, 145, 8000, 8001]
    )
    def test_a_boundary_at_every_block_edge(self, boundary, offset):
        text = "x" * offset + boundary + "y" * 5 + boundary + "tail"
        data = text.encode("utf-8")
        assert _reader(data).readlines() == text.splitlines(True)
        assert list(_reader(data)) == text.splitlines(True)

    @pytest.mark.parametrize("seed", range(12))
    def test_random_mixes_are_byte_identical(self, seed):
        rng = random.Random(seed)
        pieces = []
        for _ in range(rng.randint(1, 400)):
            pieces.append(
                "".join(rng.choice("ab cé ‍") for _ in range(rng.randint(0, 200)))
            )
            pieces.append(rng.choice(BOUNDARIES + [""]))
        text = "".join(pieces)
        assert _reader(text.encode("utf-8")).readlines() == text.splitlines(True)

    @pytest.mark.parametrize(
        "encoding", ["utf-8", "utf-16", "utf-16-le", "utf-32", "latin-1", "cp1252"]
    )
    def test_other_encodings_split_the_same_lines(self, encoding):
        text = "first\r\nsecond\rthird\nfourth\u0085fifth"
        if encoding in ("latin-1", "cp1252"):
            text = (
                text.replace("\u0085", "\x85")
                if encoding == "latin-1"
                else text.replace("\u0085", "")
            )
        data = text.encode(encoding)
        assert _reader(data, encoding).readlines() == text.splitlines(True)

    def test_a_decode_error_inside_a_line_is_reported_or_replaced(self):
        data = b"good line\nbad \xff byte\nlast\n"
        with pytest.raises(UnicodeDecodeError):
            _reader(data).readlines()
        lines = _reader(data, errors="replace").readlines()
        assert lines == ["good line\n", "bad � byte\n", "last\n"]

    def test_size_returns_at_most_that_many_characters_and_resumes(self):
        text = "abcdefghij\nsecond\n"
        r = _reader(text.encode("utf-8"))
        first = r.readline(4)
        assert first and len(first) <= 4 and text.startswith(first)
        rest = first + r.readline() + r.readline()
        assert rest == text


class TestSeekTellAndSiblings:
    def test_tell_and_seek_round_trip_around_a_long_line(self):
        long = "z" * 20000
        text = "short\n" + long + "\nend\n"
        r = _reader(text.encode("utf-8"))
        assert r.readline() == "short\n"
        pos = r.tell()
        assert r.readline() == long + "\n"
        after = r.tell()
        r.seek(pos)
        assert r.readline() == long + "\n"
        assert r.tell() == after
        assert r.readline() == "end\n" and r.readline() == ""

    def test_discard_line_and_char_seek_forward(self):
        r = _reader(b"one\ntwo\nthree\n")
        r.discard_line()
        assert r.readline() == "two\n"
        r = _reader(b"abcdef\nghi\n")
        r.char_seek_forward(3)
        assert r.readline() == "def\n"
        r = _reader(b"a\nb\nc\n")
        assert list(r.xreadlines()) == ["a\n", "b\n", "c\n"]
        r = _reader(b"a\nb\nc")
        assert r.readlines(keepends=False) == ["a", "b", "c"]


class TestBounded:
    def test_a_single_oversized_line_is_read_whole_in_bounded_time_and_memory(self):
        size = 32 * MiB
        data = b"a" * size + b"\nrest\n"
        tracemalloc.start()
        started = time.perf_counter()
        try:
            r = _reader(data)
            line = r.readline()
            peak = tracemalloc.get_traced_memory()[1]
        finally:
            tracemalloc.stop()
        elapsed = time.perf_counter() - started
        assert len(line) == size + 1 and line.endswith("\n")
        assert r.readline() == "rest\n"
        assert elapsed < 30, elapsed
        assert (
            peak < 8 * size
        ), peak  # the spans, their join and the line, never a quadratic copy chain

    def test_a_flood_of_tiny_lines_is_linear(self):
        def op(n):
            r = _reader(b"x\n" * n)
            count = 0
            while r.readline():
                count += 1
            assert count == n

        _assert_subquadratic(op, 50_000, 200_000)

    def test_a_line_of_only_boundaries_splits_into_empty_lines(self):
        text = "\n" * 5000 + "\r\n" * 5000 + " " * 5000
        assert _reader(text.encode("utf-8")).readlines() == text.splitlines(True)


class TestRealCorpora:
    """The readers built on readline give back the real files, and the
    corpora count what the documentation says they count."""

    def _path(self, name):
        import nltk.data

        try:
            return str(nltk.data.find(name))
        except LookupError:
            pytest.skip(f"{name} is not installed")

    @pytest.mark.parametrize(
        "fileid", ["austen-emma.txt", "shakespeare-macbeth.txt", "bible-kjv.txt"]
    )
    def test_gutenberg_files_read_back_byte_for_byte(self, fileid):
        path = self._path("corpora/gutenberg/" + fileid)
        with open(path, "rb") as fh:
            raw = fh.read()
        expected = raw.decode("latin-1").splitlines(True)
        with open(path, "rb") as fh:
            got = SeekableUnicodeStreamReader(fh, "latin-1").readlines()
        assert got == expected
        from nltk.corpus import gutenberg

        assert (
            hashlib.sha256(gutenberg.raw(fileid).encode("latin-1")).hexdigest()
            == hashlib.sha256(raw).hexdigest()
        )

    def test_the_documented_corpus_sizes(self):
        self._path("corpora/brown")
        self._path("corpora/treebank/combined")
        from nltk.corpus import brown, treebank

        assert len(brown.words()) == 1161192
        assert len(brown.sents()) == 57340
        assert len(treebank.parsed_sents()) == 3914
        assert treebank.words()[:3] == ["Pierre", "Vinken", ","]
