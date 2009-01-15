# Natural Language Toolkit: Collocation Finders
#
# Copyright (C) 2001-2009 NLTK Project
# Author: Joel Nothman <jnothman@student.usyd.edu.au>
# URL: <http://nltk.org>
# For license information, see LICENSE.TXT
#

"""
Classes to aid in the finding and ranking of collocations within a corpus.

"""

import itertools as _itertools
from operator import itemgetter as _itemgetter

from nltk.probability import FreqDist as _FreqDist
from nltk.util import ingrams as _ingrams

class AbstractCollocationFinder(object):
    """
    An abstract base class for X{collocation finder}s whose purpose is to
    collect collocation candidate frequencies, filter and rank them.
    """

    def __init__(self, word_fd, ngram_fd):
        """As a minimum, collocation finders require the frequencies of each
        word in a corpus, and the joint frequency of word tuples. This data
        should be provided through L{nltk.probability.FreqDist} objects or an
        identical interface.
        """
        self.word_fd = word_fd
        self.ngram_fd = ngram_fd

    @classmethod
    def from_documents(cls, documents):
        """Constructs a collocation finder given a collection of documents,
        each of which is a list (or iterable) of tokens.
        """
        return cls.from_words(_itertools.chain(*documents))

    @staticmethod
    def _ngram_freqdist(words, n):
        return _FreqDist(tuple(words[i:i+n]) for i in range(len(words)-1))

    def _apply_filter(self, fn=lambda ngram, freq: False):
        """Generic filter removes ngrams from the frequency distribution
        if the function returns True when passed an ngram tuple.
        """
        for ngram, freq in self.ngram_fd.items():
            if fn(ngram, freq):
                try:
                    del self.ngram_fd[ngram]
                except KeyError:
                    pass

    def apply_freq_filter(self, min_freq):
        """Removes candidate ngrams which have frequency less than min_freq."""
        self._apply_filter(lambda ng, freq: freq < min_freq)

    def apply_ngram_filter(self, fn):
        """Removes candidate ngrams (w1, w2, ...) where fn(w1, w2, ...)
        evaluates to True.
        """
        self._apply_filter(lambda ng, f: fn(*ng))

    def apply_word_filter(self, fn):
        """Removes candidate ngrams (w1, w2, ...) where any of (fn(w1), fn(w2),
        ...) evaluates to True.
        """
        self._apply_filter(lambda ng, f: any(fn(w) for w in ng))
 
    def _score_ngrams(self, score_fn):
        """Generates of (ngram, score) pairs as determined by the scoring
        function provided.
        """
        for tup in self.ngram_fd:
            score = self.score_ngram(*((score_fn,) + tup))
            if score is not None:
                yield tup, score

    def score_ngrams(self, score_fn):
        """Returns a sequence of (ngram, score) pairs ordered from highest to
        lowest score, as determined by the scoring function provided.
        """
        return sorted(self._score_ngrams(score_fn),
                      key=_itemgetter(1), reverse=True)

    def top_n(self, score_fn, n):
        """Returns the top n ngrams when scored by the given function."""
        return [p for p,s in self.score_ngrams(score_fn)[:n]]

    def above_score(self, score_fn, min_score):
        """Returns a sequence of ngrams, ordered by decreasing score, whose
        scores each exceed the given minimum score.
        """
        for ngram, score in self.score_ngrams(score_fn):
            if score > min_score:
                yield ngram
            else:
                break


class BigramCollocationFinder(AbstractCollocationFinder):
    """A tool for the finding and ranking of bigram collocations or other
    association measures. It is often useful to use from_words() rather than
    constructing an instance directly.
    """

    @classmethod
    def from_words(cls, words):
        """Construct a BigramCollocationFinder for all bigrams in the given
        sequence.
        """
        wfd = _FreqDist()
        bfd = _FreqDist()

        words = _itertools.chain(words, (None,))
        for w1, w2 in _ingrams(words, 2):
            wfd.inc(w1)
            if w2 is not None:
                bfd.inc((w1, w2))
        return cls(wfd, bfd)

    def score_ngram(self, score_fn, w1, w2):
        """Returns the score for a given bigram using the given scoring
        function.
        """
        n_all = self.word_fd.N()
        n_ii = self.ngram_fd[(w1, w2)]
        if not n_ii:
            return
        n_ix = self.word_fd[w1]
        n_xi = self.word_fd[w2]
        return score_fn(n_ii, (n_ix, n_xi), n_all)


class TrigramCollocationFinder(AbstractCollocationFinder):
    """A tool for the finding and ranking of bigram collocations or other
    association measures. It is often useful to use from_words() rather than
    constructing an instance directly.
    """

    def __init__(self, word_fd, bigram_fd, wildcard_fd, trigram_fd):
        """Construct a TrigramCollocationFinder, given FreqDists for
        appearances of words, bigrams, two words with any word between them,
        and trigrams.
        """
        AbstractCollocationFinder.__init__(self, word_fd, trigram_fd)
        self.wildcard_fd = wildcard_fd
        self.bigram_fd = bigram_fd

    @classmethod
    def from_words(cls, words):
        """Construct a TrigramCollocationFinder for all trigrams in the given
        sequence.
        """
        wfd = _FreqDist()
        wildfd = _FreqDist()
        bfd = _FreqDist()
        tfd = _FreqDist()

        words = _itertools.chain(words, (None,None,))
        for w1, w2, w3 in _ingrams(words, 3):
            wfd.inc(w1)
            if w2 is None:
                continue
            bfd.inc((w1, w2))
            if w3 is None:
                continue
            wildfd.inc((w1, w3))
            tfd.inc((w1, w2, w3))
        return cls(wfd, bfd, wildfd, tfd)

    def score_ngram(self, score_fn, w1, w2, w3):
        """Returns the score for a given trigram using the given scoring
        function.
        """
        n_all = self.word_fd.N()
        n_iii = self.ngram_fd[(w1, w2, w3)]
        if not n_iii:
            return
        n_iix = self.bigram_fd[(w1, w2)]
        n_ixi = self.wildcard_fd[(w1, w3)]
        n_xii = self.bigram_fd[(w2, w3)]
        n_ixx = self.word_fd[w1]
        n_xix = self.word_fd[w2]
        n_xxi = self.word_fd[w3]
        return score_fn(n_iii,
                        (n_iix, n_ixi, n_xii),
                        (n_ixx, n_xix, n_xxi),
                        n_all)


def demo(scorer=None):
    """Finds bigram collocations in the files of the WebText corpus given a
    bigram scorer (defaults to mi_like).
    """

    if scorer is None:
        import measures
        scorer = measures.BigramAssocMeasures().mi_like

    from nltk import corpus
        
    ignored_words = corpus.stopwords.words('english')
    word_filter = lambda w: len(w) < 3 or w.lower() in ignored_words

    for file in corpus.webtext.files():
        words = [word.lower()
                 for word in corpus.webtext.words(file)]

        cf = BigramCollocationFinder.from_words(words)
        cf.apply_freq_filter(3)
        cf.apply_word_filter(word_filter)

        print file, [' '.join(tup)
                for tup in cf.top_n(scorer, 15)]


if __name__ == '__main__':
    import sys
    import measures
    try:
        scorer = eval('measures.BigramAssocMeasures().' + sys.argv[1])
    except IndexError:
        scorer = None
    demo(scorer)
