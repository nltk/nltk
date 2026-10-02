"""
Tests for the code-defined ``english-extended`` stop word list.

Covers the invariants that make the extension safe to add: it never removes or
reorders anything from the corpus, it never touches the other languages, and it
contains exactly the categories documented in
:mod:`nltk.corpus.reader.stopwords_extended` -- including the words deliberately
left out.
"""

import pytest

from nltk.corpus import stopwords
from nltk.corpus.reader.stopwords_extended import StopwordsEnglishExtended
from nltk.corpus.reader.wordlist import (
    StopwordsCorpusReader,
    WordListCorpusReader,
)

pytestmark = pytest.mark.skipif(
    not stopwords.fileids(), reason="stopwords corpus not installed"
)


@pytest.fixture(scope="module")
def base():
    return stopwords.words("english")


@pytest.fixture(scope="module")
def extended():
    return stopwords.words("english-extended")


@pytest.mark.parametrize("fileid", [e.fileid for e in StopwordsCorpusReader.EXTENSIONS])
class TestExtendedIsAdditive:
    """Invariants every registered extension must satisfy.

    Parametrised over ``StopwordsCorpusReader.EXTENSIONS``, so a new ``<lang>-extended``
    entry is covered here automatically.
    """

    def test_is_a_superset_of_its_base(self, fileid):
        extension = stopwords._extension(fileid)
        base = stopwords.words(extension.base)
        assert set(base).issubset(set(stopwords.words(fileid)))

    def test_base_list_is_unchanged(self, fileid):
        # The corpus file must not be modified or shadowed by the extension.
        extension = stopwords._extension(fileid)
        base = stopwords.words(extension.base)
        assert not (extension.additions & set(base))
        assert len(base) == len(set(base))

    def test_no_duplicates(self, fileid):
        extended = stopwords.words(fileid)
        assert len(extended) == len(set(extended))

    def test_base_entries_keep_their_order(self, fileid):
        extension = stopwords._extension(fileid)
        base = stopwords.words(extension.base)
        assert stopwords.words(fileid)[: len(base)] == base

    def test_exposed_as_a_fileid(self, fileid):
        assert fileid in stopwords.fileids()

    def test_every_addition_is_present(self, fileid):
        extension = stopwords._extension(fileid)
        assert extension.additions.issubset(set(stopwords.words(fileid)))

    def test_every_advertised_fileid_can_be_read(self, fileid):
        # fileids() advertises the virtual name, so raw()/open() must work on it
        # too -- otherwise `for f in fileids(): reader.raw(f)` breaks.
        assert stopwords.raw(fileid).split("\n")[:-1] == stopwords.words(fileid)
        with stopwords.open(fileid) as stream:
            assert stream.read() == stopwords.raw(fileid)

    def test_abspath_reports_that_there_is_no_file(self, fileid):
        # A code-defined list has no path; the error must say so rather than
        # surface an OSError about a missing corpus file.
        with pytest.raises(ValueError, match="defined in code"):
            stopwords.abspath(fileid)

    def test_real_fileids_are_served_unchanged(self, fileid):
        # A non-virtual fileid must be passed straight through, so the reader
        # returns exactly what the plain WordListCorpusReader would. Note this
        # cannot be checked by asserting the additions are absent elsewhere:
        # `hinglish` legitimately lists English words in its own corpus file.
        for lang in stopwords.fileids():
            if stopwords._extension(lang):
                continue
            assert stopwords.words(lang) == WordListCorpusReader.words(stopwords, lang)


class TestAcceptedAdditions:
    @pytest.mark.parametrize(
        "word",
        [
            # in Snowball's list, absent from NLTK's
            "cannot",
            "can't",
            "could",
            "would",
            "ought",
            "let's",
            "that's",
            "there's",
            "here's",
            "who's",
            "what's",
            "where's",
            "when's",
            "why's",
            "how's",
            # paradigm completions (NLTK already has `should've`, `mustn't`, ...)
            "could've",
            "would've",
            "might've",
            "must've",
            "daren't",
            "oughtn't",
            "mayn't",
            # closed-class, pass the homonym rule
            "never",
            "without",
        ],
    )
    def test_accepted_word_is_present(self, extended, word):
        assert word in extended

    @pytest.mark.parametrize("word", ["don’t", "i’m", "can’t", "you’re", "it’s"])
    def test_curly_apostrophe_variants_present(self, extended, word):
        # U+2019 is what word processors, browsers and phones emit.
        assert word in extended

    def test_every_straight_form_has_a_curly_twin(self, extended):
        words = set(extended)
        missing = {w.replace("'", "’") for w in words if "'" in w} - words
        assert not missing, f"missing U+2019 variants: {sorted(missing)[:10]}"


class TestRejectedAdditions:
    @pytest.mark.parametrize("word", ["may", "must", "might", "shall"])
    def test_homonym_risky_modals_excluded(self, extended, word):
        # Snowball omits these because of "merry month of MAY", "a smell of
        # MUST", "with all thy MIGHT".
        assert word not in extended

    @pytest.mark.parametrize(
        "word", ["gonna", "wanna", "gotta", "lemme", "gimme", "coulda", "shoulda"]
    )
    def test_colloquial_reductions_excluded(self, extended, word):
        # Register-specific, absent from every reference list consulted, and
        # NLTK's own tokenizer splits them (`gonna` -> `gon`, `na`), so an entry
        # could never match.
        assert word not in extended

    @pytest.mark.parametrize(
        "word", ["system", "cry", "fill", "inc", "ltd", "etc", "eg", "five", "serious"]
    )
    def test_smart_list_content_words_excluded(self, extended, word):
        # Present in SMART-derived lists (scikit-learn, Terrier, MALLET,
        # stopwords-iso) but content-bearing, so out of scope here.
        assert word not in extended


class TestDeclaredExtensions:
    def test_declared_additions_match_the_delta(self, base, extended):
        # Everything gained beyond the U+2019 variants must be exactly what the
        # extension declares -- no accidental extras from the reader.
        additions = StopwordsEnglishExtended.additions
        added = set(extended) - set(base)
        plain = {w for w in added if "’" not in w}
        assert plain == additions - set(base)

    def test_declared_additions_are_immutable(self):
        for extension in StopwordsCorpusReader.EXTENSIONS:
            assert isinstance(extension.additions, frozenset)
