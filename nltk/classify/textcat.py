# Natural Language Toolkit: Language ID module using TextCat algorithm
#
# Copyright (C) 2001-2026 NLTK Project
# Author: Avital Pekker <avital.pekker@utoronto.ca>
#
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
A module for language identification using the TextCat algorithm.
An implementation of the text categorization algorithm
presented in Cavnar, W. B. and J. M. Trenkle,
"N-Gram-Based Text Categorization".

The algorithm takes advantage of Zipf's law and uses
n-gram frequencies to profile languages and text-yet to
be identified-then compares using a distance measure.

Language n-grams are provided by the "An Crubadan"
project. A corpus reader was created separately to read
those files.

For details regarding the algorithm, see:
https://www.let.rug.nl/~vannoord/TextCat/textcat.pdf

For details about An Crubadan, see:
https://borel.slu.edu/crubadan/index.html
"""

from sys import maxsize

from nltk.util import trigrams

# Note: this is NOT "re" you're likely used to. The regex module
# is an alternative to the standard re module that supports
# Unicode codepoint properties with the \p{} syntax.
# You may have to "pip install regx"
try:
    import regex as re
except ImportError:
    re = None
######################################################################
##  Language identification using TextCat
######################################################################


class TextCat:
    _corpus = None
    fingerprints = {}
    _START_CHAR = "<"
    _END_CHAR = ">"

    last_distances = {}

    def __init__(self):
        if not re:
            raise OSError(
                "classify.textcat requires the regex module that "
                "supports unicode. Try '$ pip install regex' and "
                "see https://pypi.python.org/pypi/regex for "
                "further details."
            )

        from nltk.corpus import crubadan

        self._corpus = crubadan
        # Load all language ngrams into cache
        for lang in self._corpus.langs():
            self._corpus.lang_freq(lang)

    def remove_punctuation(self, text):
        """Get rid of punctuation except apostrophes"""
        return re.sub(r"[^\P{P}\']+", "", text)

    def profile(self, text):
        """Create FreqDist of trigrams within text"""
        from nltk import FreqDist, word_tokenize

        clean_text = self.remove_punctuation(text)
        tokens = word_tokenize(clean_text)

        fingerprint = FreqDist()
        for t in tokens:
            token_trigram_tuples = trigrams(self._START_CHAR + t + self._END_CHAR)
            token_trigrams = ["".join(tri) for tri in token_trigram_tuples]

            for cur_trigram in token_trigrams:
                if cur_trigram in fingerprint:
                    fingerprint[cur_trigram] += 1
                else:
                    fingerprint[cur_trigram] = 1

        return fingerprint

    def calc_dist(self, lang, trigram, text_profile):
        """Calculate the "out-of-place" measure between the
        text and language profile for a single trigram"""

        lang_fd = self._corpus.lang_freq(lang)
        dist = 0

        if trigram in lang_fd:
            idx_lang_profile = list(lang_fd.keys()).index(trigram)
            idx_text = list(text_profile.keys()).index(trigram)

            # print(idx_lang_profile, ", ", idx_text)
            dist = abs(idx_lang_profile - idx_text)
        else:
            # Arbitrary but should be larger than
            # any possible trigram file length
            # in terms of total lines
            dist = maxsize

        return dist

    def lang_dists(self, text):
        """Calculate the "out-of-place" measure between
        the text and all languages"""

        distances = {}
        profile = self.profile(text)
        # For all the languages
        for lang in self._corpus._all_lang_freq.keys():
            # Calculate distance metric for every trigram in
            # input text to be identified
            lang_dist = 0
            for trigram in profile:
                lang_dist += self.calc_dist(lang, trigram, profile)

            distances[lang] = lang_dist

        return distances

    def guess_language(self, text, return_all=False):
        """
        Determines the most likely language(s) for the given text.

        Parameters
        ----------
        text : str
            The text whose language is to be identified.
        return_all : bool, optional
            If False (default), returns a single ISO 639-3 language code as a str,
            or None if the language is ambiguous or cannot be determined.
            If True, returns a list of all language codes sharing the minimal distance.
            The list will have one element if there is a unique best match,
            multiple elements for ties, or be empty if no language is found.

        Returns
        -------
        str or None, or list of str
            If return_all is False:
                - str: language code if unique minimum found
                - None: if ambiguous or not classifiable
            If return_all is True:
                - list: possible language code(s), or empty list if not classifiable

        Examples
        --------
        >>> from nltk.classify.textcat import TextCat
        >>> cat = TextCat()
        >>> print(cat.guess_language('The quick brown fox jumps over the lazy dog.'))
        eng

        A case with no information, returns None or an empty list:

        >>> print(cat.guess_language('', return_all=True))
        []
        >>> print(cat.guess_language(''))
        None

        A case where a single short input ties between Catalan and French:

        >>> print(sorted(cat.guess_language('ent', return_all=True)))
        ['cat', 'fra']

        By default (`return_all=False`), in a tie, guess_language returns None:

        >>> print(cat.guess_language('ent'))
        None

        Note: For short or generic inputs, or for closely related languages,
        the classifier may return an unexpected language. For example,
        the following is a perfectly grammatical English sentence, but may
        be classified as Scots ('sco') due to profile similarity:

        >>> print(cat.guess_language('This is a short English sentence.'))
        sco

        This behavior is not a bug, but an artifact of the underlying n-gram profiles.
        The classifier should be used with sufficiently distinctive and longer text fragments
        for best accuracy.
        """
        self.last_distances = self.lang_dists(text)
        if not self.last_distances:
            if return_all:
                return []
            return None
        min_dist = min(self.last_distances.values())
        candidates = [
            lang for lang, dist in self.last_distances.items() if dist == min_dist
        ]
        all_languages = list(self.last_distances.keys())

        # Special case: all languages match equally (uninformative), return empty list/None
        if len(candidates) == len(all_languages):
            if return_all:
                return []
            return None

        if return_all:
            return candidates
        if len(candidates) == 1:
            return candidates[0]
        return None


def demo():
    from nltk.corpus import udhr

    langs = [
        "Kurdish-UTF8",
        "Abkhaz-UTF8",
        "Farsi_Persian-UTF8",
        "Hindi-UTF8",
        "Hawaiian-UTF8",
        "Russian-UTF8",
        "Vietnamese-UTF8",
        "Serbian_Srpski-UTF8",
        "Esperanto-UTF8",
    ]

    friendly = {
        "kmr": "Northern Kurdish",
        "abk": "Abkhazian",
        "pes": "Iranian Persian",
        "hin": "Hindi",
        "haw": "Hawaiian",
        "rus": "Russian",
        "vie": "Vietnamese",
        "srp": "Serbian",
        "epo": "Esperanto",
    }

    tc = TextCat()

    for cur_lang in langs:
        # Get raw data from UDHR corpus
        raw_sentences = udhr.sents(cur_lang)
        rows = len(raw_sentences) - 1
        cols = list(map(len, raw_sentences))

        sample = ""

        # Generate a sample text of the language
        for i in range(0, rows):
            cur_sent = " " + " ".join([raw_sentences[i][j] for j in range(0, cols[i])])
            sample += cur_sent

        # Try to detect what it is
        print("Language snippet: " + sample[0:140] + "...")
        guess = tc.guess_language(sample)
        print(f"Language detection: {guess} ({friendly[guess]})")
        print("#" * 140)


if __name__ == "__main__":
    demo()
