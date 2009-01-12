#!/usr/bin/env python
# -*- coding: utf8 -*-

# Natural Language Toolkit: Toolbox data file parser
#
# Copyright (C) 2001-2006 NLTK Project
# Author: Greg Aumann <greg_aumann@sil.org>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
functions to normalise ElementTree structures.
"""

import nltk.etree.ElementTree as ET


def demo():
    from nltk_contrib.toolbox import ToolboxData, to_sfm_string
    from nltk_contrib.toolbox.data import iu_mien_hier as hierarchy
    import sys
    import os
    from nltk.data import ZipFilePathPointer

    file_path = data.find('corpora/toolbox/iu_mien_samp.db')
    settings.open(file_path)
#    zip_path = data.find('corpora/toolbox.zip')
#    db = ToolboxData(ZipFilePathPointer(zip_path, entry='toolbox/iu_mien_samp.db'))
    lexicon = db.grammar_parse('toolbox', hierarchy.grammar, unwrap=False, encoding='utf8')
    db.close()
    remove_blanks(lexicon)
    add_default_fields(lexicon, hierarchy.default_fields)
    sort_fields(lexicon, hierarchy.field_order)
    add_blank_lines(lexicon, hierarchy.blanks_before, hierarchy.blanks_between)
    print to_sfm_string(lexicon, encoding='utf8')
    

if __name__ == '__main__':
    demo()
