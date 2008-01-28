# Natural Language Toolkit: PropBank Corpus Reader
#
# Copyright (C) 2001-2008 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

from nltk.corpus.reader.util import *
from nltk.corpus.reader.api import *
from nltk.tree import Tree
import re

class PropbankCorpusReader(CorpusReader):
    def __init__(self, root, propfile, framefiles,
                 parse_filename_xform=None,
                 parse_corpus=None):
        
        # If framefiles is specified as a regexp, expand it.
        if isinstance(framefiles, basestring):
            framefiles = nltk.corpus.reader.find_corpus_files(root, framefiles)
        # Initialze the corpus reader.
        CorpusReader.__init__(self, root, [propfile] + list(framefiles))

        # Record our frame files & prop file.
        self._propfile = propfile
        self._framefiles = framefiles
        self._parse_filename_xform = parse_filename_xform
        self._parse_corpus = parse_corpus

    def raw(self, files=None):
        return concat([open(filename).read()
                       for filename in self.abspaths(files)])

    def instances(self):
        return StreamBackedCorpusView(self.abspath(self._propfile),
                                      self._read_instance_block)

    def lines(self):
        return StreamBackedCorpusView(self.abspath(self._propfile),
                                      read_line_block)

    def _read_instance_block(self, stream):
        block = []

        # Read 20 at a time.
        for i in range(20):
            line = stream.readline().strip()
            if line:
                block.append(PropbankInstance.parse(
                    line, self._parse_filename_xform,
                    self._parse_corpus))
                
        return block

######################################################################
#{ Propbank Instance & related datatypes
######################################################################

class PropbankInstance(object):
    
    def __init__(self, filename, sentnum, wordnum, tagger, frameset,
                 inflection, predicate, arguments, parse_corpus=None):
        
        self.filename = filename
        """The name of the file containing the parse tree for this
        instance's sentence."""

        self.sentnum = sentnum
        """The sentence number of this sentence within L{filename}.
        Indexing starts from zero."""
        
        self.wordnum = wordnum
        """The word number of this instance's predicate within its
        containing sentence.  Word numbers are indexed starting from
        zero, and include traces and other empty parse elements."""
        
        self.tagger = tagger
        """An identifier for the tagger who tagged this instance; or
        C{'gold'} if this is an adjuticated instance."""
        
        self.frameset = frameset
        """The name of the frameset used by this instance's predicate.
        Use L{propbank.frameset() <PropbankCorusReader.frameset>} to
        look up information about the frameset."""
        
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
                (self.filename, self.sentnum, self.wordnum))

    def __str__(self):
        s = '%s %s %s %s %s %s' % (self.filename, self.sentnum, self.wordnum,
                                   self.tagger, self.frameset, self.inflection)
        items = self.arguments + ((self.predicate, 'rel'),)
        for (argloc, argid) in sorted(items):
            s += ' %s-%s' % (argloc, argid)
        return s

    def _get_tree(self):
        if self.parse_corpus is None: return None
        if self.filename not in self.parse_corpus.files(): return None
        return self.parse_corpus.parsed_sents(self.filename)[self.sentnum]
    tree = property(_get_tree, doc="""
        The parse tree corresponding to this instance, or C{None} if
        the corresponding tree is not available.""")

    @staticmethod
    def parse(s, parse_filename_xform=None, parse_corpus=None):
        pieces = s.split()
        if len(pieces) < 7: 
            raise ValueError('Badly formatted propbank line: %r' % s)

        # Divide the line into its basic pieces.
        (filename, sentnum, wordnum,
         tagger, frameset, inflection) = pieces[:6]
        rel = [p for p in pieces[6:] if p.endswith('-rel')]
        args = [p for p in pieces[6:] if not p.endswith('-rel')]
        if len(rel) != 1:
            raise ValueError('Badly formatted propbank line: %r' % s)

        # Apply the filename selector, if any.
        if parse_filename_xform is not None:
            filename = parse_filename_xform(filename)

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
        return PropbankInstance(filename, sentnum, wordnum, tagger,
                                frameset, inflection, predicate,
                                arguments, parse_corpus)
            
class PropbankChainTreePointer(object):
    def __init__(self, pieces):
        self.pieces = pieces
    def __str__(self):
        return '*'.join('%s' % p for p in self.pieces)
    def __repr__(self):
        return '<PropbankChainTreePointer: %s>' % self
    def select(self, tree):
        if tree is None: raise ValueError('Parse tree not avaialable')
        return Tree('*CHAIN*', [p.select(tree) for p in self.pieces])

class PropbankSplitTreePointer(object):
    def __init__(self, pieces):
        self.pieces = pieces
    def __str__(self):
        return ','.join('%s' % p for p in self.pieces)
    def __repr__(self):
        return '<PropbankSplitTreePointer: %s>' % self
    def select(self, tree):
        if tree is None: raise ValueError('Parse tree not avaialable')
        return Tree('*SPLIT*', [p.select(tree) for p in self.pieces])

class PropbankTreePointer(object):
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
        if len(pieces) != 2: raise ValueError('bad propbank pointer %s' % s)
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
            return object.__cmp__(self, other)

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

