# Natural Language Toolkit: expanded attack harness for the Stanford input guards
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
"""The newline-per-sentence input guards of the Stanford tagger and segmenter
driven with every line-unsafe character class, benign neighbours included; where
a real tool is installed it runs for real. The CoNLL, DOT, downloader-bound,
decorator-fence and read_str matrices this file once held moved to develop with
the consolidations (#3926, #3927), whose harnesses carry them."""

import os

import pytest

# Every character class has_line_unsafe_char refuses, spelled with chr()
LINE_BREAKS = [chr(c) for c in (0x0A, 0x0D, 0x0B, 0x0C, 0x1C, 0x1D, 0x1E, 0x85)]
SEPARATORS = [chr(0x2028), chr(0x2029)]
CONTROLS = [chr(c) for c in (0x00, 0x01, 0x07, 0x08, 0x09, 0x1B, 0x7F, 0x9B)]
SURROGATE = chr(0xD800)
UNSAFE = LINE_BREAKS + SEPARATORS + CONTROLS + [SURROGATE]


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

    def test_an_empty_sentence_list_and_empty_sentences_pass_the_guard(
        self, restricted_sandbox, monkeypatch
    ):
        # nothing to refuse: the guard lets these through to the (absent) tool,
        # which is the pre-existing behaviour; the LookupError comes from the
        # jar lookup, not from the input check. Reaching the tool stage creates
        # the process-wide staging directory, so it is staged inside this
        # test's own data root and the cache is restored afterwards, or later
        # sandboxed tests would inherit a scratch directory outside their root
        import nltk.data

        monkeypatch.setattr(nltk.data, "_STAGING_TEMPDIR", None)
        for sentences in ([], [[]], [["a"], []]):
            with pytest.raises((LookupError, AttributeError, TypeError, OSError)):
                _bare_stanford_tagger().tag_sents(sentences)

    @staticmethod
    def _real_tagger_install():
        """(jar, model) of a Stanford POS tagger installed inside a data root,
        else None."""
        import glob

        import nltk.data

        # only an install inside a data root: the wrapper bounds its model to
        # the data roots, so a tool directory elsewhere (the CI's third-party
        # download) is refused by design and is not this test's subject
        homes = []
        for root in nltk.data.path:
            homes += glob.glob(os.path.join(root, "stanford-postagger*"))
        for home in [h for h in homes if h and os.path.isdir(h)]:
            jars = [
                j
                for j in glob.glob(os.path.join(home, "stanford-postagger*.jar"))
                if not j.endswith(("-sources.jar", "-javadoc.jar"))
            ]
            model = os.path.join(home, "models", "english-bidirectional-distsim.tagger")
            if jars and os.path.isfile(model):
                return jars[0], model
        return None

    def test_real_tagger_refuses_the_injection_and_still_tags(self, monkeypatch):
        # executed for real: the refusal is the guard, the tagging is the tool
        from nltk.tag.stanford import StanfordPOSTagger

        install = self._real_tagger_install()
        if install is None:
            pytest.skip("no Stanford POS tagger install inside a data root")
        jar, model = install
        jdk = "/Users/alvas/nltk_tools/jdk/jdk-21.0.12.1+1/Contents/Home"
        if not os.environ.get("JAVA_HOME") and os.path.isdir(jdk):
            monkeypatch.setenv("JAVA_HOME", jdk)
        import nltk.internals as internals

        monkeypatch.setattr(internals, "_java_bin", None)
        try:
            tagger = StanfordPOSTagger(model, jar, java_options="-mx1g")
        except (LookupError, PermissionError, ValueError, OSError) as e:
            pytest.skip(f"Stanford POS tagger not usable here: {e}")
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
# 5. Decorators: the signature fence
# --------------------------------------------------------------------------- #


# --------------------------------------------------------------------------- #
# 6. read_str: literals only
# --------------------------------------------------------------------------- #
