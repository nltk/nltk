# Natural Language Toolkit: subprocess input-injection guard tests
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""Several external-tool wrappers write caller-supplied tokens/sentences/ids into
a structured input (a CoNLL file, a newline-per-sentence stdin, a Graphviz DOT
graph) that a subprocess then reads. A token carrying a
record delimiter could inject or corrupt records in that input. These tests
drive each real guard: they reach the guarded code path on a minimally built
instance (the guard fires before any binary is looked up or spawned, so no
external tool is required, and nothing is mocked)."""

import tempfile

import pytest

# 1. CoNLL builder (used by MaltParser) - a pure generator, no binary needed.


# 3/5. Stanford tagger and Stanford segmenter: newline-per-sentence input.
# (senna's guard moved to #3858, which routes senna through pathsec.spawn_trusted
# and keeps a per-token CR/LF check.)
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


# (Boxer's candc <META> discourse-stream guard moved to #3858, tested in
# test_boxer_security.py alongside its pathsec.spawn_trusted routing.)


# 7/8. Graphviz DOT label breakout: escape, do not reject (rendering must survive
# a legitimate quote in a word).
