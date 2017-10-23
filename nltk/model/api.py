# Natural Language Toolkit: Language Models
#
# Copyright (C) 2001-2017 NLTK Project
# Authors: Ilia Kurenkov <ilia.kurenkov@gmail.com>
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT
"""Language Model Interface"""
from __future__ import unicode_literals, division
from functools import wraps, partial
import random
from abc import ABCMeta, abstractmethod
from itertools import chain

from nltk.six import add_metaclass
from nltk.util import everygrams, pad_sequence

from nltk import compat
from nltk.model.util import NEG_INF, padded_everygrams, log_base2
from nltk.model.counter import NgramCounter
from nltk.model.vocabulary import NgramModelVocabulary


def mask_oov_args(score_func):
    """Decorator that checks arguments for ngram model score methods."""

    @wraps(score_func)
    def checker(self, word, context=None):
        word_chk = self.vocab.lookup(word)

        context = tuple(map(self.vocab.lookup, context)) if context else None

        return score_func(self, word_chk, context)

    return checker


@add_metaclass(ABCMeta)
class LanguageModelI(object):
    """Interface for Language Models"""

    def __init__(self, order, vocabulary=None, ngrams_fn=None, pad_fn=None):
        """

        :param vocabulary:
        :type vocabulary: `nltk.model.NgramModelVocabulary` or None
        """
        self.order = order
        self.vocab = NgramModelVocabulary() if vocabulary is None else vocabulary
        self.counts = NgramCounter()
        self.ngrams = partial(everygrams, max_len=order) if ngrams_fn is None else ngrams_fn
        if pad_fn is None:
            self.padder = partial(
                pad_sequence,
                n=order,
                pad_left=True,
                pad_right=True,
                right_pad_symbol="</s>",
                left_pad_symbol="<s>")
        else:
            self.padder = pad_fn

    def fit(self, text):
        """Trains the model on a text.

        :param Iterable(Iterable(str)) text: Training text as a sequence of sentences.

        """
        if not self.vocab:
            self.vocab.update(chain.from_iterable(map(self.padder, text)))

        ngram_text = map(self.preprocess, text)
        self.counts.update(ngram_text)

    def preprocess(self, sent):
        return self.ngrams(list(self.vocab.lookup(self.padder(sent))))

    @abstractmethod
    def score(self, word, context=None):
        """Score a word given some optional context.

        :param str word: the word to get the probability of
        :param tuple(str) context: the context the word is in
        :rtype: float
        """
        raise NotImplementedError()

    def logscore(self, word, context=None):
        """Evaluate the log probability of this word in this context.

        This implementation actually works, child classes don't have to
        redefine it.

        :param word: the word to get the probability of
        :type word: str
        :param context: the context the word is in
        :type context: Tuple[str]
        """
        score = self.score(word, context)
        return log_base2(score)

    def context_counts(self, context_checked):
        """Helper method for retrieving counts for a given context.

        Assumes context has been checked and oov words in it masked.
        """
        if context_checked:
            order = len(context_checked) + 1
            return self.counts[order][context_checked]

        return self.counts.unigrams

    def entropy(self, text_ngrams):
        """Calculate cross-entropy of model for given evaluation text.

        This is the average log probability of each word in the text.

        :param text: words to use for evaluation
        :type text: Iterable[str]
        """

        H = 0.0  # entropy is conventionally denoted by "H"
        for ngram in text_ngrams:
            if len(ngram) == 1:
                context, word = None, ngram[0]
            else:
                context, word = ngram[:-1], ngram[-1]
            score = self.score(word, context)
            H -= score * log_base2(score)
        return H

    def perplexity(self, text_ngrams):
        """Calculates the perplexity of the given text.

        This is simply 2 ** cross-entropy for the text.

        :param text: words to calculate perplexity of
        :type text: Iterable[str]
        """

        return pow(2.0, self.entropy(text_ngrams))

    def generate_one(self, context=None):
        """Generate one word given some context."""
        samples = self.context_counts(context)
        if not samples:
            smaller_context = context[1:] if len(context) > 1 else None
            return self.generate_one(smaller_context)

        rand = random.random()
        scores = list(self.score(w, context) for w in samples)
        for word, score in zip(samples, scores):
            rand -= score
            if rand <= 0:
                return word

    def generate(self, num_words, seed=()):
        """Generate num_words with optional seed provided.

        This essentially wraps the generate_one method to produce sequences.
        """
        text = list(seed) if seed else [self.generate_one()]
        while len(text) < num_words:
            index = -self.order if len(text) >= self.order else len(text)
            relevant_context = tuple(text)[:index]
            next_word = self.generate_one(relevant_context)
            text.append(next_word)
        return text
