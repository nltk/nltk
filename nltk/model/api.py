# Natural Language Toolkit: Language Model
#
# Copyright (C) 2001-2015 NLTK Project
# Author: Tah Wei Hoon <hoon.tw@gmail.com>
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT


class LanguageModel(object):
    """
    Abstract class for language model

    A language model gives the probability of occurrence for a
    sequence of words
    """
    def probability(self, words):
        """
        Log probability of occurrence for a sequence of words

        :param words: Sequence of words. For example,
            ``['ham', 'and', 'spam']``.
        :type words: iterable(str)

        :return: Log probability of ``words``
        :rtype: float
        """
        raise NotImplementedError()

    def probability_change(self, sentence, additional_words):
        """
        Log probability change for appending ``additional_words``
        to ``sentence``

        Neither ``sentence`` nor ``additional_words`` is modified.

        This method can be used in NLP tasks that attempt to generate
        sentences, for example, in translation, speech recognition,
        and summarization.

        The base implementation is simply ``probability(sentence +
        additional_words) - probability(sentence)``. Derived classes
        should override this method if there is a more efficient way
        to compute the change in probability.

        :param sentence: Sequence of words. For example,
            ``['ham', 'and', 'spam']``.
        :type sentence: iterable(str)

        :param additional_words: Proposed sequence of words to append
            to the end of ``sentence``. For example,
            ``['but', 'not', 'eggs']``.
        :type additional_words: iterable(str)

        :return: Change in log probability
        :rtype: float
        """
        new_sentence = list(sentence).extend(additional_words)
        return self.probability(new_sentence) - self.probability(sentence)
