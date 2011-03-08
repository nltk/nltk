# Natural Language Toolkit: PropBank Corpus Reader
#
# Copyright (C) 2001-2011 NLTK Project
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

import re
import codecs

from nltk.tree import Tree
from nltk.etree import ElementTree

from util import *
from api import *

class PropbankCorpusReader(CorpusReader):
    """
    Corpus reader for the propbank corpus, which augments the Penn
    Treebank with information about the predicate argument structure
    of every verb instance.  The corpus consists of two parts: the
    predicate-argument annotations themselves, and a set of X{frameset
    files} which define the argument labels used by the annotations,
    on a per-verb basis.  Each X{frameset file} contains one or more
    predicates, such as C{'turn'} or C{'turn_on'}, each of which is
    divided into coarse-grained word senses called X{rolesets}.  For
    each X{roleset}, the frameset file provides descriptions of the
    argument roles, along with examples.
    """
    def __init__(self, root, propfile, framefiles='',
                 verbsfile=None, parse_fileid_xform=None,
                 parse_corpus=None, encoding=None):
        """
        @param root: The root directory for this corpus.
        @param propfile: The name of the file containing the predicate-
            argument annotations (relative to C{root}).
        @param framefiles: A list or regexp specifying the frameset
            fileids for this corpus.
        @param parse_fileid_xform: A transform that should be applied
            to the fileids in this corpus.  This should be a function
            of one argument (a fileid) that returns a string (the new
            fileid).
        @param parse_corpus: The corpus containing the parse trees
            corresponding to this corpus.  These parse trees are
            necessary to resolve the tree pointers used by propbank.
        """
        # If framefiles is specified as a regexp, expand it.
        if isinstance(framefiles, basestring):
            framefiles = find_corpus_fileids(root, framefiles)
        framefiles = list(framefiles)
        # Initialze the corpus reader.
        CorpusReader.__init__(self, root, [propfile, verbsfile] + framefiles,
                              encoding)

        # Record our frame fileids & prop file.
        self._propfile = propfile
        self._framefiles = framefiles
        self._verbsfile = verbsfile
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
        L{PropbankInstance} objects, one for each verb in the corpus.
        """
        return StreamBackedCorpusView(self.abspath(self._propfile),
                                      self._read_instance_block,
                                      encoding=self.encoding(self._propfile))

    def lines(self):
        """
        @return: a corpus view that acts as a list of strings, one for
        each line in the predicate-argument annotation file.  
        """
        return StreamBackedCorpusView(self.abspath(self._propfile),
                                      read_line_block,
                                      encoding=self.encoding(self._propfile))

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

    def verbs(self):
        """
        @return: a corpus view that acts as a list of all verb lemmas
        in this corpus (from the verbs.txt file).
        """
        return StreamBackedCorpusView(self.abspath(self._verbsfile),
                                      read_line_block,
                                      encoding=self.encoding(self._verbsfile))

    def _read_instance_block(self, stream):
        block = []

        # Read 100 at a time.
        for i in range(100):
            line = stream.readline().strip()
            if line:
                block.append(PropbankInstance.parse(
                    line, self._parse_fileid_xform,
                    self._parse_corpus))
                
        return block

######################################################################
#{ Propbank Instance & related datatypes
######################################################################

class PropbankInstance(object):
    
    def __init__(self, fileid, sentnum, wordnum, tagger, roleset,
                 inflection, predicate, arguments, parse_corpus=None):
        
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
        
        self.tagger = tagger
        """An identifier for the tagger who tagged this instance; or
        C{'gold'} if this is an adjuticated instance."""
        
        self.roleset = roleset
        """The name of the roleset used by this instance's predicate.
        Use L{propbank.roleset() <PropbankCorpusReader.roleset>} to
        look up information about the roleset."""
        
        self.inflection = inflection
        """A {PropbankInflection} object describing the inflection of
        this instance's predicate."""
        
        self.predicate = predicate
        """A L{PropbankTreePointer} indicating the position of this
        instance's predicate within its containing sentence."""
        
        self.arguments = tuple(arguments)
        """A list of tuples (argloc, argid), specifying the location
        and identifier for each of the predicate's argument in the
        containing sentence.  Argument identifiers are strings such as
        C{'ARG0'} or C{'ARGM-TMP'}.  This list does *not* contain
        the predicate."""

        self.parse_corpus = parse_corpus
        """A corpus reader for the parse trees corresponding to the
        instances in this propbank corpus."""

    def __repr__(self):
        return ('<PropbankInstance: %s, sent %s, word %s>' %
                (self.fileid, self.sentnum, self.wordnum))

    def __str__(self):
        s = '%s %s %s %s %s %s' % (self.fileid, self.sentnum, self.wordnum,
                                   self.tagger, self.roleset, self.inflection)
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
        if len(pieces) < 7: 
            raise ValueError('Badly formatted propbank line: %r' % s)

        # Divide the line into its basic pieces.
        (fileid, sentnum, wordnum,
         tagger, roleset, inflection) = pieces[:6]
        rel = [p for p in pieces[6:] if p.endswith('-rel')]
        args = [p for p in pieces[6:] if not p.endswith('-rel')]
        if len(rel) != 1:
            raise ValueError('Badly formatted propbank line: %r' % s)

        # Apply the fileid selector, if any.
        if parse_fileid_xform is not None:
            fileid = parse_fileid_xform(fileid)

        # Convert sentence & word numbers to ints.
        sentnum = int(sentnum)
        wordnum = int(wordnum)

        # Parse the inflection
        inflection = PropbankInflection.parse(inflection)

        # Parse the predicate location.
        predicate = PropbankTreePointer.parse(rel[0][:-4])

        # Parse the arguments.
        arguments = []
        for arg in args:
            argloc, argid = arg.split('-', 1)
            arguments.append( (PropbankTreePointer.parse(argloc), argid) )

        # Put it all together.
        return PropbankInstance(fileid, sentnum, wordnum, tagger,
                                roleset, inflection, predicate,
                                arguments, parse_corpus)

class PropbankPointer(object):
    """
    A pointer used by propbank to identify one or more constituents in
    a parse tree.  C{PropbankPointer} is an abstract base class with
    three concrete subclasses:

      - L{PropbankTreePointer} is used to point to single constituents.
      - L{PropbankSplitTreePointer} is used to point to 'split'
        constituents, which consist of a sequence of two or more
        C{PropbankTreePointer}s.
      - L{PropbankChainTreePointer} is used to point to entire trace
        chains in a tree.  It consists of a sequence of pieces, which
        can be C{PropbankTreePointer}s or C{PropbankSplitTreePointer}s.
    """
    def __init__(self):
        if self.__class__ == PropbankPoitner:
            raise AssertionError('PropbankPointer is an abstract base class')
            
class PropbankChainTreePointer(PropbankPointer):
    def __init__(self, pieces):
        self.pieces = pieces
        """A list of the pieces that make up this chain.  Elements may
           be either L{PropbankSplitTreePointer}s or
           L{PropbankTreePointer}s."""
        
    def __str__(self):
        return '*'.join('%s' % p for p in self.pieces)
    def __repr__(self):
        return '<PropbankChainTreePointer: %s>' % self
    def select(self, tree):
        if tree is None: raise ValueError('Parse tree not avaialable')
        return Tree('*CHAIN*', [p.select(tree) for p in self.pieces])

class PropbankSplitTreePointer(PropbankPointer):
    def __init__(self, pieces):
        self.pieces = pieces
        """A list of the pieces that make up this chain.  Elements are
           all L{PropbankTreePointer}s."""
        
    def __str__(self):
        return ','.join('%s' % p for p in self.pieces)
    def __repr__(self):
        return '<PropbankSplitTreePointer: %s>' % self
    def select(self, tree):
        if tree is None: raise ValueError('Parse tree not avaialable')
        return Tree('*SPLIT*', [p.select(tree) for p in self.pieces])

class PropbankTreePointer(PropbankPointer):
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
            return PropbankChainTreePointer([PropbankTreePointer.parse(elt)
                                              for elt in pieces])

        # Deal with split args (xx,yy,zz)
        pieces = s.split(',')
        if len(pieces) > 1:
            return PropbankSplitTreePointer([PropbankTreePointer.parse(elt)
                                             for elt in pieces])

        # Deal with normal pointers.
        pieces = s.split(':')
        if len(pieces) != 2: raise ValueError('bad propbank pointer %r' % s)
        return PropbankTreePointer(int(pieces[0]), int(pieces[1]))

    def __str__(self):
        return '%s:%s' % (self.wordnum, self.height)

    def __repr__(self):
        return 'PropbankTreePointer(%d, %d)' % (self.wordnum, self.height)

    def __cmp__(self, other):
        while isinstance(other, (PropbankChainTreePointer,
                                 PropbankSplitTreePointer)):
            other = other.pieces[0]
        
        if not isinstance(other, PropbankTreePointer):
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

class PropbankInflection(object):
    #{ Inflection Form 
    INFINITIVE = 'i'
    GERUND = 'g'
    PARTICIPLE = 'p'
    FINITE = 'v'
    #{ Inflection Tense
    FUTURE = 'f'
    PAST = 'p'
    PRESENT = 'n'
    #{ Inflection Aspect
    PERFECT = 'p'
    PROGRESSIVE = 'o'
    PERFECT_AND_PROGRESSIVE = 'b'
    #{ Inflection Person
    THIRD_PERSON = '3'
    #{ Inflection Voice
    ACTIVE = 'a'
    PASSIVE = 'p'
    #{ Inflection
    NONE = '-'
    #}
    
    def __init__(self, form='-', tense='-', aspect='-', person='-', voice='-'):
        self.form = form
        self.tense = tense
        self.aspect = aspect
        self.person = person
        self.voice = voice

    def __str__(self):
        return self.form+self.tense+self.aspect+self.person+self.voice

    def __repr__(self):
        return '<PropbankInflection: %s>' % self

    _VALIDATE = re.compile(r'[igpv\-][fpn\-][pob\-][3\-][ap\-]$')

    @staticmethod
    def parse(s):
        if not isinstance(s, basestring):
            raise TypeError('expected a string')
        if (len(s) != 5 or
            not PropbankInflection._VALIDATE.match(s)):
            raise ValueError('Bad propbank inflection string %r' % s)
        return PropbankInflection(*s)

