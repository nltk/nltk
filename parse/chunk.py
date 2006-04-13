# Natural Language Toolkit: A Chunk Parser
#
# Copyright (C) 2001-2006 University of Pennsylvania
# Author: Steven Bird <sb@ldc.upenn.edu>
#         Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

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
  ------------------
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

        - In tag patterns, C{'<'} and C{'>'} act as parenthases; so
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
    rate of about 300 tokens/second, with a moderately complex rule
    set.

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
    placing the cursor after the last close parenthasis, and typing
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

@type _VALID_CHUNK_STRING: C{regexp}
@var _VALID_CHUNK_STRING: A regular expression to test whether a chunk
     string is valid.
@type _VALID_TAG_PATTERN: C{regexp}
@var _VALID_TAG_PATTERN: A regular expression to test whether a tag
     pattern is valid.
"""

from nltk_lite.parse import ParseI, AbstractParse
from tree import Tree
from nltk_lite import tokenize
import types, re

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
##  Evaluation Helper
##//////////////////////////////////////////////////////

# Patched for increased performance by Yoav Goldberg <yoavg@cs.bgu.ac.il>, 2006-01-13
#  -- statistics are evaluated only on demand, instead of at every sentence evaluation

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
        if isinstance(child, Tree):
            chunks.append(((count, pos), tuple(child.freeze())))
            pos += len(child)
        else:
            pos += 1
    return set(chunks)

##//////////////////////////////////////////////////////
##  Precompiled regular expressions
##//////////////////////////////////////////////////////

_TAGCHAR = r'[^\{\}<>]'
_TAG = r'(<%s+?>)' % _TAGCHAR
_VALID_TAG_PATTERN = re.compile(r'^((%s|<%s>)*)$' %
                                ('[^\{\}<>]+',
                                 '[^\{\}<>]+'))

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
    _CHUNK = r'(\{%s+?\})+?' % _TAG
    _CHINK = r'(%s+?)+?' % _TAG
    _VALID = re.compile(r'(\{?%s\}?)*?' % _TAG)
    _BRACKETS = re.compile('[^\{\}]+')
    _BALANCED_BRACKETS = re.compile(r'(\{\})*$')
    
    def __init__(self, chunk_struct, debug_level=3):
        """
        Construct a new C{ChunkString} that encodes the chunking of
        the text C{tagged_tokens}.

        @type chunk_struct: C{Tree}
        @param chunk_struct: The chunk structured to be further chunked.
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

        @type pattern: C{string} 
        @param pattern: A regular expression pattern matching the substring
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
        if type(pattern).__name__ == 'SRE_Pattern': pattern = pattern.pattern
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

        @type pattern: C{string} or C{regexp}
        @param pattern: A regular expression pattern matching the substring
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
        if type(pattern).__name__ == 'SRE_Pattern': pattern = pattern.pattern
        self.xform(pattern+ChunkString.IN_CHINK_PATTERN, repl)

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
##  Rules
##//////////////////////////////////////////////////////

def tag_pattern2re_pattern(tag_pattern):
    """
    Convert a tag pattern to a regular expression pattern.  A X{tag
    pattern} is a modified version of a regular expression, designed
    for matching sequences of tags.  The differences between regular
    expression patterns and tag patterns are:

        - In tag patterns, C{'<'} and C{'>'} act as parenthases; so 
          C{'<NN>+'} matches one or more repetitions of C{'<NN>'}, not
          C{'<NN'} followed by one or more repetitions of C{'>'}.
        - Whitespace in tag patterns is ignored.  So
          C{'<DT> | <NN>'} is equivalant to C{'<DT>|<NN>'}
        - In tag patterns, C{'.'} is equivalant to C{'[^{}<>]'}; so
          C{'<NN.*>'} matches any single tag starting with C{'NN'}.

    In particular, C{tag_pattern2re_pattern} performs the following
    transformations on the given pattern:

        - Replace '.' with '[^<>{}]'
        - Remove any whitespace
        - Add extra parens around '<' and '>', to make '<' and '>' act
          like parenthases.  E.g., so that in '<NN>+', the '+' has scope
          over the entire '<NN>'; and so that in '<NN|IN>', the '|' has
          scope over 'NN' and 'IN', but not '<' or '>'.
        - Check to make sure the resulting pattern is valid.

    @type tag_pattern: C{string}
    @param tag_pattern: The tag pattern to convert to a regular
        expression pattern.
    @raise ValueError: If C{tag_pattern} is not a valid tag pattern.
        In particular, C{tag_pattern} should not include braces; and it
        should not contain nested or mismatched angle-brackets.
    @rtype: C{string}
    @return: A regular expression pattern corresponding to
        C{tag_pattern}. 
    """
    # Clean up the regular expression
    tag_pattern = re.sub(r'\s', '', tag_pattern)
    tag_pattern = re.sub(r'<', '(<(', tag_pattern)
    tag_pattern = re.sub(r'>', ')>)', tag_pattern)

    # Check the regular expression
    if not _VALID_TAG_PATTERN.match(tag_pattern):
        raise ValueError('Bad tag pattern: %s' % tag_pattern)

    # Replace "." with _TAGCHAR.
    # We have to do this after, since it adds {}[]<>s, which would
    # confuse _VALID_TAG_PATTERN.
    # PRE doesn't have lookback assertions, so reverse twice, and do
    # the pattern backwards (with lookahead assertions).  This can be
    # made much cleaner once we can switch back to SRE.
    def reverse_str(str):
        lst = list(str)
        lst.reverse()
        return ''.join(lst)
    tc_rev = reverse_str(_TAGCHAR)
    reversed = reverse_str(tag_pattern)
    reversed = re.sub(r'\.(?!\\(\\\\)*($|[^\\]))', tc_rev, reversed)
    tag_pattern = reverse_str(reversed)

    return tag_pattern

class RegexpChunkRule(object):
    """
    A rule specifying how to modify the chunking in a C{ChunkString},
    using a transformational regular expression.  The
    C{RegexpChunkRule} class itself can be used to implement any
    transformational rule based on regular expressions.  There are
    also a number of subclasses, which can be used to implement
    simpler types of rules, based on matching regular expressions.

    Each C{RegexpChunkRule} has a regular expression and a
    replacement expression.  When a C{RegexpChunkRule} is X{applied}
    to a C{ChunkString}, it searches the C{ChunkString} for any
    substring that matches the regular expression, and replaces it
    using the replacement expression.  This search/replace operation
    has the same semantics as C{re.sub}.

    Each C{RegexpChunkRule} also has a description string, which
    gives a short (typically less than 75 characters) description of
    the purpose of the rule.
    
    This transformation defined by this C{RegexpChunkRule} should
    only add and remove braces; it should I{not} modify the sequence
    of angle-bracket delimited tags.  Furthermore, this transformation
    may not result in nested or mismatched bracketing.
    """
    def __init__(self, regexp, repl, descr):
        """
        Construct a new RegexpChunkRule.
        
        @type regexp: C{regexp} or C{string}
        @param regexp: This C{RegexpChunkRule}'s regular expression.
            When this rule is applied to a C{ChunkString}, any
            substring that matches C{regexp} will be replaced using
            the replacement string C{repl}.  Note that this must be a
            normal regular expression, not a tag pattern.
        @type repl: C{string}
        @param repl: This C{RegexpChunkRule}'s replacement
            expression.  When this rule is applied to a
            C{ChunkString}, any substring that matches C{regexp} will
            be replaced using C{repl}.
        @type descr: C{string}
        @param descr: A short description of the purpose and/or effect
            of this rule.
        """
        if type(regexp).__name__ == 'SRE_Pattern': regexp = regexp.pattern
        self._repl = repl
        self._descr = descr
        if type(regexp) == types.StringType:
            self._regexp = re.compile(regexp)
        else:
            self._regexp = regexp

    def apply(self, chunkstr):
        # Keep docstring generic so we can inherit it.
        """
        Apply this rule to the given C{ChunkString}.  See the
        class reference documentation for a description of what it
        means to apply a rule.
        
        @type chunkstr: C{ChunkString}
        @param chunkstr: The chunkstring to which this rule is
            applied. 
        @rtype: C{None}
        @raise ValueError: If this transformation generated an
            invalid chunkstring.
        """
        chunkstr.xform(self._regexp, self._repl)

    def descr(self):
        """
        @rtype: C{string}
        @return: a short description of the purpose and/or effect of
            this rule.
        """
        return self._descr

    def __repr__(self):
        """
        @rtype: C{string}
        @return: A string representation of this rule.  This
             string representation has the form::

                 <RegexpChunkRule: '{<IN|VB.*>}'->'<IN>'>

             Note that this representation does not include the
             description string; that string can be accessed
             separately with the C{descr} method.
        """
        return ('<RegexpChunkRule: '+`self._regexp.pattern`+
                '->'+`self._repl`+'>')
        
class ChunkRule(RegexpChunkRule):
    """
    A rule specifying how to add chunks to a C{ChunkString}, using a
    matching tag pattern.  When applied to a C{ChunkString}, it will
    find any substring that matches this tag pattern and that is not
    already part of a chunk, and create a new chunk containing that
    substring.
    """
    def __init__(self, tag_pattern, descr):

        """
        Construct a new C{ChunkRule}.
        
        @type tag_pattern: C{string}
        @param tag_pattern: This rule's tag pattern.  When
            applied to a C{ChunkString}, this rule will
            chunk any substring that matches this tag pattern and that
            is not already part of a chunk.
        @type descr: C{string}
        @param descr: A short description of the purpose and/or effect
            of this rule.
        """
        self._pattern = tag_pattern
        regexp = re.compile('(?P<chunk>%s)%s' %
                            (tag_pattern2re_pattern(tag_pattern),
                             ChunkString.IN_CHINK_PATTERN))
        RegexpChunkRule.__init__(self, regexp, '{\g<chunk>}', descr)

    def __repr__(self):
        """
        @rtype: C{string}
        @return: A string representation of this rule.  This
             string representation has the form::

                 <ChunkRule: '<IN|VB.*>'>

             Note that this representation does not include the
             description string; that string can be accessed
             separately with the C{descr} method.
        """
        return '<ChunkRule: '+`self._pattern`+'>'

class ChinkRule(RegexpChunkRule):
    """
    A rule specifying how to remove chinks to a C{ChunkString},
    using a matching tag pattern.  When applied to a
    C{ChunkString}, it will find any substring that matches this
    tag pattern and that is contained in a chunk, and remove it
    from that chunk, thus creating two new chunks.
    """
    def __init__(self, tag_pattern, descr):
        """
        Construct a new C{ChinkRule}.
        
        @type tag_pattern: C{string}
        @param tag_pattern: This rule's tag pattern.  When
            applied to a C{ChunkString}, this rule will
            find any substring that matches this tag pattern and that
            is contained in a chunk, and remove it from that chunk,
            thus creating two new chunks.
        @type descr: C{string}
        @param descr: A short description of the purpose and/or effect
            of this rule.
        """
        self._pattern = tag_pattern
        regexp = re.compile('(?P<chink>%s)%s' %
                            (tag_pattern2re_pattern(tag_pattern),
                             ChunkString.IN_CHUNK_PATTERN))
        RegexpChunkRule.__init__(self, regexp, '}\g<chink>{', descr)

    def __repr__(self):
        """
        @rtype: C{string}
        @return: A string representation of this rule.  This
             string representation has the form::

                 <ChinkRule: '<IN|VB.*>'>

             Note that this representation does not include the
             description string; that string can be accessed
             separately with the C{descr} method.
        """
        return '<ChinkRule: '+`self._pattern`+'>'

class UnChunkRule(RegexpChunkRule):
    """
    A rule specifying how to remove chunks to a C{ChunkString},
    using a matching tag pattern.  When applied to a
    C{ChunkString}, it will find any complete chunk that matches this
    tag pattern, and un-chunk it.
    """
    def __init__(self, tag_pattern, descr):
        """
        Construct a new C{UnChunkRule}.
        
        @type tag_pattern: C{string}
        @param tag_pattern: This rule's tag pattern.  When
            applied to a C{ChunkString}, this rule will
            find any complete chunk that matches this tag pattern,
            and un-chunk it.
        @type descr: C{string}
        @param descr: A short description of the purpose and/or effect
            of this rule.
        """
        self._pattern = tag_pattern
        regexp = re.compile('\{(?P<chunk>%s)\}' %
                            tag_pattern2re_pattern(tag_pattern))
        RegexpChunkRule.__init__(self, regexp, '\g<chunk>', descr)

    def __repr__(self):
        """
        @rtype: C{string}
        @return: A string representation of this rule.  This
             string representation has the form::

                 <UnChunkRule: '<IN|VB.*>'>

             Note that this representation does not include the
             description string; that string can be accessed
             separately with the C{descr} method.
        """
        return '<UnChunkRule: '+`self._pattern`+'>'

class MergeRule(RegexpChunkRule):
    """
    A rule specifying how to merge chunks in a C{ChunkString}, using
    two matching tag patterns: a left pattern, and a right pattern.
    When applied to a C{ChunkString}, it will find any chunk whose end
    matches left pattern, and immediately followed by a chunk whose
    beginning matches right pattern.  It will then merge those two
    chunks into a single chunk.
    """
    def __init__(self, left_tag_pattern, right_tag_pattern, descr):
        """
        Construct a new C{MergeRule}.

        @type right_tag_pattern: C{string}
        @param right_tag_pattern: This rule's right tag
            pattern.  When applied to a C{ChunkString}, this
            rule will find any chunk whose end matches
            C{left_tag_pattern}, and immediately followed by a chunk
            whose beginning matches this pattern.  It will
            then merge those two chunks into a single chunk.
        @type left_tag_pattern: C{string}
        @param left_tag_pattern: This rule's left tag
            pattern.  When applied to a C{ChunkString}, this
            rule will find any chunk whose end matches
            this pattern, and immediately followed by a chunk
            whose beginning matches C{right_tag_pattern}.  It will
            then merge those two chunks into a single chunk.
            
        @type descr: C{string}
        @param descr: A short description of the purpose and/or effect
            of this rule.
        """
        self._left_tag_pattern = left_tag_pattern
        self._right_tag_pattern = right_tag_pattern
        regexp = re.compile('(?P<left>%s)}{(?=%s)' %
                            (tag_pattern2re_pattern(left_tag_pattern),
                             tag_pattern2re_pattern(right_tag_pattern)))
        RegexpChunkRule.__init__(self, regexp, '\g<left>', descr)

    def __repr__(self):
        """
        @rtype: C{string}
        @return: A string representation of this rule.  This
             string representation has the form::

                 <MergeRule: '<NN|DT|JJ>', '<NN|JJ>'>

             Note that this representation does not include the
             description string; that string can be accessed
             separately with the C{descr} method.
        """
        return ('<MergeRule: '+`self._left_tag_pattern`+', '+
                `self._right_tag_pattern`+'>')

class SplitRule(RegexpChunkRule):
    """
    A rule specifying how to split chunks in a C{ChunkString}, using
    two matching tag patterns: a left pattern, and a right pattern.
    When applied to a C{ChunkString}, it will find any chunk that
    matches the left pattern followed by the right pattern.  It will
    then split the chunk into two new chunks, at the point between the
    two pattern matches.
    """
    def __init__(self, left_tag_pattern, right_tag_pattern, descr):
        """
        Construct a new C{SplitRule}.
        
        @type right_tag_pattern: C{string}
        @param right_tag_pattern: This rule's right tag
            pattern.  When applied to a C{ChunkString}, this rule will
            find any chunk containing a substring that matches
            C{left_tag_pattern} followed by this pattern.  It will
            then split the chunk into two new chunks at the point
            between these two matching patterns.
        @type left_tag_pattern: C{string}
        @param left_tag_pattern: This rule's left tag
            pattern.  When applied to a C{ChunkString}, this rule will
            find any chunk containing a substring that matches this
            pattern followed by C{right_tag_pattern}.  It will then
            split the chunk into two new chunks at the point between
            these two matching patterns.
        @type descr: C{string}
        @param descr: A short description of the purpose and/or effect
            of this rule.
        """
        self._left_tag_pattern = left_tag_pattern
        self._right_tag_pattern = right_tag_pattern
        regexp = re.compile('(?P<left>%s)(?=%s)' % 
                            (tag_pattern2re_pattern(left_tag_pattern),
                             tag_pattern2re_pattern(right_tag_pattern)))
        RegexpChunkRule.__init__(self, regexp, r'\g<left>}{', descr)

    def __repr__(self):
        """
        @rtype: C{string}
        @return: A string representation of this rule.  This
             string representation has the form::

                 <SplitRule: '<NN>', '<DT>'>

             Note that this representation does not include the
             description string; that string can be accessed
             separately with the C{descr} method.
        """
        return ('<SplitRule: '+`self._left_tag_pattern`+', '+
                `self._right_tag_pattern`+'>')

class ExpandLeftRule(RegexpChunkRule):
    """
    A rule specifying how to expand chunks in a C{ChunkString} to the left,
    using two matching tag patterns: a left pattern, and a right pattern.
    When applied to a C{ChunkString}, it will find any chunk whose beginning
    matches right pattern, and immediately preceded by a chink whose
    end matches left pattern.  It will then expand the chunk to incorporate
    the new material on the left.
    """
    def __init__(self, left_tag_pattern, right_tag_pattern, descr):
        """
        Construct a new C{ExpandRightRule}.

        @type right_tag_pattern: C{string}
        @param right_tag_pattern: This rule's right tag
            pattern.  When applied to a C{ChunkString}, this
            rule will find any chunk whose beginning matches
            C{right_tag_pattern}, and immediately preceded by a chink
            whose end matches this pattern.  It will
            then merge those two chunks into a single chunk.
        @type left_tag_pattern: C{string}
        @param left_tag_pattern: This rule's left tag
            pattern.  When applied to a C{ChunkString}, this
            rule will find any chunk whose beginning matches
            this pattern, and immediately preceded by a chink
            whose end matches C{left_tag_pattern}.  It will
            then expand the chunk to incorporate the new material on the left.
            
        @type descr: C{string}
        @param descr: A short description of the purpose and/or effect
            of this rule.
        """
        self._left_tag_pattern = left_tag_pattern
        self._right_tag_pattern = right_tag_pattern
        regexp = re.compile('(?P<left>%s)\{(?P<right>%s)' %
                            (tag_pattern2re_pattern(left_tag_pattern),
                             tag_pattern2re_pattern(right_tag_pattern)))
        RegexpChunkRule.__init__(self, regexp, '{\g<left>\g<right>', descr)

    def __repr__(self):
        """
        @rtype: C{string}
        @return: A string representation of this rule.  This
             string representation has the form::

                 <ExpandLeftRule: '<NN|DT|JJ>', '<NN|JJ>'>

             Note that this representation does not include the
             description string; that string can be accessed
             separately with the C{descr} method.
        """
        return ('<ExpandLeftRule: '+`self._left_tag_pattern`+', '+
                `self._right_tag_pattern`+'>')

class ExpandRightRule(RegexpChunkRule):
    """
    A rule specifying how to expand chunks in a C{ChunkString} to the right,
    using two matching tag patterns: a left pattern, and a right pattern.
    When applied to a C{ChunkString}, it will find any chunk whose end
    matches left pattern, and immediately followed by a chink whose
    beginning matches right pattern.  It will then expand the chunk to incorporate
    the new material on the right.
    """
    def __init__(self, left_tag_pattern, right_tag_pattern, descr):
        """
        Construct a new C{ExpandRightRule}.

        @type right_tag_pattern: C{string}
        @param right_tag_pattern: This rule's right tag
            pattern.  When applied to a C{ChunkString}, this
            rule will find any chunk whose end matches
            C{left_tag_pattern}, and immediately followed by a chink
            whose beginning matches this pattern.  It will
            then merge those two chunks into a single chunk.
        @type left_tag_pattern: C{string}
        @param left_tag_pattern: This rule's left tag
            pattern.  When applied to a C{ChunkString}, this
            rule will find any chunk whose end matches
            this pattern, and immediately followed by a chink
            whose beginning matches C{right_tag_pattern}.  It will
            then expand the chunk to incorporate the new material on the right.
            
        @type descr: C{string}
        @param descr: A short description of the purpose and/or effect
            of this rule.
        """
        self._left_tag_pattern = left_tag_pattern
        self._right_tag_pattern = right_tag_pattern
        regexp = re.compile('(?P<left>%s)\}(?P<right>%s)' %
                            (tag_pattern2re_pattern(left_tag_pattern),
                             tag_pattern2re_pattern(right_tag_pattern)))
        RegexpChunkRule.__init__(self, regexp, '\g<left>\g<right>}', descr)

    def __repr__(self):
        """
        @rtype: C{string}
        @return: A string representation of this rule.  This
             string representation has the form::

                 <ExpandRightRule: '<NN|DT|JJ>', '<NN|JJ>'>

             Note that this representation does not include the
             description string; that string can be accessed
             separately with the C{descr} method.
        """
        return ('<ExpandRightRule: '+`self._left_tag_pattern`+', '+
                `self._right_tag_pattern`+'>')

##//////////////////////////////////////////////////////
##  RegexpChunk
##//////////////////////////////////////////////////////

class RegexpChunk(ChunkParseI, AbstractParse):
    """
    A regular expression based chunk parser.  C{RegexpChunk} uses a
    sequence X{rules} to find chunks within a text.  The chunking of
    the text is encoded using a C{ChunkString}, and each rule acts by
    modifying the chunking in the C{ChunkString}.  The rules are all
    implemented using regular expression matching and substitution.

    The C{RegexpChunkRule} class and its subclasses (C{ChunkRule},
    C{ChinkRule}, C{UnChunkRule}, C{MergeRule}, and C{SplitRule})
    define the rules that are used by C{RegexpChunk}.  Each rule
    defines an C{apply} method, which modifies the chunking encoded
    by a given C{ChunkString}.

    @type _rules: C{list} of C{RegexpChunkRule}
    @ivar _rules: The list of rules that should be applied to a text.
    @type _trace: C{int}
    @ivar _trace: The default level of tracing.
        
    """
    def __init__(self, rules, chunk_node='CHUNK', top_node='TEXT', trace=0):
        """
        Construct a new C{RegexpChunk}.
        
        @type rules: C{list} of C{RegexpChunkRule}
        @param rules: The sequence of rules that should be used to
            generate the chunking for a tagged text.
        @type chunk_node: C{string}
        @param chunk_node: The node value that should be used for
            chunk subtrees.  This is typically a short string
            describing the type of information contained by the chunk,
            such as C{"NP"} for base noun phrases.
        @type top_node: C{string}
        @param top_node: The node value that should be used for the
            top node of the chunk structure.
        @type trace: C{int}
        @param trace: The level of tracing that should be used when
            parsing a text.  C{0} will generate no tracing output;
            C{1} will generate normal tracing output; and C{2} or
            highter will generate verbose tracing output.
        """
        self._rules = rules
        self._trace = trace
        self._chunk_node = chunk_node
        self._top_node = top_node
        AbstractParse.__init__(self)

    def _trace_apply(self, chunkstr, verbose):
        """
        Apply each of this C{RegexpChunk}'s rules to C{chunkstr}, in
        turn.  Generate trace output between each rule.  If C{verbose}
        is true, then generate verbose output.

        @type chunkstr: C{ChunkString}
        @param chunkstr: The chunk string to which each rule should be
            applied.
        @type verbose: C{boolean}
        @param verbose: Whether output should be verbose.
        @rtype: C{None}
        """
        indent = ' '*(35-len(str(chunkstr))/2)
        
        print 'Input:'
        print indent, chunkstr
        for rule in self._rules:
            rule.apply(chunkstr)
            if verbose:
                print rule.descr()+' ('+`rule`+'):'
            else:
                print rule.descr()+':'
            print indent, chunkstr
        
    def _notrace_apply(self, chunkstr):
        """
        Apply each of this C{RegexpChunk}'s rules to C{chunkstr}, in
        turn.

        @param chunkstr: The chunk string to which each rule should be
            applied.
        @type chunkstr: C{ChunkString}
        @rtype: C{None}
        """
        
        for rule in self._rules:
            rule.apply(chunkstr)
        
    def parse(self, tokens, trace=None):
        """
        @type chunk_struct: C{Tree}
        @param chunk_struct: the chunk structure to be (further) chunked
        @type trace: C{int}
        @param trace: The level of tracing that should be used when
            parsing a text.  C{0} will generate no tracing output;
            C{1} will generate normal tracing output; and C{2} or
            highter will generate verbose tracing output.  This value
            overrides the trace level value that was given to the
            constructor. 
        @rtype: C{Tree}
        @return: a chunk structure that encodes the chunks in a given
            tagged sentence.  A chunk is a non-overlapping linguistic
            group, such as a noun phrase.  The set of chunks
            identified in the chunk structure depends on the rules
            used to define this C{RegexpChunk}.
        """
        if len(tokens) == 0:
            print 'Warning: parsing empty text'
            return Tree(self._top_node, [])
        
        # Use the default trace value?
        if trace == None: trace = self._trace

        # Create the chunkstring, using the same properties as the parser
        chunkstr = ChunkString(tokens)

        # Apply the sequence of rules to the chunkstring.
        if trace:
            verbose = (trace>1)
            self._trace_apply(chunkstr, verbose)
        else:
            self._notrace_apply(chunkstr)

        # Use the chunkstring to create a chunk structure.
        return chunkstr.to_chunkstruct(self._chunk_node)

    def rules(self):
        """
        @return: the sequence of rules used by this C{ChunkParse}.
        @rtype: C{list} of C{RegexpChunkRule}
        """
        return self._rules

    def __repr__(self):
        """
        @return: a concise string representation of this
            C{RegexpChunk}.
        @rtype: C{string}
        """
        return "<RegexpChunk with %d rules>" % len(self._rules)

    def __str__(self):
        """
        @return: a verbose string representation of this
            C{RegexpChunk}.
        @rtype: C{string}
        """
        s = "RegexpChunk with %d rules:\n" % len(self._rules)
        margin = 0
        for rule in self._rules:
            margin = max(margin, len(rule.descr()))
        if margin < 35:
            format = "    %" + `-(margin+3)` + "s%s\n"
        else:
            format = "    %s\n      %s\n"
        for rule in self._rules:
            s += format % (rule.descr(), `rule`)
        return s[:-1]
            
##//////////////////////////////////////////////////////
##  Demonstration code
##//////////////////////////////////////////////////////

def demo_eval(chunkparser, text):
    """
    Demonstration code for evaluating a chunk parser, using a
    C{ChunkScore}.  This function assumes that C{text} contains one
    sentence per line, and that each sentence has the form expected by
    C{tree.chunk}.  It runs the given chunk parser on each sentence in
    the text, and scores the result.  It prints the final score
    (precision, recall, and f-measure); and reports the set of chunks
    that were missed and the set of chunks that were incorrect.  (At
    most 10 missing chunks and 10 incorrect chunks are reported).

    @param chunkparser: The chunkparser to be tested
    @type chunkparser: C{ChunkParseI}
    @param text: The chunked tagged text that should be used for
        evaluation.
    @type text: C{string}
    """
    
    # Evaluate our chunk parser.
    chunkscore = ChunkScore()

    from nltk_lite.parse import tree
    
    for sentence in text.split('\n'):
        print sentence
        sentence = sentence.strip()
        if not sentence: continue
        gold = tree.chunk(sentence)
        tokens = gold.leaves()
        test = chunkparser.parse(tree.Tree('S', tokens))
        chunkscore.score(gold, test)

    print '/'+('='*75)+'\\'
    print 'Scoring', chunkparser
    print ('-'*77)
    print 'Precision: %5.1f%%' % (chunkscore.precision()*100), ' '*4,
    print 'Recall: %5.1f%%' % (chunkscore.recall()*100), ' '*6,
    print 'F-Measure: %5.1f%%' % (chunkscore.f_measure()*100)
    

    # Missed chunks.
    if chunkscore.missed():
        print 'Missed:'
        missed = chunkscore.missed()
        for chunk in missed[:10]:
            print '  ', chunk
        if len(chunkscore.missed()) > 10:
               print '  ...'

    # Incorrect chunks.
    if chunkscore.incorrect():
        print 'Incorrect:'
        incorrect = chunkscore.incorrect()
        for chunk in incorrect[:10]:
            print '  ', chunk
        if len(chunkscore.incorrect()) > 10:
               print '  ...'
    
    print '\\'+('='*75)+'/'

def demo_cascade(chunkparsers, text):
    """
    Demonstration code for cascading chunk parsers.

    @param chunkparser: The chunkparsers to be tested
    @type chunkparser: C{ChunkParseI}
    @param text: The chunked tagged text that should be used for evaluation.
    @type text: C{string}
    """
    
    from nltk_lite.parse.tree import Tree
    
    for sentence in text.split('\n'):
        print sentence
        sentence = sentence.strip()
        if not sentence: continue
        gold = tree.chunk(sentence)
        pieces = gold.leaves()
        for chunkparser in chunkparsers:
            pieces = chunkparser.parse(Tree('S', pieces))
            print pieces
        print

def demo():
    """
    A demonstration for the C{RegexpChunk} class.  A single text is
    parsed with four different chunk parsers, using a variety of rules
    and strategies.
    """

    from nltk_lite import parse
    from nltk_lite.tag import string2tags
    from nltk_lite.parse.tree import Tree

    text = """\
    [ the/DT little/JJ cat/NN ] sat/VBD on/IN [ the/DT mat/NN ] ./.
    [ The/DT cats/NNS ] ./.
    [ John/NNP ] saw/VBD [the/DT cat/NN] [the/DT dog/NN] liked/VBD ./.
    [ John/NNP ] saw/VBD [the/DT cat/NN] the/DT cat/NN liked/VBD ./."""

    print '*'*75
    print 'Evaluation text:'
    print text
    print '*'*75

    # Use a simple regexp to define regular expressions.
    r1 = parse.ChunkRule(r'<DT>?<JJ>*<NN.*>', 'Chunk NPs')
    cp = parse.RegexpChunk([r1], chunk_node='NP', trace=1)
    parse.demo_eval(cp, text)
    print

    # Use a chink rule to remove everything that's *not* an NP
    r1 = parse.ChunkRule(r'<.*>+', 'Chunk everything')
    r2 = parse.ChinkRule(r'<VB.*>|<IN>|<\.>', 'Unchunk VB and IN and .')
    cp = parse.RegexpChunk([r1, r2], chunk_node='NP', trace=1)
    parse.demo_eval(cp, text)
    print

    # Unchunk non-NP words, and then merge consecutive NPs
    r1 = parse.ChunkRule(r'(<.*>)', 'Chunk each tag')
    r2 = parse.UnChunkRule(r'<VB.*>|<IN>|<.>', 'Unchunk VB? and IN and .')
    r3 = parse.MergeRule(r'<DT|JJ|NN.*>', r'<DT|JJ|NN.*>', 'Merge NPs')
    cp = parse.RegexpChunk([r1,r2,r3], chunk_node='NP', trace=1)
    parse.demo_eval(cp, text)
    print

    # Chunk sequences of NP words, and split them at determiners
    r1 = parse.ChunkRule(r'(<DT|JJ|NN.*>+)', 'Chunk sequences of DT&JJ&NN')
    r2 = parse.SplitRule('', r'<DT>', 'Split before DT')
    cp = parse.RegexpChunk([r1,r2], chunk_node='NP', trace=1)
    parse.demo_eval(cp, text)
    print

    print "============== Cascaded Chunking =============="
    print

    np_chunk = parse.ChunkRule(r'<DT|JJ|NN.*>+', 'Chunk sequences of DT, JJ, NN')
    np_parse = parse.RegexpChunk([np_chunk], chunk_node='NP')
    pp_chunk = parse.ChunkRule(r'<IN><NP>', 'Chunk prepositions followed by NP')
    pp_parse = parse.RegexpChunk([pp_chunk], chunk_node='PP')
    vp_chunk = parse.ChunkRule(r'<VB.*><NP|PP|S>+$', 'Chunk verbs and arguments/adjuncts')
    vp_parse = parse.RegexpChunk([vp_chunk], chunk_node='VP')
    s_chunk = parse.ChunkRule(r'<NP><VP>$', 'Chunk NP, VP')
    s_parse = parse.RegexpChunk([s_chunk], chunk_node='S')
    chunkparsers = [np_parse, pp_parse, vp_parse, s_parse, vp_parse, s_parse]

    text = """John/NNP thinks/VBZ Mary/NN saw/VBD the/DT cat/NN
              sit/VB on/IN the/DT mat/NN"""
    ttoks = string2tags(text)
    sent = Tree('S', ttoks)
    for chunkparser in chunkparsers:
        sent = chunkparser.parse(sent)
        print sent

if __name__ == '__main__':
    demo()

