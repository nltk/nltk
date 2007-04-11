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

from nltk_lite.etree.ElementTree import ElementTree
from nltk_lite.contrib import toolbox
from nltk_lite.corpora import get_basedir
import os.path, sys

grammar = r"""
      lexfunc: {<lf>(<lv><ln|le>*)*}
      example: {<rf|xv><xn|xe>*}
      sense:   {<sn><ps><pn|gv|dv|gn|gp|dn|rn|ge|de|re>*<example>*<lexfunc>*}
      record:   {<lx><hm><sense>+<dt>}
    """

db = toolbox.ToolboxData()
db.open(os.path.join(get_basedir(), 'toolbox', 'iu_mien_samp.db'))
lexicon = db.chunk_parse(grammar, encoding='utf8')
toolbox.data.indent(lexicon)
tree = ElementTree(lexicon)
tree.write(sys.stdout, encoding='utf8')
