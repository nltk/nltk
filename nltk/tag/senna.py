# -*- coding: utf-8 -*-
# Natural Language Toolkit: Interface to the Senna tagger
#
# Copyright (C) 2001-2011 NLTK Project
# Author: Rami Al-Rfou' <ralrfou@cs.stonybrook.edu>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT
#
# $Id: senna.py $

"""
A module for interfacing with the SENNA tagger.
"""

import os
import subprocess
import tempfile
import nltk
from platform import architecture, system
from nltk.tag.api import *

_senna_url = 'http://ml.nec-labs.com/senna/'

class SennaTagger(TaggerI):
    __OPS = ['pos', 'chk', 'ner']

    def __init__(self, path, operations, encoding=None, verbose=False):
        self._encoding = encoding
        self._path = os.path.normpath(path) + os.sep
        self.operations = operations

    @property
    def executable(self):
        os_name = system()
        if os_name == 'Linux':
            bits = architecture()[0]
            if bits == '64bit':
                return os.path.join(self._path, 'senna-linux64')
            return os.path.join(self._path, 'senna-linux32')
        if os_name == 'Windows':
            return os.path.join(self._path, 'senna-win32.exe')
        if os_name == 'Darwin':
            return os.path.join(self._path, 'senna-osx')
        return os.path.join(self._path, 'senna')

    def _map(self):
        _map = {'word':0}
        i = 1
        for operation in SennaTagger.__OPS:
            if operation in self.operations:
                _map[operation] = i
                i+= 1
        return _map

    def tag(self, tokens):
        return self.batch_tag([tokens])[0]

    def batch_tag(self, sentences):
        encoding = self._encoding

        # Build the senna command to run the tagger
        _senna_cmd = [self.executable, '-path', self._path, '-usrtokens', '-iobtags']
        _senna_cmd.extend(['-'+op for op in self.operations])

        # Write the actual sentences to the temporary input file
        _input = '\n'.join((' '.join(x) for x in sentences))+'\n'
        if isinstance(_input, unicode) and encoding:
            _input = _input.encode(encoding)

        # Run the tagger and get the output
        p = subprocess.Popen(_senna_cmd,
                             stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
        (stdout, stderr) = p.communicate(input=_input)
        senna_output = stdout

        # Check the return code.
        if p.returncode != 0:
            print stderr
            raise OSError('Senna command failed!')

        if encoding:
            senna_output = stdout.decode(encoding)

        # Output the tagged sentences
        map_ = self._map()
        tagged_sentences = [[]]
        for tagged_word in senna_output.strip().split("\n"):
            if not tagged_word:
                tagged_sentences.append([])
                continue
            tags = tagged_word.split('\t')
            result = {}
            for tag in map_:
              result[tag] = tags[map_[tag]].strip()
            tagged_sentences[-1].append(result)
        return tagged_sentences


class POSTagger(SennaTagger):
    """
    A class for pos tagging with Senna POSTagger. The input is the paths to:
     - A path to the senna executables

    Example:

        >>> tagger = senna.POSTagger(path='/media/data/NER/senna-v2.0')
        >>> tagger.tag('What is the airspeed of an unladen swallow ?'.split())
        [('What', 'WP'), ('is', 'VBZ'), ('the', 'DT'), ('airspeed', 'NN'),
        ('of', 'IN'), ('an', 'DT'), ('unladen', 'JJ'), ('swallow', 'VB'), ('?', '.')]
    """
    def __init__(self, path, encoding=None, verbose=False):
        super(POSTagger, self).__init__(path, ['pos'], encoding, verbose)

    def batch_tag(self, sentences):
        tagged_sents = super(POSTagger, self).batch_tag(sentences)
        for i in range(len(tagged_sents)):
            for j in range(len(tagged_sents[i])):
                tagged_sents[i][j] = (sentences[i][j], tagged_sents[i][j]['pos'])
        return tagged_sents


class NERTagger(SennaTagger):
    def __init__(self, path, encoding=None, verbose=False):
        super(NERTagger, self).__init__(path, ['ner'], encoding, verbose)

    def batch_tag(self, sentences):
        tagged_sents = super(NERTagger, self).batch_tag(sentences)
        for i in range(len(tagged_sents)):
            for j in range(len(tagged_sents[i])):
                try:
                    tagged_sents[i][j] = (sentences[i][j], tagged_sents[i][j]['ner'])
                except:
                    import pdb
                    pdb.set_trace()
        return tagged_sents


class CHKTagger(SennaTagger):
    def __init__(self, path, encoding=None, verbose=False):
        super(CHKTagger, self).__init__(path, ['chk'], encoding, verbose)

    def batch_tag(self, sentences):
        tagged_sents = super(CHKTagger, self).batch_tag(sentences)
        for i in range(len(tagged_sents)):
            for j in range(len(tagged_sents[i])):
                tagged_sents[i][j] = (sentences[i][j], tagged_sents[i][j]['chk'])
        return tagged_sents
