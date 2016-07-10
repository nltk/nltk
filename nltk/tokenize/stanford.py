# -*- coding: utf-8 -*-
# Natural Language Toolkit: Interface to the Stanford Tokenizer
#
# Copyright (C) 2001-2016 NLTK Project
# Author: Steven Xu <xxu@student.unimelb.edu.au>
#
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

from __future__ import unicode_literals, print_function
import warnings

from nltk.tokenize.api import TokenizerI


class StanfordTokenizer(TokenizerI):
    r"""Interface to the Stanford Tokenizer.

    >>> from nltk.tokenize import StanfordTokenizer
    >>> s = "Good muffins cost $3.88\nin New York.  Please buy me\ntwo of them.\nThanks."
    >>> StanfordTokenizer().tokenize(s)
    ['Good', 'muffins', 'cost', '$', '3.88', 'in', 'New', 'York', '.', 'Please', 'buy', 'me', 'two', 'of', 'them', '.', 'Thanks', '.']
    >>> s = "The colour of the wall is blue."
    >>> StanfordTokenizer(options={"americanize": True}).tokenize(s)
    ['The', 'color', 'of', 'the', 'wall', 'is', 'blue', '.']

    """

    def __init__(self, options=None, *args, **kwargs):
        warnings.warn(
            'StanfordTokenizer is deprecated, use nltk.parse.stanford.StanfordParser instead.',
            DeprecationWarning,
        )

        self.options = options or {}

        from nltk.parse.stanford import StanfordParser
        self.parser = StanfordParser(*args, **kwargs)

    def tokenize(self, s):
        properties = {'tokenize.options': 'americanize=true'} if self.options.get('americanize', False) else {}
        return list(self.parser.tokenize(s, properties=properties))


def setup_module(module):
    from nltk.parse.stanford import CoreNLPServer, CoreNLPServerError
    from nose import SkipTest

    global server
    server = CoreNLPServer(port=9000)

    try:
        server.start()
    except CoreNLPServerError as e:
        raise SkipTest('Skipping CoreNLP tests because the server could not be started. {}'.format(e.strerror))


def teardown_module(module):
    server.stop()
