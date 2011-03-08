# Natural Language Toolkit: NomBank Corpus Reader
#
# Copyright (C) 2001-2011 NLTK Project
# Authors: Paul Bedaride <paul.bedaride@gmail.com> 
#          Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

import re
import codecs

from nltk.tree import Tree
from nltk.etree import ElementTree

from nltk.corpus.reader.util import *
from nltk.corpus.reader.api import *

class NombankCorpusReader(CorpusReader):
    """
    Corpus reader for the nombank corpus, which augments the Penn
    Treebank with information about the predicate argument structure
    of every noun instance.  The corpus consists of two parts: the
    predicate-argument annotations themselves, and a set of X{frameset
    files} which define the argument labels used by the annotations,
    on a per-noun basis.  Each X{frameset file} contains one or more
    predicates, such as C{'turn'} or C{'turn_on'}, each of which is
    divided into coarse-grained word senses called X{rolesets}.  For
    each X{roleset}, the frameset file provides descriptions of the
    argument roles, along with examples.
    """
    def __init__(self, root, nomfile, framefiles='',
                 nounsfile=None, parse_fileid_xform=None,
                 parse_corpus=None, encoding=None):
        """
        @param root: The root directory for this corpus.
        @param nomfile: The name of the file containing the predicate-
            argument annotations (relative to C{root}).
        @param framefiles: A list or regexp specifying the frameset
            fileids for this corpus.
        @param parse_fileid_xform: A transform that should be applied
            to the fileids in this corpus.  This should be a function
            of one argument (a fileid) that returns a string (the new
            fileid).
        @param parse_corpus: The corpus containing the parse trees
            corresponding to this corpus.  These parse trees are
            necessary to resolve the tree pointers used by nombank.
        """
        # If framefiles is specified as a regexp, expand it.
        if isinstance(framefiles, basestring):
            framefiles = find_corpus_fileids(root, framefiles)
        framefiles = list(framefiles)
        # Initialze the corpus reader.
        CorpusReader.__init__(self, root, [nomfile, nounsfile] + framefiles,
                              encoding)

        # Record our frame fileids & nom file.
        self._nomfile = nomfile
        self._framefiles = framefiles
        self._nounsfile = nounsfile
        self._parse_fileid_xform = parse_fileid_xform
        self._parse_corpus = parse_corpus

    def raw(self, fileids=None):
        """
        @return: the text contents of the given fileids, as a single string.
        """
        if fileids is None: fileids = self._fileids
        elif isinstance(fileids, basestring): fileids = [fileids]
        return concat([self.open(f).read() for f in fileids])

    def instances(self):
        """
        @return: a corpus view that acts as a list of
        L{NombankInstance} objects, one for each noun in the corpus.
        """
        return StreamBackedCorpusView(self.abspath(self._nomfile),
                                      self._read_instance_block,
                                      encoding=self.encoding(self._nomfile))

    def lines(self):
        """
        @return: a corpus view that acts as a list of strings, one for
        each line in the predicate-argument annotation file.  
        """
        return StreamBackedCorpusView(self.abspath(self._nomfile),
                                      read_line_block,
                                      encoding=self.encoding(self._nomfile))

    def roleset(self, roleset_id):
        """
        @return: the xml description for the given roleset.
        """
        lemma = roleset_id.split('.')[0]
        framefile = 'frames/%s.xml' % lemma
        if framefile not in self._framefiles:
            raise ValueError('Frameset file for %s not found' %
                             roleset_id)

        # n.b.: The encoding for XML fileids is specified by the file
        # itself; so we ignore self._encoding here.
        etree = ElementTree.parse(self.abspath(framefile).open()).getroot()
        for roleset in etree.findall('predicate/roleset'):
            if roleset.attrib['id'] == roleset_id:
                return roleset
        else:
            raise ValueError('Roleset %s not found in %s' %
                             (roleset_id, framefile))

    def nouns(self):
        """
        @return: a corpus view that acts as a list of all noun lemmas
        in this corpus (from the nombank.1.0.words file).
        """
        return StreamBackedCorpusView(self.abspath(self._nounsfile),
                                      read_line_block,
                                      encoding=self.encoding(self._nounsfile))

    def _read_instance_block(self, stream):
        block = []

        # Read 100 at a time.
        for i in range(100):
            line = stream.readline().strip()
            if line:
                block.append(NombankInstance.parse(
                    line, self._parse_fileid_xform,
                    self._parse_corpus))
                
        return block

######################################################################
#{ Nombank Instance & related datatypes
######################################################################

class NombankInstance(object):
    
    def __init__(self, fileid, sentnum, wordnum, baseform, sensenumber,
                 predicate, predid, arguments, parse_corpus=None):
        
        self.fileid = fileid
        """The name of the file containing the parse tree for this
        instance's sentence."""

        self.sentnum = sentnum
        """The sentence number of this sentence within L{fileid}.
        Indexing starts from zero."""
        
        self.wordnum = wordnum
        """The word number of this instance's predicate within its
        containing sentence.  Word numbers are indexed starting from
        zero, and include traces and other empty parse elements."""
            
        self.baseform = baseform
        """The baseform of the predicate."""

        self.sensenumber = sensenumber
        """The sense number os the predicate"""
               
        self.predicate = predicate
        """A L{NombankTreePointer} indicating the position of this
        instance's predicate within its containing sentence."""

        self.predid = predid
        """Identifier of the predicate """
        
        self.arguments = tuple(arguments)
        """A list of tuples (argloc, argid), specifying the location
        and identifier for each of the predicate's argument in the
        containing sentence.  Argument identifiers are strings such as
        C{'ARG0'} or C{'ARGM-TMP'}.  This list does *not* contain
        the predicate."""

        self.parse_corpus = parse_corpus
        """A corpus reader for the parse trees corresponding to the
        instances in this nombank corpus."""

    @property
    def roleset(self):
        """The name of the roleset used by this instance's predicate.
        Use L{nombank.roleset() <NombankCorpusReader.roleset>} to
        look up information about the roleset."""
        return '%s.%s'%(self.baseform, self.sensenumber)

    def __repr__(self):
        return ('<NombankInstance: %s, sent %s, word %s>' %
                (self.fileid, self.sentnum, self.wordnum))

    def __str__(self):
        s = '%s %s %s %s %s' % (self.fileid, self.sentnum, self.wordnum,
                                self.basename, self.sensenumber)
        items = self.arguments + ((self.predicate, 'rel'),)
        for (argloc, argid) in sorted(items):
            s += ' %s-%s' % (argloc, argid)
        return s

    def _get_tree(self):
        if self.parse_corpus is None: return None
        if self.fileid not in self.parse_corpus.fileids(): return None
        return self.parse_corpus.parsed_sents(self.fileid)[self.sentnum]
    tree = property(_get_tree, doc="""
        The parse tree corresponding to this instance, or C{None} if
        the corresponding tree is not available.""")

    @staticmethod
    def parse(s, parse_fileid_xform=None, parse_corpus=None):
        pieces = s.split()
        if len(pieces) < 6: 
            raise ValueError('Badly formatted nombank line: %r' % s)

        # Divide the line into its basic pieces.
        (fileid, sentnum, wordnum,
          baseform, sensenumber) = pieces[:5]

        args = pieces[5:]
        rel = [args.pop(i) for i,p in enumerate(args) if '-rel' in p]
        if len(rel) != 1:
            raise ValueError('Badly formatted nombank line: %r' % s)

        # Apply the fileid selector, if any.
        if parse_fileid_xform is not None:
            fileid = parse_fileid_xform(fileid)

        # Convert sentence & word numbers to ints.
        sentnum = int(sentnum)
        wordnum = int(wordnum)

        # Parse the predicate location.

        predloc, predid = rel[0].split('-', 1)
        predicate = NombankTreePointer.parse(predloc)

        # Parse the arguments.
        arguments = []
        for arg in args:
            argloc, argid = arg.split('-', 1)
            arguments.append( (NombankTreePointer.parse(argloc), argid) )

        # Put it all together.
        return NombankInstance(fileid, sentnum, wordnum, baseform, sensenumber, 
                               predicate, predid, arguments, parse_corpus)

class NombankPointer(object):
    """
    A pointer used by nombank to identify one or more constituents in
    a parse tree.  C{NombankPointer} is an abstract base class with
    three concrete subclasses:

      - L{NombankTreePointer} is used to point to single constituents.
      - L{NombankSplitTreePointer} is used to point to 'split'
        constituents, which consist of a sequence of two or more
        C{NombankTreePointer}s.
      - L{NombankChainTreePointer} is used to point to entire trace
        chains in a tree.  It consists of a sequence of pieces, which
        can be C{NombankTreePointer}s or C{NombankSplitTreePointer}s.
    """
    def __init__(self):
        if self.__class__ == NombankPoitner:
            raise AssertionError('NombankPointer is an abstract base class')
            
class NombankChainTreePointer(NombankPointer):
    def __init__(self, pieces):
        self.pieces = pieces
        """A list of the pieces that make up this chain.  Elements may
           be either L{NombankSplitTreePointer}s or
           L{NombankTreePointer}s."""
        
    def __str__(self):
        return '*'.join('%s' % p for p in self.pieces)
    def __repr__(self):
        return '<NombankChainTreePointer: %s>' % self
    def select(self, tree):
        if tree is None: raise ValueError('Parse tree not avaialable')
        return Tree('*CHAIN*', [p.select(tree) for p in self.pieces])

class NombankSplitTreePointer(NombankPointer):
    def __init__(self, pieces):
        self.pieces = pieces
        """A list of the pieces that make up this chain.  Elements are
           all L{NombankTreePointer}s."""
        
    def __str__(self):
        return ','.join('%s' % p for p in self.pieces)
    def __repr__(self):
        return '<NombankSplitTreePointer: %s>' % self
    def select(self, tree):
        if tree is None: raise ValueError('Parse tree not avaialable')
        return Tree('*SPLIT*', [p.select(tree) for p in self.pieces])

class NombankTreePointer(NombankPointer):
    """
    wordnum:height*wordnum:height*...
    wordnum:height,
    
    """
    def __init__(self, wordnum, height):
        self.wordnum = wordnum
        self.height = height

    @staticmethod
    def parse(s):
        # Deal with chains (xx*yy*zz)
        pieces = s.split('*')
        if len(pieces) > 1:
            return NombankChainTreePointer([NombankTreePointer.parse(elt)
                                              for elt in pieces])

        # Deal with split args (xx,yy,zz)
        pieces = s.split(',')
        if len(pieces) > 1:
            return NombankSplitTreePointer([NombankTreePointer.parse(elt)
                                             for elt in pieces])

        # Deal with normal pointers.
        pieces = s.split(':')
        if len(pieces) != 2: raise ValueError('bad nombank pointer %r' % s)
        return NombankTreePointer(int(pieces[0]), int(pieces[1]))

    def __str__(self):
        return '%s:%s' % (self.wordnum, self.height)

    def __repr__(self):
        return 'NombankTreePointer(%d, %d)' % (self.wordnum, self.height)

    def __cmp__(self, other):
        while isinstance(other, (NombankChainTreePointer,
                                 NombankSplitTreePointer)):
            other = other.pieces[0]
        
        if not isinstance(other, NombankTreePointer):
            return cmp(id(self), id(other))

        return cmp( (self.wordnum, -self.height),
                    (other.wordnum, -other.height) )

    def select(self, tree):
        if tree is None: raise ValueError('Parse tree not avaialable')
        return tree[self.treepos(tree)]

    def treepos(self, tree):
        """
        Convert this pointer to a standard 'tree position' pointer,
        given that it points to the given tree.
        """
        if tree is None: raise ValueError('Parse tree not avaialable')
        stack = [tree]
        treepos = []

        wordnum = 0
        while True:
            #print treepos
            #print stack[-1]
            # tree node:
            if isinstance(stack[-1], Tree):
                # Select the next child.
                if len(treepos) < len(stack):
                    treepos.append(0)
                else:
                    treepos[-1] += 1
                # Update the stack.
                if treepos[-1] < len(stack[-1]):
                    stack.append(stack[-1][treepos[-1]])
                else:
                    # End of node's child list: pop up a level.
                    stack.pop()
                    treepos.pop()
            # word node:
            else:
                if wordnum == self.wordnum:
                    return tuple(treepos[:len(treepos)-self.height-1])
                else:
                    wordnum += 1
                    stack.pop()

