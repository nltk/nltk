# Natural Language Toolkit: expanded attack harness for the Stanford input guards
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
"""The newline-per-sentence input guards of the Stanford tagger and segmenter
(CWE-93: a token carrying a line break injects an extra tool input line and
silently misaligns the output; a tab, NUL or control character is re-split or
truncated by the tool) driven with every line-unsafe character class, lying
objects, wrong encodings, a planted symlink at the staged input path and
benign neighbours that must pass. Where the real tools are installed inside a
data root they run for real, on fixed sentences with exact expected output,
and the wrapper's result is compared token for token with a direct java
invocation of the same jar and model on the same input. Nothing is mocked."""

import glob
import hashlib
import os
import sys
import tempfile
import unicodedata

import pytest

import nltk.data
from nltk import pathsec
from nltk.pathsec import has_line_unsafe_char
from nltk.test.unit import timing

#: seconds a direct JVM run has, as the budget and as the hang deadline
_JAVA_BUDGET = 600

# Every character class has_line_unsafe_char refuses, spelled with chr()
LINE_BREAKS = [chr(c) for c in (0x0A, 0x0D, 0x0B, 0x0C, 0x1C, 0x1D, 0x1E, 0x85)]
SEPARATORS = [chr(0x2028), chr(0x2029)]
CONTROLS = [chr(c) for c in (0x00, 0x01, 0x07, 0x08, 0x09, 0x1B, 0x7F, 0x9B)]
SURROGATE = chr(0xD800)
UNSAFE = LINE_BREAKS + SEPARATORS + CONTROLS + [SURROGATE]

# Ordinary token content the guard must let through: accented, non-breaking
# space, combining mark, CJK, Arabic with tatweel, emoji with a selector, the
# joiners real scripts need, a soft hyphen, an astral code point.
BENIGN = [
    "caf" + chr(0xE9),
    "x" + chr(0xA0) + "y",
    "e" + chr(0x301),
    chr(0x4E2D) + chr(0x6587),
    chr(0x639) + chr(0x640) + chr(0x631),
    chr(0x2764) + chr(0xFE0F),
    "a" + chr(0x200D) + "b" + chr(0x200C) + "c",
    "a" + chr(0xAD) + "b",
    chr(0x1F600),
]

JDK = "/Users/alvas/nltk_tools/jdk/jdk-21.0.12.1+1/Contents/Home"


def _bare_tagger():
    from nltk.tag.stanford import StanfordPOSTagger

    tagger = StanfordPOSTagger.__new__(StanfordPOSTagger)
    tagger._encoding = "utf8"
    return tagger


def _bare_segmenter():
    from nltk.tokenize.stanford_segmenter import StanfordSegmenter

    seg = StanfordSegmenter.__new__(StanfordSegmenter)
    seg._encoding = "utf8"
    return seg


class _Liar(str):
    """A str whose iteration and membership hide its real buffer."""

    def __iter__(self):
        return iter("clean")

    def __contains__(self, item):
        return False

    def __len__(self):
        return 5


# ------------------------------------------------------------------------- #
# The guard itself
# ------------------------------------------------------------------------- #
class TestStanfordInputGuard:
    def test_the_refused_set_is_exactly_the_documented_one(self):
        # the guard's docstring: every Cc, Zl, Zp and Cs code point, nothing
        # else; that set covers every str.splitlines boundary and the tab
        refused = {
            cp
            for cp in range(0x110000)
            if has_line_unsafe_char(chr(cp)) and not 0xDC00 <= cp <= 0xDFFF
        }
        expected = {
            cp
            for cp in range(0x110000)
            if unicodedata.category(chr(cp)) in ("Cc", "Zl", "Zp", "Cs")
            and not 0xDC00 <= cp <= 0xDFFF
        }
        assert refused == expected
        boundaries = {cp for cp in range(0x110000) if chr(cp).splitlines() != [chr(cp)]}
        assert boundaries <= refused and 0x09 in refused

    @pytest.mark.parametrize("bad", UNSAFE, ids=lambda c: "U+%04X" % ord(c))
    def test_every_unsafe_character_in_a_token_is_refused_before_any_lookup(self, bad):
        # the guard runs before the model, the jar or the JVM is looked up, so
        # a bare instance is enough and no tool is spawned
        with pytest.raises(ValueError):
            _bare_tagger().tag_sents([["ok", "a" + bad + "b"]])
        with pytest.raises(ValueError):
            _bare_segmenter().segment_sents([["ok", "a" + bad + "b"]])

    @pytest.mark.parametrize("position", ["first", "middle", "last", "own-sentence"])
    def test_the_position_of_the_unsafe_token_does_not_matter(self, position):
        token = "ev" + chr(0x0A) + "il"
        sentences = {
            "first": [[token, "b", "c"]],
            "middle": [["a", token, "c"]],
            "last": [["a", "b", token]],
            "own-sentence": [["a", "b"], [token]],
        }[position]
        with pytest.raises(ValueError, match="newline"):
            _bare_tagger().tag_sents(sentences)
        with pytest.raises(ValueError, match="newline"):
            _bare_segmenter().segment_sents(sentences)

    def test_a_lying_str_subclass_cannot_hide_a_line_break(self):
        # iteration and membership lie, but the join and count run on the real
        # buffer, so the second check (one separator per sentence gap) refuses
        for bad in (chr(0x0A), chr(0x0D)):
            with pytest.raises(ValueError, match="newline"):
                _bare_tagger().tag_sents([[_Liar("ev" + bad + "il")]])
            with pytest.raises(ValueError, match="newline"):
                _bare_segmenter().segment_sents([[_Liar("ev" + bad + "il")]])

    @pytest.mark.parametrize("token", [b"bytes", 1, None, ["list"]])
    def test_a_non_str_token_fails_before_any_file_is_staged(self, token):
        with pytest.raises((TypeError, AttributeError)):
            _bare_tagger().tag_sents([["ok", token]])
        with pytest.raises((TypeError, AttributeError)):
            _bare_segmenter().segment_sents([["ok", token]])

    @pytest.mark.parametrize("token", BENIGN, ids=lambda t: "U+%04X" % ord(t[-1]))
    def test_benign_tokens_pass_the_guard(self, token):
        # past the guard a bare instance has no model to re-check: that error,
        # not ValueError, is the proof the token was accepted
        with pytest.raises(AttributeError):
            _bare_tagger().tag_sents([["ok", token]])

    def test_an_empty_sentence_list_and_empty_sentences_pass_the_guard(
        self, restricted_sandbox, monkeypatch
    ):
        # nothing to refuse: the guard lets these through to the (absent) tool,
        # which is the pre-existing behaviour. Reaching the tool stage creates
        # the process-wide staging directory, so it is staged inside this
        # test's own data root and the cache is restored afterwards
        monkeypatch.setattr(nltk.data, "_STAGING_TEMPDIR", None)
        for sentences in ([], [[]], [["a"], []]):
            with pytest.raises((LookupError, AttributeError, TypeError, OSError)):
                _bare_tagger().tag_sents(sentences)

    def test_the_guard_is_linear_in_the_input(self):
        def op(n):
            with pytest.raises(AttributeError):
                _bare_tagger().tag_sents([["w" * 8] * n])

        # the guard only computes (a scan and a count), so its CPU time is its
        # cost: declared, not left to the share heuristic on a loaded runner
        timing.assert_subquadratic(op, 250_000, 1_000_000, cpu_bound=True)


# ------------------------------------------------------------------------- #
# The staged input file
# ------------------------------------------------------------------------- #
def _tagger_with_a_model_in(root):
    """A tagger whose model is a small file inside *root*: enough to pass the
    model re-check and reach the staging step without a jar or a JVM."""
    from nltk.tag.stanford import StanfordPOSTagger

    model = os.path.join(root, "english.tagger")
    with open(model, "wb") as fh:
        fh.write(b"not a real model")
    os.chmod(model, 0o600)
    tagger = StanfordPOSTagger.__new__(StanfordPOSTagger)
    tagger._encoding = "utf8"
    tagger._stanford_model = model
    tagger._stanford_jar = os.path.join(root, "absent.jar")
    tagger.java_options = "-mx1g"
    return tagger


class TestStagedInputFile:
    def test_a_symlink_planted_at_the_staged_path_is_refused_and_not_followed(
        self, restricted_sandbox, monkeypatch
    ):
        # the input is reopened through pathsec_open, which never follows a
        # link: a file swapped for a symlink between mkstemp and the reopen is
        # refused and the link's target is not written
        import nltk.tag.stanford as module

        monkeypatch.setattr(nltk.data, "_STAGING_TEMPDIR", None)
        tagger = _tagger_with_a_model_in(restricted_sandbox)
        staging = nltk.data.staging_tempdir()
        victim = os.path.join(staging, "victim.txt")
        with open(victim, "w") as fh:
            fh.write("untouched")
        link = os.path.join(staging, "planted")
        os.symlink(victim, link)
        monkeypatch.setattr(
            module.tempfile,
            "mkstemp",
            lambda *a, **k: (os.open(victim, os.O_RDONLY), link),
        )
        with pytest.raises(PermissionError):
            tagger.tag_sents([["ok"]])
        with open(victim) as fh:
            assert fh.read() == "untouched"

    def test_an_unencodable_token_fails_before_the_jvm_and_leaves_no_file(
        self, restricted_sandbox, monkeypatch
    ):
        monkeypatch.setattr(nltk.data, "_STAGING_TEMPDIR", None)
        tagger = _tagger_with_a_model_in(restricted_sandbox)
        tagger._encoding = "ascii"
        staging = nltk.data.staging_tempdir()
        before = set(os.listdir(staging))
        with pytest.raises(UnicodeEncodeError):
            tagger.tag_sents([["caf" + chr(0xE9)]])
        assert set(os.listdir(staging)) == before

    def test_an_unknown_encoding_fails_before_the_jvm_and_leaves_no_file(
        self, restricted_sandbox, monkeypatch
    ):
        monkeypatch.setattr(nltk.data, "_STAGING_TEMPDIR", None)
        tagger = _tagger_with_a_model_in(restricted_sandbox)
        tagger._encoding = "no-such-codec"
        staging = nltk.data.staging_tempdir()
        before = set(os.listdir(staging))
        with pytest.raises(LookupError):
            tagger.tag_sents([["ok"]])
        assert set(os.listdir(staging)) == before


# ------------------------------------------------------------------------- #
# The real tools, with exact expected output and a direct java comparison
# ------------------------------------------------------------------------- #
ENGLISH = [
    ["The", "quick", "brown", "fox", "jumps", "over", "the", "lazy", "dog", "."],
    ["What", "is", "the", "airspeed", "of", "an", "unladen", "swallow", "?"],
]
ENGLISH_TAGS = [
    ["DT", "JJ", "JJ", "NN", "VBZ", "IN", "DT", "JJ", "NN", "."],
    ["WP", "VBZ", "DT", "NN", "IN", "DT", "JJ", "VB", "."],
]
CHINESE = "".join(
    chr(c)
    for c in (
        0x8FD9,
        0x662F,
        0x65AF,
        0x5766,
        0x798F,
        0x4E2D,
        0x6587,
        0x5206,
        0x8BCD,
        0x5668,
        0x6D4B,
        0x8BD5,
    )
)
CHINESE_SEGMENTS = [
    chr(0x8FD9),
    chr(0x662F),
    chr(0x65AF) + chr(0x5766) + chr(0x798F),
    chr(0x4E2D) + chr(0x6587),
    chr(0x5206) + chr(0x8BCD) + chr(0x5668),
    chr(0x6D4B) + chr(0x8BD5),
]
ARABIC = "".join(
    chr(c) for c in (0x648, 0x633, 0x64A, 0x643, 0x62A, 0x628, 0x647, 0x627)
)
ARABIC += " " + "".join(
    chr(c) for c in (0x628, 0x627, 0x644, 0x639, 0x631, 0x628, 0x64A, 0x629)
)
ARABIC_SEGMENTS = [
    chr(0x648),
    chr(0x633),
    "".join(chr(c) for c in (0x64A, 0x643, 0x62A, 0x628)),
    chr(0x647) + chr(0x627),
    chr(0x628),
    "".join(chr(c) for c in (0x627, 0x644, 0x639, 0x631, 0x628, 0x64A, 0x629)),
]


def _in_a_data_root(pattern):
    """Directories matching *pattern* inside a registered data root."""
    homes = []
    for root in nltk.data.path:
        homes += glob.glob(os.path.join(root, pattern))
    return [h for h in homes if os.path.isdir(h)]


def _tagger_install():
    for home in _in_a_data_root("stanford-postagger*"):
        jars = [
            j
            for j in glob.glob(os.path.join(home, "stanford-postagger*.jar"))
            if not j.endswith(("-sources.jar", "-javadoc.jar"))
        ]
        for name in (
            "english-left3words-distsim.tagger",
            "english-bidirectional-distsim.tagger",
        ):
            model = os.path.join(home, "models", name)
            if jars and os.path.isfile(model):
                return jars[0], model
    return None


def _segmenter_install():
    for home in _in_a_data_root("stanford-segmenter*"):
        jars = [
            j
            for j in glob.glob(os.path.join(home, "stanford-segmenter*.jar"))
            if not j.endswith(("-sources.jar", "-javadoc.jar"))
        ]
        data = os.path.join(home, "data")
        if jars and os.path.isdir(data):
            return jars[0], data
    return None


def _java():
    """The JVM the wrappers use, or None with the reason."""
    import nltk.internals as internals

    try:
        internals.config_java()  # sets internals._java_bin, returns nothing
    except LookupError as exc:
        return None, str(exc)[:120]
    return internals._java_bin or "java", None


def _jvm_env(monkeypatch):
    import nltk.internals as internals

    if not os.environ.get("JAVA_HOME") and os.path.isdir(JDK):
        monkeypatch.setenv("JAVA_HOME", JDK)
    monkeypatch.delenv("JAVAHOME", raising=False)
    monkeypatch.setattr(internals, "_java_bin", None)


def _run_java(jar, argv, options=("-mx2g",)):
    java = os.path.join(os.environ["JAVA_HOME"], "bin", "java")
    # the JVM is a child doing the work, judged by the suite's timing rule: a
    # child still running at the deadline is a hang, killed, and fails here
    done, run = timing.run_subprocess(
        [java, *options, "-cp", jar, *argv],
        _JAVA_BUDGET,
        hard_deadline=_JAVA_BUDGET,
        capture_output=True,
        text=True,
    )
    assert done is not None and run.within_budget, run
    assert done.returncode == 0, done.stderr[-500:]
    return done.stdout


class TestRealTagger:
    def test_the_wrapper_tags_as_expected_and_matches_a_direct_invocation(
        self, monkeypatch
    ):
        from nltk.tag.stanford import StanfordPOSTagger

        install = _tagger_install()
        if install is None:
            pytest.skip(
                "no Stanford POS tagger (jar + english model) inside a data root"
            )
        _jvm_env(monkeypatch)
        java, why = _java()
        if java is None:
            pytest.skip("no usable JVM for the Stanford tagger: " + why)
        jar, model = install
        tagger = StanfordPOSTagger(model, jar, java_options="-mx1g")
        tagged = tagger.tag_sents(ENGLISH)
        assert [[w for w, _ in s] for s in tagged] == ENGLISH
        assert [[t for _, t in s] for s in tagged] == ENGLISH_TAGS
        # the same jar, model and flags on the same input, run directly
        with tempfile.NamedTemporaryFile(
            "w",
            suffix=".txt",
            delete=False,
            encoding="utf8",
            dir=os.path.dirname(model),
        ) as fh:
            fh.write("\n".join(" ".join(s) for s in ENGLISH))
            path = fh.name
        try:
            argv = [path if a == tagger._input_file_path else a for a in tagger._cmd]
            direct = _run_java(jar, argv + ["-encoding", "utf8"], ("-mx1g",))
        finally:
            os.unlink(path)
        assert tagger.parse_output(direct, ENGLISH) == tagged
        # the guard, on the real wrapper: refused before the JVM, then tagging
        # continues to work on the next call
        with pytest.raises(ValueError, match="newline"):
            tagger.tag_sents([["The", "quick" + chr(0x0A) + "brown", "fox"]])
        assert tagger.tag_sents([ENGLISH[1]]) == [tagged[1]]


class TestRealSegmenter:
    def _segmenter(self, jar, data, lang):
        from nltk.tokenize.stanford_segmenter import StanfordSegmenter

        digest = hashlib.sha256(open(jar, "rb").read()).hexdigest()
        if lang == "zh":
            return (
                StanfordSegmenter(
                    path_to_jar=jar,
                    java_class="edu.stanford.nlp.ie.crf.CRFClassifier",
                    path_to_sihan_corpora_dict=data,
                    path_to_model=os.path.join(data, "pku.gz"),
                    path_to_dict=os.path.join(data, "dict-chris6.ser.gz"),
                    sihan_post_processing="true",
                    java_options="-mx2g",
                ),
                digest,
            )
        return (
            StanfordSegmenter(
                path_to_jar=jar,
                java_class="edu.stanford.nlp.international.arabic.process.ArabicSegmenter",
                path_to_model=os.path.join(
                    data, "arabic-segmenter-atb+bn+arztrain.ser.gz"
                ),
                java_options="-mx2g",
            ),
            digest,
        )

    @pytest.mark.parametrize("lang", ["zh", "ar"])
    def test_the_wrapper_segments_as_expected_and_matches_a_direct_invocation(
        self, lang, monkeypatch
    ):
        install = _segmenter_install()
        if install is None:
            pytest.skip("no Stanford segmenter (jar + data) inside a data root")
        jar, data = install
        model = os.path.join(
            data,
            "pku.gz" if lang == "zh" else "arabic-segmenter-atb+bn+arztrain.ser.gz",
        )
        if not os.path.isfile(model):
            pytest.skip(f"the {lang} segmenter model {model} is not installed")
        _jvm_env(monkeypatch)
        java, why = _java()
        if java is None:
            pytest.skip("no usable JVM for the Stanford segmenter: " + why)
        seg, digest = self._segmenter(jar, data, lang)
        monkeypatch.setenv("NLTK_SEGMENTER_ALLOW_SHA256", digest)
        text = CHINESE if lang == "zh" else ARABIC
        expected = CHINESE_SEGMENTS if lang == "zh" else ARABIC_SEGMENTS
        sentences = [list(text)] if lang == "zh" else [text.split()]
        out = seg.segment_sents(sentences)
        assert out.split() == expected
        # the same jar, model, class and flags on the same input, run directly
        with tempfile.NamedTemporaryFile(
            "w", suffix=".txt", delete=False, encoding="utf8", dir=data
        ) as fh:
            fh.write(" ".join(sentences[0]))
            path = fh.name
        try:
            argv = [
                seg._java_class,
                "-loadClassifier",
                model,
                "-keepAllWhitespaces",
                "false",
                "-textFile",
                path,
            ]
            if lang == "zh":
                argv += [
                    "-serDictionary",
                    os.path.join(data, "dict-chris6.ser.gz"),
                    "-sighanCorporaDict",
                    data,
                    "-sighanPostProcessing",
                    "true",
                ]
            direct = _run_java(jar, argv + ["-inputEncoding", "UTF-8"])
        finally:
            os.unlink(path)
        assert direct.split() == out.split() == expected
        # the guard on the real wrapper, then segmenting still works
        with pytest.raises(ValueError, match="newline"):
            seg.segment_sents([[sentences[0][0] + chr(0x0A) + sentences[0][1]]])
        assert seg.segment_sents(sentences).split() == expected
