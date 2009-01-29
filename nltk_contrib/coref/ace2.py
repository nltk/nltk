# Natural Language Toolkit (NLTK) ACE-2 Corpus Reader
#
# Copyright (C) 2001-2009 NLTK Project 
# Author: Joseph Frazee <jfrazee@mail.utexas.edu>
# URL: http://nltk.org
# For license information, see LICENSE.TXT

"""
Corpus reader for the ACE-2 Corpus.

"""

from sgmllib import SGMLParser

from nltk.corpus.reader.api import *
from nltk.corpus.reader.util import *

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

    def __init__(self, path):
        """
        """
        str.__init__(self, path)
        self._sgmldoc_ = None

    def _sgmldoc(self):
        """
        """
        if self._sgmldoc_:
            return self._sgmldoc_
        self._sgmldoc_ = ACE2SGMLParser().parse(self)
        return self._sgmldoc_
        
    def _sent_tokenizer(self):
        """
        """
        if self.docsource() == 'broadcast news':
            return PunktSentenceTokenizer()
        if self.docsource() == 'newswire':
            return PunktSentenceTokenizer()
        if self.docsource() == 'newspaper':
            return PunktSentenceTokenizer()
        raise

    def _word_tokenizer(self):
        """
        """
        if self.docsource() == 'broadcast news':
            return PunktWordTokenizer()
        if self.docsource() == 'newswire':
            return PunktWordTokenizer()
        if self.docsource() == 'newspaper':
            return PunktWordTokenizer()
        raise

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
        for sent in self._sent_tokenizer().tokenize(self._sgmldoc().text()):
            result.append(self._word_tokenizer().tokenize(sent))
        assert None not in result
        return result

    def docno(self):
        """
        """
        result = self._sgmldoc().docno()
        assert result
        return result

    def doctype(self):
        """
        """
        result = self._sgmldoc().doctype()
        assert result
        return result

    def docsource(self):
        """
        """
        result = self._sgmldoc().docsource()
        assert result
        return result


class ACE2SGMLParser(SGMLParser):
    """
    """

    def __init__(self):
        """
        """
        SGMLParser.__init__(self)

    def reset(self):
        """
        """
        SGMLParser.reset(self)
        self._parsed = False
        self._text = None
        self._docno = None
        self._doctype = None
        self._docsource = None
        self._in = []

    def start_doc(self, attrs):
        """
        """
        self._in.insert(0, 'doc')

    def end_doc(self):
        """
        """
        self._in.remove('doc')

    def start_text(self, attrs):
        """
        """
        self._in.insert(0, 'text')
        self._text = ''

    def end_text(self):
        """
        """
        self._in.remove('text')
        self._text = self._text.strip()

    def start_docno(self, attrs):
        """
        """
        self._in.insert(0, 'docno')
        self._docno = ''

    def end_docno(self):
        """
        """
        self._in.remove('docno')
        self._docno = self._docno.strip()

    def start_doctype(self, attrs):
        """
        """
        self._in.insert(0, 'doctype')
        self._doctype = ''
        self._docsource = ''
        for k, v in attrs:
            if k == 'source':
                self._docsource = v 
                break

    def end_doctype(self):
        """
        """
        self._in.remove('doctype')
        self._doctype = self._doctype.strip()

    def handle_data(self, data):
        """
        """
        if self._in and self._in[0] == 'text':
            self._text += data
        if self._in and self._in[0] == 'docno':
            self._docno += data
        if self._in and self._in[0] == 'doctype':
            self._doctype += data

    def parse(self, filename):
        """
        """
        file = open(filename)
        for line in file:
            self.feed(line)
        file.close()
        self._parsed = True
        return self

    def text(self):
        """
        """
        assert self._parsed and self._text
        return self._text

    def docno(self):
        """
        """
        assert self._parsed and self._docno
        return self._docno

    def doctype(self):
        """
        """
        assert self._parsed and self._doctype
        return self._doctype

    def docsource(self):
        """
        """
        assert self._parsed and self._docsource
        return self._docsource


def _demo(root, file):
    """
    """
    from nltk_contrib.coref.ace2 import ACE2CorpusReader

    try:
        reader = ACE2CorpusReader(root, file)
        print 'Sentences for %s:' % (file)
        for sent in reader.sents():
            print '    %s' % (sent)
        print
        print 'Words for %s:' % (file)
        for word in reader.words():
            print '    %s' % (word)
        print
    except Exception, e:
        print 'Error encountered while running demo for %s: %s' % (file, e)
        print

def demo():
    """
    """
    import os
    import os.path

    try:
        ace2_dir = os.environ['ACE2_DIR']
    except KeyError:
        raise 'Demo requires ACE-2 Corpus, set ACE2_DIR environment variable!' 

    bnews_dir = os.path.join(ace2_dir, 'data/ace2_train/', 'bnews')
    _demo(bnews_dir, 'ABC19980106.1830.0029.sgm')

    npaper_dir = os.path.join(ace2_dir, 'data/ace2_train/', 'npaper')
    _demo(npaper_dir, '9801.139.sgm')

    nwire_dir = os.path.join(ace2_dir, 'data/ace2_train/', 'nwire')
    _demo(nwire_dir, 'APW19980213.1302.sgm')

if __name__ == '__main__':
    demo()
