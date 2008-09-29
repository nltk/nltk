# Natural Language Toolkit (NLTK) MUC-6 Corpus Reader
#
# Copyright (C) 2008 NLTK Project 
# Author: Joseph Frazee <jfrazee@mail.utexas.edu>
# URL: http://nltk.org
# For license information, see LICENSE.TXT

"""
Corpus reader for the MUC-6 Corpus.

"""

from itertools import chain
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
        
    def _doc_method(self, method):
        return lambda files=None: \
            concat([getattr(MUC6Document(filename), method)() \
                for filename in self.abspaths(files)])
    
    def __getattr__(self, name):
        if name != '_doc_method':
            return self._doc_method(name)
                       

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

    def paras(self):
        """
        """
        result = []
        for para in self._sgmldoc().text():
            sents = []
            for sent in para:
                sents.append([word for chunk in sent for word in chunk.split()])
            result.append(sents)
        assert None not in result
        return result
        
    def words(self):
        """
        """
        result = list(chain(*self.sents()))
        assert None not in result
        return result

    def sents(self):
        """
        """
        result = list(chain(*self.paras()))
        assert None not in result
        return result

    def chunks(self):
        """
        """
        result = list(chain(*chain(*self._sgmldoc().text())))
        assert None not in result
        return result

    def ne_chunks(self):
        """
        """
        result = []
        for chunk in self.chunks():
            if chunk.iob_tag() == MUC6NamedEntity.OUT:
                result.append((str(chunk), chunk.iob_tag(), chunk.ne_type()))
            else:
                result.append([(str(word), word.iob_tag(), word.ne_type()) 
                               for word in chunk.split()])
        assert None not in result
        return result

    def ne_sents(self):
        """
        """
        result = []
        for sent in self.sents():
            result.append([(word, word.iob_tag(), word.ne_type()) 
                           for word in sent])
        assert None not in result
        return result

    def ne_words(self):
        """
        """
        result = list(chain(*self.ne_sents()))
        assert None not in result
        return result
            
    def iob_chunks(self):
        result = []
        for chunk in self.ne_chunks():
            result.append([(word, iob_tag) for (word, iob_tag, ne_type) in chunk])
        assert None not in result
        return result

    def iob_sents(self):
        result = []
        for sent in self.ne_sents():
            result.append([(word, iob_tag) 
                           for (word, iob_tag, ne_type) in sent])
        assert None not in result
        return result
    
    def iob_words(self):
        result = list(chain(*self.iob_sents()))
        
    def docno(self):
        """
        """
        result = self._sgmldoc().docno()
        assert result
        return result


class MUC6Mention(str):
    """
    """

    IN = 'I'
    OUT = 'O'
    BEGINS = 'B'

    def __new__(self, s, **kwargs):
        return str.__new__(self, s)

    def __init__(self, s, **kwargs):
        mention_properties = ['ne_type', 'id', 'coref_type', 'coref_id', 'min']
        self._properties = \
            dict([(key, kwargs.get(key)) for key in mention_properties])

    def __add__(self, y):
        return MUC6NamedEntity(str.__add__(self, y),
                               self.iob_tag(), self.ne_type())

    def iob_tag(self):
        return self._iob

    def ne_type(self):
        return self._ne_type

    def split(self, sep=None, maxsplit=-1):
        if not sep:
            tokens = PunktWordTokenizer().tokenize(self)
        else:
            tokens = self.split(sep, maxsplit)
        result = []
        for (index, token) in enumerate(tokens):
            if self.iob_tag() == self.OUT:
                iob_tag = self.OUT
            elif self.iob_tag() == self.BEGINS and index == 0:
                iob_tag = self.BEGINS
            else:
                iob_tag = self.IN
            result.append(MUC6NamedEntity(token, iob_tag, self.ne_type()))
        return result


class MUC6Mention(str):
    """
    """

    IN = 'I'
    OUT = 'O'
    BEGINS = 'B'

    def __new__(self, s, **kwargs):
        return str.__new__(self, s)

    def __init__(self, s, **kwargs):
        mention_properties = ['ne_type', 'id', 'coref_type', 'coref_id', 'min']
        self._properties = \
            dict([(key, kwargs.get(key)) for key in mention_properties])

    def __add__(self, y):
        return MUC6NamedEntity(str.__add__(self, y), 
                               self.iob_tag(), self.ne_type())

    def properties(self):
        return properties.copy()

    # Dictionary mix-in ?
        
    def iob_tag(self):
        return self._iob

    def ne_type(self):
        return self._ne_type

    def split(self, sep=None, maxsplit=-1):
        if not sep:
            tokens = PunktWordTokenizer().tokenize(self)
        else:
            tokens = self.split(sep, maxsplit)
        result = []
        for (index, token) in enumerate(tokens):
            if self.iob_tag() == self.OUT:
                iob_tag = self.OUT
            elif self.iob_tag() == self.BEGINS and index == 0:
                iob_tag = self.BEGINS
            else:
                iob_tag = self.IN
            result.append(MUC6NamedEntity(token, iob_tag, self.ne_type()))
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
        self._chunks = None
        self._current = None
        self._ne_type = None
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
        self._chunks = []
        self._current = ''

    def end_s(self):
        """
        """
        if self._current.strip():
            self._chunks.append(MUC6NamedEntity(self._current.strip(), 
                MUC6NamedEntity.OUT, self._ne_type))
        if self._chunks:
            self._s.append(self._chunks)
        self._chunks = None
        self._current = None
        self._in.remove('s')

    def start_enamex(self, attrs):
        """
        """
        if self._in and 's' in self._in[0]:
            if self._current.strip():
                self._chunks.extend(MUC6NamedEntity(self._current.strip(), 
                    MUC6NamedEntity.OUT, self._ne_type).split())
            self._in.insert(0, 'enamex')
            self._current = ''
            for attr in attrs:
                if attr[0] == 'type':
                    self._ne_type = attr[1]
                    break

    def end_enamex(self):
        """
        """
        if self._in and self._in[0] == 'enamex':
            if self._current.strip():
                self._chunks.append(MUC6NamedEntity(self._current.strip(), 
                    MUC6NamedEntity.BEGINS, self._ne_type))
            self._ne_type = None
            self._current = ''
            self._in.remove('enamex')

    def start_numex(self, attrs):
        """
        """
        if self._in and 's' in self._in[0]:
            if self._current.strip():
                self._chunks.extend(MUC6NamedEntity(self._current.strip(), 
                    MUC6NamedEntity.OUT, self._ne_type).split())
            self._in.insert(0, 'numex')
            self._current = ''
            for attr in attrs:
                if attr[0] == 'type':
                    self._ne_type = attr[1]
                    break

    def end_numex(self):
        """
        """
        if self._in and self._in[0] == 'numex':
            if self._current.strip():
                self._chunks.append(MUC6NamedEntity(self._current.strip(), 
                    MUC6NamedEntity.BEGINS, self._ne_type))
            self._ne_type = None
            self._current = ''
            self._in.remove('numex')

    def start_timex(self, attrs):
        """
        """
        if self._in and 's' in self._in[0]:
            if self._current.strip():
                self._chunks.extend(MUC6NamedEntity(self._current.strip(), 
                    MUC6NamedEntity.OUT, self._ne_type).split())
            self._in.insert(0, 'timex')
            self._current = ''
            for attr in attrs:
                if attr[0] == 'type':
                    self._ne_type = attr[1]
                    break

    def end_timex(self):
        """
        """
        if self._in and self._in[0] == 'timex':
            if self._current.strip():
                self._chunks.append(MUC6NamedEntity(self._current.strip(), 
                    MUC6NamedEntity.BEGINS, self._ne_type))
            self._ne_type = None
            self._current = ''
            self._in.remove('timex')

    def start_coref(self, attrs):
        """
        """
        if self._in and 's' in self._in[0]:
            if self._current.strip():
                self._chunks.extend(MUC6NamedEntity(self._current.strip(), 
                    MUC6NamedEntity.OUT, self._ne_type).split())
            self._in.insert(0, 'coref')
            self._current = ''
            for attr in attrs:
                if attr[0] == 'type':
                    self._ne_type = attr[1]
                    break

    def end_coref(self):
        """
        """
        if self._in and self._in[0] == 'coref':
            if self._current.strip():
                self._chunks.append(MUC6NamedEntity(self._current.strip(), 
                    MUC6NamedEntity.BEGINS, self._ne_type))
            self._ne_type = None
            self._current = ''
            self._in.remove('timex')

    def handle_data(self, data):
        """
        """
        if self._in and self._in[0] == 'hl':
            self._headline += data
        if self._in and self._in[0] == 'so':
            self._source += data
        if self._in and self._in[0] == 'docno':
            self._docno += data
        if self._in and self._in[0] in ['s', 'enamex', 'numex', 'timex', 'coref']:
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
    from nltk_contrib.coref.muc6 import MUC6CorpusReader
    from nltk_contrib.coref.muc6 import MUC6NamedEntity

    reader = MUC6CorpusReader(root, file)
    print 'Paragraphs for %s:' % (file)
    for para in reader.paras():
        print '    %s' % (para)
        print
    print 'Sentences for %s:' % (file)
    for sent in reader.sents():
        print '    %s' % (sent)
    print
    print 'Chunks for %s:' % (file)
    for chunk in reader.iob_chunks():
            print chunk
    print
    print 'Words for %s:' % (file)
    for word in reader.iob_words():
        print '    ', word
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

    _demo(muc6_dir, ['891101-0080.ne.v1.3.sgm'])

if __name__ == '__main__':
    demo()
