# Natural Language Toolkit: A Chunk Parser
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Steven Bird <sb@ldc.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

from parser import *
from token import *
from tree import *
from tagger import *
from re import *
from string import *
from chunkparser import *

""" Classes for a regular-expression based chunk parser.  A chunk
parser applies a cascade of regular-expression rules to the string
representation of a tokenized sentence.  The rules insert and delete
the chunk delimiters "{" and "}".  Chunks cannot be nested.

(Note: these brace delimiters were chosen instead of the more usual
bracket delimiters "[" and "]", since the brackets always need to be
escaped "\[" and "\]" in regular expressions, greatly reducing the
readability of the code.)

The string representation of a tokenized sequence uses "<" and ">" to
delimit individual tokens (using balanced delimiters makes things
easier than using whitespace).  Here is the string representation for
a tokenized and tagged sentence "the cat sat on the mat", with both
noun phrases chunked:

{<the/DT@[1]><cat/NN@[2]>}<sat/VBD@[3]><on/IN@[4]>{<the/DT@[5]><mat/NN@[6]>} 

The ChunkRule class represents regular expression rules on strings like this.
We don't throw away the word and the location, since these strings are later
used to build a "chunk structure", a list of lists with the original tokens:

[ [ 'the'/'DT'@[1], 'cat'/'NN'@[2] ], 'sat'/'VBD'@[3], 'on'/'IN'@[4],
  [ 'the'/'DT'@[5], 'mat'/'NN'@[6] ] ]

To make life easier, the AbstractChunkRule class lets programmers
focus on the tags alone, ignoring the words and locations.  Using this
class, a programmer may write "<DT>", and this is internally
transformed so that it will match against "<the/DT@[1]>".
Conveniently, the angle brackets are also made to serve as parenthesis
groups in the regular expressions.  For example, a unary operator
after a ">" has scope over the material inside the <>, so "<JJ>*<NN>"
will match "<JJ><JJ><NN>", not "<JJ>>><NN>".  Also, disjunction inside
the <> has its scope bounded by the <>, so "<JJ|NN.*>" will match
"<NNS>".  AbstractChunkRules must always use the <> brackets when
referring to tags.

The REChunkParser class is initialized with a cascade of chunk rules.
It has a parse method which takes a tokenized string and returns a
chunk structure.

(A previous version returned a Tree in which chunks were represented
using a non-terminal node called "chunk".  However, this
representation was inconvenient for relating the output of a parse to
the standard representation of chunked text.  The list-of-lists
representation (chunk structures) was also a more natural thing for a
chunking version of the TaggedTokenizer to return.)
"""

# To do:
# experiment with syntactic sugar for <> (using space)
# test that no tokens were deleted in applying a chunking rule
# rule initializer should compile the final regexp for efficient runtime execution
# tokenizer to return a list of sentence tokens?  or ./EOS ??

# this type stuff should be pulled in from somewhere else
# rather than being defined here...
from types import InstanceType as _InstanceType
def _pytype(obj):
    """
    @return: the pytype of C{obj}.  For class instances, this is
        their class; for all other objects, it is their type, as
        returned by type().
    @rtype: C{type} or C{class}
    @param obj: The object whose pytype should be returned.
    @type obj: (any)
    """
    if type(obj) == _InstanceType:
        return obj.__class__
    else:
        return type(obj)

##//////////////////////////////////////////////////////
##  Chunk Rules
##//////////////////////////////////////////////////////

# functions for zero-width assertions
def _lookbehind(str):
    return '(?<='+str+')'
def _lookahead(str):
    return '(?='+str+')'

# A chunk rule matches a target string and performs an action
# on it, usually adding or removing {}, the chunk delimiters.
# Keyword arguments handle context using zero-width assertions.
class ChunkRule:
    """
    A chunking rule.  This class contains regular expressions
    intended for inserting and deleting the chunk delimiters {
    and } from the string representation of a sequence of tokens.

    @type _target: C{string}
    @ivar _target: The regexp describing the target of the rule.
    @type _action: C{string}
    @ivar _action: The regexp describing the action to be performed
          on the target.
    @type _left: C{string}
    @ivar _left: A zero-width assertion about left context.
    @type _right: C{string}
    @ivar _right: A zero-width assertion about right context.
    @type _doc: C{string}
    @ivar _doc: A short human-readable string describing the function
          of the rule.
    """

    def __init__(self, target, action, **kwargs):
        self._target = target
        self._action = action
        self._left = self._right = self._doc = ''
        if kwargs.has_key('left'):
            self._left = kwargs['left']
        if kwargs.has_key('right'):
            self._right = kwargs['right']
        self._pattern = re.compile(
            _lookbehind(self._left) + self._target + _lookahead(self._right))
        if kwargs.has_key('doc'):
            self._doc = kwargs['doc']
    def pattern(self):
        return self._pattern
    def action(self):
        return self._action
    def doc(self):
        return self._doc
    def __str__(self):
        return self.doc() + ":\n"\
               + "left:   " + self._left + "\n"\
               + "target: " + self._target + "\n"\
               + "right:  " + self._right + "\n"\
               + "action: " + self.action()

##//////////////////////////////////////////////////////
##  Abstract Chunk Rules
##//////////////////////////////////////////////////////

# A version of ChunkRule which understands a simplified regexp syntax
# in which users don't need to know about locations, and in which <>
# functions as anonymous brackets, both with respect to the tags
# it contains (e.g. <DT|JJ>) and with respect to external operators
# (e.g. <JJ>*)

def expand(str):
    str = sub(r'<([^>]+)>', r'(?:<[^/]*/(?:\1)@\d+>)', str)
    str = sub(r'\.', r'[^>]', str)
    return str

# Calls expand on the left, target and right arguments.
# Could this duplicate less of the ChunkRule constructor?
# Bug: Note that the lookbehind assertion won't work since
# Python won't allow variable width lookbehind assertions
class AbstractChunkRule(ChunkRule):
    def __init__(self, target, action, **kwargs):
        self._target = expand(target)
        self._action = action
        self._left = self._right = self._doc = ''
        if kwargs.has_key('left'):
            self._left = expand(kwargs['left'])
        if kwargs.has_key('right'):
            self._right = expand(kwargs['right'])
        self._pattern = re.compile(
            _lookbehind(self._left) + self._target + _lookahead(self._right))
        if kwargs.has_key('doc'):
            self._doc = kwargs['doc']

##//////////////////////////////////////////////////////
##  Chunk Parser Utility Functions
##//////////////////////////////////////////////////////

def format(str):
    """
    Format a string of tokens for display.

    This function inserts space characters in a token string, so
    that different chunkings of the same token string will line up
    when displayed one underneath the other.  This is convenient for
    diagnostics which show the progress of a chunk parser.

    @return: a formatted version of the token string for display
    @rtype: C{string}
    @param str: The token string to be formatted
    @type str: C{string}
    """
    str = sub(r' +', '', str)
    str = sub(r'@\d+', '', str)
    str = sub(r'<[^/]+/', '<', str)
    str = sub(r'<', ' <', str)
    str = sub(r'>', '> ', str)
    str = sub(r'> }', '>}', str)
    str = sub(r'{ <', '{<', str)
    return str

# Bugs: assumes tags are strings and locations are unary,
# ignores the source and unit
def tag2str(tagged_sent):
    """
    Convert a tokenized, tagged sentence to a token string.

    @return: the token string version of the tokenized, tagged sentence
    @rtype: C{string}
    @param tagged_sent: the tokenized, tagged sentence
    @type tagged_sent: C{list} of C{TaggedToken}
    """

    str = ''
    for tok in tagged_sent:
        str += '<' + tok.type().base() + '/' + tok.type().tag() + '@' + `tok.loc().start()` + '>'
    return str


# Precompiled regular expressions used by str2chunks

_re_braces = re.compile(r'[^{}]')
_re_matching_braces = re.compile(r'(\{\})*')
_re_punct_boundary = re.compile(r'([>}])(?=[<{])')
_re_token_rep = re.compile(r'<([^>]*)/([^>]*)@(\d+)>')
_re_chunks = re.compile(r'{([^}]*)}')

def str2chunks(str):
    """
    Convert a token string to a chunk structure.

    Take the token string, with embedded chunk delimiters, and
    build an executable expression which returns a chunk structure.
    E.g.: "{<the/DT@[1]><cat/NN@[2]>}<sat/VBD@[3]>"
    becomes: [ [ 'the'/'DT'@[1], 'cat'/'NN'@[2] ], 'sat'/'VBD'@[3] ]

    @return: the chunk structure for a chunked token string
    @rtype: C{list} of (C{TaggedToken} or (C{list} of C{TaggedToken}))
    @param str: the token string
    @type str: C{string}
    """

    braces = sub(_re_braces, '', str)
    if not match(_re_matching_braces, braces):
        print "ERROR: unbalanced or nested braces"

    # insert commas between closing and opening punctuation
    str = sub(_re_punct_boundary, r'\1, ', str)

    # generate code to build a token from the string representation of the token
    str = sub(_re_token_rep, r'Token(TaggedType("\1", "\2"), Location(\3, unit="word"))', str)

    # replace {} chunk syntax with [] list syntax
    str = sub(_re_chunks, r'[\1]', str)
    str = '[' + str + ']'
    return eval(str)

##//////////////////////////////////////////////////////
##  Chunk Parser
##//////////////////////////////////////////////////////

class REChunkParser(ChunkParserI):
    """
    A chunk parser.  It is initialized with a cascade of chunk rules, and
    knows how to apply these rules to the string representation of a sequence
    of tokens.

    @type _rulelist: C{list} of C{ChunkRule}s.
    @ivar _rulelist: The cascade of chunk rules to be applied.
    @type _debug: C{int}
    @ivar _debug: The debug flag
    """

    def __init__(self, rulelist, debug=0):
        """
        Construct a new chunk parser.

        @param rulelist: The cascade of chunk rules to be applied.
        @type rulelist: C{list} of C{ChunkRule}
        @param debug: The debug flag
        @type debug: C{int}
        """
        self._rulelist = rulelist
        self._debug = debug

    def _diagnostic(self, rule, str, result):
        print
        print rule
        print "input: ", format(str)
        print "   ->  ", format(result)

    def _apply(self, rule, str):
        action = rule.action()
        pattern = rule.pattern()
        result = sub(pattern, action, str)
        if self._debug:
            self._diagnostic(rule, str, result)
        return result

    def parse(self, tagged_sent):
        """
        Chunk parse a tagged, tokenized sentence.

        @param tagged_sent: the tagged, tokenized sentence.
        @type tagged_sent: C{list} of C{TaggedToken}
        @return: a chunk structure
        @rtype: C{list} of (C{TaggedToken} or (C{list} of C{TaggedToken}))
        """
        str = tag2str(tagged_sent)
        for rule in self._rulelist:
            str = self._apply(rule, str)
        return str2chunks(str)

##//////////////////////////////////////////////////////
##  Evaluation Code
##//////////////////////////////////////////////////////

def unchunk(chunked_sent):
    """
    Unchunk a chunked sentence.

    This function removes the nested-list structure, to create a flat list.

    @param chunked_sent: a chunk structure
    @type chunked_sent: C{list} of (C{TaggedToken} or (C{list} of C{TaggedToken}))
    @return: a list of tagged tokens
    @rtype: C{list} of C{TaggedToken}
    """
    unchunked_sent = []
    for token in chunked_sent:
        if _pytype(token) == _pytype([]):
            unchunked_sent.extend(token)
        else:
            unchunked_sent.append(token)
    return unchunked_sent

def score(correct_chunks, guessed_chunks):
    """
    Given a correctly chunked sentence, score another chunked sentence.
    
    For each chunked sentence, this function extracts the chunk locations,
    puts them into two sets, then reports the precision, recall and F measure.

    @param correct_chunks: a chunk structure
    @type correct_chunks: C{list} of (C{TaggedToken} or (C{list} of C{TaggedToken}))
    @param guessed_chunks: a chunk structure
    @type guessed_chunks: C{list} of (C{TaggedToken} or (C{list} of C{TaggedToken}))
    """
    correct_locs = _chunk_locs(correct_chunks)
    guessed_locs = _chunk_locs(guessed_chunks)
    correct = Set(*correct_locs) # convert to a set
    guessed = Set(*guessed_locs)
    print "CORRECT:   ", correct
    print "GUESS:     ", guessed
    print "PRECISION: ", correct.precision(guessed)
    print "RECALL:    ", correct.recall(guessed)
    print "F MEASURE: ", correct.f_measure(guessed)

##//////////////////////////////////////////////////////
##  Demonstration code
##//////////////////////////////////////////////////////

# get the location of a tokenized sequence
def _seq_loc(tok_sent):
    return TreeToken('xyzzy', *tok_sent).loc()

# get the locations of chunks in a chunked sentence
def _chunk_locs(chunked_sent):
    locs = []
    for token in chunked_sent:
        if _pytype(token) == _pytype([]):
            locs.append(_seq_loc(token))
    return locs

from nltk.set import *
def demo():

    # the canonical sentence, as if it came from a file
    correct_sent = """
    [ the/DT little/JJ cat/NN ]
    sat/VBD on/IN
    [ the/DT mat/NN ]
    """

    # process the canonical sentence to get the chunk locations
    ctt = ChunkedTaggedTokenizer()
    correct_chunked_sent = ctt.tokenize(correct_sent)

    # get an unchunked version of the sentence
    unchunked_sent = unchunk(correct_chunked_sent)

    r1 = AbstractChunkRule(r'(<DT><JJ>*<NN>)', r'{\1}', doc="chunking <DT><JJ>*<NN>")
    cp = REChunkParser([r1])
    chunked_sent = cp.parse(unchunked_sent)
    score(correct_chunked_sent, chunked_sent)

    r1 = AbstractChunkRule(r'(<.*>)', r'{\1}', doc="chunking every tag")

    EXCL = r'<VB.*|IN>'
    r2 = AbstractChunkRule('{('+EXCL+')}', r'\1', doc="chinking VB* and IN")

    DT_JJ_NNX = r'<DT|JJ|NN.*>'
    r3 = AbstractChunkRule('('+DT_JJ_NNX+')}{', r'\1', right=DT_JJ_NNX,
                doc="chunk any groups of <DT> <JJ> and <NNX>")

    cp = REChunkParser([r1,r2,r3])
    chunked_sent = cp.parse(unchunked_sent)
    score(correct_chunked_sent, chunked_sent)

if __name__ == '__main__': demo()
