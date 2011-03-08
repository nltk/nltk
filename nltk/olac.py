# Natural Language Toolkit: Support for OLAC Metadata
#
# Copyright (C) 2001-2011 NLTK Project
# Author: Steven Bird <sb@csse.unimelb.edu.au>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT


from StringIO import StringIO

def read_olac(xml):
    """
    Read an OLAC XML record and return a list of attributes.

    @param xml: XML string for conversion    
    @type xml: C{string}
    @rtype: C{list} of C{tuple}
    """
    from lxml import etree

    root = etree.parse(StringIO(xml)).getroot()
    return [(element.tag, element.attrib, element.text) for element in root.getchildren()]

def pprint_olac(xml):
    for tag, attrib, text in read_olac(xml):
        print "%-12s" % tag + ':',
        if text:
            print text,
        if attrib:
            print "(%s=%s)" % (attrib['type'], attrib['code']),
        print

def demo():
    from lxml import etree
    import nltk.data

    file = nltk.data.find('corpora/treebank/olac.xml')
    xml = open(file).read()
    pprint_olac(xml)

if __name__ == '__main__':
    demo()

__all__ = ['read_olac', 'pprint_olac']
