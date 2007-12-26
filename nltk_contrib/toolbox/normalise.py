#!/usr/bin/env python
# -*- coding: utf8 -*-

# Natural Language Toolkit: Toolbox data file parser
#
# Copyright (C) 2001-2006 University of Pennsylvania
# Author: Greg Aumann <greg_aumann@sil.org>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""
functions to normalise ElementTree structures.
"""

import re
import nltk.etree.ElementTree as ET

def remove_blanks(elem):
    """Remove all elements and subelements with no text and no child elements.
    
    @param elem: toolbox data in an elementtree structure
    @type elem: ElementTree._ElementInterface
    """
    out = list()
    for child in elem:
        remove_blanks(child)
        if child.text or len(child) > 0:
            out.append(child)
    elem[:] = out

def add_default_fields(elem, default_fields):
    """Add blank elements and subelements specified in default_fields.
    
    @param elem: toolbox data in an elementtree structure
    @type elem: ElementTree._ElementInterface
    @param default_fields: fields to add to each type of element and subelement
    @type default_fields: dictionary of tuples
    """
    try:
        default = default_fields[elem.tag]
    except KeyError:
        pass
    else:
        for field in default:
            if elem.find(field) is None:
                ET.SubElement(elem, field)
    for child in elem:
        add_default_fields(child, default_fields)

def sort_fields(elem, field_orders):
    """Sort the elements and subelements in order specified in field_orders.
    
    @param elem: toolbox data in an elementtree structure
    @type elem: ElementTree._ElementInterface
    @param field_orders: order of fields for each type of element and subelement
    @type field_orders: dictionary of tuples
    """
    order_dicts = dict()
    for field, order in field_orders.items():
        order_dicts[field] = order_key = dict()
        for i, subfield in enumerate(order):
            order_key[subfield] = i 
    _sort_fields(elem, order_dicts)

def _sort_fields(elem, orders_dicts):
    "sort the children of elem"
    try:
        order = orders_dicts[elem.tag]
    except KeyError:
        pass
    else:
        tmp = [((order.get(child.tag, 1e9), i), child) for i, child in enumerate(elem)]
        tmp.sort()
        elem[:] = [child for key, child in tmp]
    for child in elem:
        if len(child):
            _sort_fields(child, orders_dicts)

def add_blank_lines(tree, blanks_before, blanks_between):
    """Add blank lines before all elements and subelements specified in blank_before.
    
    @param elem: toolbox data in an elementtree structure
    @type elem: ElementTree._ElementInterface
    @param blank_before: elements and subelements to add blank lines before
    @type blank_before: dictionary of tuples
    """
    try:
        before = blanks_before[tree.tag]
        between = blanks_between[tree.tag]
    except KeyError:
        for elem in tree:
            if len(elem):
                add_blank_lines(elem, blanks_before, blanks_between)
    else:
        last_elem = None
        for elem in tree:
            tag = elem.tag
            if last_elem is not None and last_elem.tag != tag:
                if tag in before and last_elem is not None:
                    e = last_elem.getiterator()[-1]
                    e.text = (e.text or "") + "\n"
            else:
                if tag in between:
                    e = last_elem.getiterator()[-1]
                    e.text = (e.text or "") + "\n"
            if len(elem):
                add_blank_lines(elem, blanks_before, blanks_between)
            last_elem = elem

def demo():
    from nltk.etree.ElementTree import ElementTree    
    from nltk_contrib.toolbox.data import ToolboxData, to_sfm_string
    from nltk_contrib.toolbox import iu_mien_hier as hierarchy
    import sys
    import os

    fname = os.path.join(os.environ['NLTK_DATA'], 'corpora', 'toolbox', 'iu_mien_samp.db')
    db =  ToolboxData()
    db.open(fname)
    lexicon = db.grammar_parse('toolbox', hierarchy.grammar, unwrap=False, encoding='utf8')
    db.close()
    remove_blanks(lexicon)
    add_default_fields(lexicon, hierarchy.default_fields)
    sort_fields(lexicon, hierarchy.field_order)
    add_blank_lines(lexicon, hierarchy.blanks_before, hierarchy.blanks_between)
    print to_sfm_string(lexicon, encoding='utf8')
    

if __name__ == '__main__':
    demo()
