#
# Natural Language Toolkit:
# Tokens and Tokenizers
# Edward Loper
#
# Created [03/16/01 05:30 PM]
# $Id$
#

# To do:
#   - add reference documentation
#   - add more type checking, esp for __eq__ etc

from chktype import chktype as _chktype
from types import IntType as _IntType
from types import StringType as _StringType
from types import NoneType as _NoneType

##//////////////////////////////////////////////////////
##  Locations
##//////////////////////////////////////////////////////
class Location:
    """
    A span over indices in a text.

    The text is identified by the C{Location}'s X{source}.  A typical
    value for a C{Location}'s source would be the name of the file
    containing the text.  The unit of the indices in the text is
    specified by the C{Location}'s X{unit}.  Typical units are
    \"word\" and \"character\".

    The span is represented with by the C{Location}'s X{start index}
    and X{end index}.  A C{Location} identifies the text beginning at
    its start index, and including everything up to (but not
    including) the text at its end index.

    A C{Location}'s source and unit fields are optional; if not
    specified, they will default to C{None}.

    A location with a start index of 5 and an end index of 10, a
    source of 'example.txt', and a unit of 'word' can be written as::

        @[word 5:word 10]@'example.txt'

    C{Location}s are immutable.
    """
    def __init__(self, start, end=None, source=None, unit=None):
        _chktype("Location", 1, start, (_IntType,))
        _chktype("Location", 2, end, (_IntType, _NoneType))
        _chktype("Location", 4, unit, (_StringType, _NoneType))
        self._start = start
        if end != None: self._end = end
        else: self._end = self._start+1
        self._source = source
        self._unit = unit

    def start(self):
        """
        @return: the index at which this C{Location} begins.  The
          C{Location} identifies the text beginning at (and including)
          this value.
        @rtype: C{int}
        """
        return self._start
    
    def end(self):
        """
        @return: the index at which this C{Location} ends.  The
          C{Location} identifies the text up to (but not including)
          this value.
        @rtype: C{int}
        """
        return self._end
    
    def source(self):
        """
        @return: an identifier naming the text over which this
          location is defined. A typical example of a source would be
          a string containing the name of the file containing the
          text.  Sources may also be represented as C{Location}s; for
          example, the source for the location of a word might be the
          location of the sentence that contains that word.
        @rtype: (any)
        """
        return self._source
    
    def unit(self):
        """
        @return: the index unit used by this C{Location}.  Typical
          units are 'character' and 'word'.
        @rtype: C{string}
        """
        return self._unit
        
    def __repr__(self):
        """
        @return: A string representation of this C{Location}.
        @rtype: string
        """
        if self._end != self._start+1:
            str = '@[%d:%d]' % (self._start, self._end)
        else:
            str = '@[%d]' % self._start

        return str

    def __str__(self):
        """
        @return: A string representation of this C{Location}.
        @rtype: string
        """
        if self._end != self._start+1:
            str = '@[%d:%d]' % (self._start, self._end)
        else:
            str = '@[%d]' % self._start

        if self._source != None:
            str += '@'+`self._source`

        return str

    def __eq__(self, other):
        """
        @return: true if this C{location} is equal to C{other}.  In
            particular, return true iff this C{location}'s source,
            unit, start, and end values are equal to C{other}'s.
        @raise ValueError: If this C{location}'s source is not equal
            to C{other}'s source.
        @raise ValueError: If this C{location}'s unitis not equal
            to C{other}'s unit.
        """
        if self._unit != other._unit:
            raise ValueError('Locations have incompatible units')
        if self._source != other._source:
            raise ValueError('Locations have incompatible sources')
        return (self._start == other._start and
                self._end == other._end)
    
    def __lt__(self, other):
        if self._unit != other._unit:
            raise ValueError('Locations have incompatible units')
        if self._source != other._source:
            raise ValueError('Locations have incompatible sources')
        return (self._end <= other._start and
                self._start < other._end)
    
    def __gt__(self, other):
        if self._unit != other._unit:
            raise ValueError('Locations have incompatible units')
        if self._source != other._source:
            raise ValueError('Locations have incompatible sources')
        return (self._start >= other._end and
                self._end > other._start)

    def __le__(self, other):
        assert 0, '<= is not defined over Locations'

    def __ge__(self, other):
        assert 0, '>= is not defined over Locations'

    def __hash__(self):
        return hash( (self._start, self._end) )

##//////////////////////////////////////////////////////
##  Tokens
##//////////////////////////////////////////////////////
class Token:
    """
    An occurance of a single unit of text, such as a word or a
    punctuation mark.  A Token consists of a X{type} and a X{source}.
    The type is the unit of text (e.g., a specific word).  The source
    is the position at which this token occured in the original text.

    The precise defintion of what counts as a type will vary for
    different analyses.  For example, \"bank\" and \"run\" might be
    two different tokens for one analysis, while \"bank/N\" and
    \"bank/V\" might be two different tokens for another analysis.

    Types must be immutable objects that support hashing.  Examples of 
    valid types are strings, numbers, and tuples of immutable hashable 
    types.  Notable invalid types are lists and dictionaries.

    See also:
        - nltk.TokenTypeI
        - nltk.TextLocationI
        - (insert textbook ref here?)
    """
    def __init__(self, type, source_or_start=None, end=None):
        """
        Construct a new Token, with the given type and source.
        
        @param type: The type for the new Token.
        @type type: (any)
        @param source: The source for the new Token.
        @type source: TextLocation
        """
        self._type = type
        if isinstance(source_or_start, Location):
            self._source = source_or_start
        elif source_or_start == None:
            self._source = source_or_start
        else:
            self._source = Location(source_or_start, end)

    def type(self):
        """
        @return: the type of this token.
        @returntype: TokenTypeI
        """
        return self._type
    
    def source(self):
        """
        @return: the source of this token.
        @returntype: TextLocationI
        """
        return self._source

    def __eq__(self, other):
        """
        @return: true if this C{Token} is equal to the given C{Token}.
        @rtype: C{boolean}
        """
        if not isinstance(other, Token): return 0
        if self.source() == None or other.source() == None: return 0
        if self.source() != other.source(): return 0
        return self.type()==other.type()

    def __repr__(self):
        """
        @return: a string representation of typs C{Token}
        @rtype: string
        """
        if self.source() is None:
            return repr(self.type())+'@?'
        else:
            return repr(self.type())+repr(self.source())

    def __str__(self):
        """
        @return: a string representation of typs C{Token}
        @rtype: string
        """
        if self.source() is None:
            return repr(self.type())+'@?'
        else:
            return repr(self.type())+str(self.source())

    def __hash__(self):
        """
        Return the hash value for this Token.  If two Tokens are equal,
        they are guaranteed to have the same hash value.  However, two 
        Tokens may have the same hash value and still not be equal.

        @raise TypeError: if the <CODE>Token</CODE>'s type or source is 
               not hashable.
        @return: The hash value for this Token.
        @returntype: int
        """
        return hash(self.type(), self.source())

##//////////////////////////////////////////////////////
##  Type classes
##//////////////////////////////////////////////////////
class TaggedType:
    def __init__(self, base, tag):
        self._base = base
        self._tag = tag
    def base(self): return self.base
    def tag(self): return self.tag
    def __eq__(self, other):
        return (self.base == other.base and
                self.tag == other.tag)
    def __hash__(self):
        return hash( (self.base, self.tag) )
    def __repr__(self):
        return repr(self._base)+'/'+repr(self._tag)

def parseTaggedType(string, unknownTag='UNK'):
    _chktype("parseTaggedType", 1, string, (_StringType,))
    elts = string.split('/')
    if len(elts) > 1:
        return TaggedType('/'.join(elts[:-1]), elts[-1])
    else:
        return TaggedType(string, unknownTag)
    
##//////////////////////////////////////////////////////
##  Tokenizers
##//////////////////////////////////////////////////////
class TokenizerI:
    """##
    Processing class responsible for separating a string of text into
    a list of C{Token}s.  This process is also known as X{tokenizing}
    the string of text.  Particular C{Tokenizer}s may split the text
    at different points, or may produce Tokens with different types.
    """
    def __init__(self):
        raise NotImplementedError()
    
    def tokenize(self, str):
        """##
        Separate the given string of text into a list of C{Token}s.
        
        @param str: The string of text to tokenize.
        @type str: string
        @return: A list containing the C{Token}s
                that are contained in C{str}.
        @rtype: C{list} of C{Token}
        """
        raise NotImplementedError()

class SimpleTokenizer(TokenizerI):
    """##
    A tokenizer that separates a string of text into Tokens using
    whitespace.  Each word is encoded as a C{Token} whose type is a
    C{string}.
    """
    def tokenize(self, str):
        # Inherit docs from TokenizerI
        words = str.split()
        tokens = []
        for i in range(len(words)):
            tokens.append(Token(words[i], Location(i)))
        return tokens

class TaggedTokenizer(TokenizerI):
    """##
    A tokenizer that splits a string of tagged text into Tokens using
    whitespace.  Each tagged word is encoded as a C{Token}
    whose type is a C{TaggedType}.
    C{IndexTextLocation}s are used to encode the
    C{Token}s' sources.

    <P>More formal definition?
    """
    def tokenize(self, str):
        # Inherit docs from TokenizerI
        words = str.split()
        tokens = []
        for i in range(len(words)):
            ttype = parseTaggedType(words[i])
            tokens.append(Token(ttype, Location(i)))
        return tokens
  
##//////////////////////////////////////////////////////
##  Test code
##//////////////////////////////////////////////////////
text1="""this is a test document.  It contains several words
and some are   separated by more spaces than  others.. Whee."""

text2="""Here/x 's/y another/z test/nn document/nn."""
    
if __name__ == '__main__':
    t1=Token('asdf', Location(1,2))
    t2=Token('wer')
    t3=Token('hi there', Location(1,3,'foo.txt', 'word'))
    print (t1, t2, t3)
    print t1, t2, t3
    print SimpleTokenizer().tokenize(text1);print
    print SimpleTokenizer().tokenize(text2);print
    print TaggedTokenizer().tokenize(text1);print
    print TaggedTokenizer().tokenize(text2);print
