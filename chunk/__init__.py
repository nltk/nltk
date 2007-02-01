# Natural Language Toolkit: Chunkers
#
# Copyright (C) 2001-2007 University of Pennsylvania
# Author: Steven Bird <sb@csse.unimelb.edu.au>
#         Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#

"""
Classes and interfaces for identifying non-overlapping linguistic
groups (such as base noun phrases) in unrestricted text.  This task is
called X{chunk parsing} or X{chunking}, and the identified groups are
called X{chunks}.  The chunked text is represented using a shallow
tree called a "chunk structure."  A X{chunk structure} is a tree
containing tokens and chunks, where each chunk is a subtree containing
only tokens.  For example, the chunk structure for base noun phrase
chunks in the sentence "I saw the big dog on the hill" is::

  (SENTENCE:
    (NP: <I>)
    <saw>
    (NP: <the> <big> <dog>)
    <on>
    (NP: <the> <hill>))

To convert a chunk structure back to a list of tokens, simply use the
chunk structure's L{leaves<Tree.leaves>} method.

The C{parser.chunk} module defines L{ChunkI}, a standard interface for
chunking texts; and L{RegexpChunk}, a regular-expression based
implementation of that interface.  It uses the L{tree.chunk} and
L{tree.conll_chunk} methods, which tokenize strings containing chunked
and tagged texts.  It defines L{ChunkScore}, a utility class for
scoring chunk parsers.

RegexpChunk
===========

C{parse.RegexpChunk} is an implementation of the chunk parser interface
that uses regular-expressions over tags to chunk a text.  Its
C{parse} method first constructs a C{ChunkString}, which encodes a
particular chunking of the input text.  Initially, nothing is
chunked.  C{parse.RegexpChunk} then applies a sequence of
C{RegexpChunkRule}s to the C{ChunkString}, each of which modifies
the chunking that it encodes.  Finally, the C{ChunkString} is
transformed back into a chunk structure, which is returned.

C{RegexpChunk} can only be used to chunk a single kind of phrase.
For example, you can use an C{RegexpChunk} to chunk the noun
phrases in a text, or the verb phrases in a text; but you can not
use it to simultaneously chunk both noun phrases and verb phrases in
the same text.  (This is a limitation of C{RegexpChunk}, not of
chunk parsers in general.)

RegexpChunkRules
----------------

C{RegexpChunkRule}s are transformational rules that update the
chunking of a text by modifying its C{ChunkString}.  Each
C{RegexpChunkRule} defines the C{apply} method, which modifies
the chunking encoded by a C{ChunkString}.  The
L{RegexpChunkRule} class itself can be used to implement any
transformational rule based on regular expressions.  There are
also a number of subclasses, which can be used to implement
simpler types of rules:

    - L{ChunkRule} chunks anything that matches a given regular
      expression.
    - L{ChinkRule} chinks anything that matches a given regular
      expression.
    - L{UnChunkRule} will un-chunk any chunk that matches a given
      regular expression.
    - L{MergeRule} can be used to merge two contiguous chunks.
    - L{SplitRule} can be used to split a single chunk into two
      smaller chunks.
    - L{ExpandLeftRule} will expand a chunk to incorporate new
      unchunked material on the left.
    - L{ExpandRightRule} will expand a chunk to incorporate new
      unchunked material on the right.

Tag Patterns
~~~~~~~~~~~~

C{RegexpChunkRule}s use a modified version of regular
expression patterns, called X{tag patterns}.  Tag patterns are
used to match sequences of tags.  Examples of tag patterns are::

     r'(<DT>|<JJ>|<NN>)+'
     r'<NN>+'
     r'<NN.*>'

The differences between regular expression patterns and tag
patterns are:

    - In tag patterns, C{'<'} and C{'>'} act as parentheses; so
      C{'<NN>+'} matches one or more repetitions of C{'<NN>'}, not
      C{'<NN'} followed by one or more repetitions of C{'>'}.
    - Whitespace in tag patterns is ignored.  So
      C{'<DT> | <NN>'} is equivalant to C{'<DT>|<NN>'}
    - In tag patterns, C{'.'} is equivalant to C{'[^{}<>]'}; so
      C{'<NN.*>'} matches any single tag starting with C{'NN'}.

The function L{tag_pattern2re_pattern} can be used to transform
a tag pattern to an equivalent regular expression pattern.

Efficiency
----------

Preliminary tests indicate that C{RegexpChunk} can chunk at a
rate of about 300 tokens/second, with a moderately complex rule set.

There may be problems if C{RegexpChunk} is used with more than
5,000 tokens at a time.  In particular, evaluation of some regular
expressions may cause the Python regular expression engine to
exceed its maximum recursion depth.  We have attempted to minimize
these problems, but it is impossible to avoid them completely.  We
therefore recommend that you apply the chunk parser to a single
sentence at a time.

Emacs Tip
---------

If you evaluate the following elisp expression in emacs, it will
colorize C{ChunkString}s when you use an interactive python shell
with emacs or xemacs ("C-c !")::

    (let ()
      (defconst comint-mode-font-lock-keywords 
        '(("<[^>]+>" 0 'font-lock-reference-face)
          ("[{}]" 0 'font-lock-function-name-face)))
      (add-hook 'comint-mode-hook (lambda () (turn-on-font-lock))))

You can evaluate this code by copying it to a temporary buffer,
placing the cursor after the last close parenthesis, and typing
"C{C-x C-e}".  You should evaluate it before running the interactive
session.  The change will last until you close emacs.

Unresolved Issues
-----------------

If we use the C{re} module for regular expressions, Python's
regular expression engine generates "maximum recursion depth
exceeded" errors when processing very large texts, even for
regular expressions that should not require any recursion.  We
therefore use the C{pre} module instead.  But note that C{pre}
does not include Unicode support, so this module will not work
with unicode strings.  Note also that C{pre} regular expressions
are not quite as advanced as C{re} ones (e.g., no leftward
zero-length assertions).

@type CHUNK_TAG_PATTERN: C{regexp}
@var CHUNK_TAG_PATTERN: A regular expression to test whether a tag
     pattern is valid.
"""

import re, types
import types
from nltk_lite.parse import ParseI
from convert import tree2conlltags

##//////////////////////////////////////////////////////
##  Chunk Parser Interface
##//////////////////////////////////////////////////////

class ChunkParseI(ParseI):
    """
    A processing interface for identifying non-overlapping groups in
    unrestricted text.  Typically, chunk parsers are used to find base
    syntactic constituants, such as base noun phrases.  Unlike
    L{ParseI}, C{ChunkParseI} guarantees that the C{parse} method
    will always generate a parse.
    
    """
    def parse(self, tokens):
        """
        Find the best chunk structure for the given tokens
        and return a tree
        
        @param tokens: The list of (word, tag) tokens to be chunked.
        @type tokens: L{list} of L{tuple}
        """
        assert 0, "ChunkParseI is an abstract interface"

    def parse_n(self, tokens, n=None):
        """
        Find a list of the C{n} most likely chunk structures for the
        tokens, and return a tree.  If there are fewer than C{n}
        chunk structures, then find them all.  The chunk structures
        should be stored in descending order of estimated likelihood.
        
        @type n: C{int}
        @param n: The number of chunk structures to generate.  At most
           C{n} chunk structures will be generated.  If C{n} is not
           specified, generate all chunk structures.
        @type tokens: L{list} of L{tuple}
        @param tokens: The list of (word, tag) tokens to be chunked.
        """
        assert 0, "ChunkParseI is an abstract interface"
        

##//////////////////////////////////////////////////////
##  Precompiled regular expressions
##//////////////////////////////////////////////////////


CHUNK_TAG_CHAR = r'[^\{\}<>]'
CHUNK_TAG = r'(<%s+?>)' % CHUNK_TAG_CHAR


##//////////////////////////////////////////////////////
##  ChunkString
##//////////////////////////////////////////////////////

class ChunkString(object):
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

    @type _pieces: C{list} of pieces (tagged tokens and chunks)
    @ivar _pieces: The tagged tokens and chunks encoded by this C{ChunkString}.
    @ivar _debug: The debug level.  See the constructor docs.
               
    @cvar IN_CHUNK_PATTERN: A zero-width regexp pattern string that
        will only match positions that are in chunks.
    @cvar IN_CHINK_PATTERN: A zero-width regexp pattern string that
        will only match positions that are in chinks.
    """
    IN_CHUNK_PATTERN = r'(?=[^\{]*\})'
    IN_CHINK_PATTERN = r'(?=[^\}]*(\{|$))'

    # These are used by _verify
    _CHUNK = r'(\{%s+?\})+?' % CHUNK_TAG
    _CHINK = r'(%s+?)+?' % CHUNK_TAG
    _VALID = re.compile(r'(\{?%s\}?)*?' % CHUNK_TAG)
    _BRACKETS = re.compile('[^\{\}]+')
    _BALANCED_BRACKETS = re.compile(r'(\{\})*$')
    
    def __init__(self, chunk_struct, debug_level=3):
        """
        Construct a new C{ChunkString} that encodes the chunking of
        the text C{tagged_tokens}.

        @type chunk_struct: C{Tree}
        @param chunk_struct: The chunk structure to be further chunked.
        @type debug_level: int
        @param debug_level: The level of debugging which should be
            applied to transformations on the C{ChunkString}.  The
            valid levels are:
                - 0: no checks
                - 1: full check on to_chunkstruct
                - 2: full check on to_chunkstruct and cursory check after
                   each transformation. 
                - 3: full check on to_chunkstruct and full check after
                   each transformation.
            We recommend you use at least level 1.  You should
            probably use level 3 if you use any non-standard
            subclasses of C{RegexpChunkRule}.
        """
        self._top_node = chunk_struct.node
        self._pieces = chunk_struct[:]
        tags = [self._tag(tok) for tok in self._pieces]
        self._str = '<' + '><'.join(tags) + '>'
        self._debug = debug_level

    def _tag(self, tok):
        if type(tok) == types.TupleType:
            return tok[1]
        elif isinstance(tok, Tree):
            return tok.node
        else:
            raise ValueError, 'chunk structures must contain tokens and trees'
                      
    def _verify(self, verify_tags):
        """
        Check to make sure that C{_str} still corresponds to some chunked
        version of C{_pieces}.

        @type verify_tags: C{boolean}
        @param verify_tags: Whether the individual tags should be
            checked.  If this is false, C{_verify} will check to make
            sure that C{_str} encodes a chunked version of I{some}
            list of tokens.  If this is true, then C{_verify} will
            check to make sure that the tags in C{_str} match those in
            C{_pieces}.
        
        @raise ValueError: if this C{ChunkString}'s internal string
            representation is invalid or not consistent with _pieces.
        """
        # Check overall form
        if not ChunkString._VALID.match(self._str):
            raise ValueError('Transformation generated invalid chunkstring: %s' % self._str)

        # Check that parens are balanced.  If the string is long, we
        # have to do this in pieces, to avoid a maximum recursion
        # depth limit for regular expressions.
        brackets = ChunkString._BRACKETS.sub('', self._str)
        for i in range(1+len(brackets)/5000):
            substr = brackets[i*5000:i*5000+5000]
            if not ChunkString._BALANCED_BRACKETS.match(substr):
                raise ValueError('Transformation generated invalid chunkstring: %s' % substr)

        if verify_tags<=0: return
        
        tags1 = (re.split(r'[\{\}<>]+', self._str))[1:-1]
        tags2 = [self._tag(piece) for piece in self._pieces]
        if tags1 != tags2:
            raise ValueError('Transformation generated invalid chunkstring: %s / %s' % (tags1,tags2))

    def to_chunkstruct(self, chunk_node='CHUNK'):
        """
        @return: the chunk structure encoded by this C{ChunkString}.
        @rtype: C{Tree}
        @raise ValueError: If a transformation has generated an
            invalid chunkstring.
        """
        if self._debug > 0: self._verify(1)
            
        # Use this alternating list to create the chunkstruct.
        pieces = []
        index = 0
        piece_in_chunk = 0
        for piece in re.split('[{}]', self._str):

            # Find the list of tokens contained in this piece.
            length = piece.count('<')
            subsequence = self._pieces[index:index+length]

            # Add this list of tokens to our pieces.
            if piece_in_chunk:
                pieces.append(Tree(chunk_node, subsequence))
            else:
                pieces += subsequence

            # Update index, piece_in_chunk
            index += length
            piece_in_chunk = not piece_in_chunk

        return Tree(self._top_node, pieces)
                
    def xform(self, regexp, repl):
        """
        Apply the given transformation to this C{ChunkString}'s string
        encoding.  In particular, find all occurrences that match
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
        @raise ValueError: If this transformation generated an
            invalid chunkstring.
        """
        # Do the actual substitution

        self._str = re.sub(regexp, repl, self._str)

        # The substitution might have generated "empty chunks"
        # (substrings of the form "{}").  Remove them, so they don't
        # interfere with other transformations.
        self._str = re.sub('\{\}', '', self._str)

        # Make sure that the transformation was legal.
        if self._debug > 1: self._verify(self._debug-2)

    def __repr__(self):
        """
        @rtype: C{string}
        @return: A string representation of this C{ChunkString}.  This
            string representation has the form::
            
                <ChunkString: '{<DT><JJ><NN>}<VBN><IN>{<DT><NN>}'>
        
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
        # Add spaces to make everything line up.
        str = re.sub(r'>(?!\})', r'> ', self._str)
        str = re.sub(r'([^\{])<', r'\1 <', str)
        if str[0] == '<': str = ' ' + str
        return str


##//////////////////////////////////////////////////////
## EVALUATION
##//////////////////////////////////////////////////////

from nltk_lite import evaluate
def accuracy(chunker, gold):
    """
    Score the accuracy of the chunker against the gold standard.
    Strip the chunk information from the gold standard and rechunk it using
    the chunker, then compute the accuracy score.

    @type chunker: C{ChunkParseI}
    @param tagger: The chunker being evaluated.
    @type gold: C{tree}
    @param gold: The chunk structures to score the chunker on.
    @rtype: C{float}
    """

    gold_tags = []
    test_tags = []
    for gold_tree in gold:
        test_tree = chunker.parse(gold_tree.flatten())
        gold_tags += tree2conlltags(gold_tree)
        test_tags += tree2conlltags(test_tree)

#    print 'GOLD:', gold_tags[:50]
#    print 'TEST:', test_tags[:50]
    return evaluate.accuracy(gold_tags, test_tags)


# Patched for increased performance by Yoav Goldberg <yoavg@cs.bgu.ac.il>, 2006-01-13
#  -- statistics are evaluated only on demand, instead of at every sentence evaluation
#
# SB: use nltk_lite.evaluate for precision/recall scoring?
#
class ChunkScore(object):
    """
    A utility class for scoring chunk parsers.  C{ChunkScore} can
    evaluate a chunk parser's output, based on a number of statistics
    (precision, recall, f-measure, misssed chunks, incorrect chunks).
    It can also combine the scores from the parsing of multiple texts;
    this makes it signifigantly easier to evaluate a chunk parser that
    operates one sentence at a time.

    Texts are evaluated with the C{score} method.  The results of
    evaluation can be accessed via a number of accessor methods, such
    as C{precision} and C{f_measure}.  A typical use of the
    C{ChunkScore} class is::

        >>> chunkscore = ChunkScore()
        >>> for correct in correct_sentences:
        ...     guess = chunkparser.parse(correct.leaves())
        ...     chunkscore.score(correct, guess)
        >>> print 'F Measure:', chunkscore.f_measure()
        F Measure: 0.823

    @ivar kwargs: Keyword arguments:

        - max_tp_examples: The maximum number actual examples of true
          positives to record.  This affects the C{correct} member
          function: C{correct} will not return more than this number
          of true positive examples.  This does *not* affect any of
          the numerical metrics (precision, recall, or f-measure)

        - max_fp_examples: The maximum number actual examples of false
          positives to record.  This affects the C{incorrect} member
          function and the C{guessed} member function: C{incorrect}
          will not return more than this number of examples, and
          C{guessed} will not return more than this number of true
          positive examples.  This does *not* affect any of the
          numerical metrics (precision, recall, or f-measure)
        
        - max_fn_examples: The maximum number actual examples of false
          negatives to record.  This affects the C{missed} member
          function and the C{correct} member function: C{missed}
          will not return more than this number of examples, and
          C{correct} will not return more than this number of true
          negative examples.  This does *not* affect any of the
          numerical metrics (precision, recall, or f-measure)
        
    @type _tp: C{list} of C{Token}
    @ivar _tp: List of true positives
    @type _fp: C{list} of C{Token}
    @ivar _fp: List of false positives
    @type _fn: C{list} of C{Token}
    @ivar _fn: List of false negatives
    
    @type _tp_num: C{int}
    @ivar _tp_num: Number of true positives
    @type _fp_num: C{int}
    @ivar _fp_num: Number of false positives
    @type _fn_num: C{int}
    @ivar _fn_num: Number of false negatives.
    """
    def __init__(self, **kwargs):
        self._correct = set()
        self._guessed = set()
        self._tp = set()
        self._fp = set()
        self._fn = set()
        self._max_tp = kwargs.get('max_tp_examples', 100)
        self._max_fp = kwargs.get('max_fp_examples', 100)
        self._max_fn = kwargs.get('max_fn_examples', 100)
        self._tp_num = 0
        self._fp_num = 0
        self._fn_num = 0
        self._count = 0

        self._measuresNeedUpdate = False

    def _updateMeasures(self):
        if (self._measuresNeedUpdate):
           self._tp = self._guessed & self._correct
           self._fn = self._correct - self._guessed
           self._fp = self._guessed - self._correct
           self._tp_num = len(self._tp)
           self._fp_num = len(self._fp)
           self._fn_num = len(self._fn)
           self._measuresNeedUpdate = False

    def score(self, correct, guessed):
        """
        Given a correctly chunked sentence, score another chunked
        version of the same sentence.
        
        @type correct: chunk structure
        @param correct: The known-correct ("gold standard") chunked
            sentence.
        @type guessed: chunk structure
        @param guessed: The chunked sentence to be scored.
        """
	     
        self._correct |= _chunksets(correct, self._count)
        self._guessed |= _chunksets(guessed, self._count)
        self._count += 1
        self._measuresNeedUpdate = True

    def precision(self):
        """
        @return: the overall precision for all texts that have been
            scored by this C{ChunkScore}.
        @rtype: C{float}
        """
        self._updateMeasures()
        div = self._tp_num + self._fp_num
        if div == 0: return 0
        else: return float(self._tp_num) / div
    
    def recall(self):
        """
        @return: the overall recall for all texts that have been
            scored by this C{ChunkScore}.
        @rtype: C{float}
        """
        self._updateMeasures()
        div = self._tp_num + self._fn_num
        if div == 0: return 0
        else: return float(self._tp_num) / div
    
    def f_measure(self, alpha=0.5):
        """
        @return: the overall F measure for all texts that have been
            scored by this C{ChunkScore}.
        @rtype: C{float}
        
        @param alpha: the relative weighting of precision and recall.
            Larger alpha biases the score towards the precision value,
            while smaller alpha biases the score towards the recall
            value.  C{alpha} should have a value in the range [0,1].
        @type alpha: C{float}
        """
        self._updateMeasures()
        p = self.precision()
        r = self.recall()
        if p == 0 or r == 0:    # what if alpha is 0 or 1?
            return 0
        return 1/(alpha/p + (1-alpha)/r)
    
    def missed(self):
        """
        @rtype: C{list} of chunks
        @return: the chunks which were included in the
            correct chunk structures, but not in the guessed chunk
            structures, listed in input order.
        """
        self._updateMeasures()
        chunks = list(self._fn)
        return [c[1] for c in chunks]  # discard position information
    
    def incorrect(self):
        """
        @rtype: C{list} of chunks
        @return: the chunks which were included in the
            guessed chunk structures, but not in the correct chunk
            structures, listed in input order.
        """
        self._updateMeasures()
        chunks = list(self._fp)
        return [c[1] for c in chunks]  # discard position information
    
    def correct(self):
        """
        @rtype: C{list} of chunks
        @return: the chunks which were included in the correct
            chunk structures, listed in input order.
        """
        chunks = list(self._correct)
        return [c[1] for c in chunks]  # discard position information

    def guessed(self):
        """
        @rtype: C{list} of chunks
        @return: the chunks which were included in the guessed
            chunk structures, listed in input order.
        """
        chunks = list(self._guessed)
        return [c[1] for c in chunks]  # discard position information

    def __len__(self):
        self._updateMeasures()
        return self._tp_num + self._fn_num
    
    def __repr__(self):
        """
        @rtype: C{String}
        @return: a concise representation of this C{ChunkScoring}.
        """
        return '<ChunkScoring of '+`len(self)`+' chunks>'

    def __str__(self):
        """
        @rtype: C{String}
        @return: a verbose representation of this C{ChunkScoring}.
            This representation includes the precision, recall, and
            f-measure scores.  For other information about the score,
            use the accessor methods (e.g., C{missed()} and
            C{incorrect()}). 
        """
        return ("ChunkParse score:\n" +
                ("    Precision: %5.1f%%\n" % (self.precision()*100)) +
                ("    Recall:    %5.1f%%\n" % (self.recall()*100))+
                ("    F-Measure: %5.1f%%" % (self.f_measure()*100)))
        
    def _chunk_toks(self, text):
        """
        @return: The list of tokens contained in C{text}.
        """
        return [tok for tok in text if isinstance(tok, AbstractTree)]

# extract chunks, and assign unique id, the absolute position of
# the first word of the chunk
def _chunksets(t, count):
    pos = 0
    chunks = []
    for child in t:
        try:
            chunks.append(((count, pos), tuple(child.freeze())))
            pos += len(child)
        except AttributeError:
            pos += 1
    return set(chunks)



from regexp import *
from convert import *
