# -*- coding: utf-8 -*-
# Natural Language Toolkit: Interface to the Stanford Tokenizer
#
# Copyright (C) 2001-2013 NLTK Project
# Author: Steven Xu <xxu@student.unimelb.edu.au>
#
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

from __future__ import unicode_literals

import tempfile
import os
from subprocess import PIPE

from nltk import compat
from nltk.internals import find_jar, config_java, java, _java_options

from nltk.tokenize.api import TokenizerI

_stanford_url = 'http://nlp.stanford.edu/software/lex-parser.shtml'

class StanfordTokenizer(TokenizerI):
    _JAR = 'stanford-parser.jar'

    def __init__(self, path_to_jar=None, encoding='UTF-8', verbose=False, java_options='-mx1000m'):
        self._stanford_jar = find_jar(
                self._JAR, path_to_jar,
                searchpath=(), url=_stanford_url,
                verbose=verbose)

        self._encoding = encoding
        self.java_options = java_options

    @staticmethod
    def _parse_tokenized_output(s):
        return s.splitlines()

    def tokenize(self, s):
        """
        Use stanford tokenizer's PTBTokenizer to tokenize multiple sentences.
        """
        cmd = [
            'edu.stanford.nlp.process.PTBTokenizer',
        ]
        return self._parse_tokenized_output(self._execute(cmd, s))

    def _execute(self, cmd, input_, verbose=False):
        encoding = self._encoding
        cmd.extend(['-encoding', encoding])

        default_options = ' '.join(_java_options)

        # Configure java.
        config_java(options=self.java_options, verbose=verbose)

        # Windows is incompatible with NamedTemporaryFile() without passing in delete=False.
        with tempfile.NamedTemporaryFile(mode='wb', delete=False) as input_file:
            # Write the actual sentences to the temporary input file
            if isinstance(input_, compat.text_type) and encoding:
                input_ = input_.encode(encoding)
            input_file.write(input_)
            input_file.flush()

            cmd.append(input_file.name)

            # Run the tagger and get the output.
            stdout, stderr = java(cmd, classpath=self._stanford_jar,
                                  stdout=PIPE, stderr=PIPE)
            stdout = stdout.decode(encoding)
            if (not compat.PY3) and encoding == 'ascii':
                stdout = str(stdout)

        os.unlink(input_file.name)

        # Return java configurations to their default values.
        config_java(options=default_options, verbose=False)

        return stdout

