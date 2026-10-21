# Natural Language Toolkit: expanded attack harness for the translate guards
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
"""The AlignedSent sinks driven with the widest attack matrix, benign neighbours
included, judged by what the sink receives: the DOT text handed to Graphviz,
the repr and str a terminal shows, the alignment indices that index the word
lists. Nothing is mocked; the Graphviz stand-in is a real executable that
returns exactly the bytes it was given."""

import os
import stat
import subprocess
import sys

import pytest

from nltk.translate.api import AlignedSent, Alignment

NUL = chr(0)
ESC = chr(0x1B)
BEL = chr(0x07)
DOT_ATTACKS = [
    'x"] ; evil [label="',
    'x" -- "y" [label="',
    "x\\",
    "x\\\\",
    'x\\"',
    "x\ny",
    "x\ry",
    "x\r\ny",
    "x" + chr(0x2028) + "y",
    "x" + chr(0x2029) + "y",
    "x" + chr(0x85) + "y",
    "x\ty",
    "x" + ESC + "]0;evil" + BEL + "y",
    "x" + NUL + "y",
    "}",
    "{rank = same; evil}",
    "<b>x</b>",
    "x//comment",
    "x/*c*/y",
    "x#y",
    "é",
    "\U0001f600",
    "a" * 5000,
    "",
]
BENIGN = ["klein", "ist", "das", "Haus", "New-York", "caf" + chr(0xE9), "x_source"]


def _unescaped_quotes(dot):
    """Count double quotes that are not escaped by an odd run of backslashes."""
    count = 0
    for line in dot.split("\n"):
        i = 0
        while i < len(line):
            if line[i] == "\\":
                i += 2
                continue
            if line[i] == '"':
                count += 1
            i += 1
    return count


def _statement_lines(dot):
    return [line for line in dot.split("\n")[2:] if line and line != "}"]


def _check_dot(dot, words, mots, edges):
    """Structural invariants of the graph AlignedSent draws: exactly the
    expected statements, every quote balanced per line, no raw line break."""
    lines = dot.split("\n")
    assert lines[0] == "graph align {" and lines[1] == "node[shape=plaintext]"
    assert lines[-1] == "}", lines[-1]
    body = _statement_lines(dot)
    invisible = max(len(words) - 1, 0) + max(len(mots) - 1, 0)
    assert len(body) == len(words) + len(mots) + edges + invisible + 2, dot
    assert "\r" not in dot
    for line in lines:
        assert _unescaped_quotes(line) % 2 == 0, line
    for w in words + mots:
        assert (
            w.replace("\\", "\\\\")
            .replace('"', '\\"')
            .replace("\n", "\\n")
            .replace("\r", "\\r")
            in dot
            or w == ""
        ), w


class TestDotMatrix:
    @pytest.mark.parametrize("attack", DOT_ATTACKS, ids=lambda w: repr(w)[:16])
    @pytest.mark.parametrize("side", ["words", "mots"])
    def test_a_word_on_either_side_never_breaks_out(self, side, attack):
        words, mots = ["ok", "fine"], ["x", "y"]
        (words if side == "words" else mots)[0] = attack
        sent = AlignedSent(words, mots, Alignment.fromstring("0-0 1-1"))
        if NUL in attack:
            with pytest.raises(ValueError, match="NUL"):
                sent._to_dot()
            return
        dot = sent._to_dot()
        _check_dot(dot, words, mots, edges=2)

    def test_a_lying_str_subclass_is_escaped_from_its_real_characters(self):
        class Lying(str):
            def __str__(self):
                return "safe"

            def __contains__(self, item):
                return False

            def replace(self, old, new, count=-1):
                return str.__str__(self)

        sent = AlignedSent(
            [Lying('x"] ; evil [label="'), "ok"], ["y"], Alignment.fromstring("0-0")
        )
        dot = sent._to_dot()
        assert 'x\\"] ; evil [label=\\"' in dot and "safe" not in dot
        _check_dot(dot, ['x"] ; evil [label="', "ok"], ["y"], edges=1)

    def test_a_non_str_word_is_rendered_from_what_it_renders_to(self):
        class Renders:
            def __str__(self):
                return 'x"y'

        sent = AlignedSent([Renders(), 7], [None], Alignment.fromstring("0-0"))
        dot = sent._to_dot()
        assert (
            '"x\\"y_source"' in dot and '"7_source"' in dot and '"None_target"' in dot
        )

    def test_benign_sentence_renders_exactly(self):
        words, mots = ["klein", "ist", "das", "Haus"], ["the", "house", "is", "small"]
        sent = AlignedSent(words, mots, Alignment.fromstring("0-3 1-2 2-0 3-1"))
        dot = sent._to_dot()
        _check_dot(dot, words, mots, edges=4)
        assert '"klein_source" [label="klein"]' in dot
        assert '"klein_source" -- "small_target"' in dot
        assert (
            '{rank = same; "klein_source" "ist_source" "das_source" "Haus_source"}'
            in dot
        )

    def test_an_unaligned_source_word_draws_no_edge_and_inverts(self):
        sent = AlignedSent(["a", "b"], ["x"], Alignment([(0, 0), (1, None)]))
        dot = sent._to_dot()
        _check_dot(dot, ["a", "b"], ["x"], edges=1)
        assert '"a_source" -- "x_target"' in dot and "None" not in dot
        assert sent.invert().alignment == Alignment([(0, 0)])


class TestAlignmentValidation:
    def test_a_non_alignment_is_refused_with_a_type_error(self):
        with pytest.raises(TypeError, match="Alignment"):
            AlignedSent(["a"], ["b"], [(0, 0)])
        with pytest.raises(TypeError, match="Alignment"):
            AlignedSent(["a"], ["b"], frozenset({(0, 0)}))

    @pytest.mark.parametrize("pairs", ["1-0", "0-1", "5-5", "0-0 3-0"])
    def test_an_index_outside_the_sentence_is_refused(self, pairs):
        with pytest.raises(IndexError):
            AlignedSent(["a"], ["b"], Alignment.fromstring(pairs))

    @pytest.mark.parametrize(
        "text", ["x-0", "0-x", "0", "0-0-0", "-1-0", "0--1", "1e3-0", "0-0\x000-0"]
    )
    def test_a_malformed_giza_string_is_refused(self, text):
        with pytest.raises(ValueError):
            Alignment.fromstring(text)

    def test_the_checks_survive_python_dash_o(self):
        code = (
            "from nltk.translate.api import AlignedSent, Alignment\n"
            "for bad in ([(0, 0)], Alignment.fromstring('3-0')):\n"
            "    try:\n"
            "        AlignedSent(['a'], ['b'], bad)\n"
            "    except (TypeError, IndexError) as e:\n"
            "        print(type(e).__name__)\n"
            "    else:\n"
            "        print('ACCEPTED')\n"
        )
        root = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        )
        completed = subprocess.run(
            [sys.executable, "-O", "-c", code],
            capture_output=True,
            text=True,
            timeout=120,
            env={**os.environ, "PYTHONPATH": root},
        )
        assert completed.returncode == 0, completed.stderr
        assert completed.stdout.split() == ["TypeError", "IndexError"], completed.stdout


class TestReprAndStr:
    def test_control_sequences_are_shown_escaped_never_raw(self):
        word = "x" + ESC + "]0;evil" + BEL + "y"
        sent = AlignedSent([word, "ok"], ["\n", "z"], Alignment.fromstring("0-0"))
        text = repr(sent)
        assert ESC not in text and BEL not in text and "\n" not in text
        assert "\\x1b]0;evil\\x07" in text and "'\\n'" in text
        shown = str(sent)
        assert ESC not in shown and BEL not in shown and "\n" not in shown
        assert shown.startswith("<AlignedSent: '") and shown.endswith("...'>")

    def test_benign_repr_and_str_are_unchanged(self):
        sent = AlignedSent(
            ["klein", "ist", "das", "Haus"],
            ["the", "house", "is", "small"],
            Alignment.fromstring("0-3 1-2 2-0 3-1"),
        )
        assert repr(sent) == (
            "AlignedSent(['klein', 'ist', 'das', 'Haus'], ['the', 'house', 'is', 'small'], "
            "Alignment([(0, 3), (1, 2), (2, 0), (3, 1)]))"
        )
        assert (
            str(sent)
            == "<AlignedSent: 'klein ist das Haus...' -> 'the house is small...'>"
        )


class TestReprSvg:
    @pytest.mark.skipif(os.name != "posix", reason="a shell script stand-in for dot")
    def test_the_dot_text_reaches_the_binary_escaped(self, monkeypatch):
        """A real executable named dot on a private directory in PATH (under
        the home, not /tmp: the trusted spawn refuses a world-writable
        ancestor by design); it returns exactly what it was fed, so the SVG
        hook's output shows the DOT text Graphviz would receive, hostile word
        already escaped."""
        import shutil
        import uuid
        from pathlib import Path

        from nltk import pathsec

        home = Path.home()
        if not pathsec.is_private_dir(str(home)):
            pytest.skip(
                "the home directory is not private, so no stand-in can be trusted"
            )
        bindir = home / f".nltk_dot_stub_{os.getpid()}_{uuid.uuid4().hex[:8]}"
        bindir.mkdir(mode=0o700)
        try:
            stub = bindir / "dot"
            stub.write_text(
                "#!/bin/sh\nexec /bin/cat\n"
            )  # the trusted spawn hands it a PATH that resolves nothing
            stub.chmod(0o700)
            monkeypatch.setenv("PATH", str(bindir))
            monkeypatch.chdir(bindir)
            sent = AlignedSent(
                ['x"] ; evil [label="', "ok"], ["y"], Alignment.fromstring("0-0")
            )
            out = sent._repr_svg_()
            assert out == sent._to_dot()
            assert 'x\\"] ; evil [label=\\"' in out
            _check_dot(out, ['x"] ; evil [label="', "ok"], ["y"], edges=1)
        finally:
            shutil.rmtree(bindir, ignore_errors=True)


class TestFunctional:
    """The translate models built on AlignedSent still learn what they did."""

    def _bitext(self):
        return [
            AlignedSent(
                ["klein", "ist", "das", "haus"], ["the", "house", "is", "small"]
            ),
            AlignedSent(
                ["das", "haus", "ist", "ja", "groß"], ["the", "house", "is", "big"]
            ),
            AlignedSent(
                ["das", "buch", "ist", "ja", "klein"], ["the", "book", "is", "small"]
            ),
            AlignedSent(["das", "haus"], ["the", "house"]),
            AlignedSent(["das", "buch"], ["the", "book"]),
            AlignedSent(["ein", "buch"], ["a", "book"]),
        ]

    def test_ibm_model_1_learns_the_documented_table(self):
        from nltk.translate import IBMModel1

        bitext = self._bitext()
        ibm1 = IBMModel1(bitext, 5)
        assert round(ibm1.translation_table["buch"]["book"], 3) == 0.889
        assert round(ibm1.translation_table["das"]["book"], 3) == 0.062
        assert round(ibm1.translation_table["buch"][None], 3) == 0.113
        assert round(ibm1.translation_table["ja"][None], 3) == 0.073
        assert bitext[2].alignment == Alignment(
            [(0, 0), (1, 1), (2, 2), (3, 2), (4, 3)]
        )

    def test_ibm_model_2_learns_the_documented_alignment(self):
        from nltk.translate import IBMModel2

        bitext = self._bitext()
        ibm2 = IBMModel2(bitext, 5)
        assert round(ibm2.translation_table["buch"]["book"], 3) == 1.0
        assert round(ibm2.translation_table["das"]["book"], 3) == 0.0
        assert round(ibm2.alignment_table[1][1][2][2], 3) == 0.939
        assert bitext[2].alignment == Alignment(
            [(0, 0), (1, 1), (2, 2), (3, 2), (4, 3)]
        )

    def test_alignment_helpers(self):
        a = Alignment.fromstring("0-0 2-1 9-2 21-3 10-4 7-5")
        assert a == Alignment([(0, 0), (2, 1), (7, 5), (9, 2), (10, 4), (21, 3)])
        assert a[2] == [(2, 1)] and a[3] == []
        assert a.invert() == Alignment(
            [(0, 0), (1, 2), (2, 9), (3, 21), (4, 10), (5, 7)]
        )
        assert a.range([2, 9]) == [1, 2]
        sent = AlignedSent(["a", "b"], ["x", "y"], Alignment.fromstring("0-1 1-0"))
        assert sent.invert().words == [
            "x",
            "y",
        ] and sent.invert().alignment == Alignment([(0, 1), (1, 0)])


def _null_corpus():
    """Three pairs on which every IBM model leaves ``the`` unaligned (#3967)."""
    return [
        AlignedSent(["the", "cat"], ["katze"]),
        AlignedSent(["the", "dog"], ["hund"]),
        AlignedSent(["the", "book"], ["buch"]),
    ]


def _aligned(pairs):
    """The ``(i, j)`` pairs of ``pairs`` with a target, sorted."""
    return sorted((p[0], p[1]) for p in pairs if p[1] is not None)


def _every_surface(alignment, words, mots):
    """Drive every surface of an alignment and the sentence carrying it; the
    values each one must show for the pairs that have a target."""
    pairs = list(alignment)
    aligned = _aligned(pairs)
    assert str(alignment) == " ".join(f"{i}-{j}" for i, j in aligned)
    assert eval(repr(alignment), {"Alignment": Alignment}) == alignment
    assert alignment.range() == sorted({j for _, j in aligned})
    for i in {p[0] for p in pairs}:
        assert alignment.range([i]) == sorted({j for ii, j in aligned if ii == i})
        assert {p[:2] for p in alignment[i]} == {p[:2] for p in pairs if p[0] == i}
    inverted = alignment.invert()
    assert inverted == Alignment(
        [(p[1], p[0]) + tuple(p[2:]) for p in pairs if p[1] is not None]
    )
    assert all(p[1] is not None for p in inverted)
    sent = AlignedSent(words, mots, alignment)
    _check_dot(sent._to_dot(), words, mots, edges=len(aligned))
    assert "None" not in sent._to_dot()
    assert repr(sent) == f"AlignedSent({words!r}, {mots!r}, {alignment!r})"
    assert str(sent).startswith("<AlignedSent: '")
    return sent


NULL_SHAPES = [
    [(0, None), (1, 0)],
    [(0, None), (0, 1)],
    [(2, None), (0, 1), (1, 0)],
    [(0, None), (1, None)],
    [(0, None, "S"), (0, 1, "P")],
    [(0, 0, True), (1, 1, "P")],
    [(1, None, "S", 0.5), (0, 0)],
    [],
]


class TestNullTargetSurface:
    """An unaligned pair ``(i, None)``, the shape every IBM model emits for a
    word it leaves unaligned (#1885, #3967), on every surface of an alignment:
    shown, listed, ranged, indexed, inverted and drawn, never a TypeError."""

    @pytest.mark.parametrize("pairs", NULL_SHAPES)
    def test_every_surface_survives_an_unaligned_or_extended_pair(self, pairs):
        words = [f"w{i}" for i in range(max([p[0] for p in pairs] + [0]) + 1)]
        mots = [
            f"m{j}"
            for j in range(max([p[1] for p in pairs if p[1] is not None] + [0]) + 1)
        ]
        _every_surface(Alignment(pairs), words, mots)

    @pytest.mark.parametrize("model", [1, 2, 3, 4, 5])
    def test_what_every_ibm_model_emits_is_shown_on_every_surface(self, model):
        from nltk import translate

        corpus = _null_corpus()
        kwargs = {}
        if model >= 4:
            kwargs = {
                "source_word_classes": {w: 0 for s in corpus for w in s.mots},
                "target_word_classes": {w: 0 for s in corpus for w in s.words},
            }
        getattr(translate, f"IBMModel{model}")(corpus, 2, **kwargs)
        for sent in corpus:
            assert sent.alignment == Alignment([(0, None), (1, 0)])
            assert str(sent.alignment) == "1-0"
            assert repr(sent.alignment) == "Alignment([(0, None), (1, 0)])"
            assert sent.alignment.range() == [0] and sent.alignment.range([0]) == []
            _every_surface(sent.alignment, sent.words, sent.mots)

    def test_an_unaligned_pair_sorts_before_the_aligned_pairs_of_its_word(self):
        a = Alignment([(0, 2), (0, None), (0, 1), (1, 0)])
        assert repr(a) == "Alignment([(0, None), (0, 1), (0, 2), (1, 0)])"
        assert str(a) == "0-1 0-2 1-0"
        # integer-only alignments keep the documented tuple order
        b = Alignment.fromstring("0-0 2-1 9-2 21-3 10-4 7-5")
        assert (
            repr(b) == "Alignment([(0, 0), (2, 1), (7, 5), (9, 2), (10, 4), (21, 3)])"
        )

    def test_a_none_source_index_is_refused_at_the_sentence(self):
        # None is only ever a target: a pair with no source word is not a
        # position in the sentence, and the sentence refuses it (TypeError).
        with pytest.raises(TypeError):
            AlignedSent(["a"], ["b"], Alignment([(None, 0)]))
        with pytest.raises(TypeError):
            Alignment([(0, 0), (None, 1)])

    @pytest.mark.parametrize("pairs", [[(0,)], [("0", "0")], [(True, 0)], [(-1, 0)]])
    def test_a_pair_that_is_not_two_positions_is_refused_at_the_sentence(self, pairs):
        with pytest.raises((TypeError, IndexError)):
            AlignedSent(["a"], ["b"], Alignment(pairs))


_HUGE_INDEX = "9" * 4300


def _huge_surfaces(text):
    a = Alignment.fromstring(text)
    big = int(_HUGE_INDEX)
    assert a[0] == [(0, 0)] and a[big] == [(big, big)] and a[1] == []
    assert a.range() == [0, big] and a.range([big]) == [big]
    assert str(a) == f"0-0 {_HUGE_INDEX}-{_HUGE_INDEX}"
    assert eval(repr(a), {"Alignment": Alignment}) == a
    assert a.invert() == a


class TestGizaInput:
    """GIZA text is the attacker's channel into an alignment (a corpus file):
    every surface stays sparse on a huge index (CWE-770; CVE-2026-12837) and
    the malformed forms are refused."""

    def test_every_surface_stays_sparse_on_a_huge_index(self):
        from nltk.test.unit import timing

        text = f"0-0 {_HUGE_INDEX}-{_HUGE_INDEX}"
        run = timing.run_in_process(_huge_surfaces, (text,), budget=2.0, cpu_bound=True)
        assert run.finished and run.exitcode == 0 and run.within_budget, run

    def test_the_surfaces_scale_linearly_in_the_pair_count(self):
        from nltk.test.unit import timing

        def op(n):
            a = Alignment.fromstring(" ".join(f"{i}-{i}" for i in range(n)))
            str(a), repr(a), a.range(), a.invert(), a[0]

        timing.assert_subquadratic(op, 10000, 40000, reps=2, cpu_bound=True)

    @pytest.mark.parametrize(
        "text",
        [
            "0-0" + NUL + "1-1",
            "1-2-3",
            "0-0 1",
            "0-0 -",
            "0- 0",
            "a-b",
            "0-0 " + "9" * 5000 + "-1",
            "1.0-2",
            "0x1-0",
        ],
    )
    def test_a_malformed_pair_is_refused(self, text):
        with pytest.raises(ValueError):
            Alignment.fromstring(text)

    def test_bytes_are_refused(self):
        with pytest.raises(TypeError):
            Alignment.fromstring(b"0-0")
