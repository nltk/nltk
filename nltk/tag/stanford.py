# -*- coding: utf-8 -*-
# Natural Language Toolkit: Interface to the Stanford NER-tagger
#
# Copyright (C) 2001-2012 NLTK Project
# Author: Nitin Madnani <nmadnani@ets.org>
#         Rami Al-Rfou' <ralrfou@cs.stonybrook.edu>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
A module for interfacing with the Stanford taggers.
"""

import os
import tempfile
from subprocess import PIPE

from nltk.internals import find_file, find_jar, config_java, java, _java_options
from nltk.tag.api import TaggerI

_stanford_url = 'http://nlp.stanford.edu/software'

class StanfordTagger(TaggerI):
    """
    An interface to Stanford taggers. Subclasses must define:

    - ``_cmd`` property: A property that returns the command that will be
      executed.
    - ``_SEPARATOR``: Class constant that represents that character that
      is used to separate the tokens from their tags.
    - ``_JAR`` file: Class constant that represents the jar file name.
    """

    _SEPARATOR = ''
    _JAR = ''

    def __init__(self, path_to_model, path_to_jar=None, encoding=None, verbose=False, java_options='-mx1000m'):

        self._stanford_jar = find_jar(
                self._JAR, path_to_jar,
                searchpath=(), url=_stanford_url,
                verbose=verbose)

        self._stanford_model = find_file(path_to_model,
                env_vars=('STANFORD_MODELS'), verbose=verbose)
        self._encoding = encoding
        self.java_options = java_options

    @property
    def _cmd(self):
      raise NotImplementedError

    def tag(self, tokens):
        return self.batch_tag([tokens])[0]

    def batch_tag(self, sentences):
        encoding = self._encoding
        default_options = ' '.join(_java_options)
        config_java(options=self.java_options, verbose=False)

        # Create a temporary input file
        _input_fh, self._input_file_path = tempfile.mkstemp(text=True)

        if encoding:
            self._cmd.extend(['-encoding', encoding])

        # Write the actual sentences to the temporary input file
        _input_fh = os.fdopen(_input_fh, 'w')
        _input = '\n'.join((' '.join(x) for x in sentences))
        if isinstance(_input, unicode) and encoding:
            _input = _input.encode(encoding)
        _input_fh.write(_input)
        _input_fh.close()

        # Run the tagger and get the output
        stanpos_output, _stderr = java(self._cmd,classpath=self._stanford_jar, \
                                                       stdout=PIPE, stderr=PIPE)
        if encoding:
            stanpos_output = stanpos_output.decode(encoding)

        # Delete the temporary file
        os.unlink(self._input_file_path)

        # Return java configurations to their default values
        config_java(options=default_options, verbose=False)

        return self.parse_output(stanpos_output)

    def parse_output(self, text):
        # Output the tagged sentences
        tagged_sentences = []
        for tagged_sentence in text.strip().split("\n"):
            sentence = []
            for tagged_word in tagged_sentence.strip().split():
                word_tags = tagged_word.strip().split(self._SEPARATOR)
                sentence.append((''.join(word_tags[:-1]), word_tags[-1]))
            tagged_sentences.append(sentence)
        return tagged_sentences

class POSTagger(StanfordTagger):
    """
    A class for pos tagging with Stanford Tagger. The input is the paths to:
     - a model trained on training data
     - (optionally) the path to the stanford tagger jar file. If not specified here,
       then this jar file must be specified in the CLASSPATH envinroment variable.
     - (optionally) the encoding of the training data (default: ASCII)

    Example:

    .. doctest::
        :options: +SKIP

        >>> from nltk.tag.stanford import POSTagger
        >>> st = POSTagger('/usr/share/stanford-postagger/models/english-bidirectional-distsim.tagger',
        ...                '/usr/share/stanford-postagger/stanford-postagger.jar')
        >>> st.tag('What is the airspeed of an unladen swallow ?'.split())
        [('What', 'WP'), ('is', 'VBZ'), ('the', 'DT'), ('airspeed', 'NN'), ('of', 'IN'), ('an', 'DT'), ('unladen', 'JJ'), ('swallow', 'VB'), ('?', '.')]
    """

    _SEPARATOR = '_'
    _JAR = 'stanford-postagger.jar'

    def __init__(self, *args, **kwargs):
        super(POSTagger, self).__init__(*args, **kwargs)

    @property
    def _cmd(self):
        return ['edu.stanford.nlp.tagger.maxent.MaxentTagger', \
                '-model', self._stanford_model, '-textFile', \
                self._input_file_path, '-tokenize', 'false']

class NERTagger(StanfordTagger):
    """
    A class for ner tagging with Stanford Tagger. The input is the paths to:

    - a model trained on training data
    - (optionally) the path to the stanford tagger jar file. If not specified here,
      then this jar file must be specified in the CLASSPATH envinroment variable.
    - (optionally) the encoding of the training data (default: ASCII)

    Example:

    .. doctest::
        :options: +SKIP

        >>> from nltk.tag.stanford import NERTagger
        >>> st = NERTagger('/usr/share/stanford-ner/classifiers/all.3class.distsim.crf.ser.gz',
        ...                '/usr/share/stanford-ner/stanford-ner.jar')
        >>> st.tag('Rami Eid is studying at Stony Brook University in NY'.split())
        [('Rami', 'PERSON'), ('Eid', 'PERSON'), ('is', 'O'), ('studying', 'O'),
         ('at', 'O'), ('Stony', 'ORGANIZATION'), ('Brook', 'ORGANIZATION'),
         ('University', 'ORGANIZATION'), ('in', 'O'), ('NY', 'LOCATION')]
    """

    _SEPARATOR = '/'
    _JAR = 'stanford-ner.jar'
    _FORMAT = 'slashTags'

    def __init__(self, *args, **kwargs):
        super(NERTagger, self).__init__(*args, **kwargs)

    @property
    def _cmd(self):
        return ['edu.stanford.nlp.ie.crf.CRFClassifier', \
                '-loadClassifier', self._stanford_model, '-textFile', \
                self._input_file_path, '-outputFormat', self._FORMAT]

    def parse_output(self, text):
      if self._FORMAT == 'slashTags':
        return super(NERTagger, self).parse_output(text)
      raise NotImplementedError


if __name__ == "__main__":
    import doctest
    doctest.testmod(optionflags=doctest.NORMALIZE_WHITESPACE)
