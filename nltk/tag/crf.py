# Natural Language Toolkit: Interface to the CRFSuite Tagger
#
# Copyright (C) 2001-2026 NLTK Project
# Author: Long Duong <longdt219@gmail.com>
#         John Winstead <https://github.com/jhnwnstd> (fixes)
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
A module for POS tagging using CRFSuite
"""

import re
import unicodedata
import warnings

from nltk.tag.api import TaggerI

try:
    import pycrfsuite
except ImportError:
    pycrfsuite = None

# Punctuation categories from the Unicode general-category table.
# Module-level so the per-token feature loop doesn't rebuild it.
_PUNC_CATEGORIES = frozenset({"Pc", "Pd", "Ps", "Pe", "Pi", "Pf", "Po"})


class CRFTagger(TaggerI):
    """
    A module for POS tagging using CRFSuite https://pypi.python.org/pypi/python-crfsuite

    >>> from nltk.tag import CRFTagger
    >>> ct = CRFTagger()  # doctest: +SKIP

    >>> train_data = [
    ...     [('University','Noun'), ('is','Verb'), ('a','Det'),
    ...      ('good','Adj'), ('place','Noun')],
    ...     [('dog','Noun'), ('eat','Verb'), ('meat','Noun')],
    ... ]

    >>> ct.train(train_data, 'model.crf.tagger')  # doctest: +SKIP
    >>> ct.tag_sents([['dog','is','good'], ['Cat','eat','meat']])  # doctest: +SKIP
    [[('dog', 'Noun'), ('is', 'Verb'), ('good', 'Adj')],
     [('Cat', 'Noun'), ('eat', 'Verb'), ('meat', 'Noun')]]

    >>> gold_sentences = [
    ...     [('dog','Noun'), ('is','Verb'), ('good','Adj')],
    ...     [('Cat','Noun'), ('eat','Verb'), ('meat','Noun')],
    ... ]
    >>> ct.accuracy(gold_sentences)  # doctest: +SKIP
    1.0

    Setting learned model file
    >>> ct = CRFTagger()  # doctest: +SKIP
    >>> ct.set_model_file('model.crf.tagger')  # doctest: +SKIP
    >>> ct.accuracy(gold_sentences)  # doctest: +SKIP
    1.0

    Default features are cached by token surface form. Call
    ``clear_feature_cache()`` to drop the cache (e.g. between long-running
    open-vocabulary tagging passes). A custom ``feature_func`` bypasses
    the cache.
    """

    def __init__(self, feature_func=None, verbose=False, training_opt=None):
        """
        Initialize the CRFSuite tagger

        :param feature_func: Function that extracts features for each token
            of a sentence. Takes two parameters (``tokens``, ``idx``) and
            returns the feature list for ``tokens[idx]``. See the built-in
            ``_get_features`` for an example.
        :param verbose: Emit debugging messages during training.
        :type verbose: bool
        :param training_opt: python-crfsuite training options.
        :type training_opt: dict

        Set of possible training options (using LBFGS training algorithm).
            :'feature.minfreq': Minimum frequency of features.
            :'feature.possible_states': Force generating possible state features.
            :'feature.possible_transitions': Force generating possible transition
                features.
            :'c1': Coefficient for L1 regularization.
            :'c2': Coefficient for L2 regularization.
            :'max_iterations': Maximum number of iterations for L-BFGS.
            :'num_memories': Number of limited memories for approximating the
                inverse Hessian matrix.
            :'epsilon': Epsilon for testing the convergence of the objective.
            :'period': Duration of iterations for the stopping criterion.
            :'delta': Threshold for the stopping criterion; L-BFGS stops when
                the log-likelihood improvement over the last ${period}
                iterations is no greater than this threshold.
            :'linesearch': Line search algorithm used in L-BFGS updates:

                - 'MoreThuente': More and Thuente's method,
                - 'Backtracking': Backtracking method with regular Wolfe condition,
                - 'StrongBacktracking': Backtracking method with strong Wolfe condition
            :'max_linesearch':  Maximum number of trials for the line search.
        """

        if pycrfsuite is None:
            raise ImportError("CRFTagger requires python-crfsuite to be installed.")

        self._model_file = ""
        self._tagger = pycrfsuite.Tagger()

        if feature_func is None:
            self._feature_func = self._get_features
        else:
            self._feature_func = feature_func

        self._verbose = verbose
        # Avoid mutable default; copy so caller mutations don't leak in.
        self._training_options = {} if training_opt is None else dict(training_opt)
        self._pattern = re.compile(r"\d")
        # Avoid the module-level ``re.search`` dispatch in the feature loop.
        self._pattern_search = self._pattern.search
        # Token-keyed cache; default features are token-local. A custom
        # ``feature_func`` replaces ``_get_features`` and skips this dict.
        self._feature_cache = {}

    def set_model_file(self, model_file):
        self._model_file = model_file
        self._tagger.open(self._model_file)

    def _get_features(self, tokens, idx):
        """
        Extract basic features about this word including
            - Current word
            - is it capitalized?
            - Does it have punctuation?
            - Does it have a number?
            - Suffixes up to length 3

        Note that : we might include features over previous word, next word etc.

        :return: a list which contains the features
        :rtype: list(str)
        """
        token = tokens[idx]

        # Return a fresh list so callers can't mutate the cached tuple.
        cached = self._feature_cache.get(token)
        if cached is not None:
            return list(cached)

        feature_list = []

        if not token:
            self._feature_cache[token] = ()
            return feature_list

        append = feature_list.append
        token_len = len(token)

        if token[0].isupper():
            append("CAPITALIZATION")

        if self._pattern_search(token) is not None:
            append("HAS_NUM")

        category = unicodedata.category
        if all(category(ch) in _PUNC_CATEGORIES for ch in token):
            append("PUNCTUATION")

        if token_len > 1:
            append("SUF_" + token[-1:])
        if token_len > 2:
            append("SUF_" + token[-2:])
        if token_len > 3:
            append("SUF_" + token[-3:])

        append("WORD_" + token)

        self._feature_cache[token] = tuple(feature_list)
        return feature_list

    def clear_feature_cache(self):
        """Drop the default-feature cache.

        The cache is vocabulary-bounded, but long-running processes that
        ingest open-vocabulary streams (URLs, tweets, generated text) may
        want to reset it explicitly. A custom ``feature_func`` bypasses
        the cache, so this is a no-op for non-default extractors.
        """
        self._feature_cache.clear()

    def tag_sents(self, sentences=None, **kwargs):
        """
        Tag a list of sentences. Before using this function, the model file
        must be specified by either:

        - Train a new model using ``train`` function
        - Use the pre-trained model which is set via ``set_model_file`` function

        :param sentences: sentences to tag.
        :type sentences: list(list(str))
        :param sents: deprecated alias for ``sentences``; emits ``DeprecationWarning``.
        :return: list of tagged sentences.
        :rtype: list(list(tuple(str,str)))
        """
        if "sents" in kwargs:
            if sentences is not None:
                raise TypeError(
                    "tag_sents() got both 'sentences' and 'sents'; "
                    "use 'sentences' only ('sents' is deprecated)."
                )
            warnings.warn(
                "tag_sents(sents=...) is deprecated; use tag_sents(sentences=...).",
                DeprecationWarning,
                stacklevel=2,
            )
            sentences = kwargs.pop("sents")
        if kwargs:
            unexpected = ", ".join(sorted(kwargs))
            raise TypeError(
                f"tag_sents() got unexpected keyword arguments: {unexpected}"
            )
        if sentences is None:
            raise TypeError("tag_sents() missing 1 required argument: 'sentences'")

        if isinstance(sentences, (str, bytes)):
            raise TypeError(
                "tag_sents() expects a list of tokenized sentences, "
                "not a single string or bytes object."
            )

        # Catch ``[token, token, ...]`` (one tokenized sentence) before the
        # model-file check so the error is clear even on an untrained tagger.
        # Generators fall through to the per-iteration check below.
        if (
            isinstance(sentences, (list, tuple))
            and sentences
            and isinstance(sentences[0], (str, bytes))
        ):
            raise TypeError(
                "tag_sents() expects a list of tokenized sentences, "
                "not a single tokenized sentence."
            )

        if self._model_file == "":
            raise RuntimeError(
                "No model file set; call train() or set_model_file() first."
            )

        # Hoist hot-loop attribute lookups out of the per-sentence loop.
        feature_func = self._feature_func
        tag = self._tagger.tag

        result = []
        for tokens in sentences:
            if isinstance(tokens, (str, bytes)):
                # Safety net for generator inputs the up-front check skipped.
                raise TypeError(
                    "tag_sents() expects a list of tokenized sentences, "
                    "not a single tokenized sentence."
                )
            features = [feature_func(tokens, i) for i in range(len(tokens))]
            labels = tag(features)

            if len(labels) != len(tokens):
                raise RuntimeError(
                    f"CRF returned {len(labels)} labels for {len(tokens)} tokens."
                )

            tagged_sent = list(zip(tokens, labels, strict=True))
            result.append(tagged_sent)

        return result

    def train(self, train_data, model_file):
        """
        Train the CRF tagger using CRFSuite

        :param train_data: list of annotated sentences.
        :type train_data: list(list(tuple(str,str)))
        :param model_file: path where the trained model will be written.
        :type model_file: str
        """
        if pycrfsuite is None:
            raise ImportError("CRFTagger requires python-crfsuite to be installed.")

        trainer = pycrfsuite.Trainer(verbose=self._verbose)
        trainer.set_params(self._training_options)

        feature_func = self._feature_func
        append = trainer.append

        for sent in train_data:
            tokens, labels = zip(*sent, strict=True)
            features = [feature_func(tokens, i) for i in range(len(tokens))]
            append(features, labels)

        trainer.train(model_file)
        self.set_model_file(model_file)

    def tag(self, tokens):
        """
        Tag a sentence using the python-crfsuite tagger. Before using this
        function, the model file must be specified by either:

        - Train a new model using ``train`` function
        - Use the pre-trained model which is set via ``set_model_file`` function

        :param tokens: tokens to tag.
        :type tokens: list(str)
        :return: list of tagged tokens.
        :rtype: list(tuple(str,str))
        """
        if isinstance(tokens, (str, bytes)):
            raise TypeError(
                "tag() expects a list of tokens, not a single string or bytes. "
                "Tokenize first (e.g. tokens.split() or word_tokenize(s))."
            )
        return self.tag_sents([tokens])[0]
