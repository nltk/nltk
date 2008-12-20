
import itertools
import math
from nltk import FreqDist
from operator import itemgetter

ln = lambda x: math.log(x, 2.0)

# Possible TODOs:
# - make scorer classes into functions; make contingency a global function;
# - separate arguments for candidates and use ngram_freq, etc. functions;
# - consider the distinction between f(x,_) and f(x) and whether our
#   approximation is good enough for fragmented data, and mention the approximation;
# - make a combined scorer class for bigrams and trigrams (?) with methods
#   score_bigram and score_trigram
# - add methods to compare different association measures' results
# - is it better to refer to things as bigrams/trigrams, or pairs/triples?



class AbstractCollocationFinder(object):
    def __init__(self, word_fd, ngram_fd):
        self.word_fd = word_fd
        self.ngram_fd = ngram_fd

    @classmethod
    def from_documents(cls, documents):
        return cls.from_words(itertools.chain(*documents))

    @staticmethod
    def _ngram_freqdist(words, n):
        return FreqDist(tuple(words[i:i+n]) for i in range(len(words)-1))

    def _apply_filter(self, fn=lambda ngram, freq: False):
        for ngram, freq in self.ngram_fd.items():
            if fn(ngram, freq):
                del self.ngram_fd[ngram]

    def apply_freq_filter(self, min_freq):
        self._apply_filter(lambda ng, freq: freq < min_freq)

    def apply_ngram_filter(self, fn):
        self._apply_filter(lambda ng, f: fn(*ng))

    def apply_word_filter(self, fn):
        self._apply_filter(lambda ngram, f: [True for w in ngram if fn(w)])
 
    def score_ngrams(self, score_fn):
        return sorted(self._score_ngrams(score_fn),
                      key=itemgetter(1), reverse=True)

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
        wfd = FreqDist()
        bfd = FreqDist()

        it1, it2 = itertools.tee(words, 2)
        wfd.inc(it2.next())
        for w1, w2 in itertools.izip(it1, it2):
            wfd.inc(w2)
            bfd.inc((w1, w2))
        return cls(wfd, bfd)
    
    @classmethod
    def for_document_cooccurrence(cls, documents, boolean=True):
        if boolean:
            documents = [list(set(d)) for d in documents]

        word_fd = FreqDist(w for d in documents for w in d)
        pair_fd = FreqDist((w1,w2) for d in documents
                           for w1 in d for w2 in d
                           if w1 < w2)
        return cls(word_fd, pair_fd)

    def _score_ngrams(self, score_fn):
        n_xx = self.word_fd.N()
        for w1, w2 in self.ngram_fd:
            n_ii = self.ngram_fd[(w1, w2)]
            n_ix = self.word_fd[w1]
            n_xi = self.word_fd[w2]
            yield ((w1,w2), score_fn(n_ii, n_ix, n_xi, n_xx))


class TrigramCollocationFinder(AbstractCollocationFinder):
    def __init__(self, word_fd, bigram_fd, trigram_fd):
        AbstractCollocationFinder.__init__(self, word_fd, trigram_fd)
        self.bigram_fd = bigram_fd

    @classmethod
    def from_words(cls, words):
        wfd = FreqDist()
        bfd = FreqDist()
        tfd = FreqDist()

        it1, it2, it3 = itertools.tee(words, 3)

        wfd.inc(it3.next())
        w = it3.next()
        wfd.inc(w)
        bfd.inc((it2.next(), w))

        for w1, w2, w3 in itertools.izip(it1, it2, it3):
            wfd.inc(w3)
            bfd.inc((w2, w3))
            tfd.inc((w1, w2, w3))
        return cls(wfd, bfd, tfd)

    def _score_ngrams(self, score_fn):
        n_xxx = self.word_fd.N()
        for w1, w2, w3 in self.ngram_fd:
            n_iii = self.ngram_fd[(w1, w2, w3)]
            n_iix = self.bigram_fd[(w1, w2)]
            n_ixi = self.xxxxxx_fd[(w1, w3)] # FIXME: need to create this!
            n_xii = self.bigram_fd[(w2, w3)]
            n_ixx = self.word_fd[w1]
            n_xix = self.word_fd[w2]
            n_xxi = self.word_fd[w3]
            yield ((w1, w2, w3),
                   score_fn(n_iii,
                            n_ixx, n_xix, n_xxi,
                            n_iix, n_ixi, n_xii,
                            n_xxx))


class BigramAssociationMeasureI(object):
    def __call__(self, n_ii, n_ix, n_xi, n_xx):
        raise AssertionError, "This is an interface"

    def contingency(self, n_ii, n_ix, n_xi, n_xx):
        n_io = n_ix - n_ii
        n_oi = n_xi - n_ii
        return (n_ii, n_io, n_oi, n_xx - n_ii - n_io - n_oi)


def raw_freq_assoc(self, n_ii, n_ix, n_xi, n_xx)
    return float(n_ii) / n_xx

class MILikeScorer(BigramAssociationMeasureI):
    def __init__(self, power=3):
        self.power = power

    def __call__(self, n_ii, n_ix, n_xi, n_xx):
        return n_ii ** self.power / float(n_ix * n_xi)


class PMIScorer(BigramAssociationMeasureI):
    def __call__(self, n_ii, n_ix, n_xi, n_xx):
        return ln(n_ii * n_xx) - ln(n_ix * n_xi)


class PhiSqScorer(BigramAssociationMeasureI):
    def __call__(self, n_ii, n_ix, n_xi, n_xx):
        n_ii, n_io, n_oi, n_oo = self.contingency(n_ii, n_ix, n_xi, n_xx)

        return (float((n_ii*n_oo - n_io*n_oi)*(n_ii*n_oo - n_io*n_oi)) /
                ((n_ii + n_io) * (n_ii + n_oi) * (n_io + n_oo) * (n_oi + n_oo)))


class ChiSqScorer(PhiSqScorer):
    def __call__(self, n_ii, n_ix, n_xi, n_xx):
        return n_xx * PhiSqScorer.__call__(self, n_ii, n_ix, n_xi, n_xx)


class DiceScorer(BigramAssociationMeasureI):
    def __call__(self, n_ii, n_ix, n_xi, n_xx):
        return 2 * float(n_ix) / (n_ix + n_xi)


class JaccardScorer(BigramAssociationMeasureI):
    def __call__(self, n_ii, n_ix, n_xi, n_xx):
        n_ii, n_io, n_oi, n_oo = self.contingency(n_ii, n_ix, n_xi, n_xx)
        return float(n_ii) / (n_ii + n_io + n_oi)  # = dice/(2*dice)
                   

if __name__ == '__main__':
    import sys
    try:
        scorer = eval(sys.argv[1])
    except:
        scorer = MILikeScorer()

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
 
