# Natural Language Toolkit (NLTK) MUC Corpus Reader
#
# Copyright (C) 2001-2009 NLTK Project 
# Author: Joseph Frazee <jfrazee@mail.utexas.edu>
#         Steven Bird <sb@csse.unimelb.edu.au> (original IEER Corpus Reader)
#         Edward Loper <edloper@gradient.cis.upenn.edu> (original IEER Corpus 
#         Reader)
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

# Adapted from nltk.corpus.reader.ieer.IEERCorpusReader

import re
import codecs

from itertools import chain

from nltk import Tree

from nltk.util import LazyMap, LazyConcatenation

from nltk.tokenize.treebank import TreebankWordTokenizer
from nltk.tokenize.punkt import PunktSentenceTokenizer

from nltk.corpus.util import LazyCorpusLoader

from nltk.corpus.reader.api import CorpusReader
from nltk.corpus.reader.util import concat, StreamBackedCorpusView

muc6_titles = {
    '891102-0189.ne.v1.3.sgm':'',
    '891102-0189.co.v2.0.sgm':'',
    '891101-0050.ne.v1.3.sgm':'',
}
muc6_documents = sorted(muc6_titles)

muc7_titles = {
    'dryrun01.muc7':'',
    'dryrun02.muc7':'',    
    'dryrun03.muc7':'',    
}
muc7_documents = sorted(muc7_titles)

_MUC_CHUNK_TYPES = [
    'DATE',
    'IDENT',
    'LOCATION',
    'MONEY',
    'ORGANIZATION',
    'PERCENT',
    'PERSON',
    'TIME'
]

_MUC6_DOC_RE = re.compile(
    r'\s*<DOC>\s*'
    r"""
     (\s*(<DOCNO>\s*(?P<docno>.+?)\s*</DOCNO>|
          <CODER>\s*.+?\s*</CODER>|
          <DD>\s*.+?\s*</DD>|
          <AN>\s*.+?\s*</AN>|
          <HL>\s*(?P<headline>.+?)\s*</HL>|
          <SO>\s*.+?\s*</SO>|
          <CO>\s*.+?\s*</CO>|
          <IN>\s*.+?\s*</IN>|
          <GV>\s*.+?\s*</GV>|
          <DATELINE>\s*(?P<dateline>.+?)\s*</DATELINE>)\s*)*
     """
    r'<TXT>\s*(?P<text>(<p>\s*(<s>\s*.+?\s*</s>)+\s*</p>)+)\s*</TXT>\s*'
    r'</DOC>\s*', re.DOTALL | re.I | re.VERBOSE)
_MUC6_PARA_RE = re.compile('(<p>\s*(?P<para>.+?)\s*</p>?)+', re.DOTALL | re.I)
_MUC6_SENT_RE = re.compile('(<s>\s*(?P<sent>.+?)\s*</s>)+', re.DOTALL | re.I)    

_MUC7_DOC_RE = re.compile(
    r'\s*<DOC>\s*'
    r"""
     (\s*(<DOCID>\s*(?P<docid>.+?)\s*</DOCID>|
           <STORYID\s+[^>]*?>\s*.+?\s*</STORYID>|      
           <SLUG\s+[^>]*?>\s*.+?\s*</SLUG>|          
           <DATE>\s*(?P<date>.+?)\s*</DATE>|         
           <NWORDS>\s*.+?\s*</NWORDS>|                    
           <PREAMBLE>\s*.+?\s*</PREAMBLE>)\s*)*
     """
    r'<TEXT>\s*(?P<text>.+?)\s*</TEXT>\s*'
    r'(<TRAILER>\s*(?P<trailer>.+?)\s*</TRAILER>\s*)?'
    r'</DOC>\s*', re.DOTALL | re.I | re.VERBOSE)
_MUC7_PARA_RE = re.compile(r'\s*<p>\s*.+?\s*(<p>\s*.+?\s*?)*\s*', re.DOTALL | re.I)
_MUC7_PARA_SPLIT_RE = re.compile(r'\s*<p>\s*', re.DOTALL | re.I)

_MUC_NE_B_RE = re.compile('<(ENAMEX|NUMEX|TIMEX)\s+[^>]*?TYPE="(?P<type>\w+)"', re.DOTALL | re.I)
_MUC_NE_E_RE = re.compile('</(ENAMEX|NUMEX|TIMEX)>', re.DOTALL | re.I)
_MUC_CO_B_RE = re.compile('<COREF\s+[^>]*?ID="(?P<id>\w+)"(\s+TYPE="(?P<type>\w+)")?(\s+REF="(?P<ref>\w+)")?', re.DOTALL | re.I)
_MUC_CO_E_RE = re.compile('</COREF>', re.DOTALL | re.I)

_WORD_TOKENIZER = TreebankWordTokenizer()
_SENT_TOKENIZER = PunktSentenceTokenizer()

class MUCDocument:
    # def __init__(self, text, docno=None, dateline=None, headline=''):
    def __init__(self, **text):
        self.text = None
        if isinstance(text, basestring):
            self.text = text
        elif isinstance(text, dict):
            for key, val in text.items():
                setattr(self, key, val)
        else:
            raise
        assert self.text
        
    def __repr__(self):
        if self.headline:
            headline = ' '.join(self.headline.leaves())
        else:
            headline = ' '.join([w for w in self.text.leaves()
                                 if w[:1] != '<'][:11])+'...'
        if self.docno is not None:            
            return '<MUCDocument %s: %r>' % (self.docno, headline)
        else:
            return '<MUCDocument: %r>' % headline

class MUCCorpusReader(CorpusReader):
    """
    A corpus reader for MUC SGML files.  Each file begins with a preamble
    of SGML-tagged metadata. The document text follows. The text of the 
    document is contained in <TXT> tags for MUC6 and <TEXT> tags for MUC7.
    Paragraphs are contained in <p> tags in both corpus formats. Sentences are
    contained in <s> tags in MUC6 only. For MUC7 corpus files L{sents()},
    L{chunked_sents()}, and L{iob_sents()} return sentences via tokenizing
    with C{PunktSentenceTokenizer}.
    
    Additionally named entities and coreference mentions may be marked within 
    the document text and document metadata. The MUC6 corpus provides
    named entity and coreference annotations in two separate sets of files.
    The MUC7 corpus contains coreference annotations only. Only one kind of 
    metadata will be returned depending on which kind of file is being read.
    
    Named entities are tagged as ENAMEX (name expressions), NUMEX 
    (number expressions), or TIMEX (time expressions), all of which include 
    TYPE attributes.  
    
    Coreference mentions are tagged as COREF and include ID, TYPE, REF, and 
    MIN attributes. ID is used to give each coreference mention a unique 
    numeric idenitifier. REF indicates the ID of the intended referent of the 
    coreference mention and is not required for first mentions. MIN contains 
    the minimum coreferential string of the coreference mention.
    """
    def raw(self, fileids=None):
        """
        @return: A list of corpus file contents.
        @rtype: C{list} of C{str}
        @param fileids: A list of corpus files.
        @type fileids: C{list} of C{str} or regular expression
        """
        if fileids is None:
            fileids = self._fileids
        elif isinstance(fileids, basestring): 
            fileids = [fileids]
        return concat([self.open(f).read() for f in fileids])

    def docs(self, fileids=None):
        """
        @return: A list of corpus document strings.
        @rtype: C{list} of C{StreamBackedCorpusView}
        @param fileids: A list of corpus files.
        @type fileids: C{list} of C{str} or regular expression
        """
        return concat([StreamBackedCorpusView(fileid, 
                                              self._read_block,
                                              encoding=enc)
                       for (fileid, enc) in self.abspaths(fileids, True)])

    def parsed_docs(self, fileids=None):
        """
        @return: A list of parsed corpus documents.
        @rtype: C{list} of C{StreamBackedCorpusView}
        @param fileids: A list of corpus files.
        @type fileids: C{list} of C{str} or regular expression
        """        
        return concat([StreamBackedCorpusView(fileid,
                                              self._read_parsed_block,
                                              encoding=enc)
                       for (fileid, enc) in self.abspaths(fileids, True)])
        
    def paras(self, fileids=None, **kwargs):
        """
        @return: A list of paragraphs.
        @rtype: C{list} of C{list} of C{list} of C{str}
        @param fileids: A list of corpus files.
        @type fileids: C{list} of C{str} or regular expression.
        """
        def __para(para):
            return [sent.leaves() for sent in list(para)]
        return LazyMap(__para, self._paras(fileids))
    
    def sents(self, fileids=None):
        """
        @return: A list of sentences.
        @rtype: C{list} of C{list} of C{str}
        @param fileids: A list of corpus files.
        @type fileids: C{list} of C{str} or regular expression        
        """
        return LazyConcatenation(self.paras(fileids))
        
    def chunked_sents(self, fileids=None, **kwargs):
        """
        @return: A list of sentence chunks as tuples of string/tag pairs.
        @rtype: C{list} of C{list} of C{tuple}
        @param fileids: A list of corpus files.
        @type fileids: C{list} of C{str} or regular expression 
        @kwparam depth: Depth of chunk parsing for nested chunks.
        @type depth: C{int}       
        """
        def __chunked_sent(sent):
            chunks = []
            # Map each sentence subtree into a tuple.
            for token in map(tree2tuple, sent):
                # If the token's contents is a list of chunk pieces, append it
                # as a list of word/tag pairs.
                if isinstance(token[0], list):
                    chunks.append([(word, None) for word in token[0]])
                # If the token's contents is a string, append it as a 
                # word/tag tuple.
                elif isinstance(token[0], basestring):
                    chunks.append((token[0], None))
                # Something bad happened.
                else:
                    raise
            return chunks
        depth = kwargs.get('depth', 0)        
        sents = self._chunked_sents(self._sents(fileids, **kwargs), depth)
        return LazyMap(__chunked_sent, sents)
        
    def iob_sents(self, fileids=None, **kwargs):
        """
        @return: A list of sentences as iob word/iob/other tag pairs.
        @rtype: C{list} of C{list} of C{tuple}
        @param fileids: A list of corpus files.
        @type fileids: C{list} of C{str} or regular expression 
        @kwparam depth: Depth of chunk parsing for nested chunks.
        @type depth: C{int}      
        """
        def __iob_sent(sent):
            chunks = []
            # Map each sentence subtree into a tuple.
            for token in map(tree2tuple, sent):
                # If the token has a chunk type, parse the token contents.
                if token[1] is not None:
                    for index, word in enumerate(token[0]):
                        # The first word in a chunk B-egins the chunk.
                        if index == 0:
                            chunks.append((word, 'B-%s' % token[1:2]) + token[2:])
                        # All other words in a chunk are I-n the chunk.
                        else:
                            chunks.append((word, 'I-%s' % token[1:2]) + token[2:])
                # If the token doesn't have a chunk type, it's O-ut.
                else:
                    chunks.append((token[0], 'O'))
            return chunks
        depth = kwargs.get('depth', 0)        
        sents = self._chunked_sents(self._sents(fileids), depth)          
        return LazyMap(__iob_sent, sents)
        
    def words(self, fileids=None):
        """
        @return: A list of words.
        @rtype: C{list} of C{str}
        @param fileids: A list of corpus files.
        @type fileids: C{list} of C{str} or regular expression 
        @kwparam depth: Depth of chunk parsing for nested chunks.
        @type depth: C{int}        
        """
        # Concatenate the list of lists given by sents().
        return LazyConcatenation(self.sents(fileids))
    
    def iob_words(self, fileids=None, **kwargs):
        """
        @return: A list of word/iob/other tag tuples.
        @rtype: C{list} of C{tuple}
        @param fileids: A list of corpus files.
        @type fileids: C{list} of C{str} or regular expression 
        @kwparam depth: Depth of chunk parsing for nested chunks.
        @type depth: C{int}        
        """
        # Concatenate the list of lists given by iob_sents().
        return LazyConcatenation(self.iob_sents(fileids, **kwargs))
        
    def chunks(self, fileids=None, **kwargs):
        """
        @return: A list of chunked sents where chunks are multi-word strings.
        @rtype: C{list} of C{list} of C{str}
        @param fileids: A list of corpus files.
        @type fileids: C{list} of C{str} or regular expression 
        @kwparam depth: Depth of chunk parsing for nested chunks.
        @type depth: C{int}        
        @kwparam concat: Concatenate sentence lists into one list; works like
            itertools.chain()
        @type concat: C{bool}
        """
        def __chunks(sent):
            chunks = []
            for token in sent:
                # If the token is a list of chunk pieces, append the piece's
                # contents as a string.                
                if isinstance(token, list):
                    # TODO: Better if able to reverse Treebank-style
                    # tokenization. The join leaves some weird whitespace.                    
                    chunks.append(' '.join([word[0] for word in token]))
                # If the token is a tuple, append the token's contents.
                elif isinstance(token, tuple):
                    chunks.append(token[0])
                # Something bad happened.
                else:
                    raise
            return chunks
        sents = self.chunked_sents(fileids, **kwargs) 
        # Concatenate the lists.          
        if kwargs.get('concat'):
            return LazyConcatenation(LazyMap(__chunks, sents))
        # Or not.
        else:
            return LazyMap(__chunks, sents)
        
    def mentions(self, fileids=None, **kwargs):
        """
        @return: A list of mentions as the tuple of 
            ([words...], id, referent, type)
        @rtype: C{list} of C{list} of C{tuple}
        @param fileids: A list of corpus files.
        @type fileids: C{list} of C{str} or regular expression 
        @kwparam depth: Depth of chunk parsing for nested chunks.
        @type depth: C{int}  
        @kwparam concat: Concatenate sentence lists into one list; works like
            itertools.chain(). Defaults to False.
        @type concat: C{bool}
        @kwparam nonmentions: Return nonmentions as well as mentions. Defaults
            to False.
        @type nonmentions: C{bool}              
        """
        def __mentions(sent):
            mentions = []            
            # Map each sentence subtree into a tuple.            
            for token in map(tree2tuple, sent):
                # If the token type is COREF then append the token contents
                # and everything but the token type.
                if token[1] == 'COREF':
                    mentions.append(token[:1] + token[2:])
                # If including nonmentions, append the token contents only.
                elif kwargs.get('nonmentions'):
                    mentions.append(token[:1])
            return mentions
        # TODO: Is depth doing what it's expected to?                
        depth = kwargs.get('depth', 0)        
        sents = self._chunked_sents(self._sents(fileids), depth)                
        # Concatenate the lists.
        if kwargs.get('concat'):
            return LazyConcatenation(LazyMap(__mentions, sents))
        # Or not.
        else:
            return LazyMap(__mentions, sents)
            
    def _paras(self, fileids=None):
        """
        @return: A list of paragraphs.
        @rtype: C{list} of C{Tree}
        @param fileids: A list of corpus files.
        @type fileids: C{list} of C{str} or regular expression.
        """
        def __para(doc):
            return list(doc.text)
        return LazyConcatenation(LazyMap(__para, self.parsed_docs(fileids)))

    def _sents(self, fileids=None):
        """
        @return: A list of sentence trees.
        @rtype: C{list} of C{list} of C{Tree}
        @param fileids: A list of corpus files.
        @type fileids: C{list} of C{str} or regular expression      
        """
        def __sents(para):
            return list(para)
        # Flatten this because it's a list of list of trees for each doc. It
        # doesn't matter which doc the list is from so chain them together.
        return LazyConcatenation(LazyMap(__sents, self._paras(fileids)))
        
    def _chunked_sents(self, sents, depth=0):
        """
        @return: A list of sentence chunk trees which are flatter than the
            original trees.
        @rtype: C{list} of C{list} of C{Tree}
        @param sents: A list of sentence trees.
        @type sents: C{list} of C{list} of C{Tree}
        @param depth: How deep to read nested chunks off of the trees. If
            depth is None, all possible chunk substrees are returned, 
            otherwise, chunks are returned starting at the highest level 0,
            then the next highest 1, etc.
        @type depth: C{int}
        """        
        def __chunked_sent(sent):
            for chunk in sent:
                # If the chunk is a Tree, append it's immediate subtrees.
                if isinstance(chunk, Tree):
                    return list(chunk)
                # If the chunk is not a tree, append it.
                else:
                    return chunk
        # If depth is None, return all possible subtrees 
        if depth is None:
            return LazyMap(lambda sent: sent.subtrees(), sents)
        # If depth is too small, no need to recurse and read further.
        if not depth - 1 >= 0:
            return sents
        # Otherwise, apply __chunked_sent() and recurse.
        return self._chunked_sents(LazyConcatenation(LazyMap(__chunked_sent, sents)), depth - 1)

    def _read_parsed_block(self, stream):
        # TODO: LazyMap but StreamBackedCorpusView doesn't support
        # AbstractLazySequence currently.
        return map(self._parse, self._read_block(stream))
  
    def _parse(self, doc):
        """
        @return: A parsed MUC document.
        @rtype: C{MUCDocument}
        @param doc: The string contents of a MUC document.
        @type doc: C{str}
        """
        tree = mucstr2tree(doc, top_node='DOC')
        if isinstance(tree, dict):
            return MUCDocument(**tree)
        else:
            return MUCDocument(tree)

    def _read_block(self, stream):
        return ['\n'.join(stream.readlines())]


def mucstr2tree(s, chunk_types=_MUC_CHUNK_TYPES, top_node='S'):
    """
    Convert MUC document contents into a tree.
    
    @return: A MUC document as a tree.
    @rtype: C{Tree}
    @param s: Contents of a MUC document.
    @type s: C{str}
    @param chunk_types: Chunk types to extract from the MUC document.
    @type chunk_types: C{list} of C{str}
    @param top_node: Label to assign to the root of the tree.
    @type top_node: C{str}
    """
    tree = None
    match = _MUC6_DOC_RE.match(s)
    if match:
        # If the MUC document is valid, read the document element groups off its
        # contents and return a dictionary of each part.
        if match:
            tree = {
                'text': _muc_read_text(match.group('text'), top_node),
                'docno': match.group('docno'),
                # Capture named entities/mentions in the front-matter too.            
                'dateline': _muc_read_text(match.group('dateline'), top_node),           
                'headline': _muc_read_text(match.group('headline'), top_node),
            }
    else:
        match = _MUC7_DOC_RE.match(s)
        if match:
            tree = {
                'text': _muc_read_text(match.group('text'), top_node),
                'docid': match.group('docid'),
                # Capture named entities/mentions in the front-matter too.            
                'date': _muc_read_text(match.group('date'), top_node),
            }
    assert tree
    return tree
        
def tree2tuple(tree):
    """
    Convert a tree or string into a flat tuple of leaves and a label.
    
    @return: A tuple of tree leaves and their parent's label.
    @rtype: C{tuple}
    @param tree: A tree.
    @type tree: C{Tree}
    """
    result = ()
    # If the tree is a tree then create a tuple out of the leaves and label.
    if isinstance(tree, Tree):
        # Get the leaves.
        s = (tree.leaves(),)
        # Get the label
        if isinstance(tree.node, basestring):
            node = (tree.node,)
        elif isinstance(tree.node, tuple):
            node = tree.node
        else:
            raise
        # Merge the leaves and the label.
        return s + node
    # If the tree is a string just convert it to a tuple.
    elif isinstance(tree, basestring):
        return (tree, None)
    # Something bad happened.
    else:
        raise

def _muc_read_text(s, top_node):
    # The tokenizer sometimes splits within coref tags.
    def __fix_tokenization(sents):
        for index in range(len(sents)):
            next = 1
            while sents[index].count('<COREF') != sents[index].count('</COREF>'):
                sents[index] += ' '
                sents[index] += sents[index + next]
                sents[index + next] = ''
                next += 1
        sents = filter(None, sents)
        return sents
    if s:
        tree = Tree(top_node, [])        
        if _MUC6_PARA_RE.match(s):
            for para in _MUC6_PARA_RE.findall(s):
                if para and para[0] and para[0].strip():
                    tree.append(Tree('P', []))
                    for sent in _MUC6_SENT_RE.findall(para[0]):
                        words = _MUC6_SENT_RE.match(sent[0]).group('sent')
                        tree[-1].append(_muc_read_words(words, 'S'))                
        elif _MUC7_PARA_RE.match(s):
            for para in _MUC7_PARA_SPLIT_RE.split(s):
                if para and para.strip():
                    tree.append(Tree('P', []))
                    for sent in __fix_tokenization(_SENT_TOKENIZER.tokenize(para)):
                        tree[-1].append(_muc_read_words(sent, 'S'))
        return tree

def _muc_read_words(s, top_node):
    if not s: return []
    stack = [Tree(top_node, [])]
    for word in re.findall('<[^>]+>|[^\s<]+', s):
        ne_match = _MUC_NE_B_RE.match(word)
        co_match = _MUC_CO_B_RE.match(word)
        if ne_match:
            chunk = Tree(ne_match.group('type'), [])
            stack[-1].append(chunk)
            stack.append(chunk)
        elif co_match:
            chunk = Tree(('COREF', co_match.group('id'), 
                          co_match.group('ref'), co_match.group('type')), [])
            stack[-1].append(chunk)
            stack.append(chunk)
        elif _MUC_NE_E_RE.match(word) or _MUC_CO_E_RE.match(word):
            stack.pop()
        else:
            stack[-1].extend(_WORD_TOKENIZER.tokenize(word))
    if len(stack) != 1:
        print stack
    assert len(stack) == 1
    return stack[0]

def demo(**kwargs):
    import nltk
    from nltk_contrib.coref import NLTK_COREF_DATA    
    from nltk_contrib.coref.muc import muc6_documents, muc7_documents
    from nltk_contrib.coref.muc import MUCCorpusReader
    nltk.data.path.insert(0, NLTK_COREF_DATA)   
    muc6 = LazyCorpusLoader('muc6/', MUCCorpusReader, muc6_documents)
    for sent in muc6.iob_sents()[:]:
        for word in sent:
            print word
        print
    print
    for sent in muc6.mentions(depth=None):
        for mention in sent:
            print mention
        if sent: print
    print
    muc7 = LazyCorpusLoader('muc7/', MUCCorpusReader, muc7_documents)
    for sent in muc7.iob_sents()[:]:
        for word in sent:
            print word
        print
    print
    for sent in muc7.mentions(depth=None):
        for mention in sent:
            print mention
        if sent: print
    print
    
if __name__ == '__main__':
    demo()
