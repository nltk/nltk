#!/usr/bin/env python
# -*- coding: utf8 -*-

# Natural Language Toolkit: Shoebox Data demonstration
#
# Copyright (C) 2001-2006 University of Pennsylvania
# Author: Greg Aumann <greg_aumann@sil.org>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""
corresponds to 
12.3.1   Accessing Shoebox Data
in http://nltk.sourceforge.net/lite/doc/en/data.html
"""

from nltk_lite.contrib.shoebox.data import flat_parse_data

lexicon = flat_parse_data('rotokas.dic', 'lx')
lexemes = []
for lexeme in lexicon.findall('record/lx'):
    normalised_lexeme = lexeme.text.lower()
    lexemes.append(normalised_lexeme)

# list comprehension approach
lexemes2=[lexeme.text.lower() for lexeme in lexicon.findall('record/lx')]

##if lexemes != lexemes2:
##    print 'error two lists not equal'
##else:
##    print repr(lexemes)

import re
def cv(s):
    s = s.lower()
    s = re.sub(r'[^a-z]',     r'_', s)
    s = re.sub(r'[aeiou]',    r'V', s)
    s = re.sub(r'[^V_]',     r'C', s)
    return (s)
    
for field in lexicon[50].getchildren():
    print "\\%s %s" % (field.tag, field.text)
    if field.tag == "lx":
        print "\\cv %s" % cv(field.text)
