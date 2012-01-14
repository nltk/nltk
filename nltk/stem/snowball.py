# -*- coding: utf-8 -*-
#
# Natural Language Toolkit: Snowball Stemmer
#
# Copyright (C) 2001-2012 NLTK Project
# Author: Peter Michael Stahl <pemistahl@gmail.com>
#         Peter Ljunglof <peter.ljunglof@heatherleaf.se> (revisions)
# Algorithms: Dr Martin Porter <martin@tartarus.org>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

u"""
Snowball stemmers and appendant demo function

This module provides a port of the Snowball stemmers
developed by Martin Porter.
There is also a demo function demonstrating the different
algorithms. It can be invoked directly on the command line.
For more information take a look into the class SnowballStemmer.
"""

from nltk.corpus import stopwords
from nltk.stem import porter

from api import StemmerI

class SnowballStemmer(StemmerI):

    u"""
    Snowball Stemmer

    At the moment, this port is able to stem words from fourteen
    languages: Danish, Dutch, English, Finnish, French, German,
    Hungarian, Italian, Norwegian, Portuguese, Romanian, Russian,
    Spanish and Swedish.

    Furthermore, there is also the original English Porter algorithm:

        Porter, M. \"An algorithm for suffix stripping.\"
        Program 14.3 (1980): 130-137.

    The algorithms have been developed by Martin Porter.
    These stemmers are called Snowball, because he invented
    a programming language with this name for creating
    new stemming algorithms. There is more information available
    at http://snowball.tartarus.org/

    The stemmer is invoked as shown below:

    >>> from nltk.stem import SnowballStemmer
    >>> SnowballStemmer.languages # See which languages are supported
    ('danish', 'dutch', 'english', 'finnish', 'french', 'german', 'hungarian',
    'italian', 'norwegian', 'porter', 'portuguese', 'romanian', 'russian',
    'spanish', 'swedish')
    >>> stemmer = SnowballStemmer("german") # Choose a language
    >>> stemmer.stem(u"Autobahnen") # Stem a word
    u'autobahn'

    Invoking the stemmers that way is useful if you do not know the
    language to be stemmed at runtime. Alternatively, if you already know
    the language, then you can invoke the language specific stemmer directly:

    >>> from nltk.stem.snowball import GermanStemmer
    >>> stemmer = GermanStemmer()
    >>> stemmer.stem(u"Autobahnen")
    u'autobahn'

    Create a language specific instance of the Snowball stemmer.

    :param language: The language whose subclass is instantiated.
    :type language: str or unicode
    :param ignore_stopwords: If set to True, stopwords are
                             not stemmed and returned unchanged.
                             Set to False by default.
    :type ignore_stopwords: bool
    :raise ValueError: If there is no stemmer for the specified
                           language, a ValueError is raised.
    """

    languages = ("danish", "dutch", "english", "finnish", "french", "german",
                 "hungarian", "italian", "norwegian", "porter", "portuguese",
                 "romanian", "russian", "spanish", "swedish")

    def __init__(self, language, ignore_stopwords=False):
        if language not in self.languages:
            raise ValueError(u"The language '%s' is not supported." % language)
        stemmerclass = globals()[language.capitalize() + "Stemmer"]
        self.stemmer = stemmerclass(ignore_stopwords)
        self.stem = self.stemmer.stem
        self.stopwords = self.stemmer.stopwords


class _LanguageSpecificStemmer(StemmerI):

    u"""
    This helper subclass offers the possibility
    to invoke a specific stemmer directly.
    This is useful if you already know the language to be stemmed at runtime.

    Create an instance of the Snowball stemmer.

    :param ignore_stopwords: If set to True, stopwords are
                             not stemmed and returned unchanged.
                             Set to False by default.
    :type ignore_stopwords: bool
    """

    def __init__(self, ignore_stopwords=False):
        # The language is the name of the class, minus the final "Stemmer".
        language = type(self).__name__.lower()
        if language.endswith("stemmer"):
            language = language[:-7]

        self.stopwords = set()
        if ignore_stopwords:
            try:
                for word in stopwords.words(language):
                    self.stopwords.add(word.decode("utf-8"))
            except IOError:
                raise ValueError("%r has no list of stopwords. Please set"
                                 " 'ignore_stopwords' to 'False'." % self)

    def __repr__(self):
        u"""
        Print out the string representation of the respective class.

        """
        return "<%s>" % type(self).__name__


class PorterStemmer(_LanguageSpecificStemmer, porter.PorterStemmer):
    """
    A word stemmer based on the original Porter stemming algorithm.

        Porter, M. \"An algorithm for suffix stripping.\"
        Program 14.3 (1980): 130-137.

    A few minor modifications have been made to Porter's basic
    algorithm.  See the source code of the module
    nltk.stem.porter for more information.

    """
    def __init__(self, ignore_stopwords=False):
        _LanguageSpecificStemmer.__init__(self, ignore_stopwords)
        porter.PorterStemmer.__init__(self)


class _ScandinavianStemmer(_LanguageSpecificStemmer):

    u"""
    This subclass encapsulates a method for defining the string region R1.
    It is used by the Danish, Norwegian, and Swedish stemmer.

    """

    def _r1_scandinavian(self, word, vowels):
        u"""
        Return the region R1 that is used by the Scandinavian stemmers.

        R1 is the region after the first non-vowel following a vowel,
        or is the null region at the end of the word if there is no
        such non-vowel. But then R1 is adjusted so that the region
        before it contains at least three letters.

        :param word: The word whose region R1 is determined.
        :type word: str or unicode
        :param vowels: The vowels of the respective language that are
                       used to determine the region R1.
        :type vowels: unicode
        :return: the region R1 for the respective word.
        :rtype: unicode
        :note: This helper method is invoked by the respective stem method of
               the subclasses DanishStemmer, NorwegianStemmer, and
               SwedishStemmer. It is not to be invoked directly!

        """
        r1 = u""
        for i in xrange(1, len(word)):
            if word[i] not in vowels and word[i-1] in vowels:
                if len(word[:i+1]) < 3 and len(word[:i+1]) > 0:
                    r1 = word[3:]
                elif len(word[:i+1]) >= 3:
                    r1 = word[i+1:]
                else:
                    return word
                break

        return r1



class _StandardStemmer(_LanguageSpecificStemmer):

    u"""
    This subclass encapsulates two methods for defining the standard versions
    of the string regions R1, R2, and RV.

    """

    def _r1r2_standard(self, word, vowels):
        u"""
        Return the standard interpretations of the string regions R1 and R2.

        R1 is the region after the first non-vowel following a vowel,
        or is the null region at the end of the word if there is no
        such non-vowel.

        R2 is the region after the first non-vowel following a vowel
        in R1, or is the null region at the end of the word if there
        is no such non-vowel.

        :param word: The word whose regions R1 and R2 are determined.
        :type word: str or unicode
        :param vowels: The vowels of the respective language that are
                       used to determine the regions R1 and R2.
        :type vowels: unicode
        :return: (r1,r2), the regions R1 and R2 for the respective word.
        :rtype: tuple
        :note: This helper method is invoked by the respective stem method of
               the subclasses DutchStemmer, FinnishStemmer,
               FrenchStemmer, GermanStemmer, ItalianStemmer,
               PortugueseStemmer, RomanianStemmer, and SpanishStemmer.
               It is not to be invoked directly!
        :note: A detailed description of how to define R1 and R2
               can be found at http://snowball.tartarus.org/texts/r1r2.html

        """
        r1 = u""
        r2 = u""
        for i in xrange(1, len(word)):
            if word[i] not in vowels and word[i-1] in vowels:
                r1 = word[i+1:]
                break

        for i in xrange(1, len(r1)):
            if r1[i] not in vowels and r1[i-1] in vowels:
                r2 = r1[i+1:]
                break

        return (r1, r2)



    def _rv_standard(self, word, vowels):
        u"""
        Return the standard interpretation of the string region RV.

        If the second letter is a consonant, RV is the region after the
        next following vowel. If the first two letters are vowels, RV is
        the region after the next following consonant. Otherwise, RV is
        the region after the third letter.

        :param word: The word whose region RV is determined.
        :type word: str or unicode
        :param vowels: The vowels of the respective language that are
                       used to determine the region RV.
        :type vowels: unicode
        :return: the region RV for the respective word.
        :rtype: unicode
        :note: This helper method is invoked by the respective stem method of
               the subclasses ItalianStemmer, PortugueseStemmer,
               RomanianStemmer, and SpanishStemmer. It is not to be
               invoked directly!

        """
        rv = u""
        if len(word) >= 2:
            if word[1] not in vowels:
                for i in xrange(2, len(word)):
                    if word[i] in vowels:
                        rv = word[i+1:]
                        break

            elif word[:2] in vowels:
                for i in xrange(2, len(word)):
                    if word[i] not in vowels:
                        rv = word[i+1:]
                        break
            else:
                rv = word[3:]

        return rv



class DanishStemmer(_ScandinavianStemmer):

    u"""
    The Danish Snowball stemmer.

    :cvar __vowels: The Danish vowels.
    :type __vowels: unicode
    :cvar __consonants: The Danish consonants.
    :type __consonants: unicode
    :cvar __double_consonants: The Danish double consonants.
    :type __double_consonants: tuple
    :cvar __s_ending: Letters that may directly appear before a word final 's'.
    :type __s_ending: unicode
    :cvar __step1_suffixes: Suffixes to be deleted in step 1 of the algorithm.
    :type __step1_suffixes: tuple
    :cvar __step2_suffixes: Suffixes to be deleted in step 2 of the algorithm.
    :type __step2_suffixes: tuple
    :cvar __step3_suffixes: Suffixes to be deleted in step 3 of the algorithm.
    :type __step3_suffixes: tuple
    :note: A detailed description of the Danish
           stemming algorithm can be found under
           http://snowball.tartarus.org/algorithms/danish/stemmer.html

    """

    # The language's vowels and other important characters are defined.
    __vowels = u"aeiouy\xE6\xE5\xF8"
    __consonants = u"bcdfghjklmnpqrstvwxz"
    __double_consonants = (u"bb", u"cc", u"dd", u"ff", u"gg", u"hh", u"jj",
                           u"kk", u"ll", u"mm", u"nn", u"pp", u"qq", u"rr",
                           u"ss", u"tt", u"vv", u"ww", u"xx", u"zz")
    __s_ending = u"abcdfghjklmnoprtvyz\xE5"

    # The different suffixes, divided into the algorithm's steps
    # and organized by length, are listed in tuples.
    __step1_suffixes = (u"erendes", u"erende", u"hedens", u"ethed",
                        u"erede", u"heden", u"heder", u"endes",
                        u"ernes", u"erens", u"erets", u"ered",
                        u"ende", u"erne", u"eren", u"erer", u"heds",
                        u"enes", u"eres", u"eret", u"hed", u"ene", u"ere",
                        u"ens", u"ers", u"ets", u"en", u"er", u"es", u"et",
                        u"e", u"s")
    __step2_suffixes = (u"gd", u"dt", u"gt", u"kt")
    __step3_suffixes = (u"elig", u"l\xF8st", u"lig", u"els", u"ig")

    def stem(self, word):
        u"""
        Stem a Danish word and return the stemmed form.

        :param word: The word that is stemmed.
        :type word: str or unicode
        :return: The stemmed form.
        :rtype: unicode

        """
        # Every word is put into lower case for normalization.
        word = word.lower()

        if word in self.stopwords:
            return word

        # After this, the required regions are generated
        # by the respective helper method.
        r1 = self._r1_scandinavian(word, self.__vowels)

        # Then the actual stemming process starts.
        # Every new step is explicitly indicated
        # according to the descriptions on the Snowball website.

        # STEP 1
        for suffix in self.__step1_suffixes:
            if r1.endswith(suffix):
                if suffix == u"s":
                    if word[-2] in self.__s_ending:
                        word = word[:-1]
                        r1 = r1[:-1]
                else:
                    word = word[:-len(suffix)]
                    r1 = r1[:-len(suffix)]
                break

        # STEP 2
        for suffix in self.__step2_suffixes:
            if r1.endswith(suffix):
                word = word[:-1]
                r1 = r1[:-1]
                break

        # STEP 3
        if r1.endswith(u"igst"):
            word = word[:-2]
            r1 = r1[:-2]

        for suffix in self.__step3_suffixes:
            if r1.endswith(suffix):
                if suffix == u"l\xF8st":
                    word = word[:-1]
                    r1 = r1[:-1]
                else:
                    word = word[:-len(suffix)]
                    r1 = r1[:-len(suffix)]

                    if r1.endswith(self.__step2_suffixes):
                        word = word[:-1]
                        r1 = r1[:-1]
                break

        # STEP 4: Undouble
        for double_cons in self.__double_consonants:
            if word.endswith(double_cons) and len(word) > 3:
                word = word[:-1]
                break


        return word




class DutchStemmer(_StandardStemmer):

    u"""
    The Dutch Snowball stemmer.

    :cvar __vowels: The Dutch vowels.
    :type __vowels: unicode
    :cvar __step1_suffixes: Suffixes to be deleted in step 1 of the algorithm.
    :type __step1_suffixes: tuple
    :cvar __step3b_suffixes: Suffixes to be deleted in step 3b of the algorithm.
    :type __step3b_suffixes: tuple
    :note: A detailed description of the Dutch
           stemming algorithm can be found under
           http://snowball.tartarus.org/algorithms/dutch/stemmer.html

    """

    __vowels = u"aeiouy\xE8"
    __step1_suffixes = (u"heden", u"ene", u"en", u"se", u"s")
    __step3b_suffixes = (u"baar", u"lijk", u"bar", u"end", u"ing", u"ig")

    def stem(self, word):
        u"""
        Stem a Dutch word and return the stemmed form.

        :param word: The word that is stemmed.
        :type word: str or unicode
        :return: The stemmed form.
        :rtype: unicode

        """
        word = word.lower()

        if word in self.stopwords:
            return word

        step2_success = False

        # Vowel accents are removed.
        word = (word.replace(u"\xE4", u"a").replace(u"\xE1", u"a")
                    .replace(u"\xEB", u"e").replace(u"\xE9", u"e")
                    .replace(u"\xED", u"i").replace(u"\xEF", u"i")
                    .replace(u"\xF6", u"o").replace(u"\xF3", u"o")
                    .replace(u"\xFC", u"u").replace(u"\xFA", u"u"))

        # An initial 'y', a 'y' after a vowel,
        # and an 'i' between self.__vowels is put into upper case.
        # As from now these are treated as consonants.
        if word.startswith(u"y"):
            word = u"".join((u"Y", word[1:]))

        for i in xrange(1, len(word)):
            if word[i-1] in self.__vowels and word[i] == u"y":
                word = u"".join((word[:i], u"Y", word[i+1:]))

        for i in xrange(1, len(word)-1):
            if (word[i-1] in self.__vowels and word[i] == u"i" and
               word[i+1] in self.__vowels):
                word = u"".join((word[:i], u"I", word[i+1:]))

        r1, r2 = self._r1r2_standard(word, self.__vowels)

        # R1 is adjusted so that the region before it
        # contains at least 3 letters.
        for i in xrange(1, len(word)):
            if word[i] not in self.__vowels and word[i-1] in self.__vowels:
                if len(word[:i+1]) < 3 and len(word[:i+1]) > 0:
                    r1 = word[3:]
                elif len(word[:i+1]) == 0:
                    return word
                break

        # STEP 1
        for suffix in self.__step1_suffixes:
            if r1.endswith(suffix):
                if suffix == u"heden":
                    word = u"".join((word[:-5], u"heid"))
                    r1 = u"".join((r1[:-5], u"heid"))
                    if r2.endswith(u"heden"):
                        r2 = u"".join((r2[:-5], u"heid"))

                elif (suffix in (u"ene", u"en") and
                      not word.endswith(u"heden") and
                      word[-len(suffix)-1] not in self.__vowels and
                      word[-len(suffix)-3:-len(suffix)] != u"gem"):
                    word = word[:-len(suffix)]
                    r1 = r1[:-len(suffix)]
                    r2 = r2[:-len(suffix)]
                    if word.endswith((u"kk", u"dd", u"tt")):
                        word = word[:-1]
                        r1 = r1[:-1]
                        r2 = r2[:-1]

                elif (suffix in (u"se", u"s") and
                      word[-len(suffix)-1] not in self.__vowels and
                      word[-len(suffix)-1] != u"j"):
                    word = word[:-len(suffix)]
                    r1 = r1[:-len(suffix)]
                    r2 = r2[:-len(suffix)]
                break

        # STEP 2
        if r1.endswith(u"e") and word[-2] not in self.__vowels:
            step2_success = True
            word = word[:-1]
            r1 = r1[:-1]
            r2 = r2[:-1]

            if word.endswith((u"kk", u"dd", u"tt")):
                word = word[:-1]
                r1 = r1[:-1]
                r2 = r2[:-1]

        # STEP 3a
        if r2.endswith(u"heid") and word[-5] != u"c":
            word = word[:-4]
            r1 = r1[:-4]
            r2 = r2[:-4]

            if (r1.endswith(u"en") and word[-3] not in self.__vowels and
                word[-5:-2] != u"gem"):
                word = word[:-2]
                r1 = r1[:-2]
                r2 = r2[:-2]

                if word.endswith((u"kk", u"dd", u"tt")):
                    word = word[:-1]
                    r1 = r1[:-1]
                    r2 = r2[:-1]

        # STEP 3b: Derivational suffixes
        for suffix in self.__step3b_suffixes:
            if r2.endswith(suffix):
                if suffix in (u"end", u"ing"):
                    word = word[:-3]
                    r2 = r2[:-3]

                    if r2.endswith(u"ig") and word[-3] != u"e":
                        word = word[:-2]
                    else:
                        if word.endswith((u"kk", u"dd", u"tt")):
                            word = word[:-1]

                elif suffix == u"ig" and word[-3] != u"e":
                    word = word[:-2]

                elif suffix == u"lijk":
                    word = word[:-4]
                    r1 = r1[:-4]

                    if r1.endswith(u"e") and word[-2] not in self.__vowels:
                        word = word[:-1]
                        if word.endswith((u"kk", u"dd", u"tt")):
                            word = word[:-1]

                elif suffix == u"baar":
                    word = word[:-4]

                elif suffix == u"bar" and step2_success:
                    word = word[:-3]
                break

        # STEP 4: Undouble vowel
        if len(word) >= 4:
            if word[-1] not in self.__vowels and word[-1] != u"I":
                if word[-3:-1] in (u"aa", u"ee", u"oo", u"uu"):
                    if word[-4] not in self.__vowels:
                        word = u"".join((word[:-3], word[-3], word[-1]))

        # All occurrences of 'I' and 'Y' are put back into lower case.
        word = word.replace(u"I", u"i").replace(u"Y", u"y")


        return word



class EnglishStemmer(_StandardStemmer):

    u"""
    The English Snowball stemmer.

    :cvar __vowels: The English vowels.
    :type __vowels: unicode
    :cvar __double_consonants: The English double consonants.
    :type __double_consonants: tuple
    :cvar __li_ending: Letters that may directly appear before a word final 'li'.
    :type __li_ending: unicode
    :cvar __step0_suffixes: Suffixes to be deleted in step 0 of the algorithm.
    :type __step0_suffixes: tuple
    :cvar __step1a_suffixes: Suffixes to be deleted in step 1a of the algorithm.
    :type __step1a_suffixes: tuple
    :cvar __step1b_suffixes: Suffixes to be deleted in step 1b of the algorithm.
    :type __step1b_suffixes: tuple
    :cvar __step2_suffixes: Suffixes to be deleted in step 2 of the algorithm.
    :type __step2_suffixes: tuple
    :cvar __step3_suffixes: Suffixes to be deleted in step 3 of the algorithm.
    :type __step3_suffixes: tuple
    :cvar __step4_suffixes: Suffixes to be deleted in step 4 of the algorithm.
    :type __step4_suffixes: tuple
    :cvar __step5_suffixes: Suffixes to be deleted in step 5 of the algorithm.
    :type __step5_suffixes: tuple
    :cvar __special_words: A dictionary containing words
                           which have to be stemmed specially.
    :type __special_words: dict
    :note: A detailed description of the English
           stemming algorithm can be found under
           http://snowball.tartarus.org/algorithms/english/stemmer.html
    """

    __vowels = u"aeiouy"
    __double_consonants = (u"bb", u"dd", u"ff", u"gg", u"mm", u"nn",
                           u"pp", u"rr", u"tt")
    __li_ending = u"cdeghkmnrt"
    __step0_suffixes = (u"'s'", u"'s", u"'")
    __step1a_suffixes = (u"sses", u"ied", u"ies", u"us", u"ss", u"s")
    __step1b_suffixes = (u"eedly", u"ingly", u"edly", u"eed", u"ing", u"ed")
    __step2_suffixes = (u'ization', u'ational', u'fulness', u'ousness',
                        u'iveness', u'tional', u'biliti', u'lessli',
                        u'entli', u'ation', u'alism', u'aliti', u'ousli',
                        u'iviti', u'fulli', u'enci', u'anci', u'abli',
                        u'izer', u'ator', u'alli', u'bli', u'ogi', u'li')
    __step3_suffixes = (u'ational', u'tional', u'alize', u'icate', u'iciti',
                        u'ative', u'ical', u'ness', u'ful')
    __step4_suffixes = (u'ement', u'ance', u'ence', u'able', u'ible', u'ment',
                        u'ant', u'ent', u'ism', u'ate', u'iti', u'ous',
                        u'ive', u'ize', u'ion', u'al', u'er', u'ic')
    __step5_suffixes = (u"e", u"l")
    __special_words = {u"skis" : u"ski",
                       u"skies" : u"sky",
                       u"dying" : u"die",
                       u"lying" : u"lie",
                       u"tying" : u"tie",
                       u"idly" : u"idl",
                       u"gently" : u"gentl",
                       u"ugly" : u"ugli",
                       u"early" : u"earli",
                       u"only" : u"onli",
                       u"singly" : u"singl",
                       u"sky" : u"sky",
                       u"news" : u"news",
                       u"howe" : u"howe",
                       u"atlas" : u"atlas",
                       u"cosmos" : u"cosmos",
                       u"bias" : u"bias",
                       u"andes" : u"andes",
                       u"inning" : u"inning",
                       u"innings" : u"inning",
                       u"outing" : u"outing",
                       u"outings" : u"outing",
                       u"canning" : u"canning",
                       u"cannings" : u"canning",
                       u"herring" : u"herring",
                       u"herrings" : u"herring",
                       u"earring" : u"earring",
                       u"earrings" : u"earring",
                       u"proceed" : u"proceed",
                       u"proceeds" : u"proceed",
                       u"proceeded" : u"proceed",
                       u"proceeding" : u"proceed",
                       u"exceed" : u"exceed",
                       u"exceeds" : u"exceed",
                       u"exceeded" : u"exceed",
                       u"exceeding" : u"exceed",
                       u"succeed" : u"succeed",
                       u"succeeds" : u"succeed",
                       u"succeeded" : u"succeed",
                       u"succeeding" : u"succeed"}

    def stem(self, word):

        u"""
        Stem an English word and return the stemmed form.

        :param word: The word that is stemmed.
        :type word: str or unicode
        :return: The stemmed form.
        :rtype: unicode

        """
        word = word.lower()

        if word in self.stopwords or len(word) <= 2:
            return word

        elif word in self.__special_words:
            return self.__special_words[word]

        # Map the different apostrophe characters to a single consistent one
        word = (word.replace(u"\u2019", u"\x27")
                    .replace(u"\u2018", u"\x27")
                    .replace(u"\u201B", u"\x27"))

        if word.startswith(u"\x27"):
            word = word[1:]

        if word.startswith(u"y"):
            word = "".join((u"Y", word[1:]))

        for i in xrange(1, len(word)):
            if word[i-1] in self.__vowels and word[i] == u"y":
                word = "".join((word[:i], u"Y", word[i+1:]))

        step1a_vowel_found = False
        step1b_vowel_found = False

        r1 = u""
        r2 = u""

        if word.startswith((u"gener", u"commun", u"arsen")):
            if word.startswith((u"gener", u"arsen")):
                r1 = word[5:]
            else:
                r1 = word[6:]

            for i in xrange(1, len(r1)):
                if r1[i] not in self.__vowels and r1[i-1] in self.__vowels:
                    r2 = r1[i+1:]
                    break
        else:
            r1, r2 = self._r1r2_standard(word, self.__vowels)


        # STEP 0
        for suffix in self.__step0_suffixes:
            if word.endswith(suffix):
                word = word[:-len(suffix)]
                r1 = r1[:-len(suffix)]
                r2 = r2[:-len(suffix)]
                break

        # STEP 1a
        for suffix in self.__step1a_suffixes:
            if word.endswith(suffix):

                if suffix == u"sses":
                    word = word[:-2]
                    r1 = r1[:-2]
                    r2 = r2[:-2]

                elif suffix in (u"ied", u"ies"):
                    if len(word[:-len(suffix)]) > 1:
                        word = word[:-2]
                        r1 = r1[:-2]
                        r2 = r2[:-2]
                    else:
                        word = word[:-1]
                        r1 = r1[:-1]
                        r2 = r2[:-1]

                elif suffix == u"s":
                    for letter in word[:-2]:
                        if letter in self.__vowels:
                            step1a_vowel_found = True
                            break

                    if step1a_vowel_found:
                        word = word[:-1]
                        r1 = r1[:-1]
                        r2 = r2[:-1]
                break

        # STEP 1b
        for suffix in self.__step1b_suffixes:
            if word.endswith(suffix):
                if suffix in (u"eed", u"eedly"):

                    if r1.endswith(suffix):
                        word = u"".join((word[:-len(suffix)], u"ee"))

                        if len(r1) >= len(suffix):
                            r1 = u"".join((r1[:-len(suffix)], u"ee"))
                        else:
                            r1 = u""

                        if len(r2) >= len(suffix):
                            r2 = u"".join((r2[:-len(suffix)], u"ee"))
                        else:
                            r2 = u""
                else:
                    for letter in word[:-len(suffix)]:
                        if letter in self.__vowels:
                            step1b_vowel_found = True
                            break

                    if step1b_vowel_found:
                        word = word[:-len(suffix)]
                        r1 = r1[:-len(suffix)]
                        r2 = r2[:-len(suffix)]

                        if word.endswith((u"at", u"bl", u"iz")):
                            word = u"".join((word, u"e"))
                            r1 = u"".join((r1, u"e"))

                            if len(word) > 5 or len(r1) >=3:
                                r2 = u"".join((r2, u"e"))

                        elif word.endswith(self.__double_consonants):
                            word = word[:-1]
                            r1 = r1[:-1]
                            r2 = r2[:-1]

                        elif ((r1 == u"" and len(word) >= 3 and
                               word[-1] not in self.__vowels and
                               word[-1] not in u"wxY" and
                               word[-2] in self.__vowels and
                               word[-3] not in self.__vowels)
                              or
                              (r1 == u"" and len(word) == 2 and
                               word[0] in self.__vowels and
                               word[1] not in self.__vowels)):

                            word = u"".join((word, u"e"))

                            if len(r1) > 0:
                                r1 = u"".join((r1, u"e"))

                            if len(r2) > 0:
                                r2 = u"".join((r2, u"e"))
                break

        # STEP 1c
        if word[-1] in u"yY" and word[-2] not in self.__vowels and len(word) > 2:
            word = u"".join((word[:-1], u"i"))
            if len(r1) >= 1:
                r1 = u"".join((r1[:-1], u"i"))
            else:
                r1 = u""

            if len(r2) >= 1:
                r2 = u"".join((r2[:-1], u"i"))
            else:
                r2 = u""

        # STEP 2
        for suffix in self.__step2_suffixes:
            if word.endswith(suffix):
                if r1.endswith(suffix):
                    if suffix == u"tional":
                        word = word[:-2]
                        r1 = r1[:-2]
                        r2 = r2[:-2]

                    elif suffix in (u"enci", u"anci", u"abli"):
                        word = u"".join((word[:-1], u"e"))

                        if len(r1) >= 1:
                            r1 = u"".join((r1[:-1], u"e"))
                        else:
                            r1 = u""

                        if len(r2) >= 1:
                            r2 = u"".join((r2[:-1], u"e"))
                        else:
                            r2 = u""

                    elif suffix == u"entli":
                        word = word[:-2]
                        r1 = r1[:-2]
                        r2 = r2[:-2]

                    elif suffix in (u"izer", u"ization"):
                        word = u"".join((word[:-len(suffix)], u"ize"))

                        if len(r1) >= len(suffix):
                            r1 = u"".join((r1[:-len(suffix)], u"ize"))
                        else:
                            r1 = u""

                        if len(r2) >= len(suffix):
                            r2 = u"".join((r2[:-len(suffix)], u"ize"))
                        else:
                            r2 = u""

                    elif suffix in (u"ational", u"ation", u"ator"):
                        word = u"".join((word[:-len(suffix)], u"ate"))

                        if len(r1) >= len(suffix):
                            r1 = u"".join((r1[:-len(suffix)], u"ate"))
                        else:
                            r1 = u""

                        if len(r2) >= len(suffix):
                            r2 = u"".join((r2[:-len(suffix)], u"ate"))
                        else:
                            r2 = u"e"

                    elif suffix in (u"alism", u"aliti", u"alli"):
                        word = u"".join((word[:-len(suffix)], u"al"))

                        if len(r1) >= len(suffix):
                            r1 = u"".join((r1[:-len(suffix)], u"al"))
                        else:
                            r1 = u""

                        if len(r2) >= len(suffix):
                            r2 = u"".join((r2[:-len(suffix)], u"al"))
                        else:
                            r2 = u""

                    elif suffix == u"fulness":
                        word = word[:-4]
                        r1 = r1[:-4]
                        r2 = r2[:-4]

                    elif suffix in (u"ousli", u"ousness"):
                        word = u"".join((word[:-len(suffix)], u"ous"))

                        if len(r1) >= len(suffix):
                            r1 = u"".join((r1[:-len(suffix)], u"ous"))
                        else:
                            r1 = u""

                        if len(r2) >= len(suffix):
                            r2 = u"".join((r2[:-len(suffix)], u"ous"))
                        else:
                            r2 = u""

                    elif suffix in (u"iveness", u"iviti"):
                        word = u"".join((word[:-len(suffix)], u"ive"))

                        if len(r1) >= len(suffix):
                            r1 = u"".join((r1[:-len(suffix)], u"ive"))
                        else:
                            r1 = u""

                        if len(r2) >= len(suffix):
                            r2 = u"".join((r2[:-len(suffix)], u"ive"))
                        else:
                            r2 = u"e"

                    elif suffix in (u"biliti", u"bli"):
                        word = u"".join((word[:-len(suffix)], u"ble"))

                        if len(r1) >= len(suffix):
                            r1 = u"".join((r1[:-len(suffix)], u"ble"))
                        else:
                            r1 = u""

                        if len(r2) >= len(suffix):
                            r2 = u"".join((r2[:-len(suffix)], u"ble"))
                        else:
                            r2 = u""

                    elif suffix == u"ogi" and word[-4] == u"l":
                        word = word[:-1]
                        r1 = r1[:-1]
                        r2 = r2[:-1]

                    elif suffix in (u"fulli", u"lessli"):
                        word = word[:-2]
                        r1 = r1[:-2]
                        r2 = r2[:-2]

                    elif suffix == u"li" and word[-3] in self.__li_ending:
                        word = word[:-2]
                        r1 = r1[:-2]
                        r2 = r2[:-2]
                break

        # STEP 3
        for suffix in self.__step3_suffixes:
            if word.endswith(suffix):
                if r1.endswith(suffix):
                    if suffix == u"tional":
                        word = word[:-2]
                        r1 = r1[:-2]
                        r2 = r2[:-2]

                    elif suffix == u"ational":
                        word = u"".join((word[:-len(suffix)], u"ate"))

                        if len(r1) >= len(suffix):
                            r1 = u"".join((r1[:-len(suffix)], u"ate"))
                        else:
                            r1 = u""

                        if len(r2) >= len(suffix):
                            r2 = u"".join((r2[:-len(suffix)], u"ate"))
                        else:
                            r2 = u""

                    elif suffix == u"alize":
                        word = word[:-3]
                        r1 = r1[:-3]
                        r2 = r2[:-3]

                    elif suffix in (u"icate", u"iciti", u"ical"):
                        word = u"".join((word[:-len(suffix)], u"ic"))

                        if len(r1) >= len(suffix):
                            r1 = u"".join((r1[:-len(suffix)], u"ic"))
                        else:
                            r1 = u""

                        if len(r2) >= len(suffix):
                            r2 = u"".join((r2[:-len(suffix)], u"ic"))
                        else:
                            r2 = u""

                    elif suffix in (u"ful", u"ness"):
                        word = word[:-len(suffix)]
                        r1 = r1[:-len(suffix)]
                        r2 = r2[:-len(suffix)]

                    elif suffix == u"ative" and r2.endswith(suffix):
                        word = word[:-5]
                        r1 = r1[:-5]
                        r2 = r2[:-5]
                break

        # STEP 4
        for suffix in self.__step4_suffixes:
            if word.endswith(suffix):
                if r2.endswith(suffix):
                    if suffix == u"ion":
                        if word[-4] in u"st":
                            word = word[:-3]
                            r1 = r1[:-3]
                            r2 = r2[:-3]
                    else:
                        word = word[:-len(suffix)]
                        r1 = r1[:-len(suffix)]
                        r2 = r2[:-len(suffix)]
                break

        # STEP 5
        if r2.endswith(u"l") and word[-2] == u"l":
            word = word[:-1]
        elif r2.endswith(u"e"):
            word = word[:-1]
        elif r1.endswith(u"e"):
            if len(word) >= 4 and (word[-2] in self.__vowels or
                                   word[-2] in u"wxY" or
                                   word[-3] not in self.__vowels or
                                   word[-4] in self.__vowels):
                word = word[:-1]


        word = word.replace(u"Y", u"y")


        return word



class FinnishStemmer(_StandardStemmer):

    u"""
    The Finnish Snowball stemmer.

    :cvar __vowels: The Finnish vowels.
    :type __vowels: unicode
    :cvar __restricted_vowels: A subset of the Finnish vowels.
    :type __restricted_vowels: unicode
    :cvar __long_vowels: The Finnish vowels in their long forms.
    :type __long_vowels: tuple
    :cvar __consonants: The Finnish consonants.
    :type __consonants: unicode
    :cvar __double_consonants: The Finnish double consonants.
    :type __double_consonants: tuple
    :cvar __step1_suffixes: Suffixes to be deleted in step 1 of the algorithm.
    :type __step1_suffixes: tuple
    :cvar __step2_suffixes: Suffixes to be deleted in step 2 of the algorithm.
    :type __step2_suffixes: tuple
    :cvar __step3_suffixes: Suffixes to be deleted in step 3 of the algorithm.
    :type __step3_suffixes: tuple
    :cvar __step4_suffixes: Suffixes to be deleted in step 4 of the algorithm.
    :type __step4_suffixes: tuple
    :note: A detailed description of the Finnish
           stemming algorithm can be found under
           http://snowball.tartarus.org/algorithms/finnish/stemmer.html
    """

    __vowels = u"aeiouy\xE4\xF6"
    __restricted_vowels = u"aeiou\xE4\xF6"
    __long_vowels = (u"aa", u"ee", u"ii", u"oo", u"uu", u"\xE4\xE4",
                     u"\xF6\xF6")
    __consonants = u"bcdfghjklmnpqrstvwxz"
    __double_consonants = (u"bb", u"cc", u"dd", u"ff", u"gg", u"hh", u"jj",
                           u"kk", u"ll", u"mm", u"nn", u"pp", u"qq", u"rr",
                           u"ss", u"tt", u"vv", u"ww", u"xx", u"zz")
    __step1_suffixes = (u'kaan', u'k\xE4\xE4n', u'sti', u'kin', u'han',
                        u'h\xE4n', u'ko', u'k\xF6', u'pa', u'p\xE4')
    __step2_suffixes = (u'nsa', u'ns\xE4', u'mme', u'nne', u'si', u'ni',
                        u'an', u'\xE4n', u'en')
    __step3_suffixes = (u'siin', u'tten', u'seen', u'han', u'hen', u'hin',
                        u'hon', u'h\xE4n', u'h\xF6n', u'den', u'tta',
                        u'tt\xE4', u'ssa', u'ss\xE4', u'sta',
                        u'st\xE4', u'lla', u'll\xE4', u'lta',
                        u'lt\xE4', u'lle', u'ksi', u'ine', u'ta',
                        u't\xE4', u'na', u'n\xE4', u'a', u'\xE4',
                        u'n')
    __step4_suffixes = (u'impi', u'impa', u'imp\xE4', u'immi', u'imma',
                        u'imm\xE4', u'mpi', u'mpa', u'mp\xE4', u'mmi',
                        u'mma', u'mm\xE4', u'eja', u'ej\xE4')

    def stem(self, word):
        u"""
        Stem a Finnish word and return the stemmed form.

        :param word: The word that is stemmed.
        :type word: str or unicode
        :return: The stemmed form.
        :rtype: unicode

        """
        word = word.lower()

        if word in self.stopwords:
            return word

        step3_success = False

        r1, r2 = self._r1r2_standard(word, self.__vowels)

        # STEP 1: Particles etc.
        for suffix in self.__step1_suffixes:
            if r1.endswith(suffix):
                if suffix == u"sti":
                    if suffix in r2:
                        word = word[:-3]
                        r1 = r1[:-3]
                        r2 = r2[:-3]
                else:
                    if word[-len(suffix)-1] in u"ntaeiouy\xE4\xF6":
                        word = word[:-len(suffix)]
                        r1 = r1[:-len(suffix)]
                        r2 = r2[:-len(suffix)]
                break

        # STEP 2: Possessives
        for suffix in self.__step2_suffixes:
            if r1.endswith(suffix):
                if suffix == u"si":
                    if word[-3] != u"k":
                        word = word[:-2]
                        r1 = r1[:-2]
                        r2 = r2[:-2]

                elif suffix == u"ni":
                    word = word[:-2]
                    r1 = r1[:-2]
                    r2 = r2[:-2]
                    if word.endswith(u"kse"):
                        word = u"".join((word[:-3], u"ksi"))

                    if r1.endswith(u"kse"):
                        r1 = u"".join((r1[:-3], u"ksi"))

                    if r2.endswith(u"kse"):
                        r2 = u"".join((r2[:-3], u"ksi"))

                elif suffix == u"an":
                    if (word[-4:-2] in (u"ta", u"na") or
                        word[-5:-2] in (u"ssa", u"sta", u"lla", u"lta")):
                        word = word[:-2]
                        r1 = r1[:-2]
                        r2 = r2[:-2]

                elif suffix == u"\xE4n":
                    if (word[-4:-2] in (u"t\xE4", u"n\xE4") or
                        word[-5:-2] in (u"ss\xE4", u"st\xE4",
                                        u"ll\xE4", u"lt\xE4")):
                        word = word[:-2]
                        r1 = r1[:-2]
                        r2 = r2[:-2]

                elif suffix == u"en":
                    if word[-5:-2] in (u"lle", u"ine"):
                        word = word[:-2]
                        r1 = r1[:-2]
                        r2 = r2[:-2]
                else:
                    word = word[:-3]
                    r1 = r1[:-3]
                    r2 = r2[:-3]
                break

        # STEP 3: Cases
        for suffix in self.__step3_suffixes:
            if r1.endswith(suffix):
                if suffix in (u"han", u"hen", u"hin", u"hon", u"h\xE4n",
                              u"h\xF6n"):
                    if ((suffix == u"han" and word[-4] == u"a") or
                        (suffix == u"hen" and word[-4] == u"e") or
                        (suffix == u"hin" and word[-4] == u"i") or
                        (suffix == u"hon" and word[-4] == u"o") or
                        (suffix == u"h\xE4n" and word[-4] == u"\xE4") or
                        (suffix == u"h\xF6n" and word[-4] == u"\xF6")):
                        word = word[:-3]
                        r1 = r1[:-3]
                        r2 = r2[:-3]
                        step3_success = True

                elif suffix in (u"siin", u"den", u"tten"):
                    if (word[-len(suffix)-1] == u"i" and
                        word[-len(suffix)-2] in self.__restricted_vowels):
                        word = word[:-len(suffix)]
                        r1 = r1[:-len(suffix)]
                        r2 = r2[:-len(suffix)]
                        step3_success = True
                    else:
                        continue

                elif suffix == u"seen":
                    if word[-6:-4] in self.__long_vowels:
                        word = word[:-4]
                        r1 = r1[:-4]
                        r2 = r2[:-4]
                        step3_success = True
                    else:
                        continue

                elif suffix in (u"a", u"\xE4"):
                    if word[-2] in self.__vowels and word[-3] in self.__consonants:
                        word = word[:-1]
                        r1 = r1[:-1]
                        r2 = r2[:-1]
                        step3_success = True

                elif suffix in (u"tta", u"tt\xE4"):
                    if word[-4] == u"e":
                        word = word[:-3]
                        r1 = r1[:-3]
                        r2 = r2[:-3]
                        step3_success = True

                elif suffix == u"n":
                    word = word[:-1]
                    r1 = r1[:-1]
                    r2 = r2[:-1]
                    step3_success = True

                    if word[-2:] == u"ie" or word[-2:] in self.__long_vowels:
                        word = word[:-1]
                        r1 = r1[:-1]
                        r2 = r2[:-1]
                else:
                    word = word[:-len(suffix)]
                    r1 = r1[:-len(suffix)]
                    r2 = r2[:-len(suffix)]
                    step3_success = True
                break

        # STEP 4: Other endings
        for suffix in self.__step4_suffixes:
            if r2.endswith(suffix):
                if suffix in (u"mpi", u"mpa", u"mp\xE4", u"mmi", u"mma",
                              u"mm\xE4"):
                    if word[-5:-3] != u"po":
                        word = word[:-3]
                        r1 = r1[:-3]
                        r2 = r2[:-3]
                else:
                    word = word[:-len(suffix)]
                    r1 = r1[:-len(suffix)]
                    r2 = r2[:-len(suffix)]
                break

        # STEP 5: Plurals
        if step3_success and len(r1) >= 1 and r1[-1] in u"ij":
            word = word[:-1]
            r1 = r1[:-1]

        elif (not step3_success and len(r1) >= 2 and
              r1[-1] == u"t" and r1[-2] in self.__vowels):
            word = word[:-1]
            r1 = r1[:-1]
            r2 = r2[:-1]
            if r2.endswith(u"imma"):
                word = word[:-4]
                r1 = r1[:-4]
            elif r2.endswith(u"mma") and r2[-5:-3] != u"po":
                word = word[:-3]
                r1 = r1[:-3]

        # STEP 6: Tidying up
        if r1[-2:] in self.__long_vowels:
            word = word[:-1]
            r1 = r1[:-1]

        if (len(r1) >= 2 and r1[-2] in self.__consonants and
            r1[-1] in u"a\xE4ei"):
            word = word[:-1]
            r1 = r1[:-1]

        if r1.endswith((u"oj", u"uj")):
            word = word[:-1]
            r1 = r1[:-1]

        if r1.endswith(u"jo"):
            word = word[:-1]
            r1 = r1[:-1]

        # If the word ends with a double consonant
        # followed by zero or more vowels, the last consonant is removed.
        for i in xrange(1, len(word)):
            if word[-i] in self.__vowels:
                continue
            else:
                if i == 1:
                    if word[-i-1:] in self.__double_consonants:
                        word = word[:-1]
                else:
                    if word[-i-1:-i+1] in self.__double_consonants:
                        word = u"".join((word[:-i], word[-i+1:]))
                break


        return word



class FrenchStemmer(_StandardStemmer):

    u"""
    The French Snowball stemmer.

    :cvar __vowels: The French vowels.
    :type __vowels: unicode
    :cvar __step1_suffixes: Suffixes to be deleted in step 1 of the algorithm.
    :type __step1_suffixes: tuple
    :cvar __step2a_suffixes: Suffixes to be deleted in step 2a of the algorithm.
    :type __step2a_suffixes: tuple
    :cvar __step2b_suffixes: Suffixes to be deleted in step 2b of the algorithm.
    :type __step2b_suffixes: tuple
    :cvar __step4_suffixes: Suffixes to be deleted in step 4 of the algorithm.
    :type __step4_suffixes: tuple
    :note: A detailed description of the French
           stemming algorithm can be found under
           http://snowball.tartarus.org/algorithms/french/stemmer.html
    """

    __vowels = u"aeiouy\xE2\xE0\xEB\xE9\xEA\xE8\xEF\xEE\xF4\xFB\xF9"
    __step1_suffixes = (u'issements', u'issement', u'atrices', u'atrice',
                        u'ateurs', u'ations', u'logies', u'usions',
                        u'utions', u'ements', u'amment', u'emment',
                        u'ances', u'iqUes', u'ismes', u'ables', u'istes',
                        u'ateur', u'ation', u'logie', u'usion', u'ution',
                        u'ences', u'ement', u'euses', u'ments', u'ance',
                        u'iqUe', u'isme', u'able', u'iste', u'ence',
                        u'it\xE9s', u'ives', u'eaux', u'euse', u'ment',
                        u'eux', u'it\xE9', u'ive', u'ifs', u'aux', u'if')
    __step2a_suffixes = (u'issaIent', u'issantes', u'iraIent', u'issante',
                         u'issants', u'issions', u'irions', u'issais',
                         u'issait', u'issant', u'issent', u'issiez', u'issons',
                         u'irais', u'irait', u'irent', u'iriez', u'irons',
                         u'iront', u'isses', u'issez', u'\xEEmes',
                         u'\xEEtes', u'irai', u'iras', u'irez', u'isse',
                         u'ies', u'ira', u'\xEEt', u'ie', u'ir', u'is',
                         u'it', u'i')
    __step2b_suffixes = (u'eraIent', u'assions', u'erions', u'assent',
                         u'assiez', u'\xE8rent', u'erais', u'erait',
                         u'eriez', u'erons', u'eront', u'aIent', u'antes',
                         u'asses', u'ions', u'erai', u'eras', u'erez',
                         u'\xE2mes', u'\xE2tes', u'ante', u'ants',
                         u'asse', u'\xE9es', u'era', u'iez', u'ais',
                         u'ait', u'ant', u'\xE9e', u'\xE9s', u'er',
                         u'ez', u'\xE2t', u'ai', u'as', u'\xE9', u'a')
    __step4_suffixes = (u'i\xE8re', u'I\xE8re', u'ion', u'ier', u'Ier',
                        u'e', u'\xEB')

    def stem(self, word):
        u"""
        Stem a French word and return the stemmed form.

        :param word: The word that is stemmed.
        :type word: str or unicode
        :return: The stemmed form.
        :rtype: unicode

        """
        word = word.lower()

        if word in self.stopwords:
            return word

        step1_success = False
        rv_ending_found = False
        step2a_success = False
        step2b_success = False

        # Every occurrence of 'u' after 'q' is put into upper case.
        for i in xrange(1, len(word)):
            if word[i-1] == u"q" and word[i] == u"u":
                word = u"".join((word[:i], u"U", word[i+1:]))

        # Every occurrence of 'u' and 'i'
        # between vowels is put into upper case.
        # Every occurrence of 'y' preceded or
        # followed by a vowel is also put into upper case.
        for i in xrange(1, len(word)-1):
            if word[i-1] in self.__vowels and word[i+1] in self.__vowels:
                if word[i] == u"u":
                    word = u"".join((word[:i], u"U", word[i+1:]))

                elif word[i] == u"i":
                    word = u"".join((word[:i], u"I", word[i+1:]))

            if word[i-1] in self.__vowels or word[i+1] in self.__vowels:
                if word[i] == u"y":
                    word = u"".join((word[:i], u"Y", word[i+1:]))

        r1, r2 = self._r1r2_standard(word, self.__vowels)
        rv = self.__rv_french(word, self.__vowels)

        # STEP 1: Standard suffix removal
        for suffix in self.__step1_suffixes:
            if word.endswith(suffix):
                if suffix == u"eaux":
                    word = word[:-1]
                    step1_success = True

                elif suffix in (u"euse", u"euses"):
                    if suffix in r2:
                        word = word[:-len(suffix)]
                        step1_success = True

                    elif suffix in r1:
                        word = u"".join((word[:-len(suffix)], u"eux"))
                        step1_success = True

                elif suffix in (u"ement", u"ements") and suffix in rv:
                    word = word[:-len(suffix)]
                    step1_success = True

                    if word[-2:] == u"iv" and u"iv" in r2:
                        word = word[:-2]

                        if word[-2:] == u"at" and u"at" in r2:
                            word = word[:-2]

                    elif word[-3:] == u"eus":
                        if u"eus" in r2:
                            word = word[:-3]
                        elif u"eus" in r1:
                            word = u"".join((word[:-1], u"x"))

                    elif word[-3:] in (u"abl", u"iqU"):
                        if u"abl" in r2 or u"iqU" in r2:
                            word = word[:-3]

                    elif word[-3:] in (u"i\xE8r", u"I\xE8r"):
                        if u"i\xE8r" in rv or u"I\xE8r" in rv:
                            word = u"".join((word[:-3], u"i"))

                elif suffix == u"amment" and suffix in rv:
                    word = u"".join((word[:-6], u"ant"))
                    rv = u"".join((rv[:-6], u"ant"))
                    rv_ending_found = True

                elif suffix == u"emment" and suffix in rv:
                    word = u"".join((word[:-6], u"ent"))
                    rv_ending_found = True

                elif (suffix in (u"ment", u"ments") and suffix in rv and
                      not rv.startswith(suffix) and
                      rv[rv.rindex(suffix)-1] in self.__vowels):
                    word = word[:-len(suffix)]
                    rv = rv[:-len(suffix)]
                    rv_ending_found = True

                elif suffix == u"aux" and suffix in r1:
                    word = u"".join((word[:-2], u"l"))
                    step1_success = True

                elif (suffix in (u"issement", u"issements") and suffix in r1
                      and word[-len(suffix)-1] not in self.__vowels):
                    word = word[:-len(suffix)]
                    step1_success = True

                elif suffix in (u"ance", u"iqUe", u"isme", u"able", u"iste",
                              u"eux", u"ances", u"iqUes", u"ismes",
                              u"ables", u"istes") and suffix in r2:
                    word = word[:-len(suffix)]
                    step1_success = True

                elif suffix in (u"atrice", u"ateur", u"ation", u"atrices",
                                u"ateurs", u"ations") and suffix in r2:
                    word = word[:-len(suffix)]
                    step1_success = True

                    if word[-2:] == u"ic":
                        if u"ic" in r2:
                            word = word[:-2]
                        else:
                            word = u"".join((word[:-2], u"iqU"))

                elif suffix in (u"logie", u"logies") and suffix in r2:
                    word = u"".join((word[:-len(suffix)], u"log"))
                    step1_success = True

                elif (suffix in (u"usion", u"ution", u"usions", u"utions") and
                      suffix in r2):
                    word = u"".join((word[:-len(suffix)], u"u"))
                    step1_success = True

                elif suffix in (u"ence", u"ences") and suffix in r2:
                    word = u"".join((word[:-len(suffix)], u"ent"))
                    step1_success = True

                elif suffix in (u"it\xE9", u"it\xE9s") and suffix in r2:
                    word = word[:-len(suffix)]
                    step1_success = True

                    if word[-4:] == u"abil":
                        if u"abil" in r2:
                            word = word[:-4]
                        else:
                            word = u"".join((word[:-2], u"l"))

                    elif word[-2:] == u"ic":
                        if u"ic" in r2:
                            word = word[:-2]
                        else:
                            word = u"".join((word[:-2], u"iqU"))

                    elif word[-2:] == u"iv":
                        if u"iv" in r2:
                            word = word[:-2]

                elif (suffix in (u"if", u"ive", u"ifs", u"ives") and
                      suffix in r2):
                    word = word[:-len(suffix)]
                    step1_success = True

                    if word[-2:] == u"at" and u"at" in r2:
                        word = word[:-2]

                        if word[-2:] == u"ic":
                            if u"ic" in r2:
                                word = word[:-2]
                            else:
                                word = u"".join((word[:-2], u"iqU"))
                break

        # STEP 2a: Verb suffixes beginning 'i'
        if not step1_success or rv_ending_found:
            for suffix in self.__step2a_suffixes:
                if word.endswith(suffix):
                    if (suffix in rv and len(rv) > len(suffix) and
                        rv[rv.rindex(suffix)-1] not in self.__vowels):
                        word = word[:-len(suffix)]
                        step2a_success = True
                    break

        # STEP 2b: Other verb suffixes
            if not step2a_success:
                for suffix in self.__step2b_suffixes:
                    if rv.endswith(suffix):
                        if suffix == u"ions" and u"ions" in r2:
                            word = word[:-4]
                            step2b_success = True

                        elif suffix in (u'eraIent', u'erions', u'\xE8rent',
                                        u'erais', u'erait', u'eriez',
                                        u'erons', u'eront', u'erai', u'eras',
                                        u'erez', u'\xE9es', u'era', u'iez',
                                        u'\xE9e', u'\xE9s', u'er', u'ez',
                                        u'\xE9'):
                            word = word[:-len(suffix)]
                            step2b_success = True

                        elif suffix in (u'assions', u'assent', u'assiez',
                                        u'aIent', u'antes', u'asses',
                                        u'\xE2mes', u'\xE2tes', u'ante',
                                        u'ants', u'asse', u'ais', u'ait',
                                        u'ant', u'\xE2t', u'ai', u'as',
                                        u'a'):
                            word = word[:-len(suffix)]
                            rv = rv[:-len(suffix)]
                            step2b_success = True
                            if rv.endswith(u"e"):
                                word = word[:-1]
                        break

        # STEP 3
        if step1_success or step2a_success or step2b_success:
            if word[-1] == u"Y":
                word = u"".join((word[:-1], u"i"))
            elif word[-1] == u"\xE7":
                word = u"".join((word[:-1], u"c"))

        # STEP 4: Residual suffixes
        else:
            if (len(word) >= 2 and word[-1] == u"s" and
                word[-2] not in u"aiou\xE8s"):
                word = word[:-1]

            for suffix in self.__step4_suffixes:
                if word.endswith(suffix):
                    if suffix in rv:
                        if (suffix == u"ion" and suffix in r2 and
                            rv[-4] in u"st"):
                            word = word[:-3]

                        elif suffix in (u"ier", u"i\xE8re", u"Ier",
                                        u"I\xE8re"):
                            word = u"".join((word[:-len(suffix)], u"i"))

                        elif suffix == u"e":
                            word = word[:-1]

                        elif suffix == u"\xEB" and word[-3:-1] == u"gu":
                            word = word[:-1]
                        break

        # STEP 5: Undouble
        if word.endswith((u"enn", u"onn", u"ett", u"ell", u"eill")):
            word = word[:-1]

        # STEP 6: Un-accent
        for i in xrange(1, len(word)):
            if word[-i] not in self.__vowels:
                i += 1
            else:
                if i != 1 and word[-i] in (u"\xE9", u"\xE8"):
                    word = u"".join((word[:-i], u"e", word[-i+1:]))
                break

        word = (word.replace(u"I", u"i")
                    .replace(u"U", u"u")
                    .replace(u"Y", u"y"))


        return word



    def __rv_french(self, word, vowels):
        u"""
        Return the region RV that is used by the French stemmer.

        If the word begins with two vowels, RV is the region after
        the third letter. Otherwise, it is the region after the first
        vowel not at the beginning of the word, or the end of the word
        if these positions cannot be found. (Exceptionally, u'par',
        u'col' or u'tap' at the beginning of a word is also taken to
        define RV as the region to their right.)

        :param word: The French word whose region RV is determined.
        :type word: str or unicode
        :param vowels: The French vowels that are used to determine
                       the region RV.
        :type vowels: unicode
        :return: the region RV for the respective French word.
        :rtype: unicode
        :note: This helper method is invoked by the stem method of
               the subclass FrenchStemmer. It is not to be invoked directly!

        """
        rv = u""
        if len(word) >= 2:
            if (word.startswith((u"par", u"col", u"tap")) or
                (word[0] in vowels and word[1] in vowels)):
                rv = word[3:]
            else:
                for i in xrange(1, len(word)):
                    if word[i] in vowels:
                        rv = word[i+1:]
                        break

        return rv



class GermanStemmer(_StandardStemmer):

    u"""
    The German Snowball stemmer.

    :cvar __vowels: The German vowels.
    :type __vowels: unicode
    :cvar __s_ending: Letters that may directly appear before a word final 's'.
    :type __s_ending: unicode
    :cvar __st_ending: Letter that may directly appear before a word final 'st'.
    :type __st_ending: unicode
    :cvar __step1_suffixes: Suffixes to be deleted in step 1 of the algorithm.
    :type __step1_suffixes: tuple
    :cvar __step2_suffixes: Suffixes to be deleted in step 2 of the algorithm.
    :type __step2_suffixes: tuple
    :cvar __step3_suffixes: Suffixes to be deleted in step 3 of the algorithm.
    :type __step3_suffixes: tuple
    :note: A detailed description of the German
           stemming algorithm can be found under
           http://snowball.tartarus.org/algorithms/german/stemmer.html

    """

    __vowels = u"aeiouy\xE4\xF6\xFC"
    __s_ending = u"bdfghklmnrt"
    __st_ending = u"bdfghklmnt"

    __step1_suffixes = (u"ern", u"em", u"er", u"en", u"es", u"e", u"s")
    __step2_suffixes = (u"est", u"en", u"er", u"st")
    __step3_suffixes = (u"isch", u"lich", u"heit", u"keit",
                          u"end", u"ung", u"ig", u"ik")

    def stem(self, word):
        u"""
        Stem a German word and return the stemmed form.

        :param word: The word that is stemmed.
        :type word: str or unicode
        :return: The stemmed form.
        :rtype: unicode

        """
        word = word.lower()

        if word in self.stopwords:
            return word

        word = word.replace(u"\xDF", u"ss")

        # Every occurrence of 'u' and 'y'
        # between vowels is put into upper case.
        for i in xrange(1, len(word)-1):
            if word[i-1] in self.__vowels and word[i+1] in self.__vowels:
                if word[i] == u"u":
                    word = u"".join((word[:i], u"U", word[i+1:]))

                elif word[i] == u"y":
                    word = u"".join((word[:i], u"Y", word[i+1:]))

        r1, r2 = self._r1r2_standard(word, self.__vowels)

        # R1 is adjusted so that the region before it
        # contains at least 3 letters.
        for i in xrange(1, len(word)):
            if word[i] not in self.__vowels and word[i-1] in self.__vowels:
                if len(word[:i+1]) < 3 and len(word[:i+1]) > 0:
                    r1 = word[3:]
                elif len(word[:i+1]) == 0:
                    return word
                break

        # STEP 1
        for suffix in self.__step1_suffixes:
            if r1.endswith(suffix):
                if (suffix in (u"en", u"es", u"e") and
                    word[-len(suffix)-4:-len(suffix)] == u"niss"):
                    word = word[:-len(suffix)-1]
                    r1 = r1[:-len(suffix)-1]
                    r2 = r2[:-len(suffix)-1]

                elif suffix == u"s":
                    if word[-2] in self.__s_ending:
                        word = word[:-1]
                        r1 = r1[:-1]
                        r2 = r2[:-1]
                else:
                    word = word[:-len(suffix)]
                    r1 = r1[:-len(suffix)]
                    r2 = r2[:-len(suffix)]
                break

        # STEP 2
        for suffix in self.__step2_suffixes:
            if r1.endswith(suffix):
                if suffix == u"st":
                    if word[-3] in self.__st_ending and len(word[:-3]) >= 3:
                        word = word[:-2]
                        r1 = r1[:-2]
                        r2 = r2[:-2]
                else:
                    word = word[:-len(suffix)]
                    r1 = r1[:-len(suffix)]
                    r2 = r2[:-len(suffix)]
                break

        # STEP 3: Derivational suffixes
        for suffix in self.__step3_suffixes:
            if r2.endswith(suffix):
                if suffix in (u"end", u"ung"):
                    if (u"ig" in r2[-len(suffix)-2:-len(suffix)] and
                        u"e" not in r2[-len(suffix)-3:-len(suffix)-2]):
                        word = word[:-len(suffix)-2]
                    else:
                        word = word[:-len(suffix)]

                elif (suffix in (u"ig", u"ik", u"isch") and
                      u"e" not in r2[-len(suffix)-1:-len(suffix)]):
                    word = word[:-len(suffix)]

                elif suffix in (u"lich", u"heit"):
                    if (u"er" in r1[-len(suffix)-2:-len(suffix)] or
                        u"en" in r1[-len(suffix)-2:-len(suffix)]):
                        word = word[:-len(suffix)-2]
                    else:
                        word = word[:-len(suffix)]

                elif suffix == u"keit":
                    if u"lich" in r2[-len(suffix)-4:-len(suffix)]:
                        word = word[:-len(suffix)-4]

                    elif u"ig" in r2[-len(suffix)-2:-len(suffix)]:
                        word = word[:-len(suffix)-2]
                    else:
                        word = word[:-len(suffix)]
                break

        # Umlaut accents are removed and
        # 'u' and 'y' are put back into lower case.
        word = (word.replace(u"\xE4", u"a").replace(u"\xF6", u"o")
                    .replace(u"\xFC", u"u").replace(u"U", u"u")
                    .replace(u"Y", u"y"))


        return word



class HungarianStemmer(_LanguageSpecificStemmer):

    u"""
    The Hungarian Snowball stemmer.

    :cvar __vowels: The Hungarian vowels.
    :type __vowels: unicode
    :cvar __digraphs: The Hungarian digraphs.
    :type __digraphs: tuple
    :cvar __double_consonants: The Hungarian double consonants.
    :type __double_consonants: tuple
    :cvar __step1_suffixes: Suffixes to be deleted in step 1 of the algorithm.
    :type __step1_suffixes: tuple
    :cvar __step2_suffixes: Suffixes to be deleted in step 2 of the algorithm.
    :type __step2_suffixes: tuple
    :cvar __step3_suffixes: Suffixes to be deleted in step 3 of the algorithm.
    :type __step3_suffixes: tuple
    :cvar __step4_suffixes: Suffixes to be deleted in step 4 of the algorithm.
    :type __step4_suffixes: tuple
    :cvar __step5_suffixes: Suffixes to be deleted in step 5 of the algorithm.
    :type __step5_suffixes: tuple
    :cvar __step6_suffixes: Suffixes to be deleted in step 6 of the algorithm.
    :type __step6_suffixes: tuple
    :cvar __step7_suffixes: Suffixes to be deleted in step 7 of the algorithm.
    :type __step7_suffixes: tuple
    :cvar __step8_suffixes: Suffixes to be deleted in step 8 of the algorithm.
    :type __step8_suffixes: tuple
    :cvar __step9_suffixes: Suffixes to be deleted in step 9 of the algorithm.
    :type __step9_suffixes: tuple
    :note: A detailed description of the Hungarian
           stemming algorithm can be found under
           http://snowball.tartarus.org/algorithms/hungarian/stemmer.html

    """

    __vowels = u"aeiou\xF6\xFC\xE1\xE9\xED\xF3\xF5\xFA\xFB"
    __digraphs = (u"cs", u"dz", u"dzs", u"gy", u"ly", u"ny", u"ty", u"zs")
    __double_consonants = (u"bb", u"cc", u"ccs", u"dd", u"ff", u"gg",
                             u"ggy", u"jj", u"kk", u"ll", u"lly", u"mm",
                             u"nn", u"nny", u"pp", u"rr", u"ss", u"ssz",
                             u"tt", u"tty", u"vv", u"zz", u"zzs")

    __step1_suffixes = (u"al", u"el")
    __step2_suffixes = (u'k\xE9ppen', u'onk\xE9nt', u'enk\xE9nt',
                        u'ank\xE9nt', u'k\xE9pp', u'k\xE9nt', u'ban',
                        u'ben', u'nak', u'nek', u'val', u'vel', u't\xF3l',
                        u't\xF5l', u'r\xF3l', u'r\xF5l', u'b\xF3l',
                        u'b\xF5l', u'hoz', u'hez', u'h\xF6z',
                        u'n\xE1l', u'n\xE9l', u'\xE9rt', u'kor',
                        u'ba', u'be', u'ra', u're', u'ig', u'at', u'et',
                        u'ot', u'\xF6t', u'ul', u'\xFCl', u'v\xE1',
                        u'v\xE9', u'en', u'on', u'an', u'\xF6n',
                        u'n', u't')
    __step3_suffixes = (u"\xE1nk\xE9nt", u"\xE1n", u"\xE9n")
    __step4_suffixes = (u'astul', u'est\xFCl', u'\xE1stul',
                        u'\xE9st\xFCl', u'stul', u'st\xFCl')
    __step5_suffixes = (u"\xE1", u"\xE9")
    __step6_suffixes = (u'ok\xE9', u'\xF6k\xE9', u'ak\xE9',
                        u'ek\xE9', u'\xE1k\xE9', u'\xE1\xE9i',
                        u'\xE9k\xE9', u'\xE9\xE9i', u'k\xE9',
                        u'\xE9i', u'\xE9\xE9', u'\xE9')
    __step7_suffixes = (u'\xE1juk', u'\xE9j\xFCk', u'\xFCnk',
                        u'unk', u'juk', u'j\xFCk', u'\xE1nk',
                        u'\xE9nk', u'nk', u'uk', u'\xFCk', u'em',
                        u'om', u'am', u'od', u'ed', u'ad', u'\xF6d',
                        u'ja', u'je', u'\xE1m', u'\xE1d', u'\xE9m',
                        u'\xE9d', u'm', u'd', u'a', u'e', u'o',
                        u'\xE1', u'\xE9')
    __step8_suffixes = (u'jaitok', u'jeitek', u'jaink', u'jeink', u'aitok',
                        u'eitek', u'\xE1itok', u'\xE9itek', u'jaim',
                        u'jeim', u'jaid', u'jeid', u'eink', u'aink',
                        u'itek', u'jeik', u'jaik', u'\xE1ink',
                        u'\xE9ink', u'aim', u'eim', u'aid', u'eid',
                        u'jai', u'jei', u'ink', u'aik', u'eik',
                        u'\xE1im', u'\xE1id', u'\xE1ik', u'\xE9im',
                        u'\xE9id', u'\xE9ik', u'im', u'id', u'ai',
                        u'ei', u'ik', u'\xE1i', u'\xE9i', u'i')
    __step9_suffixes = (u"\xE1k", u"\xE9k", u"\xF6k", u"ok",
                        u"ek", u"ak", u"k")

    def stem(self, word):
        u"""
        Stem an Hungarian word and return the stemmed form.

        :param word: The word that is stemmed.
        :type word: str or unicode
        :return: The stemmed form.
        :rtype: unicode

        """
        word = word.lower()

        if word in self.stopwords:
            return word

        r1 = self.__r1_hungarian(word, self.__vowels, self.__digraphs)

        # STEP 1: Remove instrumental case
        if r1.endswith(self.__step1_suffixes):
            for double_cons in self.__double_consonants:
                if word[-2-len(double_cons):-2] == double_cons:
                    word = u"".join((word[:-4], word[-3]))

                    if r1[-2-len(double_cons):-2] == double_cons:
                        r1 = u"".join((r1[:-4], r1[-3]))
                    break

        # STEP 2: Remove frequent cases
        for suffix in self.__step2_suffixes:
            if word.endswith(suffix):
                if r1.endswith(suffix):
                    word = word[:-len(suffix)]
                    r1 = r1[:-len(suffix)]

                    if r1.endswith(u"\xE1"):
                        word = u"".join((word[:-1], u"a"))
                        r1 = u"".join((r1[:-1], u"a"))

                    elif r1.endswith(u"\xE9"):
                        word = u"".join((word[:-1], u"e"))
                        r1 = u"".join((r1[:-1], u"e"))
                break

        # STEP 3: Remove special cases
        for suffix in self.__step3_suffixes:
            if r1.endswith(suffix):
                if suffix == u"\xE9n":
                    word = u"".join((word[:-2], u"e"))
                    r1 = u"".join((r1[:-2], u"e"))
                else:
                    word = u"".join((word[:-len(suffix)], u"a"))
                    r1 = u"".join((r1[:-len(suffix)], u"a"))
                break

        # STEP 4: Remove other cases
        for suffix in self.__step4_suffixes:
            if r1.endswith(suffix):
                if suffix == u"\xE1stul":
                    word = u"".join((word[:-5], u"a"))
                    r1 = u"".join((r1[:-5], u"a"))

                elif suffix == u"\xE9st\xFCl":
                    word = u"".join((word[:-5], u"e"))
                    r1 = u"".join((r1[:-5], u"e"))
                else:
                    word = word[:-len(suffix)]
                    r1 = r1[:-len(suffix)]
                break

        # STEP 5: Remove factive case
        for suffix in self.__step5_suffixes:
            if r1.endswith(suffix):
                for double_cons in self.__double_consonants:
                    if word[-1-len(double_cons):-1] == double_cons:
                        word = u"".join((word[:-3], word[-2]))

                        if r1[-1-len(double_cons):-1] == double_cons:
                            r1 = u"".join((r1[:-3], r1[-2]))
                        break

        # STEP 6: Remove owned
        for suffix in self.__step6_suffixes:
            if r1.endswith(suffix):
                if suffix in (u"\xE1k\xE9", u"\xE1\xE9i"):
                    word = u"".join((word[:-3], u"a"))
                    r1 = u"".join((r1[:-3], u"a"))

                elif suffix in (u"\xE9k\xE9", u"\xE9\xE9i",
                                u"\xE9\xE9"):
                    word = u"".join((word[:-len(suffix)], u"e"))
                    r1 = u"".join((r1[:-len(suffix)], u"e"))
                else:
                    word = word[:-len(suffix)]
                    r1 = r1[:-len(suffix)]
                break

        # STEP 7: Remove singular owner suffixes
        for suffix in self.__step7_suffixes:
            if word.endswith(suffix):
                if r1.endswith(suffix):
                    if suffix in (u"\xE1nk", u"\xE1juk", u"\xE1m",
                                  u"\xE1d", u"\xE1"):
                        word = u"".join((word[:-len(suffix)], u"a"))
                        r1 = u"".join((r1[:-len(suffix)], u"a"))

                    elif suffix in (u"\xE9nk", u"\xE9j\xFCk",
                                    u"\xE9m", u"\xE9d", u"\xE9"):
                        word = u"".join((word[:-len(suffix)], u"e"))
                        r1 = u"".join((r1[:-len(suffix)], u"e"))
                    else:
                        word = word[:-len(suffix)]
                        r1 = r1[:-len(suffix)]
                break

        # STEP 8: Remove plural owner suffixes
        for suffix in self.__step8_suffixes:
            if word.endswith(suffix):
                if r1.endswith(suffix):
                    if suffix in (u"\xE1im", u"\xE1id", u"\xE1i",
                                  u"\xE1ink", u"\xE1itok", u"\xE1ik"):
                        word = u"".join((word[:-len(suffix)], u"a"))
                        r1 = u"".join((r1[:-len(suffix)], u"a"))

                    elif suffix in (u"\xE9im", u"\xE9id", u"\xE9i",
                                    u"\xE9ink", u"\xE9itek", u"\xE9ik"):
                        word = u"".join((word[:-len(suffix)], u"e"))
                        r1 = u"".join((r1[:-len(suffix)], u"e"))
                    else:
                        word = word[:-len(suffix)]
                        r1 = r1[:-len(suffix)]
                break

        # STEP 9: Remove plural suffixes
        for suffix in self.__step9_suffixes:
            if word.endswith(suffix):
                if r1.endswith(suffix):
                    if suffix == u"\xE1k":
                        word = u"".join((word[:-2], u"a"))
                    elif suffix == u"\xE9k":
                        word = u"".join((word[:-2], u"e"))
                    else:
                        word = word[:-len(suffix)]
                break


        return word



    def __r1_hungarian(self, word, vowels, digraphs):
        u"""
        Return the region R1 that is used by the Hungarian stemmer.

        If the word begins with a vowel, R1 is defined as the region
        after the first consonant or digraph (= two letters stand for
        one phoneme) in the word. If the word begins with a consonant,
        it is defined as the region after the first vowel in the word.
        If the word does not contain both a vowel and consonant, R1
        is the null region at the end of the word.

        :param word: The Hungarian word whose region R1 is determined.
        :type word: str or unicode
        :param vowels: The Hungarian vowels that are used to determine
                       the region R1.
        :type vowels: unicode
        :param digraphs: The digraphs that are used to determine the
                         region R1.
        :type digraphs: tuple
        :return: the region R1 for the respective word.
        :rtype: unicode
        :note: This helper method is invoked by the stem method of the subclass
               HungarianStemmer. It is not to be invoked directly!

        """
        r1 = u""
        if word[0] in vowels:
            for digraph in digraphs:
                if digraph in word[1:]:
                    r1 = word[word.index(digraph[-1])+1:]
                    return r1

            for i in xrange(1, len(word)):
                if word[i] not in vowels:
                    r1 = word[i+1:]
                    break
        else:
            for i in xrange(1, len(word)):
                if word[i] in vowels:
                    r1 = word[i+1:]
                    break

        return r1



class ItalianStemmer(_StandardStemmer):

    u"""
    The Italian Snowball stemmer.

    :cvar __vowels: The Italian vowels.
    :type __vowels: unicode
    :cvar __step0_suffixes: Suffixes to be deleted in step 0 of the algorithm.
    :type __step0_suffixes: tuple
    :cvar __step1_suffixes: Suffixes to be deleted in step 1 of the algorithm.
    :type __step1_suffixes: tuple
    :cvar __step2_suffixes: Suffixes to be deleted in step 2 of the algorithm.
    :type __step2_suffixes: tuple
    :note: A detailed description of the Italian
           stemming algorithm can be found under
           http://snowball.tartarus.org/algorithms/italian/stemmer.html

    """

    __vowels = u"aeiou\xE0\xE8\xEC\xF2\xF9"
    __step0_suffixes = (u'gliela', u'gliele', u'glieli', u'glielo',
                        u'gliene', u'sene', u'mela', u'mele', u'meli',
                        u'melo', u'mene', u'tela', u'tele', u'teli',
                        u'telo', u'tene', u'cela', u'cele', u'celi',
                        u'celo', u'cene', u'vela', u'vele', u'veli',
                        u'velo', u'vene', u'gli', u'ci', u'la', u'le',
                        u'li', u'lo', u'mi', u'ne', u'si', u'ti', u'vi')
    __step1_suffixes = (u'atrice', u'atrici', u'azione', u'azioni',
                        u'uzione', u'uzioni', u'usione', u'usioni',
                        u'amento', u'amenti', u'imento', u'imenti',
                        u'amente', u'abile', u'abili', u'ibile', u'ibili',
                        u'mente', u'atore', u'atori', u'logia', u'logie',
                        u'anza', u'anze', u'iche', u'ichi', u'ismo',
                        u'ismi', u'ista', u'iste', u'isti', u'ist\xE0',
                        u'ist\xE8', u'ist\xEC', u'ante', u'anti',
                        u'enza', u'enze', u'ico', u'ici', u'ica', u'ice',
                        u'oso', u'osi', u'osa', u'ose', u'it\xE0',
                        u'ivo', u'ivi', u'iva', u'ive')
    __step2_suffixes = (u'erebbero', u'irebbero', u'assero', u'assimo',
                        u'eranno', u'erebbe', u'eremmo', u'ereste',
                        u'eresti', u'essero', u'iranno', u'irebbe',
                        u'iremmo', u'ireste', u'iresti', u'iscano',
                        u'iscono', u'issero', u'arono', u'avamo', u'avano',
                        u'avate', u'eremo', u'erete', u'erono', u'evamo',
                        u'evano', u'evate', u'iremo', u'irete', u'irono',
                        u'ivamo', u'ivano', u'ivate', u'ammo', u'ando',
                        u'asse', u'assi', u'emmo', u'enda', u'ende',
                        u'endi', u'endo', u'erai', u'erei', u'Yamo',
                        u'iamo', u'immo', u'irai', u'irei', u'isca',
                        u'isce', u'isci', u'isco', u'ano', u'are', u'ata',
                        u'ate', u'ati', u'ato', u'ava', u'avi', u'avo',
                        u'er\xE0', u'ere', u'er\xF2', u'ete', u'eva',
                        u'evi', u'evo', u'ir\xE0', u'ire', u'ir\xF2',
                        u'ita', u'ite', u'iti', u'ito', u'iva', u'ivi',
                        u'ivo', u'ono', u'uta', u'ute', u'uti', u'uto',
                        u'ar', u'ir')

    def stem(self, word):
        u"""
        Stem an Italian word and return the stemmed form.

        :param word: The word that is stemmed.
        :type word: str or unicode
        :return: The stemmed form.
        :rtype: unicode

        """
        word = word.lower()

        if word in self.stopwords:
            return word

        step1_success = False

        # All acute accents are replaced by grave accents.
        word = (word.replace(u"\xE1", u"\xE0")
                    .replace(u"\xE9", u"\xE8")
                    .replace(u"\xED", u"\xEC")
                    .replace(u"\xF3", u"\xF2")
                    .replace(u"\xFA", u"\xF9"))

        # Every occurrence of 'u' after 'q'
        # is put into upper case.
        for i in xrange(1, len(word)):
            if word[i-1] == u"q" and word[i] == u"u":
                word = u"".join((word[:i], u"U", word[i+1:]))

        # Every occurrence of 'u' and 'i'
        # between vowels is put into upper case.
        for i in xrange(1, len(word)-1):
            if word[i-1] in self.__vowels and word[i+1] in self.__vowels:
                if word[i] == u"u":
                    word = u"".join((word[:i], u"U", word[i+1:]))

                elif word [i] == u"i":
                    word = u"".join((word[:i], u"I", word[i+1:]))

        r1, r2 = self._r1r2_standard(word, self.__vowels)
        rv = self._rv_standard(word, self.__vowels)

        # STEP 0: Attached pronoun
        for suffix in self.__step0_suffixes:
            if rv.endswith(suffix):
                if rv[-len(suffix)-4:-len(suffix)] in (u"ando", u"endo"):
                    word = word[:-len(suffix)]
                    r1 = r1[:-len(suffix)]
                    r2 = r2[:-len(suffix)]
                    rv = rv[:-len(suffix)]

                elif (rv[-len(suffix)-2:-len(suffix)] in
                      (u"ar", u"er", u"ir")):
                    word = u"".join((word[:-len(suffix)], u"e"))
                    r1 = u"".join((r1[:-len(suffix)], u"e"))
                    r2 = u"".join((r2[:-len(suffix)], u"e"))
                    rv = u"".join((rv[:-len(suffix)], u"e"))
                break

        # STEP 1: Standard suffix removal
        for suffix in self.__step1_suffixes:
            if word.endswith(suffix):
                if suffix == u"amente" and r1.endswith(suffix):
                    step1_success = True
                    word = word[:-6]
                    r2 = r2[:-6]
                    rv = rv[:-6]

                    if r2.endswith(u"iv"):
                        word = word[:-2]
                        r2 = r2[:-2]
                        rv = rv[:-2]

                        if r2.endswith(u"at"):
                            word = word[:-2]
                            rv = rv[:-2]

                    elif r2.endswith((u"os", u"ic")):
                        word = word[:-2]
                        rv = rv[:-2]

                    elif r2 .endswith(u"abil"):
                        word = word[:-4]
                        rv = rv[:-4]

                elif (suffix in (u"amento", u"amenti",
                                 u"imento", u"imenti") and
                      rv.endswith(suffix)):
                    step1_success = True
                    word = word[:-6]
                    rv = rv[:-6]

                elif r2.endswith(suffix):
                    step1_success = True
                    if suffix in (u"azione", u"azioni", u"atore", u"atori"):
                        word = word[:-len(suffix)]
                        r2 = r2[:-len(suffix)]
                        rv = rv[:-len(suffix)]

                        if r2.endswith(u"ic"):
                            word = word[:-2]
                            rv = rv[:-2]

                    elif suffix in (u"logia", u"logie"):
                        word = word[:-2]
                        rv = word[:-2]

                    elif suffix in (u"uzione", u"uzioni",
                                    u"usione", u"usioni"):
                        word = word[:-5]
                        rv = rv[:-5]

                    elif suffix in (u"enza", u"enze"):
                        word = u"".join((word[:-2], u"te"))
                        rv = u"".join((rv[:-2], u"te"))

                    elif suffix == u"it\xE0":
                        word = word[:-3]
                        r2 = r2[:-3]
                        rv = rv[:-3]

                        if r2.endswith((u"ic", u"iv")):
                            word = word[:-2]
                            rv = rv[:-2]

                        elif r2.endswith(u"abil"):
                            word = word[:-4]
                            rv = rv[:-4]

                    elif suffix in (u"ivo", u"ivi", u"iva", u"ive"):
                        word = word[:-3]
                        r2 = r2[:-3]
                        rv = rv[:-3]

                        if r2.endswith(u"at"):
                            word = word[:-2]
                            r2 = r2[:-2]
                            rv = rv[:-2]

                            if r2.endswith(u"ic"):
                                word = word[:-2]
                                rv = rv[:-2]
                    else:
                        word = word[:-len(suffix)]
                        rv = rv[:-len(suffix)]
                break

        # STEP 2: Verb suffixes
        if not step1_success:
            for suffix in self.__step2_suffixes:
                if rv.endswith(suffix):
                    word = word[:-len(suffix)]
                    rv = rv[:-len(suffix)]
                    break

        # STEP 3a
        if rv.endswith((u"a", u"e", u"i", u"o", u"\xE0", u"\xE8",
                        u"\xEC", u"\xF2")):
            word = word[:-1]
            rv = rv[:-1]

            if rv.endswith(u"i"):
                word = word[:-1]
                rv = rv[:-1]

        # STEP 3b
        if rv.endswith((u"ch", u"gh")):
            word = word[:-1]

        word = word.replace(u"I", u"i").replace(u"U", u"u")


        return word



class NorwegianStemmer(_ScandinavianStemmer):

    u"""
    The Norwegian Snowball stemmer.

    :cvar __vowels: The Norwegian vowels.
    :type __vowels: unicode
    :cvar __s_ending: Letters that may directly appear before a word final 's'.
    :type __s_ending: unicode
    :cvar __step1_suffixes: Suffixes to be deleted in step 1 of the algorithm.
    :type __step1_suffixes: tuple
    :cvar __step2_suffixes: Suffixes to be deleted in step 2 of the algorithm.
    :type __step2_suffixes: tuple
    :cvar __step3_suffixes: Suffixes to be deleted in step 3 of the algorithm.
    :type __step3_suffixes: tuple
    :note: A detailed description of the Norwegian
           stemming algorithm can be found under
           http://snowball.tartarus.org/algorithms/norwegian/stemmer.html

    """

    __vowels = u"aeiouy\xE6\xE5\xF8"
    __s_ending = u"bcdfghjlmnoprtvyz"
    __step1_suffixes = (u"hetenes", u"hetene", u"hetens", u"heter",
                        u"heten", u"endes", u"ande", u"ende", u"edes",
                        u"enes", u"erte", u"ede", u"ane", u"ene", u"ens",
                        u"ers", u"ets", u"het", u"ast", u"ert", u"en",
                        u"ar", u"er", u"as", u"es", u"et", u"a", u"e", u"s")

    __step2_suffixes = (u"dt", u"vt")

    __step3_suffixes = (u"hetslov", u"eleg", u"elig", u"elov", u"slov",
                          u"leg", u"eig", u"lig", u"els", u"lov", u"ig")

    def stem(self, word):
        u"""
        Stem a Norwegian word and return the stemmed form.

        :param word: The word that is stemmed.
        :type word: str or unicode
        :return: The stemmed form.
        :rtype: unicode

        """
        word = word.lower()

        if word in self.stopwords:
            return word

        r1 = self._r1_scandinavian(word, self.__vowels)

        # STEP 1
        for suffix in self.__step1_suffixes:
            if r1.endswith(suffix):
                if suffix in (u"erte", u"ert"):
                    word = u"".join((word[:-len(suffix)], u"er"))
                    r1 = u"".join((r1[:-len(suffix)], u"er"))

                elif suffix == u"s":
                    if (word[-2] in self.__s_ending or
                        (word[-2] == u"k" and word[-3] not in self.__vowels)):
                        word = word[:-1]
                        r1 = r1[:-1]
                else:
                    word = word[:-len(suffix)]
                    r1 = r1[:-len(suffix)]
                break

        # STEP 2
        for suffix in self.__step2_suffixes:
            if r1.endswith(suffix):
                word = word[:-1]
                r1 = r1[:-1]
                break

        # STEP 3
        for suffix in self.__step3_suffixes:
            if r1.endswith(suffix):
                word = word[:-len(suffix)]
                break


        return word



class PortugueseStemmer(_StandardStemmer):

    u"""
    The Portuguese Snowball stemmer.

    :cvar __vowels: The Portuguese vowels.
    :type __vowels: unicode
    :cvar __step1_suffixes: Suffixes to be deleted in step 1 of the algorithm.
    :type __step1_suffixes: tuple
    :cvar __step2_suffixes: Suffixes to be deleted in step 2 of the algorithm.
    :type __step2_suffixes: tuple
    :cvar __step4_suffixes: Suffixes to be deleted in step 4 of the algorithm.
    :type __step4_suffixes: tuple
    :note: A detailed description of the Portuguese
           stemming algorithm can be found under
           http://snowball.tartarus.org/algorithms/portuguese/stemmer.html

    """

    __vowels = u"aeiou\xE1\xE9\xED\xF3\xFA\xE2\xEA\xF4"
    __step1_suffixes = (u'amentos', u'imentos', u'uciones', u'amento',
                        u'imento', u'adoras', u'adores', u'a\xE7o~es',
                        u'log\xEDas', u'\xEAncias', u'amente',
                        u'idades', u'ismos', u'istas', u'adora',
                        u'a\xE7a~o', u'antes', u'\xE2ncia',
                        u'log\xEDa', u'uci\xF3n', u'\xEAncia',
                        u'mente', u'idade', u'ezas', u'icos', u'icas',
                        u'ismo', u'\xE1vel', u'\xEDvel', u'ista',
                        u'osos', u'osas', u'ador', u'ante', u'ivas',
                        u'ivos', u'iras', u'eza', u'ico', u'ica',
                        u'oso', u'osa', u'iva', u'ivo', u'ira')
    __step2_suffixes = (u'ar\xEDamos', u'er\xEDamos', u'ir\xEDamos',
                        u'\xE1ssemos', u'\xEAssemos', u'\xEDssemos',
                        u'ar\xEDeis', u'er\xEDeis', u'ir\xEDeis',
                        u'\xE1sseis', u'\xE9sseis', u'\xEDsseis',
                        u'\xE1ramos', u'\xE9ramos', u'\xEDramos',
                        u'\xE1vamos', u'aremos', u'eremos', u'iremos',
                        u'ariam', u'eriam', u'iriam', u'assem', u'essem',
                        u'issem', u'ara~o', u'era~o', u'ira~o', u'arias',
                        u'erias', u'irias', u'ardes', u'erdes', u'irdes',
                        u'asses', u'esses', u'isses', u'astes', u'estes',
                        u'istes', u'\xE1reis', u'areis', u'\xE9reis',
                        u'ereis', u'\xEDreis', u'ireis', u'\xE1veis',
                        u'\xEDamos', u'armos', u'ermos', u'irmos',
                        u'aria', u'eria', u'iria', u'asse', u'esse',
                        u'isse', u'aste', u'este', u'iste', u'arei',
                        u'erei', u'irei', u'aram', u'eram', u'iram',
                        u'avam', u'arem', u'erem', u'irem',
                        u'ando', u'endo', u'indo', u'adas', u'idas',
                        u'ar\xE1s', u'aras', u'er\xE1s', u'eras',
                        u'ir\xE1s', u'avas', u'ares', u'eres', u'ires',
                        u'\xEDeis', u'ados', u'idos', u'\xE1mos',
                        u'amos', u'emos', u'imos', u'iras', u'ada', u'ida',
                        u'ar\xE1', u'ara', u'er\xE1', u'era',
                        u'ir\xE1', u'ava', u'iam', u'ado', u'ido',
                        u'ias', u'ais', u'eis', u'ira', u'ia', u'ei', u'am',
                        u'em', u'ar', u'er', u'ir', u'as',
                        u'es', u'is', u'eu', u'iu', u'ou')
    __step4_suffixes = (u"os", u"a", u"i", u"o", u"\xE1",
                        u"\xED", u"\xF3")

    def stem(self, word):
        u"""
        Stem a Portuguese word and return the stemmed form.

        :param word: The word that is stemmed.
        :type word: str or unicode
        :return: The stemmed form.
        :rtype: unicode

        """
        word = word.lower()

        if word in self.stopwords:
            return word

        step1_success = False
        step2_success = False

        word = (word.replace(u"\xE3", u"a~")
                    .replace(u"\xF5", u"o~"))

        r1, r2 = self._r1r2_standard(word, self.__vowels)
        rv = self._rv_standard(word, self.__vowels)

        # STEP 1: Standard suffix removal
        for suffix in self.__step1_suffixes:
            if word.endswith(suffix):
                if suffix == u"amente" and r1.endswith(suffix):
                    step1_success = True

                    word = word[:-6]
                    r2 = r2[:-6]
                    rv = rv[:-6]

                    if r2.endswith(u"iv"):
                        word = word[:-2]
                        r2 = r2[:-2]
                        rv = rv[:-2]

                        if r2.endswith(u"at"):
                            word = word[:-2]
                            rv = rv[:-2]

                    elif r2.endswith((u"os", u"ic", u"ad")):
                        word = word[:-2]
                        rv = rv[:-2]

                elif (suffix in (u"ira", u"iras") and rv.endswith(suffix) and
                      word[-len(suffix)-1:-len(suffix)] == u"e"):
                    step1_success = True

                    word = u"".join((word[:-len(suffix)], u"ir"))
                    rv = u"".join((rv[:-len(suffix)], u"ir"))

                elif r2.endswith(suffix):
                    step1_success = True

                    if suffix in (u"log\xEDa", u"log\xEDas"):
                        word = word[:-2]
                        rv = rv[:-2]

                    elif suffix in (u"uci\xF3n", u"uciones"):
                        word = u"".join((word[:-len(suffix)], u"u"))
                        rv = u"".join((rv[:-len(suffix)], u"u"))

                    elif suffix in (u"\xEAncia", u"\xEAncias"):
                        word = u"".join((word[:-len(suffix)], u"ente"))
                        rv = u"".join((rv[:-len(suffix)], u"ente"))

                    elif suffix == u"mente":
                        word = word[:-5]
                        r2 = r2[:-5]
                        rv = rv[:-5]

                        if r2.endswith((u"ante", u"avel", u"\xEDvel")):
                            word = word[:-4]
                            rv = rv[:-4]

                    elif suffix in (u"idade", u"idades"):
                        word = word[:-len(suffix)]
                        r2 = r2[:-len(suffix)]
                        rv = rv[:-len(suffix)]

                        if r2.endswith((u"ic", u"iv")):
                            word = word[:-2]
                            rv = rv[:-2]

                        elif r2.endswith(u"abil"):
                            word = word[:-4]
                            rv = rv[:-4]

                    elif suffix in (u"iva", u"ivo", u"ivas", u"ivos"):
                        word = word[:-len(suffix)]
                        r2 = r2[:-len(suffix)]
                        rv = rv[:-len(suffix)]

                        if r2.endswith(u"at"):
                            word = word[:-2]
                            rv = rv[:-2]
                    else:
                        word = word[:-len(suffix)]
                        rv = rv[:-len(suffix)]
                break

        # STEP 2: Verb suffixes
        if not step1_success:
            for suffix in self.__step2_suffixes:
                if rv.endswith(suffix):
                    step2_success = True

                    word = word[:-len(suffix)]
                    rv = rv[:-len(suffix)]
                    break

        # STEP 3
        if step1_success or step2_success:
            if rv.endswith(u"i") and word[-2] == u"c":
                word = word[:-1]
                rv = rv[:-1]

        ### STEP 4: Residual suffix
        if not step1_success and not step2_success:
            for suffix in self.__step4_suffixes:
                if rv.endswith(suffix):
                    word = word[:-len(suffix)]
                    rv = rv[:-len(suffix)]
                    break

        # STEP 5
        if rv.endswith((u"e", u"\xE9", u"\xEA")):
            word = word[:-1]
            rv = rv[:-1]

            if ((word.endswith(u"gu") and rv.endswith(u"u")) or
                (word.endswith(u"ci") and rv.endswith(u"i"))):
                word = word[:-1]

        elif word.endswith(u"\xE7"):
            word = u"".join((word[:-1], u"c"))

        word = word.replace(u"a~", u"\xE3").replace(u"o~", u"\xF5")


        return word



class RomanianStemmer(_StandardStemmer):

    u"""
    The Romanian Snowball stemmer.

    :cvar __vowels: The Romanian vowels.
    :type __vowels: unicode
    :cvar __step0_suffixes: Suffixes to be deleted in step 0 of the algorithm.
    :type __step0_suffixes: tuple
    :cvar __step1_suffixes: Suffixes to be deleted in step 1 of the algorithm.
    :type __step1_suffixes: tuple
    :cvar __step2_suffixes: Suffixes to be deleted in step 2 of the algorithm.
    :type __step2_suffixes: tuple
    :cvar __step3_suffixes: Suffixes to be deleted in step 3 of the algorithm.
    :type __step3_suffixes: tuple
    :note: A detailed description of the Romanian
           stemming algorithm can be found under
           http://snowball.tartarus.org/algorithms/romanian/stemmer.html

    """

    __vowels = u"aeiou\u0103\xE2\xEE"
    __step0_suffixes = (u'iilor', u'ului', u'elor', u'iile', u'ilor',
                        u'atei', u'a\u0163ie', u'a\u0163ia', u'aua',
                        u'ele', u'iua', u'iei', u'ile', u'ul', u'ea',
                        u'ii')
    __step1_suffixes = (u'abilitate', u'abilitati', u'abilit\u0103\u0163i',
                        u'ibilitate', u'abilit\u0103i', u'ivitate',
                        u'ivitati', u'ivit\u0103\u0163i', u'icitate',
                        u'icitati', u'icit\u0103\u0163i', u'icatori',
                        u'ivit\u0103i', u'icit\u0103i', u'icator',
                        u'a\u0163iune', u'atoare', u'\u0103toare',
                        u'i\u0163iune', u'itoare', u'iciva', u'icive',
                        u'icivi', u'iciv\u0103', u'icala', u'icale',
                        u'icali', u'ical\u0103', u'ativa', u'ative',
                        u'ativi', u'ativ\u0103', u'atori', u'\u0103tori',
                        u'itiva', u'itive', u'itivi', u'itiv\u0103',
                        u'itori', u'iciv', u'ical', u'ativ', u'ator',
                        u'\u0103tor', u'itiv', u'itor')
    __step2_suffixes = (u'abila', u'abile', u'abili', u'abil\u0103',
                        u'ibila', u'ibile', u'ibili', u'ibil\u0103',
                        u'atori', u'itate', u'itati', u'it\u0103\u0163i',
                        u'abil', u'ibil', u'oasa', u'oas\u0103', u'oase',
                        u'anta', u'ante', u'anti', u'ant\u0103', u'ator',
                        u'it\u0103i', u'iune', u'iuni', u'isme', u'ista',
                        u'iste', u'isti', u'ist\u0103', u'i\u015Fti',
                        u'ata', u'at\u0103', u'ati', u'ate', u'uta',
                        u'ut\u0103', u'uti', u'ute', u'ita', u'it\u0103',
                        u'iti', u'ite', u'ica', u'ice', u'ici', u'ic\u0103',
                        u'osi', u'o\u015Fi', u'ant', u'iva', u'ive', u'ivi',
                        u'iv\u0103', u'ism', u'ist', u'at', u'ut', u'it',
                        u'ic', u'os', u'iv')
    __step3_suffixes = (u'seser\u0103\u0163i', u'aser\u0103\u0163i',
                        u'iser\u0103\u0163i', u'\xE2ser\u0103\u0163i',
                        u'user\u0103\u0163i', u'seser\u0103m',
                        u'aser\u0103m', u'iser\u0103m', u'\xE2ser\u0103m',
                        u'user\u0103m', u'ser\u0103\u0163i', u'sese\u015Fi',
                        u'seser\u0103', u'easc\u0103', u'ar\u0103\u0163i',
                        u'ur\u0103\u0163i', u'ir\u0103\u0163i',
                        u'\xE2r\u0103\u0163i', u'ase\u015Fi',
                        u'aser\u0103', u'ise\u015Fi', u'iser\u0103',
                        u'\xe2se\u015Fi', u'\xE2ser\u0103',
                        u'use\u015Fi', u'user\u0103', u'ser\u0103m',
                        u'sesem', u'indu', u'\xE2ndu', u'eaz\u0103',
                        u'e\u015Fti', u'e\u015Fte', u'\u0103\u015Fti',
                        u'\u0103\u015Fte', u'ea\u0163i', u'ia\u0163i',
                        u'ar\u0103m', u'ur\u0103m', u'ir\u0103m',
                        u'\xE2r\u0103m', u'asem', u'isem',
                        u'\xE2sem', u'usem', u'se\u015Fi', u'ser\u0103',
                        u'sese', u'are', u'ere', u'ire', u'\xE2re',
                        u'ind', u'\xE2nd', u'eze', u'ezi', u'esc',
                        u'\u0103sc', u'eam', u'eai', u'eau', u'iam',
                        u'iai', u'iau', u'a\u015Fi', u'ar\u0103',
                        u'u\u015Fi', u'ur\u0103', u'i\u015Fi', u'ir\u0103',
                        u'\xE2\u015Fi', u'\xe2r\u0103', u'ase',
                        u'ise', u'\xE2se', u'use', u'a\u0163i',
                        u'e\u0163i', u'i\u0163i', u'\xe2\u0163i', u'sei',
                        u'ez', u'am', u'ai', u'au', u'ea', u'ia', u'ui',
                        u'\xE2i', u'\u0103m', u'em', u'im', u'\xE2m',
                        u'se')

    def stem(self, word):
        u"""
        Stem a Romanian word and return the stemmed form.

        :param word: The word that is stemmed.
        :type word: str or unicode
        :return: The stemmed form.
        :rtype: unicode

        """
        word = word.lower()

        if word in self.stopwords:
            return word

        step1_success = False
        step2_success = False

        for i in xrange(1, len(word)-1):
            if word[i-1] in self.__vowels and word[i+1] in self.__vowels:
                if word[i] == u"u":
                    word = u"".join((word[:i], u"U", word[i+1:]))

                elif word[i] == u"i":
                    word = u"".join((word[:i], u"I", word[i+1:]))

        r1, r2 = self._r1r2_standard(word, self.__vowels)
        rv = self._rv_standard(word, self.__vowels)

        # STEP 0: Removal of plurals and other simplifications
        for suffix in self.__step0_suffixes:
            if word.endswith(suffix):
                if suffix in r1:
                    if suffix in (u"ul", u"ului"):
                        word = word[:-len(suffix)]

                        if suffix in rv:
                            rv = rv[:-len(suffix)]
                        else:
                            rv = u""

                    elif (suffix == u"aua" or suffix == u"atei" or
                          (suffix == u"ile" and word[-5:-3] != u"ab")):
                        word = word[:-2]

                    elif suffix in (u"ea", u"ele", u"elor"):
                        word = u"".join((word[:-len(suffix)], u"e"))

                        if suffix in rv:
                            rv = u"".join((rv[:-len(suffix)], u"e"))
                        else:
                            rv = u""

                    elif suffix in (u"ii", u"iua", u"iei",
                                    u"iile", u"iilor", u"ilor"):
                        word = u"".join((word[:-len(suffix)], u"i"))

                        if suffix in rv:
                            rv = u"".join((rv[:-len(suffix)], u"i"))
                        else:
                            rv = u""

                    elif suffix in (u"a\u0163ie", u"a\u0163ia"):
                        word = word[:-1]
                break

        # STEP 1: Reduction of combining suffixes
        while True:

            replacement_done = False

            for suffix in self.__step1_suffixes:
                if word.endswith(suffix):
                    if suffix in r1:
                        step1_success = True
                        replacement_done = True

                        if suffix in (u"abilitate", u"abilitati",
                                      u"abilit\u0103i",
                                      u"abilit\u0103\u0163i"):
                            word = u"".join((word[:-len(suffix)], u"abil"))

                        elif suffix == u"ibilitate":
                            word = word[:-5]

                        elif suffix in (u"ivitate", u"ivitati",
                                        u"ivit\u0103i",
                                        u"ivit\u0103\u0163i"):
                            word = u"".join((word[:-len(suffix)], u"iv"))

                        elif suffix in (u"icitate", u"icitati", u"icit\u0103i",
                                        u"icit\u0103\u0163i", u"icator",
                                        u"icatori", u"iciv", u"iciva",
                                        u"icive", u"icivi", u"iciv\u0103",
                                        u"ical", u"icala", u"icale", u"icali",
                                        u"ical\u0103"):
                            word = u"".join((word[:-len(suffix)], u"ic"))

                        elif suffix in (u"ativ", u"ativa", u"ative", u"ativi",
                                        u"ativ\u0103", u"a\u0163iune",
                                        u"atoare", u"ator", u"atori",
                                        u"\u0103toare",
                                        u"\u0103tor", u"\u0103tori"):
                            word = u"".join((word[:-len(suffix)], u"at"))

                            if suffix in r2:
                                r2 = u"".join((r2[:-len(suffix)], u"at"))

                        elif suffix in (u"itiv", u"itiva", u"itive", u"itivi",
                                        u"itiv\u0103", u"i\u0163iune",
                                        u"itoare", u"itor", u"itori"):
                            word = u"".join((word[:-len(suffix)], u"it"))

                            if suffix in r2:
                                r2 = u"".join((r2[:-len(suffix)], u"it"))
                    else:
                        step1_success = False
                    break

            if not replacement_done:
                break

        # STEP 2: Removal of standard suffixes
        for suffix in self.__step2_suffixes:
            if word.endswith(suffix):
                if suffix in r2:
                    step2_success = True

                    if suffix in (u"iune", u"iuni"):
                        if word[-5] == u"\u0163":
                            word = u"".join((word[:-5], u"t"))

                    elif suffix in (u"ism", u"isme", u"ist", u"ista", u"iste",
                                    u"isti", u"ist\u0103", u"i\u015Fti"):
                        word = u"".join((word[:-len(suffix)], u"ist"))

                    else:
                        word = word[:-len(suffix)]
                break

        # STEP 3: Removal of verb suffixes
        if not step1_success and not step2_success:
            for suffix in self.__step3_suffixes:
                if word.endswith(suffix):
                    if suffix in rv:
                        if suffix in (u'seser\u0103\u0163i', u'seser\u0103m',
                                      u'ser\u0103\u0163i', u'sese\u015Fi',
                                      u'seser\u0103', u'ser\u0103m', u'sesem',
                                      u'se\u015Fi', u'ser\u0103', u'sese',
                                      u'a\u0163i', u'e\u0163i', u'i\u0163i',
                                      u'\xE2\u0163i', u'sei', u'\u0103m',
                                      u'em', u'im', u'\xE2m', u'se'):
                            word = word[:-len(suffix)]
                            rv = rv[:-len(suffix)]
                        else:
                            if (not rv.startswith(suffix) and
                                rv[rv.index(suffix)-1] not in
                                u"aeio\u0103\xE2\xEE"):
                                word = word[:-len(suffix)]
                        break

        # STEP 4: Removal of final vowel
        for suffix in (u"ie", u"a", u"e", u"i", u"\u0103"):
            if word.endswith(suffix):
                if suffix in rv:
                    word = word[:-len(suffix)]
                break

        word = word.replace(u"I", u"i").replace(u"U", u"u")


        return word



class RussianStemmer(_LanguageSpecificStemmer):

    u"""
    The Russian Snowball stemmer.

    :cvar __perfective_gerund_suffixes: Suffixes to be deleted.
    :type __perfective_gerund_suffixes: tuple
    :cvar __adjectival_suffixes: Suffixes to be deleted.
    :type __adjectival_suffixes: tuple
    :cvar __reflexive_suffixes: Suffixes to be deleted.
    :type __reflexive_suffixes: tuple
    :cvar __verb_suffixes: Suffixes to be deleted.
    :type __verb_suffixes: tuple
    :cvar __noun_suffixes: Suffixes to be deleted.
    :type __noun_suffixes: tuple
    :cvar __superlative_suffixes: Suffixes to be deleted.
    :type __superlative_suffixes: tuple
    :cvar __derivational_suffixes: Suffixes to be deleted.
    :type __derivational_suffixes: tuple
    :note: A detailed description of the Russian
           stemming algorithm can be found under
           http://snowball.tartarus.org/algorithms/russian/stemmer.html

    """

    __perfective_gerund_suffixes = (u"ivshis'", u"yvshis'", u"vshis'",
                                      u"ivshi", u"yvshi", u"vshi", u"iv",
                                      u"yv", u"v")
    __adjectival_suffixes = (u'ui^ushchi^ui^u', u'ui^ushchi^ai^a',
                               u'ui^ushchimi', u'ui^ushchymi', u'ui^ushchego',
                               u'ui^ushchogo', u'ui^ushchemu', u'ui^ushchomu',
                               u'ui^ushchikh', u'ui^ushchykh',
                               u'ui^ushchui^u', u'ui^ushchaia',
                               u'ui^ushchoi^u', u'ui^ushchei^u',
                               u'i^ushchi^ui^u', u'i^ushchi^ai^a',
                               u'ui^ushchee', u'ui^ushchie',
                               u'ui^ushchye', u'ui^ushchoe', u'ui^ushchei`',
                               u'ui^ushchii`', u'ui^ushchyi`',
                               u'ui^ushchoi`', u'ui^ushchem', u'ui^ushchim',
                               u'ui^ushchym', u'ui^ushchom', u'i^ushchimi',
                               u'i^ushchymi', u'i^ushchego', u'i^ushchogo',
                               u'i^ushchemu', u'i^ushchomu', u'i^ushchikh',
                               u'i^ushchykh', u'i^ushchui^u', u'i^ushchai^a',
                               u'i^ushchoi^u', u'i^ushchei^u', u'i^ushchee',
                               u'i^ushchie', u'i^ushchye', u'i^ushchoe',
                               u'i^ushchei`', u'i^ushchii`',
                               u'i^ushchyi`', u'i^ushchoi`', u'i^ushchem',
                               u'i^ushchim', u'i^ushchym', u'i^ushchom',
                               u'shchi^ui^u', u'shchi^ai^a', u'ivshi^ui^u',
                               u'ivshi^ai^a', u'yvshi^ui^u', u'yvshi^ai^a',
                               u'shchimi', u'shchymi', u'shchego', u'shchogo',
                               u'shchemu', u'shchomu', u'shchikh', u'shchykh',
                               u'shchui^u', u'shchai^a', u'shchoi^u',
                               u'shchei^u', u'ivshimi', u'ivshymi',
                               u'ivshego', u'ivshogo', u'ivshemu', u'ivshomu',
                               u'ivshikh', u'ivshykh', u'ivshui^u',
                               u'ivshai^a', u'ivshoi^u', u'ivshei^u',
                               u'yvshimi', u'yvshymi', u'yvshego', u'yvshogo',
                               u'yvshemu', u'yvshomu', u'yvshikh', u'yvshykh',
                               u'yvshui^u', u'yvshai^a', u'yvshoi^u',
                               u'yvshei^u', u'vshi^ui^u', u'vshi^ai^a',
                               u'shchee', u'shchie', u'shchye', u'shchoe',
                               u'shchei`', u'shchii`', u'shchyi`', u'shchoi`',
                               u'shchem', u'shchim', u'shchym', u'shchom',
                               u'ivshee', u'ivshie', u'ivshye', u'ivshoe',
                               u'ivshei`', u'ivshii`', u'ivshyi`',
                               u'ivshoi`', u'ivshem', u'ivshim', u'ivshym',
                               u'ivshom', u'yvshee', u'yvshie', u'yvshye',
                               u'yvshoe', u'yvshei`', u'yvshii`',
                               u'yvshyi`', u'yvshoi`', u'yvshem',
                               u'yvshim', u'yvshym', u'yvshom', u'vshimi',
                               u'vshymi', u'vshego', u'vshogo', u'vshemu',
                               u'vshomu', u'vshikh', u'vshykh', u'vshui^u',
                               u'vshai^a', u'vshoi^u', u'vshei^u',
                               u'emi^ui^u', u'emi^ai^a', u'nni^ui^u',
                               u'nni^ai^a', u'vshee',
                               u'vshie', u'vshye', u'vshoe', u'vshei`',
                               u'vshii`', u'vshyi`', u'vshoi`',
                               u'vshem', u'vshim', u'vshym', u'vshom',
                               u'emimi', u'emymi', u'emego', u'emogo',
                               u'ememu', u'emomu', u'emikh', u'emykh',
                               u'emui^u', u'emai^a', u'emoi^u', u'emei^u',
                               u'nnimi', u'nnymi', u'nnego', u'nnogo',
                               u'nnemu', u'nnomu', u'nnikh', u'nnykh',
                               u'nnui^u', u'nnai^a', u'nnoi^u', u'nnei^u',
                               u'emee', u'emie', u'emye', u'emoe',
                               u'emei`', u'emii`', u'emyi`',
                               u'emoi`', u'emem', u'emim', u'emym',
                               u'emom', u'nnee', u'nnie', u'nnye', u'nnoe',
                               u'nnei`', u'nnii`', u'nnyi`',
                               u'nnoi`', u'nnem', u'nnim', u'nnym',
                               u'nnom', u'i^ui^u', u'i^ai^a', u'imi', u'ymi',
                               u'ego', u'ogo', u'emu', u'omu', u'ikh',
                               u'ykh', u'ui^u', u'ai^a', u'oi^u', u'ei^u',
                               u'ee', u'ie', u'ye', u'oe', u'ei`',
                               u'ii`', u'yi`', u'oi`', u'em',
                               u'im', u'ym', u'om')
    __reflexive_suffixes = (u"si^a", u"s'")
    __verb_suffixes = (u"esh'", u'ei`te', u'ui`te', u'ui^ut',
                         u"ish'", u'ete', u'i`te', u'i^ut', u'nno',
                         u'ila', u'yla', u'ena', u'ite', u'ili', u'yli',
                         u'ilo', u'ylo', u'eno', u'i^at', u'uet', u'eny',
                         u"it'", u"yt'", u'ui^u', u'la', u'na', u'li',
                         u'em', u'lo', u'no', u'et', u'ny', u"t'",
                         u'ei`', u'ui`', u'il', u'yl', u'im',
                         u'ym', u'en', u'it', u'yt', u'i^u', u'i`',
                         u'l', u'n')
    __noun_suffixes = (u'ii^ami', u'ii^akh', u'i^ami', u'ii^am', u'i^akh',
                         u'ami', u'iei`', u'i^am', u'iem', u'akh',
                         u'ii^u', u"'i^u", u'ii^a', u"'i^a", u'ev', u'ov',
                         u'ie', u"'e", u'ei', u'ii', u'ei`',
                         u'oi`', u'ii`', u'em', u'am', u'om',
                         u'i^u', u'i^a', u'a', u'e', u'i', u'i`',
                         u'o', u'u', u'y', u"'")
    __superlative_suffixes = (u"ei`she", u"ei`sh")
    __derivational_suffixes = (u"ost'", u"ost")

    def stem(self, word):
        u"""
        Stem a Russian word and return the stemmed form.

        :param word: The word that is stemmed.
        :type word: str or unicode
        :return: The stemmed form.
        :rtype: unicode

        """
        if word in self.stopwords:
            return word

        chr_exceeded = False
        for i in xrange(len(word)):
            if ord(word[i]) not in xrange(256):
                chr_exceeded = True
                break

        if chr_exceeded:
            word = self.__cyrillic_to_roman(word)

        step1_success = False
        adjectival_removed = False
        verb_removed = False
        undouble_success = False
        superlative_removed = False

        rv, r2 = self.__regions_russian(word)

        # Step 1
        for suffix in self.__perfective_gerund_suffixes:
            if rv.endswith(suffix):
                if suffix in (u"v", u"vshi", u"vshis'"):
                    if (rv[-len(suffix)-3:-len(suffix)] == "i^a" or
                        rv[-len(suffix)-1:-len(suffix)] == "a"):
                        word = word[:-len(suffix)]
                        r2 = r2[:-len(suffix)]
                        rv = rv[:-len(suffix)]
                        step1_success = True
                        break
                else:
                    word = word[:-len(suffix)]
                    r2 = r2[:-len(suffix)]
                    rv = rv[:-len(suffix)]
                    step1_success = True
                    break

        if not step1_success:
            for suffix in self.__reflexive_suffixes:
                if rv.endswith(suffix):
                    word = word[:-len(suffix)]
                    r2 = r2[:-len(suffix)]
                    rv = rv[:-len(suffix)]
                    break

            for suffix in self.__adjectival_suffixes:
                if rv.endswith(suffix):
                    if suffix in (u'i^ushchi^ui^u', u'i^ushchi^ai^a',
                              u'i^ushchui^u', u'i^ushchai^a', u'i^ushchoi^u',
                              u'i^ushchei^u', u'i^ushchimi', u'i^ushchymi',
                              u'i^ushchego', u'i^ushchogo', u'i^ushchemu',
                              u'i^ushchomu', u'i^ushchikh', u'i^ushchykh',
                              u'shchi^ui^u', u'shchi^ai^a', u'i^ushchee',
                              u'i^ushchie', u'i^ushchye', u'i^ushchoe',
                              u'i^ushchei`', u'i^ushchii`', u'i^ushchyi`',
                              u'i^ushchoi`', u'i^ushchem', u'i^ushchim',
                              u'i^ushchym', u'i^ushchom', u'vshi^ui^u',
                              u'vshi^ai^a', u'shchui^u', u'shchai^a',
                              u'shchoi^u', u'shchei^u', u'emi^ui^u',
                              u'emi^ai^a', u'nni^ui^u', u'nni^ai^a',
                              u'shchimi', u'shchymi', u'shchego', u'shchogo',
                              u'shchemu', u'shchomu', u'shchikh', u'shchykh',
                              u'vshui^u', u'vshai^a', u'vshoi^u', u'vshei^u',
                              u'shchee', u'shchie', u'shchye', u'shchoe',
                              u'shchei`', u'shchii`', u'shchyi`', u'shchoi`',
                              u'shchem', u'shchim', u'shchym', u'shchom',
                              u'vshimi', u'vshymi', u'vshego', u'vshogo',
                              u'vshemu', u'vshomu', u'vshikh', u'vshykh',
                              u'emui^u', u'emai^a', u'emoi^u', u'emei^u',
                              u'nnui^u', u'nnai^a', u'nnoi^u', u'nnei^u',
                              u'vshee', u'vshie', u'vshye', u'vshoe',
                              u'vshei`', u'vshii`', u'vshyi`', u'vshoi`',
                              u'vshem', u'vshim', u'vshym', u'vshom',
                              u'emimi', u'emymi', u'emego', u'emogo',
                              u'ememu', u'emomu', u'emikh', u'emykh',
                              u'nnimi', u'nnymi', u'nnego', u'nnogo',
                              u'nnemu', u'nnomu', u'nnikh', u'nnykh',
                              u'emee', u'emie', u'emye', u'emoe', u'emei`',
                              u'emii`', u'emyi`', u'emoi`', u'emem', u'emim',
                              u'emym', u'emom', u'nnee', u'nnie', u'nnye',
                              u'nnoe', u'nnei`', u'nnii`', u'nnyi`', u'nnoi`',
                              u'nnem', u'nnim', u'nnym', u'nnom'):
                        if (rv[-len(suffix)-3:-len(suffix)] == "i^a" or
                            rv[-len(suffix)-1:-len(suffix)] == "a"):
                            word = word[:-len(suffix)]
                            r2 = r2[:-len(suffix)]
                            rv = rv[:-len(suffix)]
                            adjectival_removed = True
                            break
                    else:
                        word = word[:-len(suffix)]
                        r2 = r2[:-len(suffix)]
                        rv = rv[:-len(suffix)]
                        adjectival_removed = True
                        break

            if not adjectival_removed:
                for suffix in self.__verb_suffixes:
                    if rv.endswith(suffix):
                        if suffix in (u"la", u"na", u"ete", u"i`te", u"li",
                                      u"i`", u"l", u"em", u"n", u"lo", u"no",
                                      u"et", u"i^ut", u"ny", u"t'", u"esh'",
                                      u"nno"):
                            if (rv[-len(suffix)-3:-len(suffix)] == "i^a" or
                                rv[-len(suffix)-1:-len(suffix)] == "a"):
                                word = word[:-len(suffix)]
                                r2 = r2[:-len(suffix)]
                                rv = rv[:-len(suffix)]
                                verb_removed = True
                                break
                        else:
                            word = word[:-len(suffix)]
                            r2 = r2[:-len(suffix)]
                            rv = rv[:-len(suffix)]
                            verb_removed = True
                            break

            if not adjectival_removed and not verb_removed:
                for suffix in self.__noun_suffixes:
                    if rv.endswith(suffix):
                        word = word[:-len(suffix)]
                        r2 = r2[:-len(suffix)]
                        rv = rv[:-len(suffix)]
                        break

        # Step 2
        if rv.endswith("i"):
            word = word[:-1]
            r2 = r2[:-1]

        # Step 3
        for suffix in self.__derivational_suffixes:
            if r2.endswith(suffix):
                word = word[:-len(suffix)]
                break

        # Step 4
        if word.endswith("nn"):
            word = word[:-1]
            undouble_success = True

        if not undouble_success:
            for suffix in self.__superlative_suffixes:
                if word.endswith(suffix):
                    word = word[:-len(suffix)]
                    superlative_removed = True
                    break
            if word.endswith("nn"):
                word = word[:-1]

        if not undouble_success and not superlative_removed:
            if word.endswith("'"):
                word = word[:-1]

        if chr_exceeded:
            word = self.__roman_to_cyrillic(word)


        return word



    def __regions_russian(self, word):
        u"""
        Return the regions RV and R2 which are used by the Russian stemmer.

        In any word, RV is the region after the first vowel,
        or the end of the word if it contains no vowel.

        R2 is the region after the first non-vowel following
        a vowel in R1, or the end of the word if there is no such non-vowel.

        R1 is the region after the first non-vowel following a vowel,
        or the end of the word if there is no such non-vowel.

        :param word: The Russian word whose regions RV and R2 are determined.
        :type word: str or unicode
        :return: the regions RV and R2 for the respective Russian word.
        :rtype: tuple
        :note: This helper method is invoked by the stem method of the subclass
               RussianStemmer. It is not to be invoked directly!

        """
        r1 = u""
        r2 = u""
        rv = u""

        vowels = (u"A", u"U", u"E", u"a", u"e", u"i", u"o", u"u", u"y")
        word = (word.replace(u"i^a", u"A")
                    .replace(u"i^u", u"U")
                    .replace(u"e`", u"E"))

        for i in xrange(1, len(word)):
            if word[i] not in vowels and word[i-1] in vowels:
                r1 = word[i+1:]
                break

        for i in xrange(1, len(r1)):
            if r1[i] not in vowels and r1[i-1] in vowels:
                r2 = r1[i+1:]
                break

        for i in xrange(len(word)):
            if word[i] in vowels:
                rv = word[i+1:]
                break

        r2 = (r2.replace(u"A", u"i^a")
                .replace(u"U", u"i^u")
                .replace(u"E", u"e`"))
        rv = (rv.replace(u"A", u"i^a")
              .replace(u"U", u"i^u")
              .replace(u"E", u"e`"))


        return (rv, r2)



    def __cyrillic_to_roman(self, word):
        u"""
        Transliterate a Russian word into the Roman alphabet.

        A Russian word whose letters consist of the Cyrillic
        alphabet are transliterated into the Roman alphabet
        in order to ease the forthcoming stemming process.

        :param word: The word that is transliterated.
        :type word: unicode
        :return: the transliterated word.
        :rtype: unicode
        :note: This helper method is invoked by the stem method of the subclass
               RussianStemmer. It is not to be invoked directly!

        """
        word = (word.replace(u"\u0410", u"a").replace(u"\u0430", u"a")
                    .replace(u"\u0411", u"b").replace(u"\u0431", u"b")
                    .replace(u"\u0412", u"v").replace(u"\u0432", u"v")
                    .replace(u"\u0413", u"g").replace(u"\u0433", u"g")
                    .replace(u"\u0414", u"d").replace(u"\u0434", u"d")
                    .replace(u"\u0415", u"e").replace(u"\u0435", u"e")
                    .replace(u"\u0401", u"e").replace(u"\u0451", u"e")
                    .replace(u"\u0416", u"zh").replace(u"\u0436", u"zh")
                    .replace(u"\u0417", u"z").replace(u"\u0437", u"z")
                    .replace(u"\u0418", u"i").replace(u"\u0438", u"i")
                    .replace(u"\u0419", u"i`").replace(u"\u0439", u"i`")
                    .replace(u"\u041A", u"k").replace(u"\u043A", u"k")
                    .replace(u"\u041B", u"l").replace(u"\u043B", u"l")
                    .replace(u"\u041C", u"m").replace(u"\u043C", u"m")
                    .replace(u"\u041D", u"n").replace(u"\u043D", u"n")
                    .replace(u"\u041E", u"o").replace(u"\u043E", u"o")
                    .replace(u"\u041F", u"p").replace(u"\u043F", u"p")
                    .replace(u"\u0420", u"r").replace(u"\u0440", u"r")
                    .replace(u"\u0421", u"s").replace(u"\u0441", u"s")
                    .replace(u"\u0422", u"t").replace(u"\u0442", u"t")
                    .replace(u"\u0423", u"u").replace(u"\u0443", u"u")
                    .replace(u"\u0424", u"f").replace(u"\u0444", u"f")
                    .replace(u"\u0425", u"kh").replace(u"\u0445", u"kh")
                    .replace(u"\u0426", u"t^s").replace(u"\u0446", u"t^s")
                    .replace(u"\u0427", u"ch").replace(u"\u0447", u"ch")
                    .replace(u"\u0428", u"sh").replace(u"\u0448", u"sh")
                    .replace(u"\u0429", u"shch").replace(u"\u0449", u"shch")
                    .replace(u"\u042A", u"''").replace(u"\u044A", u"''")
                    .replace(u"\u042B", u"y").replace(u"\u044B", u"y")
                    .replace(u"\u042C", u"'").replace(u"\u044C", u"'")
                    .replace(u"\u042D", u"e`").replace(u"\u044D", u"e`")
                    .replace(u"\u042E", u"i^u").replace(u"\u044E", u"i^u")
                    .replace(u"\u042F", u"i^a").replace(u"\u044F", u"i^a"))


        return word



    def __roman_to_cyrillic(self, word):
        u"""
        Transliterate a Russian word back into the Cyrillic alphabet.

        A Russian word formerly transliterated into the Roman alphabet
        in order to ease the stemming process, is transliterated back
        into the Cyrillic alphabet, its original form.

        :param word: The word that is transliterated.
        :type word: str or unicode
        :return: word, the transliterated word.
        :rtype: unicode
        :note: This helper method is invoked by the stem method of the subclass
               RussianStemmer. It is not to be invoked directly!

        """
        word = (word.replace(u"i^u", u"\u044E").replace(u"i^a", u"\u044F")
                    .replace(u"shch", u"\u0449").replace(u"kh", u"\u0445")
                    .replace(u"t^s", u"\u0446").replace(u"ch", u"\u0447")
                    .replace(u"e`", u"\u044D").replace(u"i`", u"\u0439")
                    .replace(u"sh", u"\u0448").replace(u"k", u"\u043A")
                    .replace(u"e", u"\u0435").replace(u"zh", u"\u0436")
                    .replace(u"a", u"\u0430").replace(u"b", u"\u0431")
                    .replace(u"v", u"\u0432").replace(u"g", u"\u0433")
                    .replace(u"d", u"\u0434").replace(u"e", u"\u0435")
                    .replace(u"z", u"\u0437").replace(u"i", u"\u0438")
                    .replace(u"l", u"\u043B").replace(u"m", u"\u043C")
                    .replace(u"n", u"\u043D").replace(u"o", u"\u043E")
                    .replace(u"p", u"\u043F").replace(u"r", u"\u0440")
                    .replace(u"s", u"\u0441").replace(u"t", u"\u0442")
                    .replace(u"u", u"\u0443").replace(u"f", u"\u0444")
                    .replace(u"''", u"\u044A").replace(u"y", u"\u044B")
                    .replace(u"'", u"\u044C"))


        return word



class SpanishStemmer(_StandardStemmer):

    u"""
    The Spanish Snowball stemmer.

    :cvar __vowels: The Spanish vowels.
    :type __vowels: unicode
    :cvar __step0_suffixes: Suffixes to be deleted in step 0 of the algorithm.
    :type __step0_suffixes: tuple
    :cvar __step1_suffixes: Suffixes to be deleted in step 1 of the algorithm.
    :type __step1_suffixes: tuple
    :cvar __step2a_suffixes: Suffixes to be deleted in step 2a of the algorithm.
    :type __step2a_suffixes: tuple
    :cvar __step2b_suffixes: Suffixes to be deleted in step 2b of the algorithm.
    :type __step2b_suffixes: tuple
    :cvar __step3_suffixes: Suffixes to be deleted in step 3 of the algorithm.
    :type __step3_suffixes: tuple
    :note: A detailed description of the Spanish
           stemming algorithm can be found under
           http://snowball.tartarus.org/algorithms/spanish/stemmer.html

    """

    __vowels = u"aeiou\xE1\xE9\xED\xF3\xFA\xFC"
    __step0_suffixes = (u"selas", u"selos", u"sela", u"selo", u"las",
                        u"les", u"los", u"nos", u"me", u"se", u"la", u"le",
                        u"lo")
    __step1_suffixes = (u'amientos', u'imientos', u'amiento', u'imiento',
                        u'aciones', u'uciones', u'adoras', u'adores',
                        u'ancias', u'log\xEDas', u'encias', u'amente',
                        u'idades', u'anzas', u'ismos', u'ables', u'ibles',
                        u'istas', u'adora', u'aci\xF3n', u'antes',
                        u'ancia', u'log\xEDa', u'uci\xf3n', u'encia',
                        u'mente', u'anza', u'icos', u'icas', u'ismo',
                        u'able', u'ible', u'ista', u'osos', u'osas',
                        u'ador', u'ante', u'idad', u'ivas', u'ivos',
                        u'ico',
                        u'ica', u'oso', u'osa', u'iva', u'ivo')
    __step2a_suffixes = (u'yeron', u'yendo', u'yamos', u'yais', u'yan',
                         u'yen', u'yas', u'yes', u'ya', u'ye', u'yo',
                         u'y\xF3')
    __step2b_suffixes = (u'ar\xEDamos', u'er\xEDamos', u'ir\xEDamos',
                         u'i\xE9ramos', u'i\xE9semos', u'ar\xEDais',
                         u'aremos', u'er\xEDais', u'eremos',
                         u'ir\xEDais', u'iremos', u'ierais', u'ieseis',
                         u'asteis', u'isteis', u'\xE1bamos',
                         u'\xE1ramos', u'\xE1semos', u'ar\xEDan',
                         u'ar\xEDas', u'ar\xE9is', u'er\xEDan',
                         u'er\xEDas', u'er\xE9is', u'ir\xEDan',
                         u'ir\xEDas', u'ir\xE9is',
                         u'ieran', u'iesen', u'ieron', u'iendo', u'ieras',
                         u'ieses', u'abais', u'arais', u'aseis',
                         u'\xE9amos', u'ar\xE1n', u'ar\xE1s',
                         u'ar\xEDa', u'er\xE1n', u'er\xE1s',
                         u'er\xEDa', u'ir\xE1n', u'ir\xE1s',
                         u'ir\xEDa', u'iera', u'iese', u'aste', u'iste',
                         u'aban', u'aran', u'asen', u'aron', u'ando',
                         u'abas', u'adas', u'idas', u'aras', u'ases',
                         u'\xEDais', u'ados', u'idos', u'amos', u'imos',
                         u'emos', u'ar\xE1', u'ar\xE9', u'er\xE1',
                         u'er\xE9', u'ir\xE1', u'ir\xE9', u'aba',
                         u'ada', u'ida', u'ara', u'ase', u'\xEDan',
                         u'ado', u'ido', u'\xEDas', u'\xE1is',
                         u'\xE9is', u'\xEDa', u'ad', u'ed', u'id',
                         u'an', u'i\xF3', u'ar', u'er', u'ir', u'as',
                         u'\xEDs', u'en', u'es')
    __step3_suffixes = (u"os", u"a", u"e", u"o", u"\xE1",
                        u"\xE9", u"\xED", u"\xF3")

    def stem(self, word):
        u"""
        Stem a Spanish word and return the stemmed form.

        :param word: The word that is stemmed.
        :type word: str or unicode
        :return: The stemmed form.
        :rtype: unicode

        """
        word = word.lower()

        if word in self.stopwords:
            return word

        step1_success = False

        r1, r2 = self._r1r2_standard(word, self.__vowels)
        rv = self._rv_standard(word, self.__vowels)

        # STEP 0: Attached pronoun
        for suffix in self.__step0_suffixes:
            if word.endswith(suffix):
                if rv.endswith(suffix):
                    if rv[:-len(suffix)].endswith((u"i\xE9ndo",
                                                   u"\xE1ndo",
                                                   u"\xE1r", u"\xE9r",
                                                   u"\xEDr")):
                        word = (word[:-len(suffix)].replace(u"\xE1", u"a")
                                                   .replace(u"\xE9", u"e")
                                                   .replace(u"\xED", u"i"))
                        r1 = (r1[:-len(suffix)].replace(u"\xE1", u"a")
                                               .replace(u"\xE9", u"e")
                                               .replace(u"\xED", u"i"))
                        r2 = (r2[:-len(suffix)].replace(u"\xE1", u"a")
                                               .replace(u"\xE9", u"e")
                                               .replace(u"\xED", u"i"))
                        rv = (rv[:-len(suffix)].replace(u"\xE1", u"a")
                                               .replace(u"\xE9", u"e")
                                               .replace(u"\xED", u"i"))

                    elif rv[:-len(suffix)].endswith((u"ando", u"iendo",
                                                     u"ar", u"er", u"ir")):
                        word = word[:-len(suffix)]
                        r1 = r1[:-len(suffix)]
                        r2 = r2[:-len(suffix)]
                        rv = rv[:-len(suffix)]

                    elif (rv[:-len(suffix)].endswith(u"yendo") and
                          word[:-len(suffix)].endswith(u"uyendo")):
                        word = word[:-len(suffix)]
                        r1 = r1[:-len(suffix)]
                        r2 = r2[:-len(suffix)]
                        rv = rv[:-len(suffix)]
                break

        # STEP 1: Standard suffix removal
        for suffix in self.__step1_suffixes:
            if word.endswith(suffix):
                if suffix == u"amente" and r1.endswith(suffix):
                    step1_success = True
                    word = word[:-6]
                    r2 = r2[:-6]
                    rv = rv[:-6]

                    if r2.endswith(u"iv"):
                        word = word[:-2]
                        r2 = r2[:-2]
                        rv = rv[:-2]

                        if r2.endswith(u"at"):
                            word = word[:-2]
                            rv = rv[:-2]

                    elif r2.endswith((u"os", u"ic", u"ad")):
                        word = word[:-2]
                        rv = rv[:-2]

                elif r2.endswith(suffix):
                    step1_success = True
                    if suffix in (u"adora", u"ador", u"aci\xF3n", u"adoras",
                                  u"adores", u"aciones", u"ante", u"antes",
                                  u"ancia", u"ancias"):
                        word = word[:-len(suffix)]
                        r2 = r2[:-len(suffix)]
                        rv = rv[:-len(suffix)]

                        if r2.endswith(u"ic"):
                            word = word[:-2]
                            rv = rv[:-2]

                    elif suffix in (u"log\xEDa", u"log\xEDas"):
                        word = word.replace(suffix, u"log")
                        rv = rv.replace(suffix, u"log")

                    elif suffix in (u"uci\xF3n", u"uciones"):
                        word = word.replace(suffix, u"u")
                        rv = rv.replace(suffix, u"u")

                    elif suffix in (u"encia", u"encias"):
                        word = word.replace(suffix, u"ente")
                        rv = rv.replace(suffix, u"ente")

                    elif suffix == u"mente":
                        word = word[:-5]
                        r2 = r2[:-5]
                        rv = rv[:-5]

                        if r2.endswith((u"ante", u"able", u"ible")):
                            word = word[:-4]
                            rv = rv[:-4]

                    elif suffix in (u"idad", u"idades"):
                        word = word[:-len(suffix)]
                        r2 = r2[:-len(suffix)]
                        rv = rv[:-len(suffix)]

                        for pre_suff in (u"abil", u"ic", u"iv"):
                            if r2.endswith(pre_suff):
                                word = word[:-len(pre_suff)]
                                rv = rv[:-len(pre_suff)]

                    elif suffix in (u"ivo", u"iva", u"ivos", u"ivas"):
                        word = word[:-len(suffix)]
                        r2 = r2[:-len(suffix)]
                        rv = rv[:-len(suffix)]
                        if r2.endswith(u"at"):
                            word = word[:-2]
                            rv = rv[:-2]
                    else:
                        word = word[:-len(suffix)]
                        rv = rv[:-len(suffix)]
                break

        # STEP 2a: Verb suffixes beginning 'y'
        if not step1_success:
            for suffix in self.__step2a_suffixes:
                if (rv.endswith(suffix) and
                    word[-len(suffix)-1:-len(suffix)] == u"u"):
                    word = word[:-len(suffix)]
                    rv = rv[:-len(suffix)]
                    break

        # STEP 2b: Other verb suffixes
            for suffix in self.__step2b_suffixes:
                if rv.endswith(suffix):
                    if suffix in (u"en", u"es", u"\xE9is", u"emos"):
                        word = word[:-len(suffix)]
                        rv = rv[:-len(suffix)]

                        if word.endswith(u"gu"):
                            word = word[:-1]

                        if rv.endswith(u"gu"):
                            rv = rv[:-1]
                    else:
                        word = word[:-len(suffix)]
                        rv = rv[:-len(suffix)]
                    break

        # STEP 3: Residual suffix
        for suffix in self.__step3_suffixes:
            if rv.endswith(suffix):
                if suffix in (u"e", u"\xE9"):
                    word = word[:-len(suffix)]
                    rv = rv[:-len(suffix)]

                    if word[-2:] == u"gu" and rv[-1] == u"u":
                        word = word[:-1]
                else:
                    word = word[:-len(suffix)]
                break

        word = (word.replace(u"\xE1", u"a").replace(u"\xE9", u"e")
                    .replace(u"\xED", u"i").replace(u"\xF3", u"o")
                    .replace(u"\xFA", u"u"))


        return word



class SwedishStemmer(_ScandinavianStemmer):

    u"""
    The Swedish Snowball stemmer.

    :cvar __vowels: The Swedish vowels.
    :type __vowels: unicode
    :cvar __s_ending: Letters that may directly appear before a word final 's'.
    :type __s_ending: unicode
    :cvar __step1_suffixes: Suffixes to be deleted in step 1 of the algorithm.
    :type __step1_suffixes: tuple
    :cvar __step2_suffixes: Suffixes to be deleted in step 2 of the algorithm.
    :type __step2_suffixes: tuple
    :cvar __step3_suffixes: Suffixes to be deleted in step 3 of the algorithm.
    :type __step3_suffixes: tuple
    :note: A detailed description of the Swedish
           stemming algorithm can be found under
           http://snowball.tartarus.org/algorithms/swedish/stemmer.html

    """

    __vowels = u"aeiouy\xE4\xE5\xF6"
    __s_ending = u"bcdfghjklmnoprtvy"
    __step1_suffixes = (u"heterna", u"hetens", u"heter", u"heten",
                        u"anden", u"arnas", u"ernas", u"ornas", u"andes",
                        u"andet", u"arens", u"arna", u"erna", u"orna",
                        u"ande", u"arne", u"aste", u"aren", u"ades",
                        u"erns", u"ade", u"are", u"ern", u"ens", u"het",
                        u"ast", u"ad", u"en", u"ar", u"er", u"or", u"as",
                        u"es", u"at", u"a", u"e", u"s")
    __step2_suffixes = (u"dd", u"gd", u"nn", u"dt", u"gt", u"kt", u"tt")
    __step3_suffixes = (u"fullt", u"l\xF6st", u"els", u"lig", u"ig")

    def stem(self, word):
        u"""
        Stem a Swedish word and return the stemmed form.

        :param word: The word that is stemmed.
        :type word: str or unicode
        :return: The stemmed form.
        :rtype: unicode

        """
        word = word.lower()

        if word in self.stopwords:
            return word

        r1 = self._r1_scandinavian(word, self.__vowels)

        # STEP 1
        for suffix in self.__step1_suffixes:
            if r1.endswith(suffix):
                if suffix == u"s":
                    if word[-2] in self.__s_ending:
                        word = word[:-1]
                        r1 = r1[:-1]
                else:
                    word = word[:-len(suffix)]
                    r1 = r1[:-len(suffix)]
                break

        # STEP 2
        for suffix in self.__step2_suffixes:
            if r1.endswith(suffix):
                word = word[:-1]
                r1 = r1[:-1]
                break

        # STEP 3
        for suffix in self.__step3_suffixes:
            if r1.endswith(suffix):
                if suffix in (u"els", u"lig", u"ig"):
                    word = word[:-len(suffix)]
                elif suffix in (u"fullt", u"l\xF6st"):
                    word = word[:-1]
                break


        return word



def demo():
    u"""
    This function provides a demonstration of the Snowball stemmers.

    After invoking this function and specifying a language,
    it stems an excerpt of the Universal Declaration of Human Rights
    (which is a part of the NLTK corpus collection) and then prints
    out the original and the stemmed text.

    """

    import re
    from nltk.corpus import udhr

    udhr_corpus = {"danish":     "Danish_Dansk-Latin1",
                   "dutch":      "Dutch_Nederlands-Latin1",
                   "english":    "English-Latin1",
                   "finnish":    "Finnish_Suomi-Latin1",
                   "french":     "French_Francais-Latin1",
                   "german":     "German_Deutsch-Latin1",
                   "hungarian":  "Hungarian_Magyar-UTF8",
                   "italian":    "Italian_Italiano-Latin1",
                   "norwegian":  "Norwegian-Latin1",
                   "porter":     "English-Latin1",
                   "portuguese": "Portuguese_Portugues-Latin1",
                   "romanian":   "Romanian_Romana-Latin2",
                   "russian":    "Russian-UTF8",
                   "spanish":    "Spanish-Latin1",
                   "swedish":    "Swedish_Svenska-Latin1",
                   }

    print u"\n"
    print u"******************************"
    print u"Demo for the Snowball stemmers"
    print u"******************************"

    while True:

        language = raw_input(u"Please enter the name of the language " +
                             u"to be demonstrated\n" +
                             u"/".join(SnowballStemmer.languages) +
                             u"\n" +
                             u"(enter 'exit' in order to leave): ")

        if language == u"exit":
            break

        if language not in SnowballStemmer.languages:
            print (u"\nOops, there is no stemmer for this language. " +
                   u"Please try again.\n")
            continue

        stemmer = SnowballStemmer(language)
        excerpt = udhr.words(udhr_corpus[language]) [:300]

        stemmed = u" ".join([stemmer.stem(word) for word in excerpt])
        stemmed = re.sub(r"(.{,70})\s", r'\1\n', stemmed+u' ').rstrip()
        excerpt = u" ".join(excerpt)
        excerpt = re.sub(r"(.{,70})\s", r'\1\n', excerpt+u' ').rstrip()

        print u"\n"
        print u'-' * 70
        print u'ORIGINAL'.center(70)
        print excerpt
        print u"\n\n"
        print u'STEMMED RESULTS'.center(70)
        print stemmed
        print u'-' * 70
        print u"\n"



if __name__ == "__main__":
    import doctest
    doctest.testmod(optionflags=doctest.NORMALIZE_WHITESPACE)

