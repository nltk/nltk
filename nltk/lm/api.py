# Natural Language Toolkit: Language Models
#
# Copyright (C) 2001-2017 NLTK Project
# Authors: Ilia Kurenkov <ilia.kurenkov@gmail.com>
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT
"""Language Model Interface."""
from __future__ import unicode_literals, division

import random
from abc import ABCMeta, abstractmethod
from functools import partial
from itertools import chain

import numpy as np

from nltk.lm.counter import NgramCounter
from nltk.lm.util import log_base2
from nltk.lm.vocabulary import Vocabulary
from nltk.six import add_metaclass
from nltk.util import everygrams, pad_sequence


@add_metaclass(ABCMeta)
class LanguageModel(object):
    """ABC for Language Models.

    Cannot be directly instantiated itself.

    """

    def __init__(self, order, vocabulary=None, counter=None, ngrams_fn=None, pad_fn=None):
        """Creates new LanguageModel.

        :param vocabulary: If provided, this vocabulary will be used instead
        of creating a new one when training.
        :type vocabulary: `nltk.lm.Vocabulary` or None
        :param counter: If provided, use this object to count ngrams.
        :type vocabulary: `nltk.lm.NgramCounter` or None
        :param ngrams_fn: If given, defines how sentences in training text are turned to ngram
                          sequences.
        :type ngrams_fn: function or None
        :param pad_fn: If given, defines how senteces in training text are padded.
        :type pad_fn: function or None

        """
        self.order = order
        self.vocab = Vocabulary() if vocabulary is None else vocabulary
        self.counts = NgramCounter() if counter is None else counter
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
        self.counts.update(self.preprocess(sent) for sent in text)

    def preprocess(self, sent):
        """Preprocess a sentence for training.

        :param Iterable(str) sent: Sentence (sequence of words).
        :rtype: Iterable(tuple(str))

        """
        return self.ngrams(list(self.padder(self.vocab.lookup(sent))))

    def score(self, word, context=None):
        """Masks out of vocab (OOV) words and passes them to `self.unmasked_score`.

        For model-specific logic of calculating scores, see `unmasked_score` method.
        """
        return self.unmasked_score(
            self.vocab.lookup(word), tuple(self.vocab.lookup(context)) if context else None)

    @abstractmethod
    def unmasked_score(self, word, context=None):
        """Score a word given some optional context.

        :param str word: Word for which we want the score
        :param tuple(str) context: Context the word is in.
        If `None`, compute unigram score.
        :param context: tuple(str) or None
        :rtype: float

        """
        raise NotImplementedError()

    def logscore(self, word, context=None):
        """Evaluate the log score of this word in this context.

        The arguments are the same as for `score`.

        """
        return log_base2(self.score(word, context))

    def context_counts(self, context):
        """Helper method for retrieving counts for a given context.

        Assumes context has been checked and oov words in it masked.
        :type context: tuple(str) or None

        """
        return self.counts[len(context) + 1][context] if context else self.counts.unigrams

    def entropy(self, text_ngrams):
        """Calculate cross-entropy of model for given evaluation text.

        :param Iterable(tuple(str)) text_ngrams: A sequence of ngram tuples.
        :rtype: float

        """
        return -1 * np.mean([self.logscore(ngram[-1], ngram[:-1]) for ngram in text_ngrams])

    def perplexity(self, text_ngrams):
        """Calculates the perplexity of the given text.

        This is simply 2 ** cross-entropy for the text, so the arguments are the same.

        """

        return pow(2.0, self.entropy(text_ngrams))

    def generate_one(self, context=None):
        """Generate one word given some context.

        :param context: Same as for `context_counts` method.

        """
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
