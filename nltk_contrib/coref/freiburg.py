# Natural Language Toolkit (NLTK) Freiburg Corpora Reader
#
# Copyright (C) 2001-2009 NLTK Project 
# Author: Joseph Frazee <jfrazee@mail.utexas.edu>
# URL: http://nltk.org
# For license information, see LICENSE.TXT

"""
Corpus reader for the Freiburg Corpora.

"""

from sgmllib import SGMLParser

from nltk.corpus.reader.api import *
from nltk.corpus.reader.util import *

from nltk.tokenize.punkt import *
from nltk.tokenize.regexp import *
from nltk.tokenize.simple import *


class FreiburgCorpusReader(CorpusReader):
    """
    """

    def __init__(self, root, files):
        CorpusReader.__init__(self, root, files)

    def words(self, files=None):
        """
        """
        return concat([FreiburgDocument(filename).words()
                       for filename in self.abspaths(files)])

    def sents(self, files=None):
        """
        """
        return concat([FreiburgDocument(filename).sents()
                       for filename in self.abspaths(files)])

    def paras(self, files=None):
        """
        """
        return concat([FreiburgDocument(filename).paras()
                       for filename in self.abspaths(files)])


class FreiburgDocument(str):
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
        self._sgmldoc_ = FreiburgSGMLParser().parse(self)
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
        result = self._sgmldoc().paras()
        assert result
        return result


class FreiburgToken(str):
    """
    """

    def __init__(self, token):
        """
        """
        str.__init__(self, token)
        self._pos = None

    def set_pos(self, pos):
        """
        """
        self._pos = pos
        return self

    def pos(self):
        """
        """
        return self._pos


class FreiburgSGMLParser(SGMLParser):
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
        self._s = None
        self._p = None
        self._current = None
        self._current_pos = None
        self._in = []

    def start_p(self, attrs):
        """
        """
        if 'p' in self._in:
            self.start_s(None)
            if self._s:
                self._p.append(self._s)
                self._s = None
            self._in.remove('p')
        self._in.insert(0, 'p')
        if not self._p:
            self._p = []
        self._s = []

    def start_head(self, attrs):
        """
        """
        self.start_p(None)

    def start_s(self, attrs):
        """
        """
        if 's' in self._in:
            if self._current:
                self._s.append(self._current) 
                self._current = None
            self._in.remove('s')
        self._in.insert(0, 's')
        if not self._s:
            self._s = []
        self._current = []

    def start_w(self, attrs):
        """
        """
        self._in.insert(0, 'w')
        if attrs:
            self._current_pos = attrs[0][1]

    def start_c(self, attrs):
        """
        """
        self._in.insert(0, 'c')
        if attrs:
            self._current_pos = attrs[0][1]

    def start_text(self, attrs):
        """
        """
        pass

    def end_text(self):
        """
        """
        self.start_p(None)

    def handle_data(self, data):
        """
        """
        if self._in and 'w' == self._in[0]:
            token = FreiburgToken(data.rstrip()).set_pos(self._current_pos)
            self._current.append(token)
            self._current_pos = None
            self._in.remove('w')
        if self._in and 'c' == self._in[0]:
            token = FreiburgToken(data.rstrip()).set_pos(self._current_pos)
            self._current.append(token)
            self._current_pos = None
            self._in.remove('c')

    def parse(self, filename):
        """
        """
        file = open(filename)
        for line in file:
            self.feed(line)
        file.close()
        self._parsed = True
        return self

    def paras(self):
        """
        """
        assert self._parsed and self._p
        return self._p


def _demo(root, file):
    """
    """
    import os.path
    from nltk_contrib.coref.ace2 import ACE2CorpusReader

    try:
        reader = FreiburgCorpusReader(root, file)
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
            print '    %s/%s' % (word, word.pos())
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
        fb_dir = os.environ['FREIBURG_DIR']
    except KeyError:
        raise 'Demo requires Freiburg Corpus, set FREIBURG_DIR environment variable!' 

    brown_dir = os.path.join(fb_dir, 'BROWN')
    _demo(brown_dir, 'R.txt')

    frown_dir = os.path.join(fb_dir, 'FROWN')
    _demo(frown_dir, 'FROWN_R.txt')

    flob_dir = os.path.join(fb_dir, 'F-LOB')
    _demo(flob_dir, 'F-LOB_R.txt')

if __name__ == '__main__':
    demo()
