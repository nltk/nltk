# Natural Language Toolkit: RTE Corpus Reader
#
# Copyright (C) 2001-2007 University of Pennsylvania
# Author:  Ewan Klein <ewan@inf.ed.ac.uk>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""
Corpus reader for the Recognizing Textual Entailment (RTE) Corpus.

The files were taken from the RTE1, RTE2 and RTE3 datasets and the filenames
were regularized.

Filenames are of the form rte*_dev.xml, rte*_test.xml, and rte*_test_gold.xml.

Each entailment corpus is a list of 'text'/'hypothesis' pairs. The following example is taken from RTE3:

<pair id="1" entailment="YES" task="IE" length="short" >
    <t>The sale was made to pay Yukos' US$ 27.5 billion tax bill, Yuganskneftegaz was originally sold for US$ 9.4 billion to a little known company Baikalfinansgroup which was later bought by the Russian state-owned oil company Rosneft .</t>
   <h>Baikalfinansgroup was sold to Rosneft.</h>
</pair>
"""

from util import *
from api import *
from xmldocs import XMLCorpusReader

class RTEPair:
    def __init__(self, pair, rteversion=None, id=None, text=None, hyp=None,
                 value=None, task=None, length=None):
        self.rteversion =  rteversion    
        self.id = pair.attrib["id"]
        self.text = pair[0].text
        self.hyp = pair[1].text

        if "value" in pair.attrib:
            self.value = pair.attrib["value"]
        elif "entailment" in pair.attrib:
            self.value = pair.attrib["entailment"]
        else:
            self.value = value
        if "task" in pair.attrib:
            self.task = pair.attrib["task"]
        else:
            self.task = task
        if "length" in pair.attrib:
            self.length = pair.attrib["length"]
        else:
            self.length = length 

    def __repr__(self):
        return '<RTEPair: id = %s>' % self.id


class RTECorpusReader(XMLCorpusReader):
    """
    """
    def __init__(self, root, items, extension=''):
        """
        @param root: The root directory for this corpus.
        @param items: A list of items in this corpus.
        @param extension: File extension for items in this corpus.
        """
        if isinstance(items, basestring):
            items = find_corpus_items(root, items, extension)
        self._root = root
        self.items = tuple(items)
        self._extension = extension
        
    def xml(self, items=None):
        return concat([ElementTree.parse(filename).getroot()
                       for filename in self._item_filenames(items)])   
 
    def _read_etree(self, doc):
        
        return [RTEPair(pair) for pair in doc.getiterator("pair")]
 

    def pairs(self, items=None):
        doc = self.xml(items)
        if doc.tag == 'documents':
            return concat([self._read_etree(corpus) for corpus in doc.getchildren()])
        else:
            return self._read_etree(doc)
    
    
    
from nltk.data  import find
path = find('corpora/rte/rte1_dev.xml')
from nltk.etree import ElementTree as ET
doc = ET.parse(path).getroot()



new = RTEPair(doc[0])
