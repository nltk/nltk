# Natural Language Toolkit: Tokens and Tokenizers
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

# Open questions:
#    Should "type" and "token" be replaced with "ttype" and "ttoken"?
#    Should representations be modified?

# To do:
#    - unit testing

"""
Basic classes useful for processing individual elements of text, such
as words or sentences.  These elements of text are known as X{text
types}, or X{types} for short.  Occurances of types are known as
X{text tokens}, or X{tokens} for short.  Note that several tokens may
have the same type.  For example, multiple occurances of the same word
in a text will constitute multiple tokens, but only one type.  Tokens
are distinguished based on their X{location} within the source text.

The token module defines the C{Token} class to represent tokens, and
the C{Location} class to represent their locations.  The token module
does not define a single class or interface for representing text
types.  Instead, text types may be represented by any immutable
object.  Typically, elements of text will be represented with strings.
In addition, the token module defines several simple classes that can
be used as text types.  Currently, the following classes are defined:

    - C{TaggedType}: A type consisting of a base type and a tag.  For
      example, this class could be used to represent part-of-speech
      tagged words.

In addition, the token module defines the C{TokenizerI} interface, as
well as several implementations of that interface.  A X{tokenizer} is
a class which converts a string of text into its constituant tokens.
Different tokenizers may split the text up differently.
"""

from chktype import chktype as _chktype
from chktype import chkclass as _chkclass
from types import IntType as _IntType
from types import StringType as _StringType
from types import NoneType as _NoneType

##//////////////////////////////////////////////////////
##  Locations
##//////////////////////////////////////////////////////
class Location:
    """
    A span over indices in a text.

    The text over which the location is defined is identified by the
    C{Location}'s X{source}.  A typical value for a C{Location}'s
    source would be the name of the file containing the text.  The
    unit of the indices in the text is specified by the C{Location}'s
    X{unit}.  Typical units are \"word\" and \"character\".  A
    C{Location}'s source and unit fields are optional; if not
    specified, they will default to C{None}.

    The span itself is represented with by the C{Location}'s X{start
    index} and X{end index}.  A C{Location} identifies the text
    beginning at its start index, and including everything up to (but
    not including) the text at its end index.

    A location with a start index of 5 and an end index of 10, a
    source of 'example.txt', and a unit of 'word' can be written as::

        @[word 5:word 10]@'example.txt'

    C{Location}s are immutable.

    @type _start: C{int}
    @ivar _start: The index at which this C{Location} begins.  The
          C{Location} identifies the text beginning at (and including)
          this value.
    @type _end: C{int}
    @ivar _end: The index at which this C{Location} ends.  The
          C{Location} identifies the text up to (but not including)
          this value.
    @type _source: (any)
    @ivar _source: An identifier naming the text over which this
          location is defined.
    @type _unit: C{string}
    @ivar _unit: The index unit used by this C{Location}.  Typical
          units are 'character' and 'word'.
    """
    def __init__(self, start, end=None, **kwargs):
        """
        Construct a new C{Location}.

        @param start: The start index of the new C{Location}.
        @type start: C{int}
        @param end: The end index of the new C{Location}.  If not
            specified, the end index defaults to C{start+1}
        @type end: C{int}
        @param kwargs: Keyword arguments.  Legal keywords are
            \"source\", which specifies the text over which the
            C{Location}'s is defined; and the \"unit\", which
            specifies the unit of the C{Location}'s indices.
        """
        # Set the start and end locations
        _chktype("Location", 1, start, (_IntType,))
        _chktype("Location", 2, end, (_IntType, _NoneType))
        self._start = start
        if end != None: self._end = end
        else: self._end = self._start+1
        if self._end<self._start:
            raise ValueError("A Location's start index must be less "+
                             "than or equal to its end index.")

        # Set the source and unit
        self._source = self._unit = None
        for (key, val) in kwargs.items():
            if key == 'source':
                self._source = val
            elif key == 'unit':
                if type(val) not in (_StringType, _NoneType):
                    raise TypeError("Unit must have type string")
                self._unit = val
            else:
                assert 0, "Invalid keyword argument: "+key

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
        @return: A concise string representation of this C{Location}.
        @rtype: string
        """
        if self._end != self._start+1:
            str = '@[%d:%d]' % (self._start, self._end)
        else:
            str = '@[%d]' % self._start

        return str

    def __str__(self):
        """
        @return: A verbose string representation of this C{Location}.
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
        @return: true if this C{Location} is equal to C{other}.  In
            particular, return true iff this C{Location}'s source,
            unit, start, and end values are equal to C{other}'s;
            raise an exception iff this C{Location}'s source or unit
            are not equal to C{other}'s; return false otherwise.
        @rtype: C{boolean}
        @raise TypeError: if C{other} is not a C{Location}.
        @raise ValueError: If this C{Location}'s source is not equal
            to C{other}'s source.
        @raise ValueError: If this C{Location}'s unitis not equal
            to C{other}'s unit.
        """
        _chkclass(self, other)
        if self._unit != other._unit:
            raise ValueError('Locations have incompatible units')
        if self._source != other._source:
            raise ValueError('Locations have incompatible sources')
        return (self._start == other._start and
                self._end == other._end)
    
    def __lt__(self, other):
        """
        @return: true if this C{Location} occurs entirely before
            C{other}.  In particular:
                - Return true iff this C{Location}'s end is less than
                  or equal to C{other}'s start, and C{self!=other}
                - Raise an exception iff this C{Location}'s source or
                  unit are not equal to C{other}'s 
                - Return false otherwise.
        @rtype: C{boolean}
        @raise TypeError: if C{other} is not a C{Location}.
        @raise ValueError: If this C{Location}'s source is not equal
            to C{other}'s source.
        @raise ValueError: If this C{Location}'s unitis not equal
            to C{other}'s unit.
        """
        _chkclass(self, other)
        if self._unit != other._unit:
            raise ValueError('Locations have incompatible units')
        if self._source != other._source:
            raise ValueError('Locations have incompatible sources')
        return (self._end <= other._start and
                self._start < other._end)
    
    def __gt__(self, other):
        """
        @return: true if this C{Location} occurs entirely before
            C{other}.  In particular:
                - Return true iff this C{Location}'s start is greater
                  than or equal to C{other}'s end, and C{self!=other}
                - Raise an exception iff this C{Location}'s source or
                  unit are not equal to C{other}'s 
                - Return false otherwise.
        @rtype: C{boolean}
        @raise TypeError: if C{other} is not a C{Location}.
        @raise ValueError: If this C{Location}'s source is not equal
            to C{other}'s source.
        @raise ValueError: If this C{Location}'s unitis not equal
            to C{other}'s unit.
        """
        _chkclass(self, other)
        if self._unit != other._unit:
            raise ValueError('Locations have incompatible units')
        if self._source != other._source:
            raise ValueError('Locations have incompatible sources')
        return (self._start >= other._end and
                self._end > other._start)

    def __le__(self, other):
        """
        @raise AssertionError: <= is not defined for Locations
        """
        assert 0, '<= is not defined over Locations'

    def __ge__(self, other):
        """
        @raise AssertionError: <= is not defined for Locations
        """
        assert 0, '>= is not defined over Locations'

    def __hash__(self):
        """
        @return: A hash value for this C{Location}.
        @rtype: C{int}
        """
        return hash( (self._start, self._end) )

##//////////////////////////////////////////////////////
##  Tokens
##//////////////////////////////////////////////////////
class Token:
    """
    A single occurance of a unit of text, such as a word, a
    punctuation mark, or a sentence.  A token consists of a X{type}
    and a X{location}.  The type is the unit of text (e.g., a specific
    word).  The location is the position at which this token occured
    in the original text.

    The precise defintion of what counts as a type will vary for
    different analyses.  For example, the strings \"bank\" and \"run\"
    might be two different tokens for one analysis, while \"bank/N\"
    and \"bank/V\" might be two different tokens for another analysis.
    Types must be immutable objects that support hashing.  Examples of 
    valid types are strings, numbers, and tuples of immutable hashable 
    types.  Notable invalid types are lists and dictionaries.  Note
    that string text types are case sensitive.

    A token's location may have the special value C{None}, which
    specifies that the token's location is unknown or unimportant.  A
    token with a location of C{None} is not equal to any other token,
    even if their types are equal.

    @type _type: (any)
    @ivar _type: The unit of text of which this token is an
            occurance.
    @type _location: C{Location}
    @ivar _location: The unit of text of which this token is an
            occurance.
    """
    # Classes that inherit from Token should generally redefine:
    #    - type()
    #    - location()
    #    - __eq__()
    #    - __hash__()
    def __init__(self, type, location_or_start=None, end=None, **kwargs):
        """
        Construct a new Token, with the given type and location.  The
        location may be specified in one of three ways:
        
            - If no location is specified, the token's location
              defaults to C{None}.
            - A location may be given as the second argument to the
              constructor.
            - The start, end, source, and unit may be specified
              directly, using the second and third arguments, and the
              keyword arguments.
        
        @param type: The type for the new Token.
        @type type: (any)
        @param location_or_start: The location of the new token; or
            the start index of the new token's location.  If no value
            is specified, the location defaults to C{None}.
        @type location_or_start: C{TextLocation} or C{int}
        @param end: The end index of the new token's location.  This
            may only be specified when C{location_or_start} gives the
            start index of the new token's location.
        @param kwargs: Keyword argments, specifying the source or unit
            for the new token's location.  These may only be specified
            when C{location_or_start} gives the start index of the new
            token's location.            
        """
        _chktype("Token", 2, location_or_start,
                 (_IntType, Location, _NoneType))
        _chktype("Token", 3, end, (_IntType, _NoneType))
        self._type = type
        if isinstance(location_or_start, Location):
            self._location = location_or_start
            if (end is not None) or (len(kwargs)!=0):
                raise TypeError("end and keyword arguments may not "+
                                "be specified in addition to a Location.")
        elif location_or_start == None:
            self._location = location_or_start
            if (end is not None) or (len(kwargs)!=0):
                raise TypeError("end and keyword arguments may not "+
                                "be specified for a location of None.")
        else:
            self._location = Location(location_or_start, end)

    def type(self):
        """
        @return: the unit of text of which this token is an
            occurance.  Typically, this will be a string containing a
            word, such as \"dog\".
        @returntype: (any)
        """
        return self._type
    
    def location(self):
        """
        @return: the position at which this token occured in the
            original text.  A token's location may have the special
            value C{None}, which specifies that the token's location
            is unknown or unimportant.  A token with a location of
            C{None} is not equal to any other token, even if their
            types are equal.
        @returntype: C{Location} or C{None}
        """
        return self._location

    def __eq__(self, other):
        """
        @return: true if this C{Token} is equal to the given
            C{Token}.  In particular, return true iff this C{Token}'s
            type and location are equal to C{other}'s type and location.
        @rtype: C{boolean}
        @raise TypeError: if C{other} is not a C{Token} or subclass of
            C{Token}.
        """
        chkclass(self, other)
        if self.location() == None or other.location() == None: return 0
        return (self._location == other.location and
                self._type == other._type)

    def __cmp__(self, other):
        """
        @raise AssertionError: no ordering relationship is defined
            for Tokens. 
        """
        assert 0, ' no ordering relationship is defined over Tokens'

    def __repr__(self):
        """
        @return: a concise string representation of this C{Token}
        @rtype: string
        """
        if self.location() is None:
            return repr(self.type())+'@[?]'
        else:
            return repr(self.type())+repr(self.location())

    def __str__(self):
        """
        @return: a verbose string representation of this C{Token}
        @rtype: string
        """
        if self.location() is None:
            return repr(self.type())+'@[?]'
        else:
            return repr(self.type())+str(self.location())

    def __hash__(self):
        """
        @return: the hash value for this Token.  If two Tokens are equal,
          they are guaranteed to have the same hash value.  However, two 
          Tokens may have the same hash value and still not be equal.
        @rtype: int

        @raise TypeError: if the C{Token}'s type is
            not hashable.
        """
        return hash( (self._type, self._location) )
    
##//////////////////////////////////////////////////////
##  Tokenizers
##//////////////////////////////////////////////////////
class TokenizerI:
    """
    Processing class responsible for separating a string of text into
    a list of C{Token}s.  This process is also known as X{tokenizing}
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

            tokenize(str)[i].location() < tokenize(str)[j].location()
        
        @param str: The string of text to tokenize.
        @type str: C{string}
        @return: A list containing the C{Token}s
            that are contained in C{str}.
        @rtype: C{list} of C{Token}
        """
        raise NotImplementedError()

class WSTokenizer(TokenizerI):
    """
    A tokenizer that separates a string of text into words, based on
    whitespace.  Each word is encoded as a C{Token} whose type is a
    C{string}.  Location indices start at zero, and have a unit of
    C{'word'}.
    """
    def __init__(self): pass
    def tokenize(self, str, source=None):
        # Inherit docs from TokenizerI
        _chktype("WSTokenizer.tokenize", 1, str, (_StringType,))
        words = str.split()
        tokens = []
        for i in range(len(words)):
            tokens.append(Token(words[i], Location(i, unit='word',
                                                   source=source)))
        return tokens

##//////////////////////////////////////////////////////
##  Test code
##//////////////////////////////////////////////////////
## This is some simple test code for now..
## More extensive unit testing will follow..
    
if __name__ == '__main__':
    text1="""this is a test document.  It contains several words
    and some are   separated by more spaces than  others.. Whee."""

    text2="""Here/x 's/y another/z test/nn document/nn."""
    
    t1=Token('asdf', Location(1,2))
    t2=Token('wer')
    t3=Token('hi there', Location(1,3, source='foo.txt', unit='word'))
    print (t1, t2, t3)
    print t1, t2, t3
    print WSTokenizer().tokenize(text1);print
    print WSTokenizer().tokenize(text2);print
    print TaggedTokenizer().tokenize(text1);print
    ts=TaggedTokenizer().tokenize(text2, 'text2');print ts;print
