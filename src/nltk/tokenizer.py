# Natural Language Toolkit: Tokenizers
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
#         Steven Bird <sb@ldc.upenn.edu> (minor additions)
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

"""
Classes and interfaces for dividing a string into a list of its
constituent tokens.  This task, which is known as X{tokenizing}, is
defined by the L{TokenizerI} interface.

This module defines several implementations of the tokenizer
interface, such as L{WSTokenizer}, which splits texts based on
whitespace; and L{RETokenizer}, which uses a regular expression to
divide a string into tokens.  Several other modules also define
specialized tokenizers, such as L{nltk.tree.TreebankTokenizer} and
L{nltk.tagger.TaggedTokenizer}.  For a complete list of available
tokenizers, see the reference documentation for L{TokenizerI}.

@group Interfaces: TokenizerI
@group Tokenizers: WSTokenizer, RETokenizer, CharTokenizer,
    LineTokenizer, _XTokenTuple
@sort: Location, Token, TokenizerI, WSTokenizer, RETokenizer, CharTokenizer,
    LineTokenizer, _XTokenTuple
"""

import re, sys, types
from nltk.chktype import chktype as _chktype 
from nltk.chktype import classeq as _classeq
from nltk.token import *

##//////////////////////////////////////////////////////
##  Tokenizers
##//////////////////////////////////////////////////////
class TokenizerI:
    """
    A processing class responsible for separating a string of text
    into a list of C{Token}s.  This process is known as X{tokenizing}
    the string of text.  Particular C{Tokenizer}s may split the text
    at different points, or may produce Tokens with different types.
    """
    def __init__(self):
        """
        Construct a new C{Tokenizer}.
        """
    
    def tokenize(self, str):
        """
        Separate the given string of text into a list of C{Token}s.
        The list of C{Token}s returned by tokenizing will be properly
        ordered; i.e., for any i and j such that i<j::

            tokenize(str)[i].loc() < tokenize(str)[j].loc()
        
        @param str: The string of text to tokenize.
        @type str: C{string}
        @return: A list containing the C{Token}s
            that are contained in C{str}.
        @rtype: C{list} of C{Token}
        """
        raise NotImplementedError()

    def xtokenize(self, str):
        """
        Separate the given string of text into a list of C{Token}s.
        The tuple of C{Token}s returned by tokenizing will be properly
        ordered; i.e., for any i and j such that i<j::

            tokenize(str)[i].loc() < tokenize(str)[j].loc()

        Like C{xrange} and C{file.xreadlines}, C{xtokenize} will
        return a structure that emulates a tuple, without actually
        keeping all of the tokens in memory.  The details of what
        structure is used are left to the individual tokenizers; but
        it is guaranteed that the value returned by xtokenize will
        emulate a tuple of tokens.
        
        @param str: The string of text to tokenize.
        @type str: C{string}
        @return: A tuple-equivalant structure containing the C{Token}s
            that are contained in C{str}.
        @rtype: C{tuple} of C{Token} (or equiv.)
        """
        # By default, call tokenize.
        return self.tokenize(str)

class _XTokenTuple:
    """
    An internal class used to implement the C{xtokenize} method of
    several tokenizers.  C{_XTokenTuple} essentially emulates a list
    tuple of tokens; however, instead of explicitly storing the
    tokens, they are generated on the fly as they are asked for.  This
    seriously decreases the memory requirements for processing large
    texts.

    Internally, C{_XTokenTuple} just maintains a list of types; the
    location of each type should be its offset.  Thus, _XTokenTuple
    only supports token tuples where the location of the M{n}th token
    is @[M{n}].
    """
    def __init__(self, typelist, unit=None, source=None):
        self._typelist = tuple(typelist)
        self._unit = unit
        self._source = source

    def __getitem__(self, index):
        if type(index) == types.SliceType:
            start, stop = (index.start, index.stop)
            if stop == sys.maxint: stop = len(self)

            toks = []
            for i in range(start, stop):
                loc = Location(i, unit=self._unit, source=self._source)
                toks.append(Token(self._typelist[i], loc))
            return toks
        else:
            loc = Location(index, unit=self._unit, source=self._source)
            return Token(self._typelist[index], loc)

    def __len__(self):
        return len(self._typelist)

    def __in__(self, token):
        if not isinstance(token, Token): return 0
        loc = token.loc()
        if loc is None: return 0
        if loc.length() != 1: return 0
        if loc.unit() != self._unit: return 0
        if loc.source() != self._source: return 0
        start = loc.start()
        if start<0 or start>=len(self._typelist): return 0
        return self._typelist[start] == token.type()

    def __repr__(self):
        return repr(self[0:len(self)])
    
class WSTokenizer(TokenizerI):
    """
    A tokenizer that separates a string of text into words, based on
    whitespace.  Each word is encoded as a C{Token} whose type is a
    C{string}.  Location indices start at zero, and have a default
    unit of C{'w'}.
    """
    def __init__(self): pass
    def tokenize(self, str, unit='w', source=None):
        # Inherit docs from TokenizerI
        assert _chktype(1, str, types.StringType)
        words = str.split()
        return [Token(words[i], Location(i, unit=unit, source=source))
                for i in range(len(words))]

    def xtokenize(self, str, unit='w', source=None):
        # Inherit docs from TokenizerI
        assert _chktype(1, str, types.StringType)
        return _XTokenTuple(str.split(), unit='w', source=source)

# Do we really want this tokenizer to ignore whitespace characters?
class CharTokenizer(TokenizerI):
    """
    A tokenizer that returns each non-whitespace character as a token.
    Each character is encoded as a C{Token} whose type is a C{string}.
    Location indices start at zero, and have a default unit of C{'c'}.
    """
    def __init__(self): pass
    def tokenize(self, str, unit='c', source=None):
        # Inherit docs from TokenizerI
        assert _chktype(1, str, types.StringType)
        return [Token(str[i], Location(i, unit=unit, source=source))
                for i in range(len(str))
                if str[i] not in ' \t\n\r\v']

class LineTokenizer(TokenizerI):
    """
    A tokenizer that separates a string of text into sentences, based
    on newline characters.  Blank lines are ignored.  Each sentence is
    encoded as a C{Token} whose type is a C{string}.  Location indices
    start at zero, and have a default unit of C{'l'}.
    """
    def __init__(self): pass
    def tokenize(self, str, unit='l', source=None):
        # Inherit docs from TokenizerI
        assert _chktype(1, str, types.StringType)
        lines = [s for s in str.split('\n') if s.strip() != '']
        return [Token(lines[i], Location(i, unit=unit, source=source))
                for i in range(len(lines))]

    def xtokenize(self, str, source=None):
        # Inherit docs from TokenizerI
        assert _chktype(1, str, types.StringType)
        lines = [s for s in str.split('\n') if s.strip() != '']
        return _XTokenTuple(lines, source=source, unit='l') 

class RETokenizer(TokenizerI):
    """
    A tokenizer that separates a string of text into words, based on a
    regular expression.  By default, the regular expression specifies
    the form of a single word type; so the list of tokens returned
    includes all non-overlapping substrings that match the given
    regular expression.  However, if the optional constructor
    parameter C{negative} is true, then the regular expression
    specifies the form of word separators; so the list of tokens
    returned includes all substrings that occur between matches of the
    regular expression.
    
    Each word is encoded as a C{Token} whose type is a C{string}.
    Location indices start at zero, and have a unit of C{'word'}.
    """
    def __init__(self, regexp, negative=0):
        """
        Create a new C{RETokenizer} from a given regular expression.
        
        @type regexp: C{string} or C{SRE_Pattern}
        @param regexp: The regular expression used to tokenized texts.
            Unless C{negative} is true, this regular expression
            specifies the form of a single word type; so the list of
            tokens generated by tokenization includes all non-overlapping
            substrings that match C{regexp}
        @type negative: C{boolean}
        @param negative: An optional parameter that inverts the
            meaning of C{regexp}.  In particular, if C{negative} is
            true, then C{regexp} is taken to specify the form of word
            separators (and not word types); so the list of tokens
            generated by tokenization includes all substrings that
            occur I{between} matches of the regular expression.
        """
        if type(regexp).__name__ == 'SRE_Pattern': regexp = regexp.pattern
        assert _chktype(1, regexp, types.StringType)
        self._negative = negative
        
        # Replace any grouping parenthases with non-grouping ones.  We
        # need to do this, because the list returned by re.sub will
        # contain an element corresponding to every set of grouping
        # parenthases.
        regexp = re.sub(r'\((?!\?)', r'(?:', regexp)

        # Add grouping parenthases around the regexp; this will allow
        # us to access the material that was split on.
        self._regexp = re.compile('('+regexp+')', re.UNICODE)
        
    def tokenize(self, str, unit='w', source=None):
        # Inherit docs from TokenizerI
        assert _chktype(1, str, types.StringType)

        # This split will return a list of alternating matches and
        # non-matches.  If negative=1, then we want the even elements;
        # if negative=0, then we want the odd elements.
        words = self._regexp.split(str)
        
        if self._negative:
            words = [words[i] for i in range(len(words))
                     if i%2==0 and words[i] != '']
        else:
            words = [words[i] for i in range(len(words))
                     if i%2==1 and words[i] != '']
            
        return [Token(words[i], Location(i, unit=unit, source=source))
                for i in range(len(words))]

    def xtokenize(self, str, unit='w', source=None):
        # Inherit docs from TokenizerI
        assert _chktype(1, str, types.StringType)

        # This split will return a list of alternating matches and
        # non-matches.  If negative=1, then we want the even elements;
        # if negative=0, then we want the odd elements.
        words = self._regexp.split(str)
        
        if self._negative:
            words = [words[i] for i in range(len(words))
                     if i%2==0 and words[i] != '']
        else:
            words = [words[i] for i in range(len(words))
                     if i%2==1 and words[i] != '']

        return _XTokenTuple(words, unit, source)

##//////////////////////////////////////////////////////
##  Demonstration
##//////////////////////////////////////////////////////

def demo():
    """
    A demonstration function, showing the output of several different
    tokenizers on the same string.
    """
    # Set up the test data.
    s = "Good muffins cost $3.88\nin New York.  Please buy me\ntwo of them. "
    tokenizers = [
        [r"WSTokenizer()                     # Simple word tokenizer"],
        [r"RETokenizer(r'\w+')               # Only keep alphanumerics"],
        [r"RETokenizer(r'\w+|[^a-zA-Z\s]+')  # Group non-alpha characters"],
        [r"RETokenizer(r'\.\s+', negative=1) # Simple sentence tokenizer",
         's'], # unit for tokenize()
        [r"LineTokenizer()                   # Tokenize into lines"],
        [r"CharTokenizer()                   # Tokenize into characters"],
        ]
                  
    def wordwrap(tokens):
        str = '['
        index = 0
        lines = 0
        for tok in tokens:
            tokrepr = `tok`
            index += len(tokrepr)+2
            if index >= 75:
                str += '\n '
                index = len(tokrepr)+3
                lines += 1
            if lines > 2:
                str += '..., '
                break
            str += '%s, ' % tokrepr
        str = str[:-2] + ']'
        return str
    
    print '='*75
    print 'Test string:'
    print "'''%s'''" % s
    for elt in tokenizers:
        print '_'*75
        descr = elt[0]
        tokenizer = eval(descr.split('#')[0])
        print 'tokenizer = %s' % descr
        if len(elt) == 1:
            print 'tokenizer.tokenize(s)'
            print wordwrap(tokenizer.tokenize(s))
        else:
            print 'tokenizer.tokenize(s, unit="%s")' % elt[1]
            print wordwrap(tokenizer.tokenize(s, unit=elt[1]))

    print '='*75
    
if __name__ == '__main__':
    demo()
    
