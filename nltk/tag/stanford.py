# -*- coding: utf-8 -*-
# Natural Language Toolkit: Interface to the Stanford POS-tagger
#
# Copyright (C) 2001-2011 NLTK Project
# Author: Nitin Madnani <nmadnani@ets.org>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT
#
# $Id: stanford.py $

"""
A module for interfacing with the Stanford POS-tagger.
"""

import os
from subprocess import PIPE
import tempfile
import nltk
from api import *

_stanford_url = 'http://nlp.stanford.edu/software/tagger.shtml'

class StanfordTagger(TaggerI):
    """
    A class for pos tagging with Stanford Tagger. The input is the paths to:
     - a model trained on training data
     - (optionally) the path to the stanford tagger jar file. If not specified here,
       then this jar file must be specified in the CLASSPATH envinroment variable.
     - (optionally) the encoding of the training data (default: ASCII)

    Example:

        >>> st = StanfordTagger('bidirectional-distsim-wsj-0-18.tagger')
        >>> st.tag('What is the airspeed of an unladen swallow ?'.split())
        [('What', 'WP'), ('is', 'VBZ'), ('the', 'DT'), ('airspeed', 'NN'),
        ('of', 'IN'), ('an', 'DT'), ('unladen', 'JJ'), ('swallow', 'VB'), ('?', '.')]
    """
    def __init__(self, path_to_model, path_to_jar=None, encoding=None, verbose=False):

        self._stanford_jar = nltk.internals.find_jar(
                'stanford-postagger.jar', path_to_jar,
                searchpath=(), url=_stanford_url,
                verbose=verbose)

        if not os.path.isfile(path_to_model):
            raise IOError("Stanford tagger model file not found: %s" % path_to_model)
        self._stanford_model = path_to_model
        self._encoding = encoding

    def tag(self, tokens):
        return self.batch_tag([tokens])[0]

    def batch_tag(self, sentences):
        encoding = self._encoding
        nltk.internals.config_java(options='-mx1000m', verbose=False)

        # Create a temporary input file
        _input_fh, _input_file_path = tempfile.mkstemp(text=True)

        # Build the java command to run the tagger
        _stanpos_cmd = ['edu.stanford.nlp.tagger.maxent.MaxentTagger', \
                        '-model', self._stanford_model, '-textFile', \
                        _input_file_path, '-tokenize', 'false']
        if encoding:
            _stanpos_cmd.extend(['-encoding', encoding])

        # Write the actual sentences to the temporary input file
        _input_fh = os.fdopen(_input_fh, 'w')
        _input = '\n'.join((' '.join(x) for x in sentences))
        if isinstance(_input, unicode) and encoding:
            _input = _input.encode(encoding)
        _input_fh.write(_input)
        _input_fh.close()

        # Run the tagger and get the output
        stanpos_output, _stderr = nltk.internals.java(_stanpos_cmd,classpath=self._stanford_jar, \
                                                       stdout=PIPE, stderr=PIPE)
        if encoding:
            stanpos_output = stanpos_output.decode(encoding)

        # Delete the temporary file
        os.unlink(_input_file_path)

        # Output the tagged sentences
        tagged_sentences = []
        for tagged_sentence in stanpos_output.strip().split("\n"):
            sentence = [tuple(tagged_word.strip().split("_"))
                        for tagged_word in tagged_sentence.strip().split()]
            tagged_sentences.append(sentence)
        return tagged_sentences

