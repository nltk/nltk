# -*- coding: utf-8 -*-
# Natural Language Toolkit: Interface to the Stanford Tokenizer
#
# Copyright (C) 2001-2017 NLTK Project
# Author: Steven Xu <xxu@student.unimelb.edu.au>
#
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

from __future__ import unicode_literals, print_function

import tempfile
import os
import json
from subprocess import PIPE
import warnings

from six import text_type

from nltk.internals import find_jar, config_java, java, _java_options
from nltk.tokenize.api import TokenizerI
from nltk.parse.corenlp import CoreNLPParser

_stanford_url = 'https://nlp.stanford.edu/software/tokenizer.shtml'

class StanfordTokenizer(TokenizerI):
    r"""
    Interface to the Stanford Tokenizer

    >>> from nltk.tokenize.stanford import StanfordTokenizer
    >>> s = "Good muffins cost $3.88\nin New York.  Please buy me\ntwo of them.\nThanks."
    >>> StanfordTokenizer().tokenize(s)
    ['Good', 'muffins', 'cost', '$', '3.88', 'in', 'New', 'York', '.', 'Please', 'buy', 'me', 'two', 'of', 'them', '.', 'Thanks', '.']
    >>> s = "The colour of the wall is blue."
    >>> StanfordTokenizer(options={"americanize": True}).tokenize(s)
    ['The', 'color', 'of', 'the', 'wall', 'is', 'blue', '.']
    """

    _JAR = 'stanford-postagger.jar'

    def __init__(self, path_to_jar=None, encoding='utf8', options=None, verbose=False, java_options='-mx1000m'):
        # Raise deprecation warning.
        warnings.simplefilter('always', DeprecationWarning)
        warnings.warn(str("\nThe StanfordTokenizer will "
                          "be deprecated in version 3.2.5.\n"
                          "Please use \033[91mnltk.parse.corenlp.CoreNLPTokenizer\033[0m instead.'"),
                      DeprecationWarning, stacklevel=2)
        warnings.simplefilter('ignore', DeprecationWarning)
        self._stanford_jar = find_jar(
            self._JAR, path_to_jar,
            env_vars=('STANFORD_POSTAGGER',),
            searchpath=(), url=_stanford_url,
            verbose=verbose
        )

        self._encoding = encoding
        self.java_options = java_options

        options = {} if options is None else options
        self._options_cmd = ','.join('{0}={1}'.format(key, val) for key, val in options.items())

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
        cmd.extend(['-charset', encoding])
        _options_cmd = self._options_cmd
        if _options_cmd:
            cmd.extend(['-options', self._options_cmd])

        default_options = ' '.join(_java_options)

        # Configure java.
        config_java(options=self.java_options, verbose=verbose)

        # Windows is incompatible with NamedTemporaryFile() without passing in delete=False.
        with tempfile.NamedTemporaryFile(mode='wb', delete=False) as input_file:
            # Write the actual sentences to the temporary input file
            if isinstance(input_, text_type) and encoding:
                input_ = input_.encode(encoding)
            input_file.write(input_)
            input_file.flush()

            cmd.append(input_file.name)

            # Run the tagger and get the output.
            stdout, stderr = java(cmd, classpath=self._stanford_jar,
                                  stdout=PIPE, stderr=PIPE)
            stdout = stdout.decode(encoding)

        os.unlink(input_file.name)

        # Return java configurations to their default values.
        config_java(options=default_options, verbose=False)

        return stdout


class CoreNLPTokenizer(CoreNLPParser):
    def __init__(self, url='http://localhost:9000', encoding='utf8'):
        r"""
        This is a duck-type of CoreNLPParser that has the tokenizing
        functionality similar to the original Stanford POS tagger.

            >>> from nltk.tokenize.stanford import CoreNLPTokenizer
            >>> s = "Good muffins cost $3.88\nin New York.  Please buy me\ntwo of them.\nThanks."
            >>> CoreNLPTokenizer(url='http://localhost:9000').tokenize(s) == expected # doctest: +SKIP
            [u'Good', u'muffins', u'cost', u'$', u'3.88', u'in', u'New', u'York', u'.', u'Please', u'buy', u'me', u'two', u'of', u'them', u'.', u'Thanks', u'.']
        """
        super(CoreNLPTokenizer, self).__init__(url, encoding)

    def tokenize(self, text, properties=None):
        """
        Tokenize a string of text. Consistent with the StanfordTokenizer, This
        function returns a list of string. The orignal CoreNLPParser.tokenize()
        returns a generator of string.
        """
        return list(super(CoreNLPTokenizer, self).tokenize(text, properties))


def setup_module(module):
    from nose import SkipTest

    try:
        StanfordTokenizer()
    except LookupError:
        raise SkipTest('doctests from nltk.tokenize.stanford are skipped because the stanford postagger jar doesn\'t exist')

    try:
        CoreNLPTokenizer()
    except LookupError:
        raise SkipTest('doctests from nltk.tokenize.stanford.CoreNLPTokenizer are skipped because the '
                       'stanford corenlp server not started')
