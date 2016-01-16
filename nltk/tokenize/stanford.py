# -*- coding: utf-8 -*-
# Natural Language Toolkit: Interface to the Stanford Tokenizer
#
# Copyright (C) 2001-2015 NLTK Project
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
    from nose import SkipTest
    import requests

    if not requests.get('http://localhost:9000').ok:
        raise SkipTest(
            'Doctests from nltk.parse.stanford are skipped because '
            'the CoreNLP server is not available.'
        )
