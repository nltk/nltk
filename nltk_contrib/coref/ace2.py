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
from nltk.tokenize.simple import *


class ACE2CorpusReader(CorpusReader):
    """
    """

    def __init__(self, root, files):
        CorpusReader.__init__(self, root, files)

    def words(self, files=None):
        """
        """
        return concat([ACE2SourceDocument(filename).words()
                       for filename in self.abspaths(files)])

    def sents(self, files=None):
        """
        """
        return concat([ACE2SourceDocument(filename).sents()
                       for filename in self.abspaths(files)])


class ACE2SourceDocument(str):
    """
    """

    try:
        import xml.etree.cElementTree as ElementTree
    except ImportError:
        import nltk.etree.ElementTree

    import htmlentitydefs

    from nltk.tokenize.punkt import PunktWordTokenizer
    from nltk.tokenize.regexp import BlanklineTokenizer
    from nltk.tokenize.simple import LineTokenizer 

    def __init__(self, path):
        """
        """
        str.__init__(self, path)
        self._xmldoc_ = None

    def _xmldoc(self):
        """
        """
        if self._xmldoc_:
            return self._xmldoc_
        self._xmldoc_ = ElementTree.parse(self).getroot()
        return self._xmldoc_
        
    def _xpath(self):
        """
        """
        if self.docsource() == 'broadcast news':
            return './/TEXT/turn'
        if self.docsource() == 'newswire':
            return './/TEXT'
        if self.docsource() == 'newspaper':
            return './/TEXT'
        raise

    def _sent_tokenizer(self):
        """
        """
        if self.docsource() == 'broadcast news':
            return PunktSentenceTokenizer()
        if self.docsource() == 'newswire':
            return PunktSentenceTokenizer()
        if self.docsource() == 'newspaper':
            return BlanklineTokenizer()
        raise

    def _word_tokenizer(self):
        return PunktWordTokenizer()

    def xmldoc(self):
        """
        """
        return self._xmldoc()

    def words(self):
        """
        """
        result = []
        for sent in self.sents():
            result.extend(sent)
        assert None not in result
        return result

    def sents(self):
        """
        """
        result = []
        for xmltext in self._xmldoc().findall(self._xpath()):
            result.extend([self._word_tokenizer().tokenize(xmlsent)
                           for xmlsent in
                           self._sent_tokenizer().tokenize(xmltext.text)])
        assert None not in result
        return result

    def docno(self):
        """
        """
        result = self._xmldoc().find('.//DOCNO').text.strip()
        assert result
        return result

    def doctype(self):
        """
        """
        result = self._xmldoc().find('.//DOCTYPE').text.strip()
        assert result
        return result

    def docsource(self):
        """
        """
        result = self._xmldoc().find('.//DOCTYPE').get('SOURCE').strip()
        assert result
        return result


def _demo(root, file):
    """
    """
    from nltk_contrib.coref.ace2 import ACE2CorpusReader

    try:
        reader = ACE2CorpusReader(root, file)
        print 'Sentences for %s:' % (file)
        for sent in reader.sents():
            print sent
        print
        print 'Words for %s:' % (file)
        for word in reader.words():
            print word
        print
    except Exception, e:
        print 'Error encountered while running demo for %s: %s' % (file, e)
        print

def demo():
    """
    """
    import os
    import os.path
    ace2_dir = os.environ['ACE2_DIR']
    bnews_dir = os.path.join(ace2_dir, 'data/ace2_train/', 'bnews')
    npaper_dir = os.path.join(ace2_dir, 'data/ace2_train/', 'npaper')
    nwire_dir = os.path.join(ace2_dir, 'data/ace2_train/', 'nwire')
    _demo(bnews_dir, 'ABC19980106.1830.0029.sgm')
    _demo(npaper_dir, '9801.139.sgm')
    _demo(nwire_dir, 'APW19980213.1302.sgm')

if __name__ == '__main__':
    demo()
