# Natural Language Toolkit: Language Models
#
# Copyright (C) 2001-2017 NLTK Project
# Authors: Ilia Kurenkov <ilia.kurenkov@gmail.com>
# URL: <http://nltk.org/
# For license information, see LICENSE.TXT
"""NLTK Language Modeling Module.

Training
========

Here is an example of very basic usage where the vocabulary is created directly from
data used for collecting counts.
We start by defining some simple data.

    >>> sents = [list("abc"), list("acdcef")]

Then we import and instantiate a language model.
We only need to specify the highest ngram order for it.

    >>> from nltk.model import MleLanguageModel
    >>> lm = MleLanguageModel(2)

This automatically creates an empty vocabulary for the model.

    >>> len(lm.vocab)
    0

This vocabulary will get filled in as part of fitting the model to data.
Even though it is done behind the scenes, it is always done *before* the
actual counts are collected.

    >>> lm.fit(sents)

The `fit` method does several things:
- If the vocabulary is empty, updates it from the training data.
- Preprocesses the text to turn it into ngrams with OOV words masked.
- Counts these ngrams.

For convenience you can use the `preprocess` method to inspect what is fed
to the counter part of the model.

    >>> list(lm.preprocess(["a", "b", "r"])) # doctest: +NORMALIZE_WHITESPACE
    [('<s>',), ('a',), ('b',), ('<UNK>',), ('</s>',),
    ('<s>', 'a'), ('a', 'b'), ('b', '<UNK>'), ('<UNK>', '</s>')]

As you can see, by default we pad the sequence out and use `nltk.util.everygrams` to generate
all ngrams up to the highest order.
These two behaviors can be changed by specifying the `pad_fn` and `ngrams_fn` to the model constructor.

    >>> no_padding = MleLanguageModel(2, pad_fn=lambda sent: sent)
    >>> no_padding.fit(sents)
    >>> list(no_padding.preprocess(["a", "b", "r"]))
    [('a',), ('b',), ('<UNK>',), ('a', 'b'), ('b', '<UNK>')]

    >>> from nltk.util import bigrams
    >>> only_bigrams = MleLanguageModel(2, ngrams_fn=bigrams)
    >>> only_bigrams.fit(sents)
    >>> list(only_bigrams.preprocess(["a", "b", "r"]))
    [('<s>', 'a'), ('a', 'b'), ('b', '<UNK>'), ('<UNK>', '</s>')]

What cannot be disabled in the preprocessing is replacing out-of-vocabulary (OOV) words
with the `vocab.unk_label` symbol.
This is an integral part of training a language model, so it's baked in.
See the `nltk.model.vocabulary` module for more details about how vocabularies work.

Using a Trained Model
=====================

The `fit` method populated our vocabulary added some ngram counts to our model.
These also include the padding symbols and the symbol for "unknown" words.

    >>> print(lm.vocab)
    <NgramModelVocabulary with cutoff 1, unk_label '<UNK>' and 9 items>
    >>> print(lm.counts)
    <NgramCounter with 2 ngram orders and 24 ngrams>

Note that subsequent calls to `fit` *will not* update the vocabulary!
The counts are accumulated in instances of `nltk.FreqDist`. Here's how you can access them.

    >>> lm.counts.unigrams['a']
    2
    >>> lm.counts.unigrams.N()
    13

This being MLE, the model returns the relative frequency of an item as its score.

    >>> lm.score("a")
    0.15384615384615385
    >>> lm.logscore("a")
    -2.700439718141092

Items that are not seen during training are mapped to the vocabulary's "unknown label" token.
This is "<UNK>" by default.

    >>> lm.vocab.lookup("aliens")
    '<UNK>'

Thus out-of-vocabulary (OOV) words get the same score as the unknown token.
In this case it is 0 because we built the vocabulary from the training data
and the cutoff was set such that anything that was seen at least once is considered
part of the vocabulary and as a result we never counted anything as "<UNK>" during training.

    >>> lm.score("<UNK>")
    0.0
    >>> lm.score("aliens")
    0.0

Here's how you can access counts for bigrams etc.

    >>> print(lm.counts[["a"]])
    <FreqDist with 2 samples and 2 outcomes>

    >>> lm.counts[["a"]]["b"]
    1
    >>> lm.counts[["a"]].N()
    2

Here's how you get the score for a word given some preceding context.
For example we want to know what is the chance that "b" is preceded by "a".

    >>> lm.score("b", ["a"])
    0.5

In addition to scores for individual bigrams we can also evaluate our model's
cross-entropy and perplexity with respect to sequences of ngrams.

    >>> test = [('a', 'b'), ('c', 'd')]
    >>> lm.entropy(test)
    1.0283208335737188
    >>> lm.perplexity(test)
    2.0396489026555056

We can also generate text, using `generate` and `generate_one` methods!

"""

from nltk.model.models import (MleLanguageModel, LidstoneNgramModel, LaplaceNgramModel)
from nltk.model.counter import NgramCounter
from nltk.model.vocabulary import NgramModelVocabulary
