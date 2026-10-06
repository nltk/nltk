# Natural Language Toolkit
#
# Copyright (C) 2001-2026 NLTK Project
# Author: Ilia Kurenkov <ilia.kurenkov@gmail.com>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
"""
Language Model Counter
----------------------
"""

from collections import defaultdict
from collections.abc import Sequence

from nltk.probability import ConditionalFreqDist, FreqDist

#: Upper bound on the number of *distinct* ngrams a single ``NgramCounter`` may
#: store. The counter keeps every distinct ngram of every order in a nested
#: dictionary tree, so training a language model on an untrusted corpus of
#: distinct tokens grows memory without limit (~order * tokens) and OOM-kills the
#: worker (CWE-770; CVE-2026-12928). Once this many distinct ngrams have been
#: stored, ``update`` raises ``ValueError`` instead of growing unbounded. The
#: default is generous enough for NLTK's documented training corpora (e.g. Brown
#: at the usual orders); raise it if you train on a genuinely larger corpus.
MAX_NGRAMS = 10_000_000


class NgramCounter:
    """Class for counting ngrams.

    Will count any ngram sequence you give it ;)

    First we need to make sure we are feeding the counter sentences of ngrams.

    >>> text = [["a", "b", "c", "d"], ["a", "c", "d", "c"]]
    >>> from nltk.util import ngrams
    >>> text_bigrams = [ngrams(sent, 2) for sent in text]
    >>> text_unigrams = [ngrams(sent, 1) for sent in text]

    The counting itself is very simple.

    >>> from nltk.lm import NgramCounter
    >>> ngram_counts = NgramCounter(text_bigrams + text_unigrams)

    You can conveniently access ngram counts using standard python dictionary notation.
    String keys will give you unigram counts.

    >>> ngram_counts['a']
    2
    >>> ngram_counts['aliens']
    0

    If you want to access counts for higher order ngrams, use a list or a tuple.
    These are treated as "context" keys, so what you get is a frequency distribution
    over all continuations after the given context.

    >>> sorted(ngram_counts[['a']].items())
    [('b', 1), ('c', 1)]
    >>> sorted(ngram_counts[('a',)].items())
    [('b', 1), ('c', 1)]

    This is equivalent to specifying explicitly the order of the ngram (in this case
    2 for bigram) and indexing on the context.

    >>> ngram_counts[2][('a',)] is ngram_counts[['a']]
    True

    Note that the keys in `ConditionalFreqDist` cannot be lists, only tuples!
    It is generally advisable to use the less verbose and more flexible square
    bracket notation.

    To get the count of the full ngram "a b", do this:

    >>> ngram_counts[['a']]['b']
    1

    Specifying the ngram order as a number can be useful for accessing all ngrams
    in that order.

    >>> ngram_counts[2]
    <ConditionalFreqDist with 4 conditions>

    The keys of this `ConditionalFreqDist` are the contexts we discussed earlier.
    Unigrams can also be accessed with a human-friendly alias.

    >>> ngram_counts.unigrams is ngram_counts[1]
    True

    Similarly to `collections.Counter`, you can update counts after initialization.

    >>> ngram_counts['e']
    0
    >>> ngram_counts.update([ngrams(["d", "e", "f"], 1)])
    >>> ngram_counts['e']
    1

    """

    def __init__(self, ngram_text=None):
        """Creates a new NgramCounter.

        If `ngram_text` is specified, counts ngrams from it, otherwise waits for
        `update` method to be called explicitly.

        :param ngram_text: Optional text containing sentences of ngrams, as for `update` method.
        :type ngram_text: Iterable(Iterable(tuple(str))) or None

        """
        self._counts = defaultdict(ConditionalFreqDist)
        self._counts[1] = self.unigrams = FreqDist()
        #: Number of distinct ngrams stored, tracked for the ``MAX_NGRAMS`` guard.
        self._distinct = 0

        if ngram_text:
            self.update(ngram_text)

    def update(self, ngram_text):
        """Updates ngram counts from `ngram_text`.

        Expects `ngram_text` to be a sequence of sentences (sequences).
        Each sentence consists of ngrams as tuples of strings.

        :param Iterable(Iterable(tuple(str))) ngram_text: Text containing sentences of ngrams.
        :raises TypeError: if the ngrams are not tuples.

        """

        for sent in ngram_text:
            for ngram in sent:
                if not isinstance(ngram, tuple):
                    raise TypeError(
                        "Ngram <{}> isn't a tuple, " "but {}".format(ngram, type(ngram))
                    )

                ngram_order = len(ngram)
                if ngram_order == 1:
                    if ngram[0] not in self.unigrams:
                        self._note_new_ngram()
                    self.unigrams[ngram[0]] += 1
                    continue

                context, word = ngram[:-1], ngram[-1]
                # Probe with .get() so testing whether this (context, word) pair
                # is new does not eagerly create empty nested entries through the
                # defaultdicts; otherwise an ngram refused by the MAX_NGRAMS guard
                # would still leave new contexts/orders behind, defeating the
                # memory bound. The real entries are created only once the guard
                # below has passed.
                order_counts = self._counts.get(ngram_order)
                context_counts = (
                    order_counts.get(context) if order_counts is not None else None
                )
                if context_counts is None or word not in context_counts:
                    self._note_new_ngram()
                self[ngram_order][context][word] += 1

    def _note_new_ngram(self):
        """Account for one newly-stored distinct ngram and enforce the bound.

        The counter retains every distinct ngram, so without a bound an untrusted
        corpus of distinct tokens grows memory without limit and OOM-kills the
        worker (CWE-770; CVE-2026-12928). Refuse once ``MAX_NGRAMS`` distinct
        ngrams have been stored. The bound is checked *before* incrementing so a
        refused ngram (which is never stored) does not inflate the counter.
        """
        if self._distinct >= MAX_NGRAMS:
            raise ValueError(
                "Refusing to count further: NgramCounter exceeded the limit of "
                "%d distinct ngrams (CWE-770). Training on this corpus would grow "
                "memory without bound. Use a smaller corpus or order, or raise "
                "nltk.lm.counter.MAX_NGRAMS." % MAX_NGRAMS
            )
        self._distinct += 1

    def N(self):
        """Returns grand total number of ngrams stored.

        This includes ngrams from all orders, so some duplication is expected.
        :rtype: int

        >>> from nltk.lm import NgramCounter
        >>> counts = NgramCounter([[("a", "b"), ("c",), ("d", "e")]])
        >>> counts.N()
        3

        """
        return sum(val.N() for val in self._counts.values())

    def __getitem__(self, item):
        """User-friendly access to ngram counts."""
        if isinstance(item, int):
            return self._counts[item]
        elif isinstance(item, str):
            return self._counts.__getitem__(1)[item]
        elif isinstance(item, Sequence):
            return self._counts.__getitem__(len(item) + 1)[tuple(item)]

    def __str__(self):
        return "<{} with {} ngram orders and {} ngrams>".format(
            self.__class__.__name__, len(self._counts), self.N()
        )

    def __len__(self):
        return self._counts.__len__()

    def __contains__(self, item):
        return item in self._counts
