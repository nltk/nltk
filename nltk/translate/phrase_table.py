# -*- coding: utf-8 -*-
# Natural Language Toolkit: Phrase table
#
# Copyright (C) 2001-2015 NLTK Project
# Author: Tah Wei Hoon <hoon.tw@gmail.com>
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

from collections import namedtuple

PhraseTableEntry = namedtuple('PhraseTableEntry', ['trg_phrase', 'log_prob'])


class PhraseTable(object):
    """
    In-memory store of translations for a given phrase, and the log
    probability of the those translations
    """
    def __init__(self):
        self.src_phrases = dict()

    def translations_for(self, src_phrase):
        """
        Get the translations for a source language phrase

        :param src_phrase: Source language phrase of interest
        :type src_phrase: tuple(str)

        :return: A list of target language phrases that are translations
            of ``src_phrase``, ordered in decreasing order of
            likelihood. Each list element is a tuple of the target
            phrase and its log probability.
        :rtype: list(PhraseTableEntry)
        """
        return self.src_phrases[src_phrase]

    def add(self, src_phrase, trg_phrase, log_prob):
        """
        :type src_phrase: tuple(str)
        :type trg_phrase: tuple(str)

        :param log_prob: Log probability that given ``src_phrase``,
            ``trg_phrase`` is its translation
        :type log_prob: float
        """
        entry = PhraseTableEntry(trg_phrase=trg_phrase, log_prob=log_prob)
        if src_phrase not in self.src_phrases:
            self.src_phrases[src_phrase] = []
        self.src_phrases[src_phrase].append(entry)
        self.src_phrases[src_phrase].sort(key=lambda e: e.log_prob,
                                          reverse=True)

    def __contains__(self, src_phrase):
        return src_phrase in self.src_phrases
