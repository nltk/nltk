# Natural Language Toolkit (NLTK) MUC-6 Corpus Reader
#
# Copyright (C) 2008 Joseph Frazee
# Author: Joseph Frazee <jfrazee@mail.utexas.edu>
# URL: http://nltk.org
# For license information, see LICENSE.TXT

"""
Corpus reader for the MUC-6 Corpus.

"""

from sgmllib import SGMLParser

from nltk.corpus.reader.api import *
from nltk.corpus.reader.util import *

from nltk.tokenize.punkt import *
from nltk.tokenize.regexp import *
from nltk.tokenize.simple import *


class MUC6CorpusReader(CorpusReader):
    """
    """

    def __init__(self, root, files):
        CorpusReader.__init__(self, root, files)

    def words(self, files=None):
        """
        """
        return concat([MUC6Document(filename).words()
                       for filename in self.abspaths(files)])

    def sents(self, files=None):
        """
        """
        return concat([MUC6Document(filename).sents()
                       for filename in self.abspaths(files)])

    def paras(self, files=None):
        """
        """
        return concat([MUC6Document(filename).paras()
                       for filename in self.abspaths(files)])


class MUC6Document(str):
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
        self._sgmldoc_ = MUC6SGMLParser().parse(self)
        return self._sgmldoc_

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
            for s in p:
                sent.append(self._word_tokenizer().tokenize(s))
            result.append(sent)
        assert None not in result
        return result

    def docno(self):
        """
        """
        result = self._sgmldoc().docno()
        assert result
        return result


class MUC6SGMLParser(SGMLParser):
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
        self._docno = None
        self._headline = None
        self._source = None
        self._p = None
        self._s = None
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

    def start_hl(self, attrs):
        """
        """
        self._in.insert(0, 'hl')
        self._headline = ''

    def end_hl(self):
        """
        """
        self._headline = self._headline.strip()
        self._in.remove('hl')

    def start_so(self, attrs):
        """
        """
        self._in.insert(0, 'so')
        self._source = ''

    def end_so(self):
        """
        """
        self._source = self._source.strip()
        self._in.remove('so')

    def start_txt(self, attrs):
        """
        """
        self._in.insert(0, 'txt')

    def end_txt(self):
        """
        """
        self._in.remove('txt')

    def start_docno(self, attrs):
        """
        """
        self._in.insert(0, 'docno')
        self._docno = ''

    def end_docno(self):
        """
        """
        self._docno = self._docno.strip()
        self._in.remove('docno')

    def start_p(self, attrs):
        """
        """
        self._in.insert(0, 'p')
        if self._p == None:
            self._p = []

    def end_p(self):
        """
        """
        self._p.append(self._s)
        self._s = None
        self._in.remove('p')

    def start_s(self, attrs):
        """
        """
        self._in.insert(0, 's')
        if self._s == None:
            self._s = []
        self._current = ''

    def end_s(self):
        """
        """
        self._s.append(self._current.strip())
        self._current = None
        self._in.remove('s')

    def handle_data(self, data):
        """
        """
        if self._in and self._in[0] == 'hl':
            self._headline += data
        if self._in and self._in[0] == 'so':
            self._source += data
        if self._in and self._in[0] == 'docno':
            self._docno += data
        if self._in and self._in[0] == 's':
            self._current += data.replace('\n', '')

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

    def docno(self):
        """
        """
        assert self._parsed and self._docno
        return self._docno

    def headline(self):
        """
        """
        assert self._parsed and self._headline
        return self._headline

    def source(self):
        """
        """
        assert self._parsed and self._source
        return self._source

def _demo(root, file):
    """
    """
    import os.path
    from nltk_contrib.coref.ace2 import ACE2CorpusReader

    try:
        reader = MUC6CorpusReader(root, file)
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
        muc6_dir = os.environ['MUC6_DIR']
    except KeyError:
        raise 'Demo requires MUC-6 Corpus, set MUC6_DIR environment variable!' 

    _demo(muc6_dir, 'dryrun-trng01.muc6')

if __name__ == '__main__':
    demo()
