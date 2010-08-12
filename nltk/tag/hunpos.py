# -*- coding: utf-8 -*-
# Natural Language Toolkit: Interface to the HunPos POS-tagger
#
# Copyright (C) 2001-2010 NLTK Project
# Author: Peter Ljunglöf <peter.ljunglof@heatherleaf.se>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT
#
# $Id: hunpos.py $

"""
A module for interfacing with the HunPos open-source POS-tagger.
"""

import os
from subprocess import Popen, PIPE
import nltk
from api import *

_hunpos_url = 'http://code.google.com/p/hunpos/'

class HunposTagger(TaggerI):
    """
    A class for pos tagging with HunPos. The input is the paths to:
     - a model trained on training data
     - (optionally) the path to the hunpos-tag binary
     - (optionally) the encoding of the training data (default: ASCII)

    Example:

        >>> ht = HunposTagger('english.model')
        >>> ht.tag('What is the airspeed of an unladen swallow ?'.split())
        [('What', 'WP'), ('is', 'VBZ'), ('the', 'DT'), ('airspeed', 'NN'),
         ('of', 'IN'), ('an', 'DT'), ('unladen', 'NN'), ('swallow', 'VB'), ('?', '.')]
    """
    def __init__(self, path_to_model, path_to_bin=None, encoding=None, verbose=False):
        hunpos_paths = ['.', '/usr/bin', '/usr/local/bin', '/opt/local/bin',
                        '/Applications/bin', '~/bin', '~/Applications/bin']
        hunpos_paths = map(os.path.expanduser, hunpos_paths)

        self._hunpos_bin = nltk.internals.find_binary(
                'hunpos-tag', path_to_bin, 
                env_vars=('HUNPOS', 'HUNPOS_HOME'),
                searchpath=hunpos_paths, 
                url=_hunpos_url, 
                verbose=verbose)

        if not os.path.isfile(path_to_model):
            raise IOError("Hunpos model file not found: %s" % path_to_model)
        self._hunpos_model = path_to_model
        self._encoding = encoding

    def tag(self, tokens):
        return self.batch_tag([tokens])[0]

    def batch_tag(self, sentences):
        encoding = self._encoding
        hunpos = Popen([self._hunpos_bin, self._hunpos_model],
                       shell=False, stdin=PIPE, stdout=PIPE, stderr=PIPE)

        hunpos_input = "\n\n".join("\n".join(sentence) for sentence in sentences)
        if encoding:
            hunpos_input = hunpos_input.encode(encoding)
        hunpos_output, _stderr = hunpos.communicate(hunpos_input)
        if encoding:
            hunpos_output = hunpos_output.decode(encoding)

        tagged_sentences = []
        for tagged_sentence in hunpos_output.strip().split("\n\n"):
            sentence = [tuple(tagged_word.strip().split("\t"))
                        for tagged_word in tagged_sentence.strip().split("\n")]
            tagged_sentences.append(sentence)
        return tagged_sentences

