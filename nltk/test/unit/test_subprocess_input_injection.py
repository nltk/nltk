# Natural Language Toolkit: subprocess input-injection guard tests
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""Several external-tool wrappers write caller-supplied tokens/sentences/ids into
a structured input (a CoNLL file, a newline-per-sentence stdin, a candc <META>
stream, a Graphviz DOT graph) that a subprocess then reads. A token carrying a
record delimiter could inject or corrupt records in that input. These tests
drive each real guard: they reach the guarded code path on a minimally built
instance (the guard fires before any binary is looked up or spawned, so no
external tool is required, and nothing is mocked)."""

import tempfile

import pytest


# 1. CoNLL builder (used by MaltParser) - a pure generator, no binary needed.
class TestConllInjection:
    def test_legit_sentence_builds(self):
        from nltk.parse.util import taggedsent_to_conll

        rows = list(taggedsent_to_conll([("John", "NN"), ("runs", "VB")]))
        assert len(rows) == 2 and all(r.endswith("\n") for r in rows)

    @pytest.mark.parametrize(
        "pair",
        [
            ("a\tb", "NN"),  # tab adds a CoNLL column
            ("a\nb", "NN"),  # newline injects a CoNLL row
            ("a\rb", "NN"),
            ("w", "N\tN"),
            ("w", "N\nN"),
            ("w", "N\x00N"),
        ],
    )
    def test_delimiter_in_field_refused(self, pair):
        from nltk.parse.util import taggedsent_to_conll

        with pytest.raises(ValueError, match="tab, newline or NUL"):
            list(taggedsent_to_conll([pair]))


# 3/4/5. Stanford tagger, senna, Stanford segmenter: newline-per-sentence input.
def _min(cls, **attrs):
    obj = object.__new__(cls)
    for k, v in attrs.items():
        setattr(obj, k, v)
    return obj


class TestNewlinePerSentenceInjection:
    def test_stanford_tagger_refuses_newline_token(self):
        from nltk.tag.stanford import StanfordPOSTagger

        tagger = _min(StanfordPOSTagger, _encoding="utf8")
        with pytest.raises(ValueError, match="newline"):
            tagger.tag_sents([["good"], ["ev\nil"]])

    def test_senna_refuses_newline_token(self):
        from nltk.classify.senna import Senna

        senna = _min(Senna, _encoding="utf8")
        with pytest.raises(ValueError, match="newline"):
            senna.tag_sents([["ev\nil"]])

    def test_stanford_segmenter_refuses_newline_token(self):
        from nltk.tokenize.stanford_segmenter import StanfordSegmenter

        seg = _min(StanfordSegmenter, _encoding="utf8")
        with pytest.raises(ValueError, match="newline"):
            seg.segment_sents([["ev\ril"]])


# 6. REPP tokenizer: newline-per-sentence temp file.
class TestReppInjection:
    def test_repp_refuses_newline_sentence(self):
        from nltk.tokenize.repp import ReppTokenizer

        with tempfile.TemporaryDirectory() as d:
            repp = _min(ReppTokenizer, working_dir=d, encoding="utf8")
            with pytest.raises(ValueError, match="newline"):
                list(repp.tokenize_sents(["a real sentence", "ev\nil"]))


# 2. Boxer candc <META> discourse stream.
class TestBoxerCandcInjection:
    def test_newline_in_discourse_id_refused(self):
        from nltk.sem.boxer import Boxer

        boxer = object.__new__(Boxer)
        with pytest.raises(ValueError, match="discourse id"):
            boxer._call_candc([["a sentence"]], ["ok\n<META>'evil"], question=False)

    def test_quote_in_discourse_id_refused(self):
        from nltk.sem.boxer import Boxer

        boxer = object.__new__(Boxer)
        with pytest.raises(ValueError, match="discourse id"):
            boxer._call_candc([["a sentence"]], ["x'y"], question=False)

    def test_newline_in_input_line_refused(self):
        from nltk.sem.boxer import Boxer

        boxer = object.__new__(Boxer)
        with pytest.raises(ValueError, match="newline"):
            boxer._call_candc([["line one\nline two"]], ["d0"], question=False)

    def test_meta_marker_in_input_line_refused(self):
        from nltk.sem.boxer import Boxer

        boxer = object.__new__(Boxer)
        with pytest.raises(ValueError, match="META"):
            boxer._call_candc([["<META>'spoofed'"]], ["d0"], question=False)


# 7/8. Graphviz DOT label breakout: escape, do not reject (rendering must survive
# a legitimate quote in a word).
def _no_unescaped_breakout(dot):
    # After removing escaped backslashes and escaped quotes, every DOT line must
    # have balanced delimiter quotes and hold no raw newline injected mid-value.
    for line in dot.splitlines():
        stripped = line.replace("\\\\", "").replace('\\"', "")
        if stripped.count('"') % 2 != 0:
            return False
    return True


class TestDotEscaping:
    def test_dependencygraph_escapes_quote_and_newline(self):
        from nltk.parse.dependencygraph import DependencyGraph

        dg = DependencyGraph('ev"il N 2\nloves V 0\nMary N 2')
        dot = dg.to_dot()
        assert '\\"' in dot  # the quote is escaped
        assert _no_unescaped_breakout(dot)

    def test_alignedsent_escapes_quote_and_newline(self):
        from nltk.translate.api import AlignedSent, Alignment

        a = AlignedSent(
            ['a"b', "c\nd", "ok"], ["x", "y", "z"], Alignment.fromstring("0-0 1-1 2-2")
        )
        dot = a._to_dot()
        assert '\\"' in dot and "\\n" in dot  # quote and newline escaped
        assert "\nd" not in dot.replace("\\n", "")  # no raw newline injected
        assert _no_unescaped_breakout(dot)

    def test_dependencygraph_legit_still_renders(self):
        from nltk.parse.dependencygraph import DependencyGraph

        dg = DependencyGraph("John N 2\nloves V 0\nMary N 2")
        dot = dg.to_dot()
        assert 'label="0 (None)"' in dot and "John" in dot
