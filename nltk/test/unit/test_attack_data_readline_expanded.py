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
import tracemalloc

import pytest

from nltk.data import SeekableUnicodeStreamReader
from nltk.test.unit import timing
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
        with timing.budget(30, "one oversized line") as clock:
            try:
                r = _reader(data)
                line = r.readline()
                peak = tracemalloc.get_traced_memory()[1]
            finally:
                tracemalloc.stop()
        elapsed = clock.charged
        assert len(line) == size + 1 and line.endswith("\n")
        assert r.readline() == "rest\n"
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
        """One file of ordinary short lines, read whole by both implementations,
        best of five: the fixed readline must stay within twice the historical
        per-line cost (the timed-regex version ran at about five times it).
        Measured in process CPU time on a file that takes a few tenths of a
        second: a busy runner stretches the wall clock, not the work, and the
        Windows CPU clock steps in 15.6 ms (a 60k-line file read 2.5x there)."""
        data = (
            "the quick brown fox jumps over the lazy dog, again and again\n" * 240000
        ).encode()

        def elapsed(cls):
            return timing.charged(_all_lines, cls, data, cpu_bound=True)

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

        monkeypatch.setattr(data, "_has_line_boundary", lambda text: True)

        def op(n):
            SeekableUnicodeStreamReader(io.BytesIO(b"a" * n), "utf-8").readline()

        # runs that clear the helper's 0.1 s floor on the fastest runner: a
        # 300k run took 18 ms on Windows and 20 ms on macOS, and a 900k one
        # 40 ms of CPU on ubuntu, where the floored quadratic read 6.1x
        ratio = timing.scaling_ratio(op, 1_800_000, 7_200_000, reps=2, cpu_bound=True)
        assert ratio > 8, ratio


def _trace(reader_cls, data, encoding="utf-8", sizes=(None,) * 60, errors="strict"):
    """Every line and the tell() after it, or the decode error that ended the read."""
    stream = data if hasattr(data, "read") else io.BytesIO(data)
    r = reader_cls(stream, encoding, errors)
    out = []
    for size in sizes:
        try:
            line = r.readline(size)
        except UnicodeDecodeError as e:
            out.append(("UnicodeDecodeError", e.start, e.end))
            break
        out.append((line, r.tell()))
        if not line:
            break
    return out


def _assert_same_trace(data, **kw):
    # a stream object can be consumed once, so a factory hands out a fresh one
    make = data if callable(data) else (lambda: data)
    historical = _trace(_HistoricalReader, make(), **kw)
    current = _trace(SeekableUnicodeStreamReader, make(), **kw)
    assert current == historical, (
        current[: len(historical)][-1:],
        historical[: len(current)][-1:],
    )


# chars read before the 9216-character span: 72, 144, ..., 4608 (the read size
# doubles until it reaches 8000, so the span after these is 72 * 128)
_BEFORE_LAST_SPAN = sum(72 * 2**k for k in range(7))


def _carried(term):
    """A file whose second line, ending in *term*, fills the last span exactly.

    readline then hands that complete line, longer than the switch, over in the
    line buffer. The exact length depends on the boundary, so search around it
    and return None when no length reaches the carried state.
    """
    first = "a" * (_BEFORE_LAST_SPAN + 10) + "\n"
    third = "c" * (4 * 8192) + "\n"
    for extra in range(-3, 4):
        second = "b" * (9216 - 12 - len(term) + 1 + extra) + term
        r = _reader((first + second + third).encode("utf-8"))
        assert r.readline() == first
        if r.linebuffer == [second] and len(second) > 8192:
            return first, second, third
    return None


class _ShortReadStream(io.RawIOBase):
    """A real raw stream that hands out at most *chunk* bytes per read (a pipe or
    socket does this), so every read the reader makes can come back short."""

    def __init__(self, data, chunk, seed=None):
        self._data = io.BytesIO(data)
        self._chunk = chunk
        self._rng = random.Random(seed) if seed is not None else None

    def readable(self):
        return True

    def seekable(self):
        return True

    def readinto(self, buffer):
        most = self._chunk if self._rng is None else self._rng.randint(1, self._chunk)
        got = self._data.read(min(len(buffer), most))
        buffer[: len(got)] = got
        return len(got)

    def seek(self, offset, whence=0):
        return self._data.seek(offset, whence)

    def tell(self):
        return self._data.tell()


class TestCarriedLines:
    """A complete line the line buffer hands to the next readline call, longer
    than the switch, with every boundary and at end of stream: readline must
    return it without reading on, and lines and tell() must match the
    historical reader."""

    @pytest.mark.parametrize("term", [b for b in BOUNDARIES if b != "\r"])
    def test_every_boundary_reads_no_further(self, term):
        # a carried complete line can end in a bare CR only at end of stream:
        # a CR inside a span makes readline read one more character, so the
        # span never ends there (test_at_end_of_stream covers that case)
        first, second, third = _carried(term)
        data = (first + second + third).encode("utf-8")
        r = _reader(data)
        assert r.readline() == first
        position = r.stream.tell()
        assert r.readline() == second
        assert r.stream.tell() - position < len(third)
        _assert_same_trace(data)

    @pytest.mark.parametrize("encoding", ["utf-8", "utf-16"])
    @pytest.mark.parametrize(
        "tail", ["b" * 9000 + "\r", "b" * 9204 + "\n", "b" * 9000, "b" * 9204 + "\r\n"]
    )
    def test_at_end_of_stream(self, tail, encoding):
        first = "a" * (_BEFORE_LAST_SPAN + 10) + "\n"
        _assert_same_trace((first + tail).encode(encoding), encoding=encoding)

    def test_seek_and_tell_land_inside_the_carried_line(self):
        # readline must split on the span that holds the boundary: splitting
        # later leaves a negative rewind count behind, and tell() then loops
        # forever instead of failing (the no-prefix variant did exactly that)
        first, second, third = _carried("\n")
        data = (first + second + third + "tail\n").encode("utf-8")
        results = []
        for cls in (_HistoricalReader, SeekableUnicodeStreamReader):
            r = cls(io.BytesIO(data), "utf-8")
            assert r.readline() == first
            position = r.tell()
            r.seek(position)
            again = r.readline()
            r2 = cls(io.BytesIO(data), "utf-8")
            r2.readline()
            r2.readline()
            inside = r2.tell()
            r2.seek(inside)
            results.append((position, again, inside, r2.readline(), r2.tell()))
        assert results[0] == results[1]
        assert results[1][1] == second and results[1][3] == third

    def test_a_negative_rewind_count_raises_instead_of_looping(self):
        r = _reader(b"abc\ndef\nghi\n")
        assert r.readline() == "abc\n"
        assert r._rewind_numchars >= 0
        r._rewind_numchars = -1
        with pytest.raises(ValueError):
            r.tell()

    def test_iteration_discard_and_char_seek_after_the_carried_line(self):
        first, second, third = _carried("\n")
        text = first + second + third + "tail\n"
        data = text.encode("utf-8")
        assert list(_reader(data)) == text.splitlines(True)
        results = []
        for cls in (_HistoricalReader, SeekableUnicodeStreamReader):
            r = cls(io.BytesIO(data), "utf-8")
            r.readline()
            r.discard_line()
            r.char_seek_forward(5)
            results.append((r.readline(), r.tell(), r.readline(), r.tell()))
        assert results[0] == results[1]


class TestReadShapesAroundTheSwitch:
    """size arguments, encodings, decode errors and short reads placed at and
    around the split bound and the span edges, judged against the historical
    reader on lines and tell() alike."""

    @pytest.mark.parametrize("size", [8191, 8192, 8193, 9215, 9216, 9217, 20000, 10**6])
    @pytest.mark.parametrize("shape", ["long", "short", "mixed"])
    def test_size_calls_straddling_the_switch(self, size, shape):
        rng = random.Random(size)
        if shape == "long":
            text = "x" * 30000 + "\n" + "y" * 100 + "\n"
        elif shape == "short":
            text = "".join(
                "w" * rng.randint(0, 80) + rng.choice(BOUNDARIES) for _ in range(500)
            )
        else:
            text = "".join(
                "w" * rng.choice([0, 10, 8000, 8192, 9000, 20000])
                + rng.choice(BOUNDARIES)
                for _ in range(30)
            )
        data = text.encode("utf-8")
        _assert_same_trace(data, sizes=(size,) * 60)
        _assert_same_trace(data, sizes=(size, None) * 30)

    @pytest.mark.parametrize(
        "encoding",
        [
            "utf-16",
            "utf-16-le",
            "utf-16-be",
            "utf-32",
            "utf-32-le",
            "utf-32-be",
            "utf-8-sig",
        ],
    )
    @pytest.mark.parametrize("n", [10, 71, 72, 73, 8191, 8192, 8193, 9215, 9216, 9217])
    def test_wide_and_bom_encodings_with_cr_lf_at_every_edge(self, encoding, n):
        # after a CR readline reads one more byte, which in a wide encoding is
        # half a code unit: the reader must still see the LF and split alike
        text = (
            "a" * n + "\r\n" + "b" * n + "\r" + "c" * 20 + "\r\n" + "d" * 20000 + "\n"
        )
        _assert_same_trace(text.encode(encoding), encoding=encoding)

    @pytest.mark.parametrize(
        "at", [8190, 8191, 8192, 8193, 9215, 9216, 9217, 18359, 18360]
    )
    @pytest.mark.parametrize("errors", ["strict", "replace", "ignore"])
    def test_a_decode_error_at_the_switch(self, at, errors):
        bad = b"a" * at + b"\xff" + b"a" * 100 + b"\n" + b"rest\n"
        _assert_same_trace(bad, errors=errors)
        truncated = b"a" * at + "é".encode()[:1] + b"\n" + b"rest\n"
        _assert_same_trace(truncated, errors=errors)

    @pytest.mark.parametrize(
        "chunk, lengths, pieces",
        [
            (1, [0, 10, 100, 8191, 8192, 8193], 6),
            (7, [0, 10, 8000, 8191, 8192, 8193, 20000], 12),
            (100, [0, 10, 8000, 8191, 8192, 8193, 20000], 12),
        ],
    )
    def test_a_stream_that_returns_short_reads(self, chunk, lengths, pieces):
        # one byte per read makes the historical oracle and the tell() check
        # quadratic per line, so that case keeps its lines at the switch edges
        rng = random.Random(chunk)
        text = "".join(
            "w" * rng.choice(lengths) + rng.choice(BOUNDARIES) for _ in range(pieces)
        )
        data = text.encode("utf-8")
        _assert_same_trace(lambda: _ShortReadStream(data, chunk))
        _assert_same_trace(lambda: _ShortReadStream(data, chunk, seed=chunk))
        wide = text.encode("utf-16")
        _assert_same_trace(lambda: _ShortReadStream(wide, chunk), encoding="utf-16")
        assert _all_lines(SeekableUnicodeStreamReader, data) == text.splitlines(True)

    @pytest.mark.parametrize("term", BOUNDARIES)
    def test_a_file_of_only_boundaries_past_the_switch(self, term):
        text = term * 20000
        data = text.encode("utf-8")
        assert _all_lines(SeekableUnicodeStreamReader, data) == text.splitlines(True)
        _assert_same_trace(data, sizes=(None,) * 20100)

    def test_mixed_boundaries_only(self):
        rng = random.Random(30000)
        text = "".join(rng.choice(BOUNDARIES) for _ in range(30000))
        data = text.encode("utf-8")
        assert _all_lines(SeekableUnicodeStreamReader, data) == text.splitlines(True)
        _assert_same_trace(data, sizes=(None,) * 30100)

    def test_short_lines_then_one_long_line_stay_linear(self):
        prefix = b"short line\n" * 1000

        def op(n):
            r = _reader(prefix + b"a" * n)
            while r.readline():
                pass

        _assert_subquadratic(op, 400_000, 1_600_000)

    @pytest.mark.parametrize("seed", range(40))
    def test_random_traces_with_the_readers_own_tell_check(self, seed):
        # DEBUG makes tell() re-decode the stream at the position it computed
        # and compare it with the line buffer: the reader checks itself
        rng = random.Random(seed)
        pieces = []
        for _ in range(rng.randint(1, 10)):
            pieces.append(
                rng.choice("xyz")
                * rng.choice(
                    [0, 1, 71, 72, 73, 8191, 8192, 8193, 9215, 9216, 9217, 20000]
                )
            )
            pieces.append(rng.choice(BOUNDARIES))
        text = "".join(pieces)
        sizes = [
            rng.choice([None, None, 1, 50, 72, 8192, 9000, 20000]) for _ in range(30)
        ]
        assert SeekableUnicodeStreamReader.DEBUG
        for encoding in ("utf-8", "utf-16"):
            _assert_same_trace(text.encode(encoding), encoding=encoding, sizes=sizes)
