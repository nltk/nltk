# Natural Language Toolkit: Word List Corpus Reader
#
# Copyright (C) 2001-2026 NLTK Project
# Author: Steven Bird <stevenbird1@gmail.com>
#         Edward Loper <edloper@gmail.com>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
import os
from io import StringIO

from nltk.corpus.reader.api import *
from nltk.corpus.reader.stopwords_extended import StopwordsEnglishExtended
from nltk.corpus.reader.util import *
from nltk.tokenize import line_tokenize


class WordListCorpusReader(CorpusReader):
    """
    List of words, one per line.  Blank lines are ignored.
    """

    def words(self, fileids=None, ignore_lines_startswith="\n", hf=False):
        if hf:
            from nltk.huggingface.dataset import load_data

            corpus_id = (
                self._root.corpus_id
                if hasattr(self._root, "corpus_id")
                else os.path.basename(self._root.path.rstrip("/"))
            )
            content = load_data(corpus_id, fileid=fileids)
            return [
                line
                for line in content.splitlines()
                if line and not line.startswith(ignore_lines_startswith)
            ]
        return [
            line
            for line in line_tokenize(self.raw(fileids))
            if not line.startswith(ignore_lines_startswith)
        ]


class StopwordsCorpusReader(WordListCorpusReader):
    """A word list reader that also serves code-defined stop word lists.

    ``stopwords.words("english")`` reads the ``stopwords`` corpus from
    ``nltk_data`` unchanged. ``english-extended`` is a *virtual* fileid: it is
    not a file in ``nltk_data``, but is assembled from the ``english`` file plus
    the additions registered for it, and the U+2019 variants of both. No
    corpus file is added or modified, so the extension ships with the library
    and needs no data download.

        >>> from nltk.corpus import stopwords
        >>> base = stopwords.words("english")
        >>> extended = stopwords.words("english-extended")
        >>> set(base).issubset(extended)
        True
        >>> "cannot" in base, "cannot" in extended
        (False, True)

    The word lists themselves, and the criterion used to choose them, live in
    :mod:`nltk.corpus.reader.stopwords_extended`.
    """

    #: The code-defined lists this reader serves, as virtual fileids. Listing a
    #: new :class:`~nltk.corpus.reader.stopwords_extended.StopwordsExtension`
    #: here is all it takes to serve another ``<lang>-extended``.
    EXTENSIONS = (StopwordsEnglishExtended,)

    def _extension(self, fileid):
        """The extension serving *fileid*, or ``None``."""
        if isinstance(fileid, str):
            for extension in self.EXTENSIONS:
                if extension.fileid == fileid:
                    return extension
        return None

    def fileids(self):
        """The corpus fileids, plus any virtual fileid whose base is present."""
        available = super().fileids()
        virtual = [e.fileid for e in self.EXTENSIONS if e.base in available]
        return sorted(available + virtual)

    def words(self, fileids=None, ignore_lines_startswith="\n", hf=False):
        """As :meth:`WordListCorpusReader.words`, honouring virtual fileids."""
        extension = self._extension(fileids)
        if extension is None:
            return super().words(
                fileids, ignore_lines_startswith=ignore_lines_startswith, hf=hf
            )
        return extension.build(
            super().words(
                extension.base,
                ignore_lines_startswith=ignore_lines_startswith,
                hf=hf,
            )
        )

    def raw(self, fileids=None):
        """As :meth:`CorpusReader.raw`, honouring virtual fileids.

        A virtual fileid has no file behind it, so its raw form is generated
        from the word list. Without this, ``raw()`` would fail for a fileid that
        :meth:`fileids` advertises.
        """
        if self._extension(fileids) is not None:
            return "\n".join(self.words(fileids)) + "\n"
        return super().raw(fileids)

    def open(self, file):
        """As :meth:`CorpusReader.open`, honouring virtual fileids."""
        if self._extension(file) is not None:
            return StringIO(self.raw(file))
        return super().open(file)

    def abspath(self, fileid):
        """As :meth:`CorpusReader.abspath`; virtual fileids have no path.

        Raising here is deliberate: a code-defined list has no file on disk, and
        a clear error beats the ``OSError`` about a missing corpus file that a
        path lookup would otherwise produce.
        """
        if self._extension(fileid) is not None:
            raise ValueError(
                f"{fileid!r} is defined in code, not by a file in the corpus, "
                "so it has no path; use words() or raw() instead"
            )
        return super().abspath(fileid)


class SwadeshCorpusReader(WordListCorpusReader):
    def entries(self, fileids=None):
        """
        :return: a tuple of words for the specified fileids.
        """
        if not fileids:
            fileids = self.fileids()

        wordlists = [self.words(f) for f in fileids]
        return list(zip(*wordlists))


class NonbreakingPrefixesCorpusReader(WordListCorpusReader):
    """
    This is a class to read the nonbreaking prefixes textfiles from the
    Moses Machine Translation toolkit. These lists are used in the Python port
    of the Moses' word tokenizer.
    """

    available_langs = {
        "catalan": "ca",
        "czech": "cs",
        "german": "de",
        "greek": "el",
        "english": "en",
        "spanish": "es",
        "finnish": "fi",
        "french": "fr",
        "hungarian": "hu",
        "icelandic": "is",
        "italian": "it",
        "latvian": "lv",
        "dutch": "nl",
        "polish": "pl",
        "portuguese": "pt",
        "romanian": "ro",
        "russian": "ru",
        "slovak": "sk",
        "slovenian": "sl",
        "swedish": "sv",
        "tamil": "ta",
    }
    # Also, add the lang IDs as the keys.
    available_langs.update({v: v for v in available_langs.values()})

    def words(self, lang=None, fileids=None, ignore_lines_startswith="#"):
        """
        This module returns a list of nonbreaking prefixes for the specified
        language(s).

        >>> from nltk.corpus import nonbreaking_prefixes as nbp
        >>> nbp.words('en')[:10] == [u'A', u'B', u'C', u'D', u'E', u'F', u'G', u'H', u'I', u'J']
        True
        >>> nbp.words('ta')[:5] == [u'\u0b85', u'\u0b86', u'\u0b87', u'\u0b88', u'\u0b89']
        True

        :return: a list words for the specified language(s).
        """
        # If *lang* in list of languages available, allocate apt fileid.
        # Otherwise, the function returns non-breaking prefixes for
        # all languages when fileids==None.
        if lang in self.available_langs:
            lang = self.available_langs[lang]
            fileids = ["nonbreaking_prefix." + lang]
        return [
            line
            for line in line_tokenize(self.raw(fileids))
            if not line.startswith(ignore_lines_startswith)
        ]


class UnicharsCorpusReader(WordListCorpusReader):
    """
    This class is used to read lists of characters from the Perl Unicode
    Properties (see https://perldoc.perl.org/perluniprops.html).
    The files in the perluniprop.zip are extracted using the Unicode::Tussle
    module from https://search.cpan.org/~bdfoy/Unicode-Tussle-1.11/lib/Unicode/Tussle.pm
    """

    # These are categories similar to the Perl Unicode Properties
    available_categories = [
        "Close_Punctuation",
        "Currency_Symbol",
        "IsAlnum",
        "IsAlpha",
        "IsLower",
        "IsN",
        "IsSc",
        "IsSo",
        "IsUpper",
        "Line_Separator",
        "Number",
        "Open_Punctuation",
        "Punctuation",
        "Separator",
        "Symbol",
    ]

    def chars(self, category=None, fileids=None):
        """
        This module returns a list of characters from  the Perl Unicode Properties.
        They are very useful when porting Perl tokenizers to Python.

        >>> from nltk.corpus import perluniprops as pup
        >>> pup.chars('Open_Punctuation')[:5] == [u'(', u'[', u'{', u'\u0f3a', u'\u0f3c']
        True
        >>> pup.chars('Currency_Symbol')[:5] == [u'$', u'\xa2', u'\xa3', u'\xa4', u'\xa5']
        True
        >>> pup.available_categories
        ['Close_Punctuation', 'Currency_Symbol', 'IsAlnum', 'IsAlpha', 'IsLower', 'IsN', 'IsSc', 'IsSo', 'IsUpper', 'Line_Separator', 'Number', 'Open_Punctuation', 'Punctuation', 'Separator', 'Symbol']

        :return: a list of characters given the specific unicode character category
        """
        if category in self.available_categories:
            fileids = [category + ".txt"]
        return list(self.raw(fileids).strip())


class MWAPPDBCorpusReader(WordListCorpusReader):
    """
    This class is used to read the list of word pairs from the subset of lexical
    pairs of The Paraphrase Database (PPDB) XXXL used in the Monolingual Word
    Alignment (MWA) algorithm described in Sultan et al. (2014a, 2014b, 2015):

     - http://acl2014.org/acl2014/Q14/pdf/Q14-1017
     - https://www.aclweb.org/anthology/S14-2039
     - https://www.aclweb.org/anthology/S15-2027

    The original source of the full PPDB corpus can be found on
    https://www.cis.upenn.edu/~ccb/ppdb/

    :return: a list of tuples of similar lexical terms.
    """

    mwa_ppdb_xxxl_file = "ppdb-1.0-xxxl-lexical.extended.synonyms.uniquepairs"

    def entries(self, fileids=mwa_ppdb_xxxl_file):
        """
        :return: a tuple of synonym word pairs.
        """
        return [tuple(line.split("\t")) for line in line_tokenize(self.raw(fileids))]
