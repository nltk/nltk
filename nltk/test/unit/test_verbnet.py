"""
Unit tests for VerbnetCorpusReader, covering version support (2.1, 3.2, 3.3)
and the longid/shortid bug fix for dash-style numeric identifiers.
"""

import os
import unittest

import pytest

import nltk.data
from nltk.corpus.reader.verbnet import VerbnetCorpusReader

# ---------------------------------------------------------
# Paths – tests that require a local corpus are skipped when absent.
# ---------------------------------------------------------


def _find_verbnet_in_nltk_data():
    """Search nltk.data.path for the verbnet corpus directory."""
    for search_dir in nltk.data.path:
        candidate = os.path.join(search_dir, "corpora", "verbnet")
        if os.path.isdir(candidate):
            return candidate
    return None


_VN21_ROOT = _find_verbnet_in_nltk_data()
_VN32_ROOT = os.path.join(os.path.expanduser("~"), "Downloads", "verbnet")
_VN33_ROOT = os.path.join(os.path.expanduser("~"), "verbnet3.3")

_FILEIDS = r"(?!\.).*\.xml"


def _corpus_available(path):
    return (
        path is not None
        and os.path.isdir(path)
        and any(f.endswith(".xml") for f in os.listdir(path))
    )


# ---------------------------------------------------------
# Regex unit tests (no corpus required)
# ---------------------------------------------------------
class TestRegexPatterns(unittest.TestCase):
    """Test _LONGID_RE and _SHORTID_RE directly."""

    longid_re = VerbnetCorpusReader._LONGID_RE
    shortid_re = VerbnetCorpusReader._SHORTID_RE

    # -- longid --
    def test_longid_simple(self):
        m = self.longid_re.match("confess-37.10")
        assert m and m.group(1) == "confess" and m.group(2) == "37.10"

    def test_longid_underscore(self):
        m = self.longid_re.match("animal_sounds-38")
        assert m and m.group(1) == "animal_sounds" and m.group(2) == "38"

    def test_longid_with_dash_shortid(self):
        m = self.longid_re.match("act-114-1")
        assert m and m.group(1) == "act" and m.group(2) == "114-1"

    def test_longid_rejects_numeric_prefix(self):
        """The bug: '114-1' must NOT be matched as a longid."""
        assert self.longid_re.match("114-1") is None

    def test_longid_rejects_pure_digits(self):
        assert self.longid_re.match("37.10") is None

    # -- shortid --
    def test_shortid_dotted(self):
        assert self.shortid_re.match("37.10")

    def test_shortid_dashed(self):
        assert self.shortid_re.match("114-1")

    def test_shortid_complex(self):
        assert self.shortid_re.match("22.2-3-1-1")

    def test_shortid_rejects_alpha(self):
        assert self.shortid_re.match("confess-37.10") is None


# ---------------------------------------------------------
# Hardcoded entry tests – real examples from each VerbNet version, tested
# against the regex without loading corpus files.
# ---------------------------------------------------------
class TestRealEntries(unittest.TestCase):
    """Test longid/shortid regex matching against real entries from each version.

    These examples are taken directly from VerbNet 2.1, 3.2, and 3.3 corpora
    so we can verify correctness without requiring the files on disk.
    """

    longid_re = VerbnetCorpusReader._LONGID_RE
    shortid_re = VerbnetCorpusReader._SHORTID_RE

    # -- VerbNet 2.1 examples (shipped with nltk.download('verbnet')) --

    def test_v21_accompany_51_7(self):
        """VerbNet 2.1: accompany-51.7 (simple dotted id)"""
        m = self.longid_re.match("accompany-51.7")
        assert m and m.group(1) == "accompany" and m.group(2) == "51.7"
        assert self.shortid_re.match("51.7")
        assert self.longid_re.match("51.7") is None

    def test_v21_admire_31_2_1(self):
        """VerbNet 2.1: admire-31.2-1 (dotted id with dash subclass)"""
        m = self.longid_re.match("admire-31.2-1")
        assert m and m.group(1) == "admire" and m.group(2) == "31.2-1"
        assert self.shortid_re.match("31.2-1")
        assert self.longid_re.match("31.2-1") is None

    def test_v21_animal_sounds_38(self):
        """VerbNet 2.1: animal_sounds-38 (underscore in name, integer id)"""
        m = self.longid_re.match("animal_sounds-38")
        assert m and m.group(1) == "animal_sounds" and m.group(2) == "38"
        assert self.shortid_re.match("38")
        assert self.longid_re.match("38") is None

    def test_v21_weather_57(self):
        """VerbNet 2.1: weather-57"""
        m = self.longid_re.match("weather-57")
        assert m and m.group(1) == "weather" and m.group(2) == "57"

    def test_v21_put_9_1_2(self):
        """VerbNet 2.1: put-9.1-2 (subclass with dash)"""
        m = self.longid_re.match("put-9.1-2")
        assert m and m.group(1) == "put" and m.group(2) == "9.1-2"
        assert self.shortid_re.match("9.1-2")

    # -- VerbNet 3.2 examples --

    def test_v32_absorb_39_8(self):
        """VerbNet 3.2: absorb-39.8"""
        m = self.longid_re.match("absorb-39.8")
        assert m and m.group(1) == "absorb" and m.group(2) == "39.8"

    def test_v32_advise_37_9_1(self):
        """VerbNet 3.2: advise-37.9-1 (subclass)"""
        m = self.longid_re.match("advise-37.9-1")
        assert m and m.group(1) == "advise" and m.group(2) == "37.9-1"

    def test_v32_amalgamate_22_2_3_1_1(self):
        """VerbNet 3.2: amalgamate-22.2-3-1-1 (deeply nested subclass)"""
        m = self.longid_re.match("amalgamate-22.2-3-1-1")
        assert m and m.group(1) == "amalgamate" and m.group(2) == "22.2-3-1-1"
        assert self.shortid_re.match("22.2-3-1-1")
        assert self.longid_re.match("22.2-3-1-1") is None

    def test_v32_body_internal_motion_49(self):
        """VerbNet 3.2: body_internal_motion-49 (underscore name)"""
        m = self.longid_re.match("body_internal_motion-49")
        assert m and m.group(1) == "body_internal_motion" and m.group(2) == "49"

    def test_v32_entity_specific_cos_45_5(self):
        """VerbNet 3.2: entity_specific_cos-45.5 (multiple underscores)"""
        m = self.longid_re.match("entity_specific_cos-45.5")
        assert m and m.group(1) == "entity_specific_cos" and m.group(2) == "45.5"

    # -- VerbNet 3.3 examples --

    def test_v33_act_114(self):
        """VerbNet 3.3: act-114 (top-level class)"""
        m = self.longid_re.match("act-114")
        assert m and m.group(1) == "act" and m.group(2) == "114"

    def test_v33_act_114_1(self):
        """VerbNet 3.3: act-114-1 (the original bug case)"""
        m = self.longid_re.match("act-114-1")
        assert m and m.group(1) == "act" and m.group(2) == "114-1"
        # The bug: '114-1' was incorrectly matched as a longid
        assert self.longid_re.match("114-1") is None
        assert self.shortid_re.match("114-1")

    def test_v33_act_114_1_1(self):
        """VerbNet 3.3: act-114-1-1 (nested subclass)"""
        m = self.longid_re.match("act-114-1-1")
        assert m and m.group(1) == "act" and m.group(2) == "114-1-1"
        assert self.longid_re.match("114-1-1") is None
        assert self.shortid_re.match("114-1-1")

    def test_v33_acquiesce_95_1_1(self):
        """VerbNet 3.3: acquiesce-95.1-1"""
        m = self.longid_re.match("acquiesce-95.1-1")
        assert m and m.group(1) == "acquiesce" and m.group(2) == "95.1-1"

    def test_v33_accept_77_1(self):
        """VerbNet 3.3: accept-77.1"""
        m = self.longid_re.match("accept-77.1")
        assert m and m.group(1) == "accept" and m.group(2) == "77.1"

    def test_v33_entity_specific_modes_being_47_2(self):
        """VerbNet 3.3: entity_specific_modes_being-47.2 (long underscore name)"""
        m = self.longid_re.match("entity_specific_modes_being-47.2")
        assert (
            m and m.group(1) == "entity_specific_modes_being" and m.group(2) == "47.2"
        )


# ---------------------------------------------------------
# Version parameter tests (no corpus required)
# ---------------------------------------------------------
class TestVersionParameter(unittest.TestCase):
    def test_supported_versions(self):
        assert "2.1" in VerbnetCorpusReader.SUPPORTED_VERSIONS
        assert "3.2" in VerbnetCorpusReader.SUPPORTED_VERSIONS
        assert "3.3" in VerbnetCorpusReader.SUPPORTED_VERSIONS

    def test_invalid_version_raises(self):
        with pytest.raises(ValueError, match="not supported"):
            VerbnetCorpusReader("/tmp", ".*", version="4.0")


# ---------------------------------------------------------
# Corpus-level integration tests
# ---------------------------------------------------------
def _make_corpus_tests(version, root):
    """Factory that returns a test class for a specific VerbNet version."""

    @unittest.skipUnless(
        _corpus_available(root), f"VerbNet {version} not found at {root}"
    )
    class _Tests(unittest.TestCase):
        @classmethod
        def setUpClass(cls):
            cls.vn = VerbnetCorpusReader(root, _FILEIDS, version=version)

        def test_version_property(self):
            assert self.vn.version == version

        def test_classids_nonempty(self):
            assert len(self.vn.classids()) > 0

        def test_lemmas_nonempty(self):
            assert len(self.vn.lemmas()) > 0

        def test_wordnetids_nonempty(self):
            assert len(self.vn.wordnetids()) > 0

        def test_fileids_nonempty(self):
            assert len(self.vn.fileids()) > 0

        def test_roundtrip_all_ids(self):
            """Every longid must survive shortid -> longid round-trip."""
            for cid in self.vn.classids():
                sid = self.vn.shortid(cid)
                assert self.vn.longid(sid) == cid, f"round-trip failed for {cid}"

        def test_vnclass_by_longid(self):
            cid = self.vn.classids()[0]
            vc = self.vn.vnclass(cid)
            assert vc is not None
            assert vc.get("ID") == cid

        def test_vnclass_by_shortid(self):
            cid = self.vn.classids()[0]
            sid = self.vn.shortid(cid)
            vc = self.vn.vnclass(sid)
            assert vc is not None
            assert vc.get("ID") == cid

        def test_frames(self):
            cid = self.vn.classids()[0]
            frames = self.vn.frames(cid)
            assert isinstance(frames, list)

        def test_themroles(self):
            cid = self.vn.classids()[0]
            roles = self.vn.themroles(cid)
            assert isinstance(roles, list)

        def test_subclasses(self):
            cid = self.vn.classids()[0]
            subs = self.vn.subclasses(cid)
            assert isinstance(subs, list)

        def test_pprint(self):
            cid = self.vn.classids()[0]
            pp = self.vn.pprint(cid)
            assert isinstance(pp, str) and len(pp) > 0

        def test_classids_by_lemma(self):
            lemma = self.vn.lemmas()[0]
            cids = self.vn.classids(lemma=lemma)
            assert len(cids) > 0

        def test_classids_by_fileid(self):
            fid = self.vn.fileids()[0]
            cids = self.vn.classids(fileid=fid)
            assert len(cids) > 0

        def test_fileids_by_classid(self):
            cid = self.vn.classids()[0]
            fids = self.vn.fileids(cid)
            assert len(fids) == 1

    _Tests.__name__ = f"TestVerbNet{version.replace('.', '')}"
    _Tests.__qualname__ = _Tests.__name__
    return _Tests


TestVerbNet21 = _make_corpus_tests("2.1", _VN21_ROOT)
TestVerbNet32 = _make_corpus_tests("3.2", _VN32_ROOT)
TestVerbNet33 = _make_corpus_tests("3.3", _VN33_ROOT)


# ---------------------------------------------------------
# Bug-specific regression tests (require VerbNet 3.3)
# ---------------------------------------------------------
@unittest.skipUnless(
    _corpus_available(_VN33_ROOT), f"VerbNet 3.3 not found at {_VN33_ROOT}"
)
class TestLongidShortidBugFix(unittest.TestCase):
    """Regression tests for the longid/shortid bug with dash-style IDs."""

    @classmethod
    def setUpClass(cls):
        cls.vn = VerbnetCorpusReader(_VN33_ROOT, _FILEIDS, version="3.3")

    def test_longid_numeric_dash(self):
        """longid('114-1') must return 'act-114-1', not '114-1'."""
        assert self.vn.longid("114-1") == "act-114-1"

    def test_longid_numeric_dash_nested(self):
        assert self.vn.longid("114-1-1") == "act-114-1-1"

    def test_shortid_from_dash_longid(self):
        assert self.vn.shortid("act-114-1") == "114-1"

    def test_longid_passthrough(self):
        """A longid passed to longid() should be returned as-is."""
        assert self.vn.longid("act-114-1") == "act-114-1"

    def test_shortid_passthrough(self):
        """A shortid passed to shortid() should be returned as-is."""
        assert self.vn.shortid("114-1") == "114-1"
