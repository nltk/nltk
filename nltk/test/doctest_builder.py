# -*- coding: utf-8 -*-
from __future__ import absolute_import
import doctest
from sphinx.ext.doctest import DocTestBuilder

class NltkDocTestBuilder(DocTestBuilder):
    """
    Custom Sphinx doctest builder with NORMALIZE_WHITESPACE option added by default.
    """

    name = 'nltk-doctest'

    def init(self):
        super(NltkDocTestBuilder, self).init()
        self.opt |= doctest.NORMALIZE_WHITESPACE

def setup(app):
    app.add_builder(NltkDocTestBuilder)
