# Natural Language Toolkit: Collocation Finders
#
# Copyright (C) 2001-2008 NLTK Project
# Author: Joel Nothman <jnothman@student.usyd.edu.au>
# URL: <http://nltk.org>
# For license information, see LICENSE.TXT
#
"""
TODO: write comment
"""

import itertools as _itertools
from operator import itemgetter as _itemgetter

from nltk import FreqDist as _FreqDist


class AbstractCollocationFinder(object):
    def __init__(self, word_fd, ngram_fd):
        self.word_fd = word_fd
        self.ngram_fd = ngram_fd

    @classmethod
    def from_documents(cls, documents):
        return cls.from_words(_itertools.chain(*documents))

    @staticmethod
    def _ngram_freqdist(words, n):
        return _FreqDist(tuple(words[i:i+n]) for i in range(len(words)-1))

    def _apply_filter(self, fn=lambda ngram, freq: False):
        for ngram, freq in self.ngram_fd.items():
            if fn(ngram, freq):
                try:
                    del self.ngram_fd[ngram]
                except KeyError:
                    pass

    def apply_freq_filter(self, min_freq):
        self._apply_filter(lambda ng, freq: freq < min_freq)

    def apply_ngram_filter(self, fn):
        self._apply_filter(lambda ng, f: fn(*ng))

    def apply_word_filter(self, fn):
        self._apply_filter(lambda ngram, f: [True for w in ngram if fn(w)])
 
    def score_ngrams(self, score_fn):
        n_words = self.word_fd.N()
        data = ((tup, self.score_ngram(*((score_fn,) + tup), **{'n_all':n_words}))
                for tup in self.ngram_fd)
        return sorted(data,
                      key=_itemgetter(1), reverse=True)

    def top_n(self, score_fn, n):
        return [p for p,s in self.score_ngrams(score_fn)[:n]]

    def above_score(self, score_fn, min_score):
        for ngram, score in self.score_ngrams(score_fn):
            if score > min_score:
                yield ngram
            else:
                break


class BigramCollocationFinder(AbstractCollocationFinder):
    @classmethod
    def from_words(cls, words):
        wfd = _FreqDist()
        bfd = _FreqDist()

        it1, it2 = _itertools.tee(words, 2)
        wfd.inc(it2.next())
        for w1, w2 in _itertools.izip(it1, it2):
            wfd.inc(w2)
            bfd.inc((w1, w2))
        return cls(wfd, bfd)
    
    @classmethod
    def for_document_cooccurrence(cls, documents, boolean=True):
        if boolean:
            documents = [list(set(d)) for d in documents]

        word_fd = _FreqDist(w for d in documents for w in d)
        pair_fd = _FreqDist((w1,w2) for d in documents
                           for w1 in d for w2 in d
                           if w1 < w2)
        return cls(word_fd, pair_fd)

    def score_ngram(self, score_fn, w1, w2, n_all=None):
        if n_all is None:
            n_all = self.word_fd.N()
        n_ii = self.ngram_fd[(w1, w2)]
        n_ix = self.word_fd[w1]
        n_xi = self.word_fd[w2]
        return score_fn(n_ii, n_ix, n_xi, n_all)


class TrigramCollocationFinder(AbstractCollocationFinder):
    def __init__(self, word_fd, bigram_fd, wildcard_fd, trigram_fd):
        AbstractCollocationFinder.__init__(self, word_fd, trigram_fd)
        self.wildcard_fd = wildcard_fd
        self.bigram_fd = bigram_fd

    @classmethod
    def from_words(cls, words):
        wfd = _FreqDist()
        wildfd = _FreqDist()
        bfd = _FreqDist()
        tfd = _FreqDist()

        it1, it2, it3 = _itertools.tee(words, 3)

        wfd.inc(it3.next())
        w = it3.next()
        wfd.inc(w)
        bfd.inc((it2.next(), w))

        for w1, w2, w3 in _itertools.izip(it1, it2, it3):
            wfd.inc(w3)
            bfd.inc((w2, w3))
            wildfd.inc((w1, w3))
            tfd.inc((w1, w2, w3))
        return cls(wfd, bfd, wildfd, tfd)

    def score_ngram(score_fn, w1, w2, w3, n_all=None):
        if n_all is None:
            n_all = self.word_fd.N()

        n_iii = self.ngram_fd[(w1, w2, w3)]
        n_iix = self.bigram_fd[(w1, w2)]
        n_ixi = self.wildcard_fd[(w1, w3)]
        n_xii = self.bigram_fd[(w2, w3)]
        n_ixx = self.word_fd[w1]
        n_xix = self.word_fd[w2]
        n_xxi = self.word_fd[w3]
        return score_fn(n_iii,
                        n_ixx, n_xix, n_xxi,
                        n_iix, n_ixi, n_xii,
                        n_all)


if __name__ == '__main__':
    import sys
    import bigram_measures
    try:
        scorer = eval('bigram_measures.' + sys.argv[1])
    except IndexError:
        scorer = bigram_measures.mi_like
    def contingency(self, n_ii, n_ix, n_xi, n_xx):
        n_io = n_ix - n_ii
        n_oi = n_xi - n_ii
        return (n_ii, n_io, n_oi, n_xx - n_ii - n_io - n_oi)

    from nltk import corpus
        
    ignored_words = corpus.stopwords.words('english')
    word_filter = lambda w: len(w) < 3 or w.lower() in ignored_words

    for file in corpus.webtext.files():
        words = [word.lower()
                 for word in corpus.webtext.words(file)]

        cf = BigramCollocationFinder.from_words(words)
        cf.apply_freq_filter(3)
        cf.apply_word_filter(word_filter)

        print file, [w1+' '+w2
                for w1, w2 in cf.top_n(scorer, 15)]
 
