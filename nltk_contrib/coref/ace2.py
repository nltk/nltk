# Natural Language Toolkit (NLTK) ACE-2 Corpus Reader
#
# Copyright (C) 2008 Joseph Frazee
# Author: Joseph Frazee <jfrazee@mail.utexas.edu>
# URL: http://nltk.org
# For license information, see LICENSE.TXT

"""
Corpus reader for the ACE-2 Corpus.

"""

try:
    import xml.etree.cElementTree as ElementTree
except ImportError:
    import nltk.etree.ElementTree

from nltk.corpus.reader.api import *
from nltk.corpus.reader.util import *
from nltk.corpus.reader.xmldocs import *

from nltk.tokenize.punkt import *
from nltk.tokenize.regexp import *


class ACE2CorpusReader(XMLCorpusReader):
    """
    """

    def __init__(self, root, files, lazy=True,
                 sent_tokenizer=BlanklineTokenizer(),
                 word_tokenizer=PunktWordTokenizer()):
        XMLCorpusReader.__init__(self, root, files)
        self._lazy = lazy
        self._sent_tokenizer = sent_tokenizer
        self._word_tokenizer = word_tokenizer

    def words(self, files=None):
        """
        """
        return concat([self._words(filename)
                       for filename in self.abspaths(files)])

    def _words(self, filename):
        """
        """
        result = []
        for sent in self.sents(filename):
            result.extend(sent)
        assert None not in result
        return result

    def sents(self, files=None):
        """
        """
        if self._lazy:
            return concat([ACE2TextView(filename, self._sent_tokenizer,
                                        self._word_tokenizer)
                           for filename in self.abspaths(files)])
        else:
            return concat([self._sents(filename)
                           for filename in self.abspaths(files)])

    def _sents(self, filename):
        """
        """
        result = []
        xmldoc = ElementTree.parse(filename).getroot()
        for xmltext in xmldoc.findall('.//TEXT'):
            result.append([self._word_tokenizer.tokenize(xmlsent)
                           for xmlsent in
                           self._sent_tokenizer.tokenize(xmltext.text)])
        assert None not in result
        return result



class ACE2TextView(XMLCorpusView):
    """
    """

    def __init__(self, filename, sent_tokenizer, word_tokenizer):
        """
        """
        XMLCorpusView.__init__(self, filename, '.*/TEXT')
        self._sent_tokenizer = sent_tokenizer
        self._word_tokenizer = word_tokenizer

    def handle_elt(self, elt, context):
        result = []
        for sent in self._sent_tokenizer.tokenize(elt.text):
            result.append(self._word_tokenizer.tokenize(sent))
        assert None not in result
        return result


# This is not from the actual ACE-2 Corpus so there shouldn't be any license
# issues with including this in the code.
toy_nwire = """
<DOC>
<DOCNO> 0000.000 </DOCNO>
<DOCTYPE SOURCE="newswire"> NEWS STORY</DOCTYPE>
<DATE_TIME>04/26/2006</DATE_TIME>
<HEADER>
SOURCE: American Forces Press Service
HEADLINE: Rumsfeld: All Neighbors Except Iran Benefit From Success in Iraq
</HEADER>
<BODY>
<SLUG>American Forces Press Service</SLUG>
<HEADLINE>Rumsfeld: All Neighbors Except Iran Benefit From Success in Iraq</HEADLINE>
<TEXT>
By John D. Banusiewicz

American Forces Press Service

BAGHDAD, April 26, 2006 --

While success in Iraq's march to freedom would mean good things for most of its neighbors, Iran could only view that as a failure, Defense Secretary Donald H. Rumsfeld said here today.

Rumsfeld and Secretary of State Condoleezza Rice are here to meet with U.S. and Iraqi officials.

"A successful Iraq that is at peace with its neighbors and that has a government that's representative of the various elements within the country would represent an enormous success for this region," Rumsfeld said.

"It would add to prosperity for the region. It would be something that all of the neighbors would benefit from, except Iran.

"Iran's view of the world is quite different," he continued, "and (a successful democracy in Iraq) would represent a failure from the standpoint of Iran."

Rumsfeld said people who are concerned by the Iranian government's provocative statements and its quest for nuclear weapons would recognize that a successful Iraq is "fundamentally inconsistent with the interests of Iran."

The secretary declined to speculate as to whether any need to contain Iran might require long-term U.S. military presence in Iraq.

He noted that the U.N. resolution under which coalition forces now operate in Iraq is scheduled to expire at the end of the year.

"What we would want to do would be to engage in discussions with the new (Iraqi) government about that resolution and arrangements between our two countries with respect to our military-to-military relationship," Rumsfeld said.

"It also will require us to begin the process in the Department of State and the Department of Defense to look forward in terms of the budget cycle to see what our arrangements would be in Iraq."

Rumsfeld said U.S. troop strength in Iraq would continue to be based on conditions on the ground and discussions with the Iraqi government.

</TEXT>
</BODY>
</DOC>
"""

def nwire_demo():
    """
    """

    import os
    import os.path
    import tempfile

    from nltk_contrib.coref.ace2 import ACE2CorpusReader

    try:
        (fd, path) = tempfile.mkstemp()
        os.write(fd, toy_nwire.lstrip())
        os.close(fd)
        dirname = os.path.dirname(path)
        basename = os.path.basename(path)
        ace2 = ACE2CorpusReader(dirname, basename, False)
        for doc in ace2.sents():
            for sent in doc:
                print sent
        print
        for doc in ace2.words():
            for word in doc:
                print word
    finally:
        os.remove(path)

def demo():
    """
    """
    nwire_demo()

if __name__ == '__main__':
    demo()
