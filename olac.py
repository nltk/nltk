# Natural Language Toolkit: Support for OLAC Metadata
#
# Copyright (C) 2001-2007 University of Pennsylvania
# Author: Steven Bird <sb@csse.unimelb.edu.au>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

from lxml import etree

def demo():
    from nltk.corpus import find_corpus_file
    file = find_corpus_file('treebank', 'olac', '.xml')
    root = etree.parse(file).getroot()
    for element in root.getchildren():
        print element.tag, element.attrib, element.text

if __name__ == '__main__':
    demo()

__all__ = []
