# Natural Language Toolkit: A Chunk Parser
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Steven Bird <sb@ldc.upenn.edu>
# Major Revisions: Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""
Defines a regular-expression based chunk parser, and several
supporting classes and functions.  The chunk parser itself is
implemented by the C{REChunkParser} class, which implements the
C{ChunkParserI} interface.  See the reference documentation for
C{nltk.chunkparser} for more information about the C{ChunkParserI}
interface.

C{REChunkParser} defines the C{parse} method.  This method identifies
linguistic groups in a text.  Its input is a list of tagged tokens;
its output is a X{chunk structure}, or a list containing tagged tokens
and lists of tagged tokens.

The C{parse} method first constructs a C{ChunkString}, which encodes a
particular chunking of the input text.  Initially, nothing is chunked.
The C{REChunkParser} then applies a sequence of C{REChunkParserRule}s
to the C{ChunkString}, each of which modifies the chunking that it
encodes.  Finally, the C{ChunkString} is used to construct a chunk
structure, which is returned.

REChunkParserRules
==================

C{REChunkParserRule}s define the C{apply} method, which modifies the
chunking encoded by a C{ChunkString}.  For example, a
C{REChunkParserRule} might chunk every token with a given tag.  The
C{REChunkParserRule} class itself can be used to implement any
transformational rule based on regular expressions.  There are also a
number of subclasses, which can be used to implement simpler types of
rules:

  - C{ChunkRule} chunks anything that matches a given regular
    expression.
  - C{ChinkRule} chunks anything that matches a given regular
    expression.
  - C{UnChunkRule} will un-chunk any chunk that matches a given
    regular expression.
  - C{MergeRule} will merge any two contiguous chunks that match a
    given regular expression.
  - C{SplitRule} can be used to split a chunk in two pieces

Tag Patterns
------------

C{REChunkParserRule}s use a modified version of regular expression
patterns, called X{tag patterns}.  Tag patterns are used to match
sequences of tags.  Examples of tag patterns are::

    r'(<DT>|<JJ>|<NN>)+'
    r'<NN>+'
    r'<NN.*>'

The differences between regular expression patterns and tag patterns
are:

    - In tag patterns, C{'<'} and C{'>'} act as parenthases; so
      C{'<NN>+'} matches one or more repetitions of C{'<NN>'}, not
      C{'<NN'} followed by one or more repetitions of C{'>'}.
    - Whitespace in tag patterns is ignored.  So
      C{'<DT> | <NN>'} is equivalant to C{'<DT>|<NN>'}
    - In tag patterns, C{'.'} is equivalant to C{'[^{}<>]'}; so
      C{'<NN.*>'} matches any single tag starting with C{'NN'}.

Helper Functions
================

The C{unchunk} method can be used to convert a chunk structure to a
list of tagged tokens.  This is useful for testing C{REChunkParser}s.
The C{score} method can be used to report statistics on the
performance of a C{REChunkParser}.

Efficiency
==========

Preliminary tests indicate that C{REChunkParser} can chunk at a rate
of about 300 tokens/second, with a moderately complex rule set.

There may be problems if C{REChunkParser} is used with more than
5,000 tokens at a time.  In particular, evaluation of some regular
expressions may cause the Python regular expression engine to exceed
its maximum recursion depth.  We have attempted to minimize these
problems, but it is impossible to avoid them completely.

Fun with emacs
==============

The following will colorize tags and bracketing when you use an
interactive python shell with emacs ("C-C !")::

   (defconst comint-mode-font-lock-keywords 
     '(("<[^>]+>" 0 'font-lock-reference-face)
       ("[{}]" 0 'font-lock-function-name-face)))
   (add-hook 'comint-mode-hook (lambda () (turn-on-font-lock)))

@type _VALID_CHUNK_STRING: C{regexp}
@var _VALID_CHUNK_STRING: A regular expression to test whether a chunk
     string is valid.
@type _VALID_TAG_PATTERN: C{regexp}
@var _VALID_TAG_PATTERN: A regular expression to test whether a tag
     pattern is valid.
"""

from nltk.token import Token
from nltk.tree import TreeToken
from nltk.chunkparser import ChunkParserI, ChunkedTaggedTokenizer
from nltk.set import Set

import re
import string

##//////////////////////////////////////////////////////
##  Thoughts/comments
##//////////////////////////////////////////////////////

"""
Terms/representations that should be defined in module docstring:
  - chunk = a list of tagged tokens
  - ttoklist = a list of tagged tokens (=chunk, but used in different
    contexts) 
  - chunklist = a list of tagged tokens and chunks
  - ChunkString = string rep of chunked tags
  - tag pattern = a regexp pattern over tags.  Has slightly different
    rules than normal regexps (since it gets translated): <> act like
    parens, . gets \w, etc.

High priority:
  - More checking?
      - _verify
      - check the tag patterns

Medium priority:
  - generalize ChunkString constructor to accept a chunk list?
  - rename ChunkString?
  - rename "chunklist" to "chunkstruct", to better cohere with the
    terminology used in chunkparser.py?
  - should ChunkString have a str-ish method? (that returns its
    internal rep)
  - Add more documentation explaining precompiled regexps.
  - In order to conform to interfaces, we might want to change reps:
    - chunkparser output as a tree
    - chunkedtaggedtokenizer should produce a list of tokens
  - IN_CHINK_PATTERN, IN_CHUNK_PATTERN exceed maximum recursion depth
    when we try to do chunking above the sentence level (~1000-2000
    words).  Grr. :)  So maybe we need a sentence tokenizer?  Or
    something?  

Low priority:
  - Efficiency issues? (currently we do ~500-1500 tokens/sec; faster
    when we chunk more text at a time)

Questions:
  - Should ChunkString be made immutable?

Indication of current efficiency::

  TIMING TEST (3 rules: chunk/unchunk/merge)
  1 x 10008 words:
      Time = 15.3654409647
  8 x 1260 words:
      Time = 10.0115730762
  27 x 372 words:
      Time = 9.67810499668
  64 x 168 words:
      Time = 10.1981619596
  125 x 84 words:
      Time = 10.1149849892
  216 x 48 words:
      Time = 10.5362759829
  343 x 36 words:
      Time = 12.9556429386
  512 x 24 words:
      Time = 13.6545710564
  729 x 24 words:
      Time = 19.4766739607
  1000 x 12 words:
      Time = 16.0188289881

"""

##//////////////////////////////////////////////////////
##  Precompiled regular expressions
##//////////////////////////////////////////////////////

_TAGCHAR = r'[^\{\}<>]'
_TAG = r'(<%s+?>)' % _TAGCHAR
_VALID_TAG_PATTERN = re.compile(r'^((%s|<%s>)+)$' %
                                ('[^\{\}<>]+',
                                 '[^\{\}<>]+'))

##//////////////////////////////////////////////////////
##  ChunkString
##//////////////////////////////////////////////////////

class ChunkString:
    """
    A string-based encoding of a particular chunking of a text.
    Internally, the C{ChunkString} class uses a single string to
    encode the chunking of the input text.  This string contains a
    sequence of angle-bracket delimited tags, with chunking indicated
    by braces.  An example of this encoding is::

        {<DT><JJ><NN>}<VBN><IN>{<DT><NN>}<.>{<DT><NN>}<VBD><.>

    C{ChunkString} are created from tagged texts (i.e., C{list}s of
    C{tokens} whose type is C{TaggedType}).  Initially, nothing is
    chunked.
    
    The chunking of a C{ChunkString} can be modified with the C{xform}
    method, which uses a regular expression to transform the string
    representation.  These transformations should only add and remove
    braces; they should I{not} modify the sequence of angle-bracket
    delimited tags.

    @type _str: C{string}
    @ivar _str: The internal string representation of the text's
        encoding.  This string representation contains a sequence of
        angle-bracket delimited tags, with chunking indicated by
        braces.  An example of this encoding is::

            {<DT><JJ><NN>}<VBN><IN>{<DT><NN>}<.>{<DT><NN>}<VBD><.>

    @type _ttoks: C{list} of C{Token}
    @ivar _ttoks: The text whose chunking is encoded by this
        C{ChunkString}.
    @ivar _debug: The debug level.  See the constructor docs.
               
    @cvar IN_CHUNK_PATTERN: A zero-width regexp pattern string that
        will only match positions that are in chunks.
    @cvar IN_CHINK_PATTERN: A zero-width regexp pattern string that
        will only match positions that are in chinks.
    """
    IN_CHUNK_PATTERN = r'(?=[^\{]*\})'
    IN_CHINK_PATTERN = r'(?=[^\}]*(\{|$))'

    # These are used by _verify
    _CHUNK = r'(\{%s+?\})+?' % _TAG
    _CHINK = r'(%s+?)+?' % _TAG
    _VALID = re.compile(r'(\{?%s\}?)+?' % _TAG)
    _BRACKETS = re.compile('[^\{\}]+')
    _BALANCED_BRACKETS = re.compile(r'(\{\})*$')
    
    def __init__(self, tagged_tokens, debug_level=3):
        """
        Construct a new C{ChunkString} that encodes the chunking of
        the text C{tagged_tokens}.

        @type tagged_tokens: C{list} of C{Token} with C{TaggedType}s
        @ivar tagged_tokens: The text whose chunking is encoded by
            this C{ChunkString}.  
        @type debug_level: int
        @var debug_level: The level of debugging which should be
            applied to transformations on the C{ChunkString}.  The
            valid levels are:
                0. no checks
                1. full check on to_chunklist
                2. full check on to_chunklist and cursory check after
                   each transformation. 
                3. full check on to_chunklist and full check after
                   each transformation.
            We recommend you use at least level 1.  You should
            probably use level 3 if you use any non-standard
            subclasses of C{REChunkParserRule}.
        """
        self._ttoks = tagged_tokens
        tags = [tok.type().tag() for tok in tagged_tokens]
        self._str = '<'+string.join(tags, '><')+'>'
        self._debug = debug_level

    def _verify(self, verify_tags):
        """
        Check to make sure that _str still corresponds to some chunked
        version of _ttoks.

        @raise ValueError: if this C{ChunkString}'s internal string
            representation is invalid or not consistant with _ttoks.
        """
        # Check overall form
        if not ChunkString._VALID.match(self._str):
            raise ValueError('Transformation generated invalid chunkstring')

        # Check that parens are balanced.  If the string is long, we
        # have to do this in pieces, to avoid a maximum recursion
        # depth limit for regular expressions.
        brackets = ChunkString._BRACKETS.sub('', self._str)
        for i in range(1+len(brackets)/5000):
            substr = brackets[i*5000:i*5000+5000]
            if not ChunkString._BALANCED_BRACKETS.match(substr):
                raise ValueError('Transformation generated invalid '+
                                 'chunkstring')

        if verify_tags<=0: return
        
        tags1 = (re.split(r'[\{\}<>]+', self._str))[1:-1]
        tags2 = [tok.type().tag() for tok in self._ttoks]
        if tags1 != tags2:
            raise ValueError('Transformation generated invalid chunkstring')

    def to_chunklist(self):
        """
        @return: the chunk structure encoded by this C{ChunkString}.
        @rtype: chunk structure
        """
        if self._debug > 0: self._verify(1)
            
        # Extract a list of alternating chinks & chunks
        pieces = re.split('[{}]', self._str)

        # Use this alternating list to create the chunklist.
        chunklist = []
        index = 0
        piece_in_chunk = 0
        for piece in pieces:

            # Find the list of tokens contained in this piece.
            length = piece.count('<')
            subsequence = self._ttoks[index:index+length]

            # Add this list of tokens to our chunklist.
            if piece_in_chunk:
                chunklist.append(subsequence)
            else:
                chunklist += subsequence

            # Update index, piece_in_chunk
            index += length
            piece_in_chunk = not piece_in_chunk

        return chunklist
                
    def xform(self, regexp, repl):
        """
        Apply the given transformation to this C{ChunkString}'s string
        encoding.  In particular, find all occurances that match
        C{regexp}, and replace them using C{repl} (as done by
        C{re.sub}).

        This transformation should only add and remove braces; it
        should I{not} modify the sequence of angle-bracket delimited
        tags.  Furthermore, this transformation may not result in
        improper bracketing.  Note, in particular, that bracketing may
        not be nested.

        @type regexp: C{string} or C{regexp}
        @param regexp: A regular expression matching the substring
            that should be replaced.  This will typically include a
            named group, which can be used by C{repl}.
        @type repl: C{string}
        @param repl: An expression specifying what should replace the
            matched substring.  Typically, this will include a named
            replacement group, specified by C{regexp}.
        @rtype: C{None}
        """
        # Do the actual substitution
        self._str = re.sub(regexp, repl, self._str)

        # The substitution might have generated "empty chunks"
        # (substrings of the form "{}").  Remove them, so they don't
        # interfere with other transformations.
        self._str = re.sub('\{\}', '', self._str)

        # Make sure that the transformation was legal.
        if self._debug > 1: self._verify(self._debug-2)

    def xform_chunk(self, pattern, repl):
        # Docstring adopted from xform's docstring.
        """
        Apply the given transformation to the chunks in this
        C{ChunkString}'s string encoding.  In particular, find all
        occurances within chunks that match C{regexp}, and replace
        them using C{repl} (as done by C{re.sub}).

        This transformation should only add and remove braces; it
        should I{not} modify the sequence of angle-bracket delimited
        tags.  Furthermore, this transformation may not result in
        improper bracketing.  Note, in particular, that bracketing may
        not be nested.

        @type regexp: C{string} or C{regexp}
        @param regexp: A regular expression matching the substring
            that should be replaced.  This will typically include a
            named group, which can be used by C{repl}.
        @type repl: C{string}
        @param repl: An expression specifying what should replace the
            matched substring.  Typically, this will include a named
            replacement group, specified by C{regexp}.
        @rtype: C{None}
        """
        self.xform(pattern+ChunkString.IN_CHUNK_PATTERN, repl)

    def xform_chink(self, pattern, repl):
        # Docstring adopted from xform's docstring.
        """
        Apply the given transformation to the chinks in this
        C{ChinkString}'s string encoding.  In particular, find all
        occurances within chinks that match C{regexp}, and replace
        them using C{repl} (as done by C{re.sub}).

        This transformation should only add and remove braces; it
        should I{not} modify the sequence of angle-bracket delimited
        tags.  Furthermore, this transformation may not result in
        improper bracketing.  Note, in particular, that bracketing may
        not be nested.

        @type regexp: C{string} or C{regexp}
        @param regexp: A regular expression matching the substring
            that should be replaced.  This will typically include a
            named group, which can be used by C{repl}.
        @type repl: C{string}
        @param repl: An expression specifying what should replace the
            matched substring.  Typically, this will include a named
            replacement group, specified by C{regexp}.
        @rtype: C{None}
        """
        self.xform(pattern+ChunkString.IN_CHINK_PATTERN, repl)

    def __repr__(self):
        """
        @rtype: C{string}
        @return: A string representation of this C{ChunkString}
        """
        return '<ChunkString: %s>' % `self._str`

    def __str__(self):
        """
        @rtype: C{string}
        @return: A formatted representation of this C{ChunkString}'s
            string encoding.  This representation will include extra
            spaces to ensure that tags will line up with the
            representation of other C{ChunkStrings} for the same text,
            regardless of the chunking.
        """
        str = re.sub(r'>(?!\})', '> ', self._str)
        str = re.sub(r'(?<!\{)<', ' <', str)
        if str[0] == '<': str = ' ' + str
        return str

##//////////////////////////////////////////////////////
##  Rules
##//////////////////////////////////////////////////////

def _clean(pattern):
    """
    Convert a regular expression pattern over tags into its cannonical
    form:

        - Replace '.' with _TAGCHAR (so it doesn't match '[<>{}]')
        - Remove any whitespace
        - Add extra parens around '<' and '>', to make '<' and '>' act
          like parenthases.  E.g., so that in '<NN>+', the '+' has scope
          over the entire '<NN>'; and so that in '<NN|IN>', the '|' has
          scope over 'NN' and 'IN', but not '<' or '>'.
        - Check to make sure the resulting pattern is valid.
    """
    # Clean up the regular expression
    pattern = re.sub(r'\s', '', pattern)
    pattern = re.sub(r'<', '(<(', pattern)
    pattern = re.sub(r'>', ')>)', pattern)

    # Check the regular expression
    if not _VALID_TAG_PATTERN.match(pattern):
        raise ValueError('Bad pattern: %s' % pattern)

    # We have to do this after, since it adds {}[]<>s
    pattern = re.sub(r'\.', _TAGCHAR, pattern)
    return pattern

class REChunkParserRule:
    """
    A rule specifying how to update the chunking in a C{ChunkString}.
    The C{apply} method is used to modify the chunking encoded by a
    C{ChunkString}.  The C{REChunkParserRule} class itself can be used
    to implement any transformational rule based on regular
    expressions.  There are also a number of subclasses, which can be
    used to implement simpler types of rules.
    """
    def __init__(self, regexp, repl, descr):
        """
        @type regexp: C{regexp}
        """
        self._repl = repl
        self._descr = descr
        if type(regexp) == type(''):
            self._regexp = re.compile(regexp)
        else:
            self._regexp = regexp

    def apply(self, chunkstr):
        """
        Apply this rule to the given C{ChunkString}.
        """
        chunkstr.xform(self._regexp, self._repl)

    def descr(self):
        # Inherit docs from REChunkParserRule
        return self._descr

    def __repr__(self):
        return ('<ChunkRule: '+`self._regexp.pattern`+
                '->'+`self._repl`+'>')
        
class ChunkRule(REChunkParserRule):
    def __init__(self, tag_pattern, descr):
        self._pattern = tag_pattern
        regexp = re.compile('(?P<chunk>'+_clean(tag_pattern)+')'+
                            ChunkString.IN_CHINK_PATTERN)
        REChunkParserRule.__init__(self, regexp, '{\g<chunk>}', descr)

    def __repr__(self):
        return '<ChunkRule: '+`self._pattern`+'>'

class ChinkRule(REChunkParserRule):
    def __init__(self, tag_pattern, descr):
        self._pattern = tag_pattern
        regexp = re.compile('(?P<chink>'+_clean(tag_pattern)+')'+
                            ChunkString.IN_CHUNK_PATTERN)
        REChunkParserRule.__init__(self, regexp, '}\g<chink>{', descr)

    def __repr__(self):
        return '<ChinkRule: '+`self._pattern`+'>'

class UnChunkRule(REChunkParserRule):
    def __init__(self, tag_pattern, descr):
        self._pattern = tag_pattern
        regexp = re.compile('\{(?P<chunk>'+_clean(tag_pattern)+')\}')
        REChunkParserRule.__init__(self, regexp, '\g<chunk>', descr)

    def __repr__(self):
        return '<UnChunkRule: '+`self._pattern`+'>'

class MergeRule(REChunkParserRule):
    def __init__(self, left_tag_pattern, right_tag_pattern, descr):
        self._left_tag_pattern = left_tag_pattern
        self._right_tag_pattern = right_tag_pattern
        regexp = re.compile('(?P<left>'+_clean(left_tag_pattern)+')'+
                            '}{(?='+_clean(right_tag_pattern)+')')
        REChunkParserRule.__init__(self, regexp, '\g<left>', descr)

    def __repr__(self):
        return ('<MergeRule: '+`self._left_tag_pattern`+', '+
                `self._right_tag_pattern`+'>')

class SplitRule(REChunkParserRule):
    def __init__(self, left_tag_pattern, right_tag_pattern, descr):
        self._left_tag_pattern = left_tag_pattern
        self._rigthpattern = right_tag_pattern
        regexp = re.compile('(?P<left>'+_clean(left_tag_pattern)+')'+
                            '(?='+_clean(right_tag_pattern)+')')
        REChunkParserRule.__init__(self, regexp, '\g<left>\}\{', descr)

    def __repr__(self):
        return ('<MergeRule: '+`self._left_tag_pattern`+', ',
                `self._right_tag_pattern`+'>')

##//////////////////////////////////////////////////////
##  REChunkParser
##//////////////////////////////////////////////////////

class REChunkParser:
    def __init__(self, rules, trace=0):
        """
        @type rules: C{list} of C{REChunkParserRule}
        """
        self._rules = rules
        self._trace = trace

    def _trace_apply(self, chunkstr, tagged_sentence, verbose):
        indent = ' '*(35-len(str(chunkstr))/2)
        
        print '\nInput:'
        print indent, chunkstr
        for rule in self._rules:
            rule.apply(chunkstr)
            if verbose:
                print rule.descr()+' ('+`rule`+'):'
            else:
                print rule.descr()+':'
            print indent, chunkstr
        return chunkstr.to_chunklist()
        
    def _notrace_apply(self, chunkstr, tagged_sentence):
        for rule in self._rules:
            rule.apply(chunkstr)
        return chunkstr.to_chunklist()
        
    def parse(self, tagged_sentence, trace=0):
        chunkstr = ChunkString(tagged_sentence)
        if trace or self._trace:
            verbose = (trace>1 or self._trace>1)
            self._trace_apply(chunkstr, tagged_sentence, verbose)
        else:
            self._notrace_apply(chunkstr, tagged_sentence)
        return chunkstr.to_chunklist()
                             
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
        if isinstance(token, Token):
            unchunked_sent.append(token)
        else:
            unchunked_sent.extend(token)
    return unchunked_sent

def score(correct_chunks, guessed_chunks, verbosity=1):
    """
    Given a correctly chunked sentence, score another chunked sentence.
    
    For each chunked sentence, this function extracts the chunk locations,
    puts them into two sets, then reports the precision, recall and F measure.

    @param correct_chunks: a chunk structure
    @type correct_chunks: C{list} of (C{TaggedToken} or
        (C{list} of C{TaggedToken}))
    @param guessed_chunks: a chunk structure
    @type guessed_chunks: C{list} of (C{TaggedToken} or
        (C{list} of C{TaggedToken}))
    """
    correct_locs = _chunk_locs(correct_chunks)
    guessed_locs = _chunk_locs(guessed_chunks)
    correct = Set(*correct_locs) # convert to a set
    guessed = Set(*guessed_locs)
    missed = correct - guessed
    wrong = guessed - correct
    if ((len(correct) < 50 and verbosity >= 2) or (verbosity > 3)):
        print "CORRECT:   ", correct
    if ((len(guessed) < 50 and verbosity >= 2) or (verbosity > 3)):
        print "GUESS:     ", guessed
    if ((len(missed) < 50 and verbosity >= 1) or (verbosity > 2)):
        print "MISSED:    ", missed
    if ((len(wrong) < 50 and verbosity >= 1) or (verbosity > 2)):
        print "INCORRECT: ", wrong
        
    print "PRECISION: ", correct.precision(guessed)
    print "RECALL:    ", correct.recall(guessed)
    print "F MEASURE: ", correct.f_measure(guessed)

##//////////////////////////////////////////////////////
##  Demonstration code
##//////////////////////////////////////////////////////

# get the location of a tokenized sequence
def _seq_loc(tok_sent):
    return TreeToken('xyzzy', *tok_sent).loc()

def _unify(tok_sent):
    words = [tok.type().base() for tok in tok_sent]
    str = ' '.join(words)
    return Token(str, _seq_loc(tok_sent))

# get the locations of chunks in a chunked sentence
def _chunk_locs(chunked_sent):
    locs = []
    for piece in chunked_sent:
        if type(piece) == type([]):
            #locs.append(_seq_loc(piece))
            locs.append(_unify(piece))
    return locs

NUM=1
import time
def demo():

    # the canonical sentence, as if it came from a file
    correct_sent = """
    [ the/DT little/JJ cat/NN ]
    sat/VBD on/IN
    [ the/DT mat/NN ] ./.
    [ the/DT cat/NN ] sat/VBD ./.
    """

    # process the canonical sentence to get the chunk locations
    ctt = ChunkedTaggedTokenizer()
    correct_chunked_sent = ctt.tokenize(correct_sent)*NUM

    # get an unchunked version of the sentence
    unchunked_sent = unchunk(correct_chunked_sent)

    print len(unchunked_sent), 'Words'
    print len(unchunked_sent)/4, 'Chunks'
    
    t = time.time()
    r1 = ChunkRule(r'<DT><JJ>*<NN>', 'Chunk NPs')
    cp = REChunkParser([r1])
    chunked_sent = cp.parse(unchunked_sent, 1)
    score(correct_chunked_sent, chunked_sent)
    print 'TIME:', time.time()-t
    t = time.time()

    r1 = ChunkRule(r'<.*>+', 'Chunk everything')
    r2 = ChinkRule(r'<VB.*>|<IN>', 'Chink VB?s and INs')
    cp = REChunkParser([r1, r2])
    chunked_sent = cp.parse(unchunked_sent, 1)
    score(correct_chunked_sent, chunked_sent)
    print 'TIME:', time.time()-t
    t = time.time()

    r1 = ChunkRule(r'(<.*>)', 'Chunk each tag')
    r2 = UnChunkRule(r'<VB.*>|<IN>', 'Unchunk VB? and INs')
    r3 = MergeRule(r'<DT|JJ|NN.*>', r'<DT|JJ|NN.*>', 'Merge NPs')
    cp = REChunkParser([r1,r2,r3])
    chunked_sent = cp.parse(unchunked_sent, 1)
    score(correct_chunked_sent, chunked_sent)
    print 'TIME:', time.time()-t

if __name__ == '__main__': demo()

