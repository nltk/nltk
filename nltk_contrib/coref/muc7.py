# Natural Language Toolkit (NLTK) MUC-7 Corpus Reader
#
# Copyright (C) 2001-2009 NLTK Project 
# Author: Joseph Frazee <jfrazee@mail.utexas.edu>
# URL: http://nltk.org
# For license information, see LICENSE.TXT

"""
Corpus reader for the MUC-7 Corpus.

"""

from sgmllib import SGMLParser

from nltk.corpus.reader.api import *
from nltk.corpus.reader.util import *

from nltk.tokenize.punkt import *
from nltk.tokenize.regexp import *
from nltk.tokenize.simple import *


class MUC7CorpusReader(CorpusReader):
    """
    """

    def __init__(self, root, files):
        CorpusReader.__init__(self, root, files)

    def words(self, files=None):
        """
        """
        return concat([MUC7Document(filename).words()
                       for filename in self.abspaths(files)])

    def sents(self, files=None):
        """
        """
        return concat([MUC7Document(filename).sents()
                       for filename in self.abspaths(files)])

    def paras(self, files=None):
        """
        """
        return concat([MUC7Document(filename).paras()
                       for filename in self.abspaths(files)])


class MUC7Document(str):
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
        self._sgmldoc_ = MUC7SGMLParser().parse(self)
        return self._sgmldoc_

    def _sent_tokenizer(self):
        """
        """
        return PunktSentenceTokenizer()

    def _word_tokenizer(self):
        """
        """
        return PunktWordTokenizer()

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
        for p in self.paras():
            result.extend(p)
        assert None not in result
        return result

    def paras(self):
        """
        """
        result = []
        for p in self._sgmldoc().text():
            sent = []
            for s in self._sent_tokenizer().tokenize(p):
                sent.append(self._word_tokenizer().tokenize(s))
            result.append(sent)
        assert None not in result
        return result

    def docid(self):
        """
        """
        result = self._sgmldoc().docid()
        assert result
        return result

    def preamble(self):
        """
        """
        result = self._sgmldoc().preamble()
        assert result
        return result

    def trailer(self):
        """
        """
        result = self._sgmldoc().trailer()
        assert result
        return result


class MUC7SGMLParser(SGMLParser):
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
        self._docid = None
        self._preamb = None
        self._p = None
        self._trailer = None
        self._current = None
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

    def end_text(self):
        """
        """
        if self._in and self._in[0] == 'p':
            self._p.append(self._current)
            self._current = None
            self._in.remove('p')
        self._in.remove('text')

    def start_docid(self, attrs):
        """
        """
        self._in.insert(0, 'docid')
        self._docid = ''

    def end_docid(self):
        """
        """
        self._docid = self._docid.strip()
        self._in.remove('docid')

    def start_preamble(self, attrs):
        """
        """
        self._in.insert(0, 'preamble')
        self._preamb = ''

    def end_preamble(self):
        """
        """
        self._preamb = self._preamb.strip() 
        self._in.remove('preamble')

    def start_p(self, attrs):
        """
        """
        if self._in and self._in[0] == 'p':
            self._p.append(self._current)
            self._current = None
            self._in.remove('p')
        self._in.insert(0, 'p')
        if self._p == None:
            self._p = []
        self._current = ''

    def start_trailer(self, attrs):
        """
        """
        self._in.insert(0, 'trailer')
        self._trailer = ''

    def end_trailer(self):
        """
        """
        self._trailer = self._trailer.strip()
        self._in.remove('trailer')

    def handle_data(self, data):
        """
        """
        if self._in and self._in[0] == 'docid':
            self._docid += data
        if self._in and self._in[0] == 'preamble':
            self._preamb += data.replace('\n', '')
        if self._in and self._in[0] == 'p':
            self._current += data.replace('\n', '')
        if self._in and self._in[0] == 'trailer':
            self._trailer += data.replace('\n', '')

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
        assert self._parsed and self._p
        return self._p

    def docid(self):
        """
        """
        assert self._parsed and self._docid
        return self._docid

    def preamble(self):
        """
        """
        assert self._parsed and self._preamb
        return self._preamb

    def trailer(self):
        """
        """
        assert self._parsed and self._trailer
        return self._trailer

def _demo(root, file):
    """
    """
    import os.path
    from nltk_contrib.coref.ace2 import ACE2CorpusReader

    try:
        reader = MUC7CorpusReader(root, file)
        print 'Paragraphs for %s:' % (file)
        for para in reader.paras():
            print '    %s' % (para)
            print
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
        muc7_dir = os.environ['MUC7_DIR']
    except KeyError:
        raise 'Demo requires MUC-7 Corpus, set MUC7_DIR environment variable!' 

    _demo(muc7_dir, 'dryrun01.muc7')

if __name__ == '__main__':
    demo()
