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
C{ChunkParserI} interface.  See the reference documentation in the
C{nltk.chunkparser} module for more information about the
C{ChunkParserI} interface.

C{REChunkParser} defines the C{parse} method.  This method identifies
linguistic groups in a text, such as noun phrases.  Its input is a
list of tokens.  Its output is a X{chunk structure} that encodes the
linguistic groups.  A chunk structure is a list containing tagged
tokens and sublists of tagged tokens.  For example, the following
chunk structure encodes the noun phrases in a simple sentence:

    [['the'/'DT'@[0w], 'little'/'JJ'@[1w], 'cat'/'NN'@[2w]],
     'sat'/'VBD'@[3w], 'on'/'IN'@[4w],
     ['the'/'DT'@[5w], 'mat'/'NN'@[6w]]]

Parsing
=======

The C{parse} method first constructs a C{ChunkString}, which encodes a
particular chunking of the input text.  Initially, nothing is chunked.
The C{REChunkParser} then applies a sequence of C{REChunkParserRule}s
to the C{ChunkString}, each of which modifies the chunking that it
encodes.  Finally, the C{ChunkString} is used to construct a chunk
structure, which is returned.

REChunkParserRules
~~~~~~~~~~~~~~~~~~

C{REChunkParserRule}s define the C{apply} method, which modifies the
chunking encoded by a C{ChunkString}.  The C{REChunkParserRule} class
itself can be used to implement any transformational rule based on
regular expressions.  There are also a number of subclasses, which can
be used to implement simpler types of rules:

  - C{ChunkRule} chunks anything that matches a given regular
    expression.
  - C{ChinkRule} chinks anything that matches a given regular
    expression.
  - C{UnChunkRule} will un-chunk any chunk that matches a given
    regular expression.
  - C{MergeRule} can be used to merge two contiguous chunks.
  - C{SplitRule} can be used to split a single chunk into two smaller
    chunks. 

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

Efficiency
==========

Preliminary tests indicate that C{REChunkParser} can chunk at a rate
of about 300 tokens/second, with a moderately complex rule set.

There may be problems if C{REChunkParser} is used with more than 5,000
tokens at a time.  In particular, evaluation of some regular
expressions may cause the Python regular expression engine to exceed
its maximum recursion depth.  We have attempted to minimize these
problems, but it is impossible to avoid them completely.  We therefore
recommend that you apply the chunk parser to a single sentence at a
time.

Emacs Tip
=========

If you evaluate the following, it will colorize tags and bracketing
when you use an interactive python shell with emacs ("C-C !")::

   (let ()
     (defconst comint-mode-font-lock-keywords 
       '(("<[^>]+>" 0 'font-lock-reference-face)
         ("[{}]" 0 'font-lock-function-name-face)))
     (add-hook 'comint-mode-hook (lambda () (turn-on-font-lock))))

You can evaluate this code by copying it to a temporary buffer,
placing the cursor after the last close parenthasis, and typing
"C-x C-e".  The change will last until you close emacs.

Unresolved Issues
=================

Python's regular expression engine seems to generate "maximum
recursion depth exceeded" errors when processing very large texts,
even for regular expressions that should not require any recursion.
We therefore recommend that you apply chunk parsing to texts one
sentence at a time.

@type _VALID_CHUNK_STRING: C{regexp}
@var _VALID_CHUNK_STRING: A regular expression to test whether a chunk
     string is valid.
@type _VALID_TAG_PATTERN: C{regexp}
@var _VALID_TAG_PATTERN: A regular expression to test whether a tag
     pattern is valid.
"""

from nltk.token import Token, Location, LineTokenizer
from nltk.chunkparser import ChunkParserI, ChunkedTaggedTokenizer
from nltk.chunkparser import unchunk, ChunkScore
from nltk.set import Set

import re
import string

##//////////////////////////////////////////////////////
##  Thoughts/comments
##//////////////////////////////////////////////////////

"""
Terms/representations that should be defined in module docstring..
Chunking:
  - chunk = a list of tagged tokens
  - ttoklist = a list of tagged tokens (=chunk, but used in different
    contexts)
  - chunkstruct = a list of tagged tokens and chunks

REChunking:
  - ChunkString = string rep of chunked tags
  - tag pattern = a regexp pattern over tags.  Has slightly different
    rules than normal regexps (since it gets translated): <> act like
    parens, . gets \w, etc.

Issues:
  - generalize ChunkString constructor to accept a chunk struct?
  - Add more documentation explaining precompiled regexps.
  - In order to conform to interfaces, we might eventually want to
    change reps: 
    - chunkparser output as a tree
    - chunkedtaggedtokenizer should produce a list of tokens
  - Efficiency issues? (currently we do ~500-1500 tokens/sec; faster
    when we chunk more text at a time)
  - maximum recursion depth issues grr...

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
        @param tagged_tokens: The text whose chunking is encoded by
            this C{ChunkString}.  
        @type debug_level: int
        @param debug_level: The level of debugging which should be
            applied to transformations on the C{ChunkString}.  The
            valid levels are:
                0. no checks
                1. full check on to_chunkstruct
                2. full check on to_chunkstruct and cursory check after
                   each transformation. 
                3. full check on to_chunkstruct and full check after
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
        Check to make sure that C{_str} still corresponds to some chunked
        version of C{_ttoks}.

        @type verify_tags: C{boolean}
        @param verify_tags: Whether the individual tags should be
            checked.  If this is false, C{_verify} will check to make
            sure that C{_str} encodes a chunked version of I{some}
            list of tokens.  If this is true, then C{_verify} will
            check to make sure that the tags in C{_str} match those in
            C{_ttoks}.
        
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

    def to_chunkstruct(self):
        """
        @return: the chunk structure encoded by this C{ChunkString}.
            A chunk structure is a C{list} containing tagged tokens
            and sublists of tagged tokens, where each sublist
            represents a single chunk.
        @rtype: chunk structure
        @raise ValueError: If a transformation has generated an
            invalid chunkstring.
        """
        if self._debug > 0: self._verify(1)
            
        # Extract a list of alternating chinks & chunks
        pieces = re.split('[{}]', self._str)

        # Use this alternating list to create the chunkstruct.
        chunkstruct = []
        index = 0
        piece_in_chunk = 0
        for piece in pieces:

            # Find the list of tokens contained in this piece.
            length = piece.count('<')
            subsequence = self._ttoks[index:index+length]

            # Add this list of tokens to our chunkstruct.
            if piece_in_chunk:
                chunkstruct.append(subsequence)
            else:
                chunkstruct += subsequence

            # Update index, piece_in_chunk
            index += length
            piece_in_chunk = not piece_in_chunk

        return chunkstruct
                
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
        @raise ValueError: If this transformation generateds an
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
        @raise ValueError: If this transformation generateds an
            invalid chunkstring.
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

        @type pattern: C{string} or C{regexp}
        @param pattern: A regular expression pattern matching the substring
            that should be replaced.  This will typically include a
            named group, which can be used by C{repl}.
        @type repl: C{string}
        @param repl: An expression specifying what should replace the
            matched substring.  Typically, this will include a named
            replacement group, specified by C{regexp}.
        @rtype: C{None}
        @raise ValueError: If this transformation generateds an
            invalid chunkstring.
        """
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
        str = re.sub(r'>(?!\})', '> ', self._str)
        str = re.sub(r'(?<!\{)<', ' <', str)
        if str[0] == '<': str = ' ' + str
        return str

##//////////////////////////////////////////////////////
##  Rules
##//////////////////////////////////////////////////////

def tag_pattern2re_pattern(tag_pattern):
    """
    Convert a tag pattern to a regular expression pattern.  A X{tag
    pattern} is a modified verison of a regular expression, designed
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

    # We have to do this after, since it adds {}[]<>s
    tag_pattern = re.sub(r'\.', _TAGCHAR, tag_pattern)
    return tag_pattern

class REChunkParserRule:
    """
    A rule specifying how to modify the chunking in a C{ChunkString},
    using a transformational regular expression.  The
    C{REChunkParserRule} class itself can be used to implement any
    transformational rule based on regular expressions.  There are
    also a number of subclasses, which can be used to implement
    simpler types of rules, based on matching regular expressions.

    Each C{REChunkParserRule} has a regular expression and a
    replacement expression.  When a C{REChunkParserRule} is X{applied}
    to a C{ChunkString}, it searches the C{ChunkString} for any
    substring that matches the regular expression, and replaces it
    using the replacement expression.  This search/replace operation
    has the same semantics as C{re.sub}.

    Each C{REChunkParserRule} also has a description string, which
    gives a short (typically less than 75 characters) description of
    the purpose of the rule.
    
    This transformation defined by this C{REChunkParserRule} should
    only add and remove braces; it should I{not} modify the sequence
    of angle-bracket delimited tags.  Furthermore, this transformation
    may not result in nested or mismatched bracketing.
    """
    def __init__(self, regexp, repl, descr):
        """
        Construct a new REChunkParserRule.
        
        @type regexp: C{regexp} or C{string}
        @param regexp: This C{REChunkParserRule}'s regular expression.
            When this rule is applied to a C{ChunkString}, any
            substring that matches C{regexp} will be replaced using
            the replacement string C{repl}.  Note that this must be a
            normal regular expression, not a tag pattern.
        @type repl: C{string}
        @param repl: This C{REChunkParserRule}'s replacement
            expression.  When this rule is applied to a
            C{ChunkString}, any substring that matches C{regexp} will
            be replaced using C{repl}.
        @type descr: C{string}
        @param descr: A short description of the purpose and/or effect
            of this rule.
        """
        self._repl = repl
        self._descr = descr
        if type(regexp) == type(''):
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
        @raise ValueError: If this transformation generateds an
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

                 <REChunkParserRule: '{<IN|VB.*>}'->'<IN>'>

             Note that this representation does not include the
             description string; that string can be accessed
             separately with the C{descr} method.
        """
        return ('<REChunkParserRule: '+`self._regexp.pattern`+
                '->'+`self._repl`+'>')
        
class ChunkRule(REChunkParserRule):
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
        regexp = re.compile('(?P<chunk>'+tag_pattern2re_pattern(tag_pattern)+')'+
                            ChunkString.IN_CHINK_PATTERN)
        REChunkParserRule.__init__(self, regexp, '{\g<chunk>}', descr)

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

class ChinkRule(REChunkParserRule):
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
        regexp = re.compile('(?P<chink>'+tag_pattern2re_pattern(tag_pattern)+')'+
                            ChunkString.IN_CHUNK_PATTERN)
        REChunkParserRule.__init__(self, regexp, '}\g<chink>{', descr)

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

class UnChunkRule(REChunkParserRule):
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
        regexp = re.compile('\{(?P<chunk>'+tag_pattern2re_pattern(tag_pattern)+')\}')
        REChunkParserRule.__init__(self, regexp, '\g<chunk>', descr)

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

class MergeRule(REChunkParserRule):
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
        regexp = re.compile('(?P<left>'+tag_pattern2re_pattern(left_tag_pattern)+')'+
                            '}{(?='+tag_pattern2re_pattern(right_tag_pattern)+')')
        REChunkParserRule.__init__(self, regexp, '\g<left>', descr)

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

class SplitRule(REChunkParserRule):
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
        self._rigthpattern = right_tag_pattern
        regexp = re.compile('(?P<left>'+tag_pattern2re_pattern(left_tag_pattern)+')'+
                            '(?='+tag_pattern2re_pattern(right_tag_pattern)+')')
        REChunkParserRule.__init__(self, regexp, '\g<left>\}\{', descr)

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
        return ('<SplitRule: '+`self._left_tag_pattern`+', ',
                `self._right_tag_pattern`+'>')

##//////////////////////////////////////////////////////
##  REChunkParser
##//////////////////////////////////////////////////////

class REChunkParser(ChunkParserI):
    """

    A regular expression based chunk parser.  C{REChunkParser} uses a
    sequence X{rules} to find chunks within a text.  The chunking of
    the text is encoded using a C{ChunkString}, and each rule acts by
    modifying the chunking in the C{ChunkString}.  The rules are all
    implemented using regular expression matching and substitution.

    The C{REChunkParserRule} class and its subclasses (C{ChunkRule},
    C{ChinkRule}, C{UnChunkRule}, C{MergeRule}, and C{SplitRule})
    define the rules that are used by C{REChunkParser}.  Each rule
    defines an C{apply} method, which modifies the chunking encoded
    by a given C{ChunkString}.

    @type _rules: C{list} of C{REChunkParserRule}
    @ivar _rules: The list of rules that should be applied to a text.
    @type _trace: C{int}
    @ivar _trace: The default level of tracing.
    """
    def __init__(self, rules, trace=0):
        """
        Construct a new C{REChunkParser}.
        
        @type rules: C{list} of C{REChunkParserRule}
        @param rules: The sequence of rules that should be used to
            generate the chunking for a tagged text.
        @type trace: C{int}
        @param trace: The level of tracing that should be used when
            parsing a text.  C{0} will generate no tracing output;
            C{1} will generate normal tracing output; and C{2} or
            highter will generate verbose tracing output.
        """
        self._rules = rules
        self._trace = trace

    def _trace_apply(self, chunkstr, verbose):
        """
        Apply each of this C{REChunkParser}'s rules to C{chunkstr}, in
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
        print
        
    def _notrace_apply(self, chunkstr):
        """
        Apply each of this C{REChunkParser}'s rules to C{chunkstr}, in
        turn.

        @param chunkstr: The chunk string to which each rule should be
            applied.
        @type chunkstr: C{ChunkString}
        @rtype: C{None}
        """
        for rule in self._rules:
            rule.apply(chunkstr)
        
    def parse(self, tagged_sentence, trace=None):
        """
        @rtype: chunk structure
        @return: a chunk structure that encodes the chunks in a given
            tagged sentence.  A chunk is a non-overlapping linguistic
            group, such as a noun phrase.  The set of chunks
            identified in the chunk structure depends on the rules
            used to define this C{REChunkParser}.
        @type trace: C{int}
        @param trace: The level of tracing that should be used when
            parsing a text.  C{0} will generate no tracing output;
            C{1} will generate normal tracing output; and C{2} or
            highter will generate verbose tracing output.  This value
            overrides the trace level value that was given to the
            constructor. 
        """
        if len(tagged_sentence) == 0:
            print 'Warning: parsing empty sentence'
            return []
        
        # Use the default trace value?
        if trace == None: trace = self._trace

        # Create the chunkstring.
        chunkstr = ChunkString(tagged_sentence)

        # Apply the sequence of rules to the chunkstring.
        if trace:
            verbose = (trace>1)
            self._trace_apply(chunkstr, verbose)
        else:
            self._notrace_apply(chunkstr)

        # Use the chunkstring to create a chunk structure.
        return chunkstr.to_chunkstruct()

    def rules(self):
        """
        @return: the sequence of rules used by this C{ChunkParser}.
        @rtype: C{list} of C{REChunkParserRule}
        """
        return self._rules

    def __repr__(self):
        """
        @return: a concise string representation of this
            C{REChunkParser}.
        @rtype: C{string}
        """
        return "<REChunkParser with %d rules>" % len(self._rules)

    def __str__(self):
        """
        @return: a verbose string representation of this
            C{REChunkParser}.
        @rtype: C{string}
        """
        s = "REChunkParser with %d rules:\n" % len(self._rules)
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
    C{ChunkedTaggedTokenizer}.  It runs the given chunk parser on each
    sentence in the text, and scores the result.  It prints the final
    score (precision, recall, and f-measure); and reports the set of
    chunks that were missed and the set of chunks that were
    incorrect.  I{Warning: for large texts, these sets might be very
    large.}

    @param chunkparser: The chunkparser to be tested
    @type chunkparser: C{ChunkParserI}
    @param text: The chunked tagged text that should be used for
        evaluation.
    @type text: C{string}
    """
    # Evaluate our chunk parser.
    chunkscore = ChunkScore()

    sentences = LineTokenizer().xtokenize(text)
    ctt = ChunkedTaggedTokenizer()
    for sentence in sentences:
        correct = ctt.tokenize(sentence.type(), source=sentence.loc())
        unchunked = unchunk(correct)
        guess = chunkparser.parse(unchunked)
        chunkscore.score(correct, guess)

    print '/'+('='*75)+'\\'
    print 'Scoring', chunkparser
    print ('-'*77)
    print chunkscore
    print 'Missed:', chunkscore.missed()
    print 'Incorrect:', chunkscore.incorrect()
    print '\\'+('='*75)+'/'
    print

def demo():
    text = """
    [ the/DT little/JJ cat/NN ] sat/VBD on/IN [ the/DT mat/NN ] ./.
    [ The/DT cats/NNS ] ./.
    """
    
    r1 = ChunkRule(r'<DT><JJ>*<NN.*>', 'Chunk NPs')
    cp = REChunkParser([r1])
    demo_eval(cp, text)

    r1 = ChunkRule(r'<.*>+', 'Chunk everything')
    r2 = ChinkRule(r'<VB.*>|<IN>', 'Chink VB?s and INs')
    cp = REChunkParser([r1, r2])
    demo_eval(cp, text)

    r1 = ChunkRule(r'(<.*>)', 'Chunk each tag')
    r2 = UnChunkRule(r'<VB.*>|<IN>', 'Unchunk VB? and INs')
    r3 = MergeRule(r'<DT|JJ|NN.*>', r'<DT|JJ|NN.*>', 'Merge NPs')
    cp = REChunkParser([r1,r2,r3])
    demo_eval(cp, text)

if __name__ == '__main__':
    demo()

