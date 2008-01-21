# Natural Language Toolkit: RTE Corpus Reader
#
# Copyright (C) 2001-2008 University of Pennsylvania
# Author:  Ewan Klein <ewan@inf.ed.ac.uk>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""
Corpus reader for the Recognizing Textual Entailment (RTE) Challenge Corpora.

The files were taken from the RTE1, RTE2 and RTE3 datasets and the filenames
were regularized. 

Filenames are of the form rte*_dev.xml and rte*_test.xml. The latter are the gold standard annotated files.

Each entailment corpus is a list of 'text'/'hypothesis' pairs. The following example is taken from RTE3:

<pair id="1" entailment="YES" task="IE" length="short" >
    <t>The sale was made to pay Yukos' US$ 27.5 billion tax bill, Yuganskneftegaz was originally sold for US$ 9.4 billion to a little known company Baikalfinansgroup which was later bought by the Russian state-owned oil company Rosneft .</t>
   <h>Baikalfinansgroup was sold to Rosneft.</h>
</pair>

In order to provide globally unique IDs for each pair, a new attribute C{challenge} has been added to the root element C{entailment-corpus} of each file, taking values 1, 2 or 3.  The GID is formatted 'm-n', where 'm' is the challenge number and 'n' is the pair ID.
"""

from util import *
from api import *
from xmldocs import XMLCorpusReader

def norm(value_string):
    """
    Normalize the string value in an RTE pair's C{value} or C{entailment} 
    attribute.
    """

    valdict = {"TRUE": 1,
           "FALSE": 0,
           "YES": 1,
           "NO": 0}
    return valdict[value_string.upper()]

class RTEPair:
    """
    Container for RTE text-hypothesis pairs.

    The entailment relation is signalled by the C{value| attribute in RTE1, and by 
    C{entailment} in RTE2 and RTE3. These both get mapped on to the C{entailment}
    attribute of this class.
    """
    def __init__(self, pair, challenge=None, id=None, text=None, hyp=None,
             value=None, task=None, length=None):
        self.challenge =  challenge    
        self.id = pair.attrib["id"]
        self.gid = "%s-%s" % (self.challenge, self.id)
        self.text = pair[0].text
        self.hyp = pair[1].text

        if "value" in pair.attrib:
            self.value = norm(pair.attrib["value"])
        elif "entailment" in pair.attrib:
            self.value = norm(pair.attrib["entailment"])
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
        if self.challenge:
            return '<RTEPair: gid=%s-%s>' % (self.challenge, self.id)
        else:
            return '<RTEPair: id=%s>' % self.id


# [xx] This could use more documentation!
class RTECorpusReader(XMLCorpusReader):
    """
    Corpus reader for corpora in RTE challenges.
    """
    def xml(self, files=None):
        return concat([ElementTree.parse(filename).getroot()
                   for filename in self.abspaths(files)])   

    def _read_etree(self, doc):
        try:
            challenge = doc.attrib['challenge']
        except KeyError:
            challenge = None
        return [RTEPair(pair, challenge=challenge)
                for pair in doc.getiterator("pair")]


    def pairs(self, files=None):
        doc = self.xml(files)
        if doc.tag == 'documents':
            return concat([self._read_etree(corpus)
                           for corpus in doc.getchildren()])
        else:
            return self._read_etree(doc)





