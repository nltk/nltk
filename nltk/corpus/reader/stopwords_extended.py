# Natural Language Toolkit: Code-defined additions to word list corpora
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
"""
Stop word lists defined in code rather than read from ``nltk_data``.

:class:`~nltk.corpus.reader.wordlist.StopwordsCorpusReader` serves each
:class:`StopwordsExtension` listed in its ``EXTENSIONS`` as a virtual fileid
(``english-extended``), built from the corpus file plus the words below. No
corpus file is added or changed, so an extension works on existing installs with
no data download.

Additions are limited to closed-class function words that have no frequent
content-word homonym -- the rule the Snowball English stop list states for
omitting ``will``, ``can``, ``may``, ``must`` and ``might``. See nltk/nltk#3747
for the full survey and the accept/reject rationale.

To add ``<lang>-extended``, define the word groups here, name the extension, and
list it in ``StopwordsCorpusReader.EXTENSIONS``::

    StopwordsLangExtended = StopwordsExtension(
        fileid="<lang>-extended", base="<lang>", additions=_GROUP_ONE | _GROUP_TWO
    )

The invariant tests in ``nltk/test/unit/test_stopwords_extended.py`` are
parametrised over ``EXTENSIONS``, so a new entry is covered automatically.
"""

from dataclasses import dataclass


def curly_variants(words):
    """Return U+2019 spellings of every entry containing a straight apostrophe.

    Word processors, browsers and phone keyboards emit ``don’t``, which never
    matches a list holding only ``don't``. Not English-specific: Catalan has 14
    apostrophe forms in its list.

        >>> sorted(curly_variants(["don't", "the"]))
        ['don’t']
    """
    return frozenset(word.replace("'", "’") for word in words if "'" in word)


@dataclass(frozen=True)
class StopwordsExtension:
    """One code-defined stop word list, layered over a corpus fileid.

    :param fileid: the virtual fileid it is served as, e.g. ``english-extended``.
    :param base: the corpus fileid it builds on, e.g. ``english``.
    :param additions: words to add that are not in the corpus file.
    :param add_curly_variants: also add U+2019 spellings of every apostrophe
        form in the combined list. See :func:`curly_variants`.
    """

    fileid: str
    base: str
    additions: frozenset
    add_curly_variants: bool = True

    def build(self, base_words):
        """Return *base_words* first and unchanged, then this extension's words."""
        words = list(base_words)
        words += sorted(self.additions.difference(words))
        if self.add_curly_variants:
            words += sorted(curly_variants(words).difference(words))
        return words


# ---------------------------------------------------------------------------
# English
# ---------------------------------------------------------------------------

#: In the Snowball list, absent from NLTK's.
_SNOWBALL_ADDITIONS = frozenset(
    {
        # modals with no content homonym -- Snowball: "would, could, should,
        # ought might however be included". NLTK has `should` but not these.
        "could",
        "would",
        "ought",
        # negated `can`. NLTK carries every other negated modal
        # (`don't`, `won't`, `shouldn't`, `couldn't`, ...) but not this one.
        "cannot",
        "can't",
        # Snowball "COMPOUND FORMS ... pronoun + verb": deictic/wh-word + `is`.
        # NLTK carries `that'll` and `it's` but none of these.
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
    }
)

#: Missing members of paradigms NLTK already carries in part -- the recurring
#: complaint behind #1800, #2588, #3047, #3073 and #3358.
_PARADIGM_ADDITIONS = frozenset(
    {
        # modal + reduced `have`. NLTK has `should've` only.
        "could've",
        "would've",
        "might've",
        "must've",
        # negated modals. NLTK has `mightn't`, `mustn't`, `needn't`, `shan't`.
        "daren't",
        "oughtn't",
        "mayn't",
    }
)

#: Preposition and negative adverb; homonym-free, in 5 of the 8 lists surveyed.
_CLOSED_CLASS_ADDITIONS = frozenset({"never", "without"})

#: ``stopwords.words("english-extended")``.
StopwordsEnglishExtended = StopwordsExtension(
    fileid="english-extended",
    base="english",
    additions=_SNOWBALL_ADDITIONS | _PARADIGM_ADDITIONS | _CLOSED_CLASS_ADDITIONS,
)
