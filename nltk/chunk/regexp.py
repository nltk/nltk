# Natural Language Toolkit: Regular Expression Chunkers
#
# Copyright (C) 2001-2009 NLTK Project
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
#         Steven Bird <sb@csse.unimelb.edu.au> (minor additions)
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

import re
import types

from nltk import Tree

from nltk.chunk.api import *
from nltk.chunk.util import *

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
    CHUNK_TAG_CHAR = r'[^\{\}<>]'
    CHUNK_TAG = r'(<%s+?>)' % CHUNK_TAG_CHAR
    
    IN_CHUNK_PATTERN = r'(?=[^\{]*\})'
    IN_CHINK_PATTERN = r'(?=[^\}]*(\{|$))'

    # These are used by _verify
    _CHUNK = r'(\{%s+?\})+?' % CHUNK_TAG
    _CHINK = r'(%s+?)+?' % CHUNK_TAG
    _VALID = re.compile(r'^(\{?%s\}?)*?$' % CHUNK_TAG)
    _BRACKETS = re.compile('[^\{\}]+')
    _BALANCED_BRACKETS = re.compile(r'(\{\})*$')
    
    def __init__(self, chunk_struct, debug_level=1):
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
            raise ValueError('chunk structures must contain tagged '
                             'tokens or trees')
                      
    def _verify(self, s, verify_tags):
        """
        Check to make sure that C{s} still corresponds to some chunked
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
        if not ChunkString._VALID.match(s):
            raise ValueError('Transformation generated invalid '
                             'chunkstring:\n  %s' % s)

        # Check that parens are balanced.  If the string is long, we
        # have to do this in pieces, to avoid a maximum recursion
        # depth limit for regular expressions.
        brackets = ChunkString._BRACKETS.sub('', s)
        for i in range(1+len(brackets)/5000):
            substr = brackets[i*5000:i*5000+5000]
            if not ChunkString._BALANCED_BRACKETS.match(substr):
                raise ValueError('Transformation generated invalid '
                                 'chunkstring:\n  %s' % s)

        if verify_tags<=0: return
        
        tags1 = (re.split(r'[\{\}<>]+', s))[1:-1]
        tags2 = [self._tag(piece) for piece in self._pieces]
        if tags1 != tags2:
            raise ValueError('Transformation generated invalid '
                             'chunkstring: tag changed')

    def to_chunkstruct(self, chunk_node='CHUNK'):
        """
        @return: the chunk structure encoded by this C{ChunkString}.
        @rtype: C{Tree}
        @raise ValueError: If a transformation has generated an
            invalid chunkstring.
        """
        if self._debug > 0: self._verify(self._str, 1)
            
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
        s = re.sub(regexp, repl, self._str)

        # The substitution might have generated "empty chunks"
        # (substrings of the form "{}").  Remove them, so they don't
        # interfere with other transformations.
        s = re.sub('\{\}', '', s)

        # Make sure that the transformation was legal.
        if self._debug > 1: self._verify(s, self._debug-2)

        # Commit the transformation.
        self._str = s

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
##  Chunking Rules
##//////////////////////////////////////////////////////

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
        if isinstance(regexp, basestring):
            regexp = re.compile(regexp)
        self._repl = repl
        self._descr = descr
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

    @staticmethod
    def parse(s):
        """
        Create a RegexpChunkRule from a string description.
        Currently, the following formats are supported::

          {regexp}         # chunk rule
          }regexp{         # chink rule
          regexp}{regexp   # split rule
          regexp{}regexp   # merge rule

        Where C{regexp} is a regular expression for the rule.  Any
        text following the comment marker (C{#}) will be used as
        the rule's description:
        
        >>> RegexpChunkRule.parse('{<DT>?<NN.*>+}')
        <ChunkRule: '<DT>?<NN.*>+'>
        """
        # Split off the comment (but don't split on '\#')
        m = re.match(r'(?P<rule>(\\.|[^#])*)(?P<comment>#.*)?', s)
        rule = m.group('rule').strip()
        comment = (m.group('comment') or '')[1:].strip()
        
        # Pattern bodies: chunk, chink, split, merge
        try:
            if not rule:
                raise ValueError('Empty chunk pattern')
            if rule[0] == '{' and rule[-1] == '}':
                return ChunkRule(rule[1:-1], comment)
            elif rule[0] == '}' and rule[-1] == '{':
                return ChinkRule(rule[1:-1], comment)
            elif '}{' in rule:
                left, right = rule.split('}{')
                return SplitRule(left, right, comment)
            elif '{}' in rule:
                left, right = rule.split('{}')
                return MergeRule(left, right, comment)
            elif re.match('[^{}]*{[^{}]*}[^{}]*', rule):
                left, chunk, right = re.split('[{}]', rule)
                return ChunkRuleWithContext(left, chunk, right, comment)
            else:
                raise ValueError('Illegal chunk pattern: %s' % rule)
        except (ValueError, re.error):
            raise ValueError('Illegal chunk pattern: %s' % rule)


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
        # Ensure that the individual patterns are coherent.  E.g., if
        # left='(' and right=')', then this will raise an exception:
        re.compile(tag_pattern2re_pattern(left_tag_pattern))
        re.compile(tag_pattern2re_pattern(right_tag_pattern))

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
        # Ensure that the individual patterns are coherent.  E.g., if
        # left='(' and right=')', then this will raise an exception:
        re.compile(tag_pattern2re_pattern(left_tag_pattern))
        re.compile(tag_pattern2re_pattern(right_tag_pattern))

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
        # Ensure that the individual patterns are coherent.  E.g., if
        # left='(' and right=')', then this will raise an exception:
        re.compile(tag_pattern2re_pattern(left_tag_pattern))
        re.compile(tag_pattern2re_pattern(right_tag_pattern))

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
    A rule specifying how to expand chunks in a C{ChunkString} to the
    right, using two matching tag patterns: a left pattern, and a
    right pattern.  When applied to a C{ChunkString}, it will find any
    chunk whose end matches left pattern, and immediately followed by
    a chink whose beginning matches right pattern.  It will then
    expand the chunk to incorporate the new material on the right.
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
        # Ensure that the individual patterns are coherent.  E.g., if
        # left='(' and right=')', then this will raise an exception:
        re.compile(tag_pattern2re_pattern(left_tag_pattern))
        re.compile(tag_pattern2re_pattern(right_tag_pattern))

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

class ChunkRuleWithContext(RegexpChunkRule):
    """
    A rule specifying how to add chunks to a C{ChunkString}, using
    three matching tag patterns: one for the left context, one for the
    chunk, and one for the right context.  When applied to a
    C{ChunkString}, it will find any substring that matches the chunk
    tag pattern, is surrounded by substrings that match the two
    context patterns, and is not already part of a chunk; and create a
    new chunk containing the substring that matched the chunk tag
    pattern.

    Caveat: Both the left and right context are consumed when this
    rule matches; therefore, if you need to find overlapping matches,
    you will need to apply your rule more than once.
    """
    def __init__(self, left_context_tag_pattern, chunk_tag_pattern,
                 right_context_tag_pattern, descr):
        """
        Construct a new C{ChunkRuleWithContext}.
        
        @type left_context_tag_pattern: C{string}
        @param left_context_tag_pattern: A tag pattern that must match
            the left context of C{chunk_tag_pattern} for this rule to
            apply.
        @type chunk_tag_pattern: C{string}
        @param chunk_tag_pattern: A tag pattern that must match for this
            rule to apply.  If the rule does apply, then this pattern
            also identifies the substring that will be made into a chunk.
        @type right_context_tag_pattern: C{string}
        @param right_context_tag_pattern: A tag pattern that must match
            the right context of C{chunk_tag_pattern} for this rule to
            apply.
        @type descr: C{string}
        @param descr: A short description of the purpose and/or effect
            of this rule.
        """
        # Ensure that the individual patterns are coherent.  E.g., if
        # left='(' and right=')', then this will raise an exception:
        re.compile(tag_pattern2re_pattern(left_context_tag_pattern))
        re.compile(tag_pattern2re_pattern(chunk_tag_pattern))
        re.compile(tag_pattern2re_pattern(right_context_tag_pattern))

        self._left_context_tag_pattern = left_context_tag_pattern
        self._chunk_tag_pattern = chunk_tag_pattern
        self._right_context_tag_pattern = right_context_tag_pattern
        regexp = re.compile('(?P<left>%s)(?P<chunk>%s)(?P<right>%s)%s' %
                            (tag_pattern2re_pattern(left_context_tag_pattern),
                             tag_pattern2re_pattern(chunk_tag_pattern),
                             tag_pattern2re_pattern(right_context_tag_pattern),
                             ChunkString.IN_CHINK_PATTERN))
        replacement = r'\g<left>{\g<chunk>}\g<right>'
        RegexpChunkRule.__init__(self, regexp, replacement, descr)

    def __repr__(self):
        """
        @rtype: C{string}
        @return: A string representation of this rule.  This
             string representation has the form::

                 <ChunkRuleWithContext: '<IN>', '<NN>', '<DT>'>

             Note that this representation does not include the
             description string; that string can be accessed
             separately with the C{descr} method.
        """
        return '<ChunkRuleWithContext: %r, %r, %r>' % (
            self._left_context_tag_pattern, self._chunk_tag_pattern,
            self._right_context_tag_pattern)

##//////////////////////////////////////////////////////
##  Tag Pattern Format Conversion
##//////////////////////////////////////////////////////

# this should probably be made more strict than it is -- e.g., it
# currently accepts 'foo'.
CHUNK_TAG_PATTERN = re.compile(r'^((%s|<%s>)*)$' %
                                ('[^\{\}<>]+',
                                 '[^\{\}<>]+'))

def tag_pattern2re_pattern(tag_pattern):
    """
    Convert a tag pattern to a regular expression pattern.  A X{tag
    pattern} is a modified version of a regular expression, designed
    for matching sequences of tags.  The differences between regular
    expression patterns and tag patterns are:

        - In tag patterns, C{'<'} and C{'>'} act as parentheses; so 
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
          like parentheses.  E.g., so that in '<NN>+', the '+' has scope
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
    if not CHUNK_TAG_PATTERN.match(tag_pattern):
        raise ValueError('Bad tag pattern: %r' % tag_pattern)

    # Replace "." with CHUNK_TAG_CHAR.
    # We have to do this after, since it adds {}[]<>s, which would
    # confuse CHUNK_TAG_PATTERN.
    # PRE doesn't have lookback assertions, so reverse twice, and do
    # the pattern backwards (with lookahead assertions).  This can be
    # made much cleaner once we can switch back to SRE.
    def reverse_str(str):
        lst = list(str)
        lst.reverse()
        return ''.join(lst)
    tc_rev = reverse_str(ChunkString.CHUNK_TAG_CHAR)
    reversed = reverse_str(tag_pattern)
    reversed = re.sub(r'\.(?!\\(\\\\)*($|[^\\]))', tc_rev, reversed)
    tag_pattern = reverse_str(reversed)

    return tag_pattern


##//////////////////////////////////////////////////////
##  RegexpChunkParser
##//////////////////////////////////////////////////////

class RegexpChunkParser(ChunkParserI):
    """
    A regular expression based chunk parser.  C{RegexpChunkParser} uses a
    sequence of X{rules} to find chunks of a single type within a
    text.  The chunking of the text is encoded using a C{ChunkString},
    and each rule acts by modifying the chunking in the
    C{ChunkString}.  The rules are all implemented using regular
    expression matching and substitution.

    The C{RegexpChunkRule} class and its subclasses (C{ChunkRule},
    C{ChinkRule}, C{UnChunkRule}, C{MergeRule}, and C{SplitRule})
    define the rules that are used by C{RegexpChunkParser}.  Each rule
    defines an C{apply} method, which modifies the chunking encoded
    by a given C{ChunkString}.

    @type _rules: C{list} of C{RegexpChunkRule}
    @ivar _rules: The list of rules that should be applied to a text.
    @type _trace: C{int}
    @ivar _trace: The default level of tracing.
        
    """
    def __init__(self, rules, chunk_node='NP', top_node='S', trace=0):
        """
        Construct a new C{RegexpChunkParser}.
        
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
            higher will generate verbose tracing output.
        """
        self._rules = rules
        self._trace = trace
        self._chunk_node = chunk_node
        self._top_node = top_node

    def _trace_apply(self, chunkstr, verbose):
        """
        Apply each of this C{RegexpChunkParser}'s rules to C{chunkstr}, in
        turn.  Generate trace output between each rule.  If C{verbose}
        is true, then generate verbose output.

        @type chunkstr: C{ChunkString}
        @param chunkstr: The chunk string to which each rule should be
            applied.
        @type verbose: C{boolean}
        @param verbose: Whether output should be verbose.
        @rtype: C{None}
        """
        print '# Input:'
        print chunkstr
        for rule in self._rules:
            rule.apply(chunkstr)
            if verbose:
                print '#', rule.descr()+' ('+`rule`+'):'
            else:
                print '#', rule.descr()+':'
            print chunkstr
        
    def _notrace_apply(self, chunkstr):
        """
        Apply each of this C{RegexpChunkParser}'s rules to C{chunkstr}, in
        turn.

        @param chunkstr: The chunk string to which each rule should be
            applied.
        @type chunkstr: C{ChunkString}
        @rtype: C{None}
        """
        
        for rule in self._rules:
            rule.apply(chunkstr)
        
    def parse(self, chunk_struct, trace=None):
        from nltk import Tree
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
            used to define this C{RegexpChunkParser}.
        """
        if len(chunk_struct) == 0:
            print 'Warning: parsing empty text'
            return Tree(self._top_node, [])
        
        try:
            chunk_struct.node
        except AttributeError:
            chunk_struct = Tree(self._top_node, chunk_struct)
        
        # Use the default trace value?
        if trace == None: trace = self._trace

        chunkstr = ChunkString(chunk_struct)

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
        @return: the sequence of rules used by C{RegexpChunkParser}.
        @rtype: C{list} of C{RegexpChunkRule}
        """
        return self._rules

    def __repr__(self):
        """
        @return: a concise string representation of this
            C{RegexpChunkParser}.
        @rtype: C{string}
        """
        return "<RegexpChunkParser with %d rules>" % len(self._rules)

    def __str__(self):
        """
        @return: a verbose string representation of this C{RegexpChunkParser}.
        @rtype: C{string}
        """
        s = "RegexpChunkParser with %d rules:\n" % len(self._rules)
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
##  Chunk Grammar
##//////////////////////////////////////////////////////

class RegexpParser(ChunkParserI):
    """
    A grammar based chunk parser.  C{chunk.RegexpParser} uses a set of
    regular expression patterns to specify the behavior of the parser.
    The chunking of the text is encoded using a C{ChunkString}, and
    each rule acts by modifying the chunking in the C{ChunkString}.
    The rules are all implemented using regular expression matching
    and substitution.

    A grammar contains one or more clauses in the following form::

     NP:
       {<DT|JJ>}          # chunk determiners and adjectives
       }<[\.VI].*>+{      # chink any tag beginning with V, I, or .
       <.*>}{<DT>         # split a chunk at a determiner
       <DT|JJ>{}<NN.*>    # merge chunk ending with det/adj
                          # with one starting with a noun

    The patterns of a clause are executed in order.  An earlier
    pattern may introduce a chunk boundary that prevents a later
    pattern from executing.  Sometimes an individual pattern will
    match on multiple, overlapping extents of the input.  As with
    regular expression substitution more generally, the chunker will
    identify the first match possible, then continue looking for matches
    after this one has ended.

    The clauses of a grammar are also executed in order.  A cascaded
    chunk parser is one having more than one clause.  The maximum depth
    of a parse tree created by this chunk parser is the same as the
    number of clauses in the grammar.

    When tracing is turned on, the comment portion of a line is displayed
    each time the corresponding pattern is applied.

    @type _start: C{string}
    @ivar _start: The start symbol of the grammar (the root node of
        resulting trees)
    @type _stages: C{int}
    @ivar _stages: The list of parsing stages corresponding to the grammar
        
    """
    def __init__(self, grammar, top_node='S', loop=1, trace=0):
        """
        Create a new chunk parser, from the given start state
        and set of chunk patterns.
        
        @param grammar: The list of patterns that defines the grammar
        @type grammar: C{list} of C{string}
        @param top_node: The top node of the tree being created
        @type top_node: L{string} or L{Nonterminal}
        @param loop: The number of times to run through the patterns
        @type loop: L{int}
        @type trace: C{int}
        @param trace: The level of tracing that should be used when
            parsing a text.  C{0} will generate no tracing output;
            C{1} will generate normal tracing output; and C{2} or
            higher will generate verbose tracing output.
        """
        self._trace = trace
        self._stages = []
        self._grammar = grammar
        self._loop = loop

        if isinstance(grammar, basestring):
            self._parse_grammar(grammar, top_node, trace)
        else:
            # Make sur the grammar looks like it has the right type:
            type_err = ('Expected string or list of RegexpChunkParsers '
                        'for the grammar.')
            try: grammar = list(grammar)
            except: raise TypeError(type_err)
            for elt in grammar:
                if not isinstance(elt, RegexpChunkParser):
                    raise TypeError(type_err)
            self._stages = grammar

    def _parse_grammar(self, grammar, top_node, trace):
        """
        Helper function for __init__: parse the grammar if it is a
        string.
        """
        rules = []
        lhs = None
        for line in grammar.split('\n'):
            line = line.strip()
            
            # New stage begins if there's an unescaped ':'
            m = re.match('(?P<nonterminal>(\\.|[^:])*)(:(?P<rule>.*))', line)
            if m:
                # Record the stage that we just completed.
                self._add_stage(rules, lhs, top_node, trace)
                # Start a new stage.
                lhs = m.group('nonterminal').strip()
                rules = []
                line = m.group('rule').strip()

            # Skip blank & comment-only lines
            if line=='' or line.startswith('#'): continue

            # Add the rule
            rules.append(RegexpChunkRule.parse(line))

        # Record the final stage
        self._add_stage(rules, lhs, top_node, trace)

    def _add_stage(self, rules, lhs, top_node, trace):
        """
        Helper function for __init__: add a new stage to the parser.
        """
        if rules != []:
            if not lhs:
                raise ValueError('Expected stage marker (eg NP:)')
            parser = RegexpChunkParser(rules, chunk_node=lhs,
                                       top_node=top_node, trace=trace)
            self._stages.append(parser)

    def parse(self, chunk_struct, trace=None):
        """
        Apply the chunk parser to this input.
        
        @type chunk_struct: C{Tree}
        @param chunk_struct: the chunk structure to be (further) chunked
            (this tree is modified, and is also returned)
        @type trace: C{int}
        @param trace: The level of tracing that should be used when
            parsing a text.  C{0} will generate no tracing output;
            C{1} will generate normal tracing output; and C{2} or
            highter will generate verbose tracing output.  This value
            overrides the trace level value that was given to the
            constructor. 
        @return: the chunked output.
        @rtype: C{Tree}
        """
        if trace == None: trace = self._trace
        for i in range(self._loop):
            for parser in self._stages:
                chunk_struct = parser.parse(chunk_struct, trace=trace)
        return chunk_struct

    def __repr__(self):
        """
        @return: a concise string representation of this C{chunk.RegexpParser}.
        @rtype: C{string}
        """
        return "<chunk.RegexpParser with %d stages>" % len(self._stages)

    def __str__(self):
        """
        @return: a verbose string representation of this
            C{RegexpChunkParser}.
        @rtype: C{string}
        """
        s = "chunk.RegexpParser with %d stages:\n" % len(self._stages)
        margin = 0
        for parser in self._stages:
            s += parser.__str__() + "\n"
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
    @type chunkparser: C{ChunkParserI}
    @param text: The chunked tagged text that should be used for
        evaluation.
    @type text: C{string}
    """
    
    from nltk import chunk, Tree

    # Evaluate our chunk parser.
    chunkscore = chunk.ChunkScore()

    for sentence in text.split('\n'):
        print sentence
        sentence = sentence.strip()
        if not sentence: continue
        gold = chunk.tagstr2tree(sentence)
        tokens = gold.leaves()
        test = chunkparser.parse(Tree('S', tokens), trace=1)
        chunkscore.score(gold, test)
        print

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
            print '  ', ' '.join(c.__str__() for c in chunk)
        if len(chunkscore.missed()) > 10:
            print '  ...'

    # Incorrect chunks.
    if chunkscore.incorrect():
        print 'Incorrect:'
        incorrect = chunkscore.incorrect()
        for chunk in incorrect[:10]:
            print '  ', ' '.join(c.__str__() for c in chunk)
        if len(chunkscore.incorrect()) > 10:
            print '  ...'
    
    print '\\'+('='*75)+'/'
    print

def demo():
    """
    A demonstration for the C{RegexpChunkParser} class.  A single text is
    parsed with four different chunk parsers, using a variety of rules
    and strategies.
    """

    from nltk import chunk, Tree

    text = """\
    [ the/DT little/JJ cat/NN ] sat/VBD on/IN [ the/DT mat/NN ] ./.
    [ John/NNP ] saw/VBD [the/DT cats/NNS] [the/DT dog/NN] chased/VBD ./.
    [ John/NNP ] thinks/VBZ [ Mary/NN ] saw/VBD [ the/DT cat/NN ] sit/VB on/IN [ the/DT mat/NN ]./.
    """

    print '*'*75
    print 'Evaluation text:'
    print text
    print '*'*75
    print

    grammar = r"""
    NP:                   # NP stage
      {<DT>?<JJ>*<NN>}    # chunk determiners, adjectives and nouns
      {<NNP>+}            # chunk proper nouns
    """
    cp = chunk.RegexpParser(grammar)
    chunk.demo_eval(cp, text)

    grammar = r"""
    NP:
      {<.*>}              # start by chunking each tag
      }<[\.VI].*>+{       # unchunk any verbs, prepositions or periods
      <DT|JJ>{}<NN.*>     # merge det/adj with nouns
    """
    cp = chunk.RegexpParser(grammar)
    chunk.demo_eval(cp, text)

    grammar = r"""
    NP: {<DT>?<JJ>*<NN>}    # chunk determiners, adjectives and nouns
    VP: {<TO>?<VB.*>}       # VP = verb words
    """
    cp = chunk.RegexpParser(grammar)
    chunk.demo_eval(cp, text)

    grammar = r"""
    NP: {<.*>*}             # start by chunking everything
        }<[\.VI].*>+{       # chink any verbs, prepositions or periods
        <.*>}{<DT>          # separate on determiners
    PP: {<IN><NP>}          # PP = preposition + noun phrase
    VP: {<VB.*><NP|PP>*}    # VP = verb words + NPs and PPs
    """
    cp = chunk.RegexpParser(grammar)
    chunk.demo_eval(cp, text)

# Evaluation

    from nltk.corpus import conll2000

    print
    print "Demonstration of empty grammar:"
    
    cp = chunk.RegexpParser("")
    print chunk.accuracy(cp, conll2000.chunked_sents('test.txt',
                                                     chunk_types=('NP',)))

    print
    print "Demonstration of accuracy evaluation using CoNLL tags:"

    grammar = r"""
    NP:
      {<.*>}              # start by chunking each tag
      }<[\.VI].*>+{       # unchunk any verbs, prepositions or periods
      <DT|JJ>{}<NN.*>     # merge det/adj with nouns
    """
    cp = chunk.RegexpParser(grammar)
    print chunk.accuracy(cp, conll2000.chunked_sents('test.txt')[:5])

    print
    print "Demonstration of tagged token input"
    
    grammar = r"""
    NP: {<.*>*}             # start by chunking everything
        }<[\.VI].*>+{       # chink any verbs, prepositions or periods
        <.*>}{<DT>          # separate on determiners
    PP: {<IN><NP>}          # PP = preposition + noun phrase
    VP: {<VB.*><NP|PP>*}    # VP = verb words + NPs and PPs
    """
    cp = chunk.RegexpParser(grammar)
    print cp.parse([("the","DT"), ("little","JJ"), ("cat", "NN"),
                    ("sat", "VBD"), ("on", "IN"), ("the", "DT"),
                    ("mat", "NN"), (".", ".")])

if __name__ == '__main__':
    demo()
