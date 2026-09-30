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


class _HistoricalReader(SeekableUnicodeStreamReader):
    """readline exactly as it was before GHSA-j8g8 was fixed: it re-split the
    whole buffer on every block (quadratic on one long line) but was fast on
    ordinary short lines. Kept as the reference for byte-identical output and
    for the per-line cost ordinary files must not exceed."""

    def readline(self, size=None):
        if self.linebuffer and len(self.linebuffer) > 1:
            line = self.linebuffer.pop(0)
            self._rewind_numchars += len(line)
            return line
        readsize = size or 72
        chars = ""
        if self.linebuffer:
            chars += self.linebuffer.pop()
            self.linebuffer = None
        while True:
            startpos = self.stream.tell() - len(self.bytebuffer)
            new_chars = self._read(readsize)
            if new_chars and new_chars.endswith("\r"):
                new_chars += self._read(1)
            chars += new_chars
            lines = chars.splitlines(True)
            if len(lines) > 1:
                line = lines[0]
                self.linebuffer = lines[1:]
                self._rewind_numchars = len(new_chars) - (len(chars) - len(line))
                self._rewind_checkpoint = startpos
                break
            elif len(lines) == 1:
                line0withend = lines[0]
                line0withoutend = lines[0].splitlines(False)[0]
                if line0withend != line0withoutend:
                    line = line0withend
                    break
            if not new_chars or size is not None:
                line = chars
                break
            if readsize < 8000:
                readsize *= 2
        return line


def _all_lines(reader_cls, data, encoding="utf-8", size=None):
    r = reader_cls(io.BytesIO(data), encoding)
    out = []
    while True:
        line = r.readline(size) if size else r.readline()
        if not line:
            return out
        out.append(line)


class TestBoundaryCheck:
    """The boundary check readline runs on each fresh span agrees with
    str.splitlines on every code point and on every mix, costs no regex, and
    keeps ordinary files as fast as the historical readline."""

    BOUNDARY_SET = frozenset(
        [
            "\n",
            "\r",
            "\v",
            "\f",
            chr(0x1C),
            chr(0x1D),
            chr(0x1E),
            chr(0x85),
            chr(0x2028),
            chr(0x2029),
        ]
    )

    def test_agrees_with_splitlines_on_every_code_point(self):
        from nltk.data import _has_line_boundary

        wrong = [
            hex(cp)
            for cp in range(0x110000)
            if _has_line_boundary(chr(cp)) != (chr(cp) in self.BOUNDARY_SET)
        ]
        assert wrong == []

    @pytest.mark.parametrize("seed", range(10))
    def test_agrees_on_random_mixes_and_edges(self, seed):
        from nltk.data import _has_line_boundary

        rng = random.Random(seed)
        alphabet = ["a", " ", chr(0x200D), chr(0xA0)] + sorted(self.BOUNDARY_SET)
        for _ in range(3000):
            s = "".join(rng.choice(alphabet) for _ in range(rng.randint(0, 12)))
            assert _has_line_boundary(s) == (not self.BOUNDARY_SET.isdisjoint(s)), repr(
                s
            )
        assert _has_line_boundary("") is False
        assert (
            _has_line_boundary("\r\n") is True
            and _has_line_boundary("x" * 9000) is False
        )

    def test_readline_uses_no_regex(self):
        import inspect

        import nltk.data as data

        src = inspect.getsource(data.SeekableUnicodeStreamReader.readline)
        assert "redos" not in src and ".search(" not in src and "_RE" not in src

    @pytest.mark.parametrize("seed", range(6))
    def test_output_is_byte_identical_to_the_historical_readline(self, seed):
        rng = random.Random(seed)
        pieces = []
        for _ in range(rng.randint(50, 400)):
            pieces.append(
                "".join(rng.choice("ab cé") for _ in range(rng.randint(0, 300)))
            )
            pieces.append(rng.choice(BOUNDARIES + ["", "\r", "\r\n"]))
        data = "".join(pieces).encode("utf-8")
        assert _all_lines(SeekableUnicodeStreamReader, data) == _all_lines(
            _HistoricalReader, data
        )
        assert _all_lines(SeekableUnicodeStreamReader, data, size=50) == _all_lines(
            _HistoricalReader, data, size=50
        )

    def test_ordinary_lines_cost_no_more_than_the_historical_readline(self):
        # One file of ordinary short lines, read whole by both implementations,
        # best of five: the fixed readline must stay within twice the historical
        # per-line cost (the timed-regex version ran at about five times it).
        data = (
            "the quick brown fox jumps over the lazy dog, again and again\n" * 60000
        ).encode()

        def elapsed(cls):
            started = time.perf_counter()
            _all_lines(cls, data)
            return time.perf_counter() - started

        # alternate the two, so a load change during the test cannot favour
        # whichever implementation happened to run second
        best = dict.fromkeys(
            (_HistoricalReader, SeekableUnicodeStreamReader), float("inf")
        )
        for _ in range(5):
            for cls in best:
                best[cls] = min(best[cls], elapsed(cls))
        historical, current = best[_HistoricalReader], best[SeekableUnicodeStreamReader]
        assert current <= 2.0 * historical, (current, historical, current / historical)


class TestSplitDirectlyBound:
    """readline splits a small buffer directly and asks the boundary check only
    past _SPLIT_DIRECTLY_BELOW; lines of every length around that switch, with
    every boundary and a CR LF straddling it, come back exactly as
    str.splitlines gives them."""

    @pytest.mark.parametrize("delta", [-73, -2, -1, 0, 1, 2, 73, 8000])
    @pytest.mark.parametrize("boundary", ["\n", "\r", "\r\n", chr(0x2028), chr(0x85)])
    def test_lines_around_the_switch(self, delta, boundary):
        from nltk.data import _SPLIT_DIRECTLY_BELOW

        n = _SPLIT_DIRECTLY_BELOW + delta
        text = "a" * n + boundary + "b" * (n // 2) + boundary + "tail"
        data = text.encode("utf-8")
        assert _all_lines(SeekableUnicodeStreamReader, data) == text.splitlines(True)
        assert _all_lines(SeekableUnicodeStreamReader, data) == _all_lines(
            _HistoricalReader, data
        )

    def test_a_cr_lf_straddling_every_block_edge_past_the_switch(self):
        from nltk.data import _SPLIT_DIRECTLY_BELOW

        for n in range(_SPLIT_DIRECTLY_BELOW - 20, _SPLIT_DIRECTLY_BELOW + 20):
            text = "a" * n + "\r\n" + "b\r\n"
            assert _all_lines(SeekableUnicodeStreamReader, text.encode()) == [
                "a" * n + "\r\n",
                "b\r\n",
            ]

    def test_a_carried_complete_line_past_the_switch_reads_no_further(self):
        # The line buffer can hand readline one complete line longer than the
        # switch. The previous span's last character is what lets the boundary
        # check see its end: without it readline pulls the whole next line first.
        from nltk.data import _SPLIT_DIRECTLY_BELOW

        before = sum(72 * 2**k for k in range(7))  # read before the 9216 span
        first = "a" * (before + 10) + "\n"
        second = "b" * (9216 - 12) + "\n"  # fills the rest of that span exactly
        assert len(second) > _SPLIT_DIRECTLY_BELOW
        third = "c" * (4 * _SPLIT_DIRECTLY_BELOW) + "\n"
        stream = io.BytesIO((first + second + third).encode("utf-8"))
        reader = SeekableUnicodeStreamReader(stream, "utf-8")
        assert reader.readline() == first
        assert reader.linebuffer == [second]
        position = stream.tell()
        assert reader.readline() == second
        assert stream.tell() - position < len(third)
        assert reader.readline() == third

    def test_the_switch_keeps_one_long_line_linear(self):
        def op(n):
            SeekableUnicodeStreamReader(io.BytesIO(b"a" * n), "utf-8").readline()

        _assert_subquadratic(op, 400_000, 1_600_000)

    def test_forcing_every_block_to_split_goes_quadratic(self, monkeypatch):
        # the teeth: a check that reports a boundary everywhere makes readline
        # re-split the whole growing buffer on every pass past the switch
        import nltk.data as data
        from nltk.test.unit.test_quadratic_dos import _elapsed

        monkeypatch.setattr(data, "_has_line_boundary", lambda text: True)

        def op(n):
            SeekableUnicodeStreamReader(io.BytesIO(b"a" * n), "utf-8").readline()

        small = min(_elapsed(lambda: op(300_000)) for _ in range(2))
        big = min(_elapsed(lambda: op(1_200_000)) for _ in range(2))
        assert big / max(small, 1e-3) > 8, (small, big)
