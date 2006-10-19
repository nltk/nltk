#!/usr/bin/env python
# -*- coding: utf8 -*-

# Natural Language Toolkit: Toolbox Data demonstration
#
# Copyright (C) 2001-2006 University of Pennsylvania
# Author: Greg Aumann <greg_aumann@sil.org>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""
demonstration of grammar parsing
"""

from nltk_lite.etree import ElementTree
from nltk_lite.contrib import toolbox
from nltk_lite.corpora import get_basedir
import os.path

grammar = {
        'toolbox':      (('_sh',), ('_DateStampHasFourDigitYear', 'entry')),
        'entry':          (('lx',), ('hm', 'sense', 'dt')),
        'sense':          (('sn', 'ps'), ('pn', 'gv', 'dv',
                                   'gn', 'gp', 'dn', 'rn',
                                   'ge', 'de', 're',
                                   'example', 'lexfunc')),
        'example':      (('rf', 'xv',), ('xn', 'xe')),
        'lexfunc':      (('lf',), ('lexvalue',)),
        'lexvalue':    (('lv',), ('ln', 'le')),
}

db = toolbox.ToolboxData()
db.open(os.path.join(get_basedir(), 'toolbox', 'iu_mien_samp.db'))
lexicon = db.grammar_parse('toolbox', grammar, encoding='utf8')
tree = ElementTree.ElementTree(lexicon)
tree.write('iu_mien_samp.xml', encoding='utf8')
num_lexemes = 0
num_senses = 0
num_examples = 0
for lexeme in lexicon.findall('entry'):
    num_lexemes += 1
    for sense in lexeme.findall('sense'):
        num_senses += 1
        for example in sense.findall('example'):
            num_examples += 1
print 'num. lexemes  =', num_lexemes
print 'num. senses   =', num_senses
print 'num. examples =', num_examples

#another approach
print 'num. examples =', len(lexicon.findall('.//example'))
