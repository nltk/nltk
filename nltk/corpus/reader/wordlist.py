# Natural Language Toolkit: Word List Corpus Reader
#
# Copyright (C) 2001-2015 NLTK Project
# Author: Steven Bird <stevenbird1@gmail.com>
#         Edward Loper <edloper@gmail.com>
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

from nltk import compat
from nltk.tokenize import line_tokenize

from nltk.corpus.reader.util import *
from nltk.corpus.reader.api import *

class WordListCorpusReader(CorpusReader):
    """
    List of words, one per line.  Blank lines are ignored.
    """
    def words(self, fileids=None, ignore_lines_startswith='\n'):
        return [line for line in line_tokenize(self.raw(fileids))
                if not line.startswith(ignore_lines_startswith)]

    def raw(self, fileids=None):
        if fileids is None: fileids = self._fileids
        elif isinstance(fileids, compat.string_types): fileids = [fileids]
        return concat([self.open(f).read() for f in fileids])


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
    :return: a list words for the specified language(s).
    """
    available_langs = {'catalan': 'ca', 'czech': 'cs', 'german': 'de',
                        'greek': 'el', 'english': 'en', 'spanish': 'es',
                        'finnish': 'fi',  'french': 'fr', 'hungarian': 'hu',
                        'icelandic': 'is', 'italian': 'it', 'latvian': 'lv',
                        'dutch': 'nl', 'polish': 'pl', 'portuguese': 'pt',
                        'romanian': 'ro', 'russian': 'ru', 'slovak': 'sk',
                        'slovenian': 'sl', 'swedish': 'sv',  'tamil': 'ta'}
    # Also, add the lang IDs as the keys.
    available_langs.update({v:v for v in available_langs.values()})
    
    def words(self, lang=None, fileids=None, ignore_lines_startswith='#'):
        # If *lang* in list of languages available, allocate apt fileid.
        # Otherwise, the function returns non-breaking prefixes for 
        # all languages when fileids==None.
        if lang in self.available_langs:
            lang = self.available_langs[lang]
            fileids = ['nonbreaking_prefix.'+lang]
        return [line for line in line_tokenize(self.raw(fileids))
                if not line.startswith(ignore_lines_startswith)]

class UnicharsCorpusReader(WordListCorpusReader):
    """
    Returns a list of characters from Perl Unicode Properties 
    (see http://perldoc.perl.org/perluniprops.html). The files in the 
    perluniprop.zip are extracted using the Unicode::Tussle module from 
    http://search.cpan.org/~bdfoy/Unicode-Tussle-1.11/lib/Unicode/Tussle.pm
    
    They are very useful when porting Perl tokenizers to Python.
    
    :return: a list of characters given the specific unicode character category 
    """
    # These are categories similar to the Perl Unicode Properties
    available_categories = ['Close_Punctuation', 'Currency_Symbol', 
                            'IsAlnum', 'IsAlpha', 'IsLower', 'IsN', 'IsSc', 
                            'IsSo', 'Open_Punctuation']
    
    def chars(self, category=None, fileids=None):
        if category in self.available_categories:
            fileids = [category+'.txt']
        return list(self.raw(fileids).strip())
