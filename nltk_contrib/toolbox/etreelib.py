#!/usr/bin/env python
# -*- coding: utf8 -*-

# Natural Language Toolkit: Toolbox data file parser
#
# Copyright (C) Frederick Lundh
# Author: Frederick Lundh
# URL: <http://effbot.org>

"""
module of utility functions for ElementTree structures. Many
are from U{http://effbot.org/zone/element-lib.htm}
"""

import nltk.etree.ElementTree as ET

class _E(object):

    def __call__(self, tag, *children, **attrib):
        elem = ET.Element(tag, attrib)
        for item in children:
            if isinstance(item, dict):
                elem.attrib.update(item)
            elif isinstance(item, basestring):
                if len(elem):
                    elem[-1].tail = (elem[-1].tail or "") + item
                else:
                    elem.text = (elem.text or "") + item
            elif ET.iselement(item):
                elem.append(item)
            else:
                raise TypeError("bad argument: %r" % item)
        return elem

    def __getattr__(self, tag):
        return functools.partial(self, tag)

# create factory object
E = _E()


def append(elem, item):
    """append a string or an element to elem
    code from U{http://effbot.org/zone/element-lib.htm#append}

    @type elem: ElementTree.Element
    @param elem: parent element that item is appended to
    @type item: string or ElementTree.Element
    @param item: string or element appended to elem
    """
    if isinstance(item, basestring):
        if len(elem):
            elem[-1].tail = (elem[-1].tail or "") + item
        else:
            elem.text = (elem.text or "") + item
    else:
        elem.append(item)

def indent(elem, level=0):
    """
    Recursive function to indent an ElementTree._ElementInterface
    used for pretty printing. Based on code from 
    U{http://www.effbot.org/zone/element-lib.htm}. To use run indent
    on elem and then output in the normal way. 
    
    @param elem: element to be indented. will be modified. 
    @type elem: ElementTree._ElementInterface
    @param level: level of indentation for this element
    @type level: nonnegative integer
    @rtype:   ElementTree._ElementInterface
    @return:  Contents of elem indented to reflect its structure
    """
    i = "\n" + level*"  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        for child in elem:
            indent(child, level+1)
        if not child.tail or not child.tail.strip():
            child.tail = i
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
##        for elem in elem:
##            indent(elem, level+1)
##        if not elem.tail or not elem.tail.strip():
##            elem.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i

if __name__ == '__main__':
    pass
