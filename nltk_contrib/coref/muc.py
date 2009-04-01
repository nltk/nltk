# Natural Language Toolkit (NLTK) MUC-6 Corpus Reader
#
# Copyright (C) 2001-2009 NLTK Project 
# Author: Joseph Frazee <jfrazee@mail.utexas.edu>
# URL: http://nltk.org
# For license information, see LICENSE.TXT

"""
Corpus reader for the MUC-6 Corpus.
"""

from itertools import chain
from sgmllib import SGMLParser

from nltk.internals import Deprecated

from nltk.corpus.reader.api import *
from nltk.corpus.reader.util import *

from nltk.tokenize.punkt import *
from nltk.tokenize.regexp import *
from nltk.tokenize.simple import *

class MUC6CorpusReader(CorpusReader):
    """
    A corpus reader for MUC6 SGML files.  Each file begins with a preamble
    of SGML-tagged metadata.  The document text follows.  The text of the 
    document is contained in <TXT> tags.  Paragraphs are contained in <p> tags.  
    Sentences are contained in <s> tags.
    
    Additionally named entities and coreference mentions may be marked within 
    the document text and document metadata.  The MUC6 corpus provides
    named entity and coreference annotations in two separate sets of files.
    Only one kind of metadata will be returned depending on which kind of
    file is being read.
    
    Named entities are tagged as ENAMEX (name expressions), NUMEX 
    (number expressions), or TIMEX (time expressions), all of which include 
    TYPE attributes.  
    
    Coreference mentions are tagged as COREF and include ID, TYPE, REF, and 
    MIN attributes.  ID is used to give each coreference mention a unique 
    numeric idenitifier.  REF indicates the ID of the intended referent of the 
    coreference mention and is not required for first mentions.  MIN contains 
    the minimum coreferential string of the coreference mention.
    
    This class is a facade and all methods call similarly named methods in
    C{MUC6Document}. Each returns some possibly complete subset of the tuple
    (word, iob tag, NE type, coref id, coref type, coref ref, coref min).
    """
    def __init__(self, root, files):
        CorpusReader.__init__(self, root, files)
        
    def paras(self, files=None):
        return concat([MUC6Document(filename).paras()
                       for filename in self.abspaths(files)])
    
    def words(self, files=None):
        return concat([MUC6Document(filename).words()
                       for filename in self.abspaths(files)])
    
    def sents(self, files=None):
        return concat([MUC6Document(filename).sents()
                       for filename in self.abspaths(files)])
    
    def chunks(self, files=None):
        return concat([MUC6Document(filename).chunks()
                       for filename in self.abspaths(files)])
    
    def ne_words(self, files=None):
        return concat([MUC6Document(filename).ne_words()
                       for filename in self.abspaths(files)])
    
    def ne_sents(self, files=None):
        return concat([MUC6Document(filename).ne_sents()
                       for filename in self.abspaths(files)])
    
    def ne_chunks(self, files=None):
        return concat([MUC6Document(filename).ne_chunks()
                       for filename in self.abspaths(files)])
    
    def iob_words(self, files=None):
        return concat([MUC6Document(filename).iob_words()
                       for filename in self.abspaths(files)])
    
    def iob_sents(self, files=None):
        return concat([MUC6Document(filename).iob_sents()
                       for filename in self.abspaths(files)])
    
    def iob_chunks(self, files=None):
        return concat([MUC6Document(filename).iob_chunks()
                       for filename in self.abspaths(files)])
                       
    def coref_chunks(self, files=None):
        return concat([MUC6Document(filename).coref_chunks()
                       for filename in self.abspaths(files)])
                       
    def coref_sents(self, files=None):
        return concat([MUC6Document(filename).coref_sents()
                       for filename in self.abspaths(files)])                       
                       
    def coref_words(self, files=None):
        return concat([MUC6Document(filename).coref_words()
                       for filename in self.abspaths(files)])

    def coref_mentions(self, files=None):
        return concat([MUC6Document(filename).coref_mentions()
                       for filename in self.abspaths(files)])                    
                       

# TODO: At some point it'd be nice to replace this with a class that doesn't 
# use SGMLParser.  It's slow and the StreamBackedCorpusReader does some nice
# things.
class MUC6Document(str):
    """A helper class for reading individual MUC6 documents."""
    def __init__(self, path):
        str.__init__(self, path)
        self._sgmldoc_ = None

    # Lazy-loade the SGML doc.  I.e. if the document is loaded and never read
    # from, don't bother parsing it because parsing is rather slow.
    def _sgmldoc(self):
        if self._sgmldoc_:
            return self._sgmldoc_
        self._sgmldoc_ = MUC6SGMLParser().parse(self)
        return self._sgmldoc_

    def paras(self):
        result = []
        for para in self._sgmldoc().text():
            sents = []
            for sent in para:
                sents.append([word for chunk in sent for word in chunk.split()])
            result.append(sents)
        assert None not in result
        return result
        
    def words(self):
        result = list(chain(*self.sents()))
        assert None not in result
        return result

    def sents(self):
        result = list(chain(*self.paras()))
        assert None not in result
        return result

    def chunks(self):
        result = list(chain(*chain(*self._sgmldoc().text())))
        assert None not in result
        return result
    
    def ne_chunks(self):
        result = []
        for chunk in self.coref_chunks():
            if isinstance(chunk, tuple):
                result.append(chunk[:3])
            elif isinstance(chunk, list):
                result.append([token[:3] for token in chunk])
            else:
                raise
        assert None not in result
        return result
    
    def ne_sents(self):
        result = []
        for sent in self.coref_sents():
            result.append([token[:3] for token in sent])
        assert None not in result
        return result
    
    def ne_words(self):
        result = list(chain(*self.ne_sents()))
        assert None not in result
        return result
    
    def iob_chunks(self):
        result = []
        for chunk in self.coref_chunks():
            if isinstance(chunk, tuple):
                result.append(chunk[:2])
            elif isinstance(chunk, list):
                result.append([token[:2] for token in chunk])
            else:
                raise
        assert None not in result
        return result
    
    def iob_sents(self):
        result = []
        for sent in self.coref_sents():
            result.append([token[:2] for token in sent])
        assert None not in result
        return result
    
    def iob_words(self):
        result = list(chain(*self.iob_sents()))
        assert None not in result
        return result

    def coref_chunks(self):
        result = []
        for chunk in self.chunks():
            if chunk.iob_tag() == MUC6Mention.OUT:
                result.append((str(chunk), chunk.iob_tag(), chunk.ne_type(),
                               chunk.id(), chunk.coref_type(), chunk.ref(), 
                               chunk.min()))
            else:
                result.append([(str(word), word.iob_tag(), word.ne_type(),
                                word.id(), word.coref_type(), word.ref(), 
                                word.min()) 
                               for word in chunk.split()])
        assert None not in result
        return result
        
    def coref_sents(self):
        result = []
        for sent in self.sents():
            result.append([(word, word.iob_tag(), word.ne_type(), word.id(), 
                            word.coref_type(), word.ref(), word.min()) 
                           for word in sent])
        assert None not in result
        return result
        
    def coref_words(self):
        result = list(chain(*self.coref_sents()))
        assert None not in result
        return result        
    
    def coref_mentions(self):
        result = []
        for chunk in self.chunks():
            if chunk.is_coref():
                result.append((str(chunk), chunk.iob_tag(), chunk.ne_type(),
                               chunk.id(), chunk.coref_type(), chunk.ref(), 
                               chunk.min()))                 
        assert None not in result
        return result
                
    def docno(self):
        result = self._sgmldoc().docno()
        assert result
        return result


class MUC6Mention(str):
    """
    A helper class for keeping track of and operating on named entities, 
    mentions, and their attributes during parsing and reading.  Tuples are 
    a bit clumsy for the number of attributes and there are various tasks
    in parsing and reading the require concatenating and splitting named
    entities and mentions.
    
    C{MUC6Mention} subclasses C{str} so C{MUC6SGMLParser} can be used as if it
    returns nothing more than C{str} objects.
    """
    IN = 'I'
    OUT = 'O'
    BEGINS = 'B'    

    # This is a hack to allow a str subclass that takes **kwargs in its
    # __init__() signature.
    def __new__(self, s, **kwargs):
        return str.__new__(self, s)

    def __init__(self, s, **kwargs):
        """
        Creates a MUC6Mention instance.
        
        @param s: the underlying string
        @type s: C{str}
        @kwparam iob: the IOB symbol, 'I', 'O', or 'B'
        @type iob: C{str}
        @kwparam ne_type: the named entity type
        @type ne_type: C{str}
        @kwparam id: the coreference unique identifier
        @type id: C{str}
        @kwparam type: the coreference type
        @type type: C{str}
        @kwparam ref: the mention's intended referent identifier
        @type ref: C{str}
        @kwparam min: the minimum coreferential string
        @type min: C{str}
        """
        self._iob = kwargs.get('iob')
        self._ne_type = kwargs.get('ne_type')
        self._id = kwargs.get('id')
        self._type = kwargs.get('type')
        self._ref = kwargs.get('ref')
        self._min = kwargs.get('min')

    def __add__(self, y):
        return MUC6Mention(str.__add__(self, y), iob=self._iob, 
                ne_type=self._ne_typ, id=self._id, type=self._type, 
                ref=self._ref, min=self._min)

    def iob_tag(self):
        """
        The mention IOB symbol, 'I', 'O', or 'B'.
        
        @return: an IOB symbol
        @rtype: C{str}
        """
        return self._iob

    def ne_type(self):
        """
        The mention named entity type.
        
        @return: a named entity type
        @rtype: C{str}        
        """
        return self._ne_type
        
    def id(self):
        """
        The mention coreference unique identifier.
        
        @return: a coreference id
        @rtype: C{str}        
        """
        return self._id
    
    def coref_type(self):
        """
        The mention coreference type.
        
        @return: a coreference type
        @rtype: C{str}        
        """        
        return self._type
    
    def ref(self):
        """
        The mention intended reference identifier.
        
        @return: a referent id
        @rtype: C{str}        
        """        
        return self._ref
    
    def min(self):
        """
        The mention minimum coreferential string.
        
        @return: a minimum coreferential string
        @rtype: C{str}        
        """        
        return self._min
        
    def is_coref(self):
        """
        Whether the mention is coreferential.  All strings in the reader are
        handled as mention objects so some are not coreferential.
        
        @return: mention coreferential flag
        @rtype: C{bool}        
        """        
        return bool(self._id)

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
            result.append(MUC6Mention(token, iob=iob_tag, 
                ne_type=self._ne_type, id=self._id, type=self._type, 
                ref=self._ref, min=self._min))
        return result
        
        
class MUC6NamedEntity(MUC6Mention, Deprecated):
    """Use C{MUC6Mention} instead."""
    def __new__(self, s, iob, ne_type):
        return str.__new__(self, s)

    def __init__(self, s, iob, ne_type):
        MUC6Mention(s, iob=iob, ne_type=ne_type)

class MUC6SGMLParser(SGMLParser):
    """
    An C{SGMLParser} for MUC6 corpus files.
    """
    def __init__(self):
        """Create a C{MUC6SGMLParser} instance."""
        SGMLParser.__init__(self)
    
    def reset(self):
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
        self._coref_id = None
        self._coref_type = None
        self._coref_ref = None
        self._coref_min = None                
        self._in = []

    def start_doc(self, attrs):
        self._in.insert(0, 'doc')

    def end_doc(self):
        self._in.remove('doc')

    def start_hl(self, attrs):
        self._in.insert(0, 'hl')
        self._headline = ''

    def end_hl(self):
        self._headline = self._headline.strip()
        self._in.remove('hl')

    def start_so(self, attrs):
        self._in.insert(0, 'so')
        self._source = ''

    def end_so(self):
        self._source = self._source.strip()
        self._in.remove('so')

    def start_txt(self, attrs):
        self._in.insert(0, 'txt')

    def end_txt(self):
        self._in.remove('txt')

    def start_docno(self, attrs):
        self._in.insert(0, 'docno')
        self._docno = ''

    def end_docno(self):
        self._docno = self._docno.strip()
        self._in.remove('docno')

    def start_p(self, attrs):
        self._in.insert(0, 'p')
        if self._p == None:
            self._p = []

    def end_p(self):
        self._p.append(self._s)
        self._s = None
        self._in.remove('p')

    def start_s(self, attrs):
        self._in.insert(0, 's')
        if self._s == None:
            self._s = []
        self._chunks = []
        self._current = ''

    def end_s(self):
        if self._current.strip():
            self._chunks.extend(MUC6Mention(self._current.strip(), 
                iob=MUC6Mention.OUT, ne_type=self._ne_type).split())
        if self._chunks:
            self._s.append(self._chunks)
        self._chunks = None
        self._current = None
        self._in.remove('s')

    def start_enamex(self, attrs):
        if self._in and 's' in self._in[0]:
            if self._current.strip():
                self._chunks.extend(MUC6Mention(self._current.strip(), 
                    iob=MUC6Mention.OUT, ne_type=self._ne_type).split())
            self._in.insert(0, 'enamex')
            self._current = ''
            for attr in attrs:
                if attr[0] == 'type':
                    self._ne_type = attr[1]
                    break

    def end_enamex(self):
        if self._in and self._in[0] == 'enamex':
            if self._current.strip():
                self._chunks.append(MUC6Mention(self._current.strip(), 
                    iob=MUC6Mention.BEGINS, ne_type=self._ne_type))
            self._ne_type = None
            self._current = ''
            self._in.remove('enamex')

    def start_numex(self, attrs):
        if self._in and 's' in self._in[0]:
            if self._current.strip():
                self._chunks.extend(MUC6Mention(self._current.strip(), 
                    iob=MUC6Mention.OUT, ne_type=self._ne_type).split())
            self._in.insert(0, 'numex')
            self._current = ''
            for attr in attrs:
                if attr[0] == 'type':
                    self._ne_type = attr[1]
                    break

    def end_numex(self):
        if self._in and self._in[0] == 'numex':
            if self._current.strip():
                self._chunks.append(MUC6Mention(self._current.strip(), 
                    iob=MUC6Mention.BEGINS, ne_type=self._ne_type))
            self._ne_type = None
            self._current = ''
            self._in.remove('numex')

    def start_timex(self, attrs):
        if self._in and 's' in self._in[0]:
            if self._current.strip():
                self._chunks.extend(MUC6Mention(self._current.strip(), 
                    iob=MUC6Mention.OUT, ne_type=self._ne_type).split())
            self._in.insert(0, 'timex')
            self._current = ''
            for attr in attrs:
                if attr[0] == 'type':
                    self._ne_type = attr[1]
                    break

    def end_timex(self):
        if self._in and self._in[0] == 'timex':
            if self._current.strip():
                self._chunks.append(MUC6Mention(self._current.strip(), 
                    iob=MUC6Mention.BEGINS, ne_type=self._ne_type))
            self._ne_type = None
            self._current = ''
            self._in.remove('timex')

    def start_coref(self, attrs):
        if self._in and 's' in self._in[0]:
            if self._current.strip():
                self._chunks.extend(MUC6Mention(self._current.strip(),
                    iob=MUC6Mention.OUT, id=self._coref_id, 
                    type=self._coref_type, ref=self._coref_ref,
                    min=self._coref_min).split())
            self._in.insert(0, 'coref')
            self._current = ''
            for attr in attrs:
                if attr[0] == 'type':
                    self._coref_type = attr[1]
                elif attr[0] == 'id':
                    self._coref_id = attr[1]
                elif attr[0] == 'ref':
                    self._coref_ref = attr[1]                    
                elif attr[0] == 'min':
                    self._coref_min = attr[1]                    

    def end_coref(self):
        if self._in and self._in[0] == 'coref':
            if self._current.strip():
                self._chunks.append(MUC6Mention(self._current.strip(),
                    iob=MUC6Mention.BEGINS, id=self._coref_id,
                    type=self._coref_type, ref=self._coref_ref,
                    min=self._coref_min))
            self._coref_id = None
            self._coref_type = None
            self._coref_ref = None
            self._coref_min = None                        
            self._current = ''
            self._in.remove('coref')

    def handle_data(self, data):
        if self._in and self._in[0] == 'hl':
            self._headline += data
        if self._in and self._in[0] == 'so':
            self._source += data
        if self._in and self._in[0] == 'docno':
            self._docno += data
        if self._in and self._in[0] in ['s', 'enamex', 'numex', 'timex', 'coref']:
            self._current += data.replace('\n', '')

    def parse(self, filename):
        file = open(filename)
        for line in file:
            self.feed(line)
        file.close()
        self._parsed = True
        return self

    def text(self):
        """
        The text of the parsed MUC6 corpus document.
        
        @return: the file text
        @rtype: C{list} of C{list} of C{MUC6Mention}
        """
        assert self._parsed and self._p
        return self._p

    def docno(self):
        """
        The MUC6 corpus document document number.
        
        @return: document number
        @rtype: C{str}
        """
        assert self._parsed and self._docno
        return self._docno

    def headline(self):
        """
        The MUC6 corpus document headline.
        
        @return: document headline
        @rtype: C{str}
        """
        assert self._parsed and self._headline
        return self._headline

    def source(self):
        """
        The MUC6 corpus document source.
        
        @return: document source
        @rtype: C{str}
        """
        assert self._parsed and self._source
        return self._source

def _demo(root, file):
    import os.path
    from nltk_contrib.coref.muc6 import MUC6CorpusReader
    from nltk_contrib.coref.muc6 import MUC6NamedEntity

    reader = MUC6CorpusReader(root, file)
    print 'Paragraphs for %s:' % (file)
    for (index, para) in enumerate(reader.paras()):
        if index <= 3:
            print '    %s' % (para)
            print
    print 'Sentences for %s:' % (file)
    for (index, sent) in enumerate(reader.coref_sents()):
        if index <= 5:
            print '    %s' % (sent)
    print
    print 'Chunks for %s:' % (file)
    for (index, chunk) in enumerate(reader.coref_chunks()):
        if index <= 50:
            print chunk
    print
    print 'Mentions for %s:' % (file)
    for (index, mention) in enumerate(reader.coref_mentions()):
        if index <= 50:
            print '    ', mention
    print    
    print 'Words for %s:' % (file)
    for (index, word) in enumerate(reader.coref_words()):
        if index <= 50:
            print '    ', word
    print

def demo():
    import os
    import os.path

    try:
        muc6_ne_dir = os.environ['MUC6_NE_DIR']
        muc6_co_dir = os.environ['MUC6_CO_DIR']
    except KeyError:
        raise 'Demo requires MUC-6 Corpus, set MUC6_NE_DIR and ', \
              'MUC6_CO_DIR environment variables!' 

    _demo(muc6_ne_dir, ['891101-0080.ne.v1.3.sgm'])
    _demo(muc6_co_dir, ['891101-0090.co.v2.0.sgm'])

if __name__ == '__main__':
    demo()
