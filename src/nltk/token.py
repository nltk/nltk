# Natural Language Toolkit: Tokens and Tokenizers
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
#         Steven Bird <sb@ldc.upenn.edu> (minor additions)
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

# Open questions:
#    Should "type" and "token" be replaced with "ttype" and "ttoken"?
#    Should representations be modified?
#    What should comparisons do when given bad types??? e.g., != with
#        None? 

# To do:
#    - unit testing
#    - Am I happy with current str/repr???

"""
Basic classes useful for processing individual elements of text, such
as words or sentences.  These elements of text are known as X{text
types}, or X{types} for short.  Individual occurances of types are
known as X{text tokens}, or X{tokens} for short.  Note that several
different tokens may have the same type.  For example, multiple
occurances of the same word in a text will constitute multiple tokens,
but only one type.  Tokens are distinguished based on their
X{location} within the source text.

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

from nltk.chktype import chktype as _chktype 
from nltk.chktype import chkclass as _chkclass

import re, sys

from types import IntType as _IntType
from types import StringType as _StringType
from types import NoneType as _NoneType
from types import SliceType as _SliceType

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
        if end is not None: self._end = end
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

    def length(self):
        """
        @return: the length of this C{Location}.  In particular,
            for a location M{@[a:b]}, return M{b-a}.
        @rtype: int
        """
        return self._end - self._start
    
    def __len__(self):
        """
        @return: the length of this C{Location}.  In particular,
            for a location M{@[a:b]}, return M{b-a}.
        @rtype: int
        """
        return self._end - self._start
    
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

    def union(self, other):
        _chktype('union', 1, other, (Location,))
        if self._unit != other._unit:
            raise ValueError('Locations have incompatible units')
        if self._source != other._source:
            raise ValueError('Locations have incompatible sources')
        if self._end == other._start:
            return Location(self._start, other._end, unit=self._unit,
                            source=self._source)
        elif self._start == other._end:
            return Location(other._start, self._end, unit=self._unit,
                            source=self._source)
        else:
            raise ValueError('Locations are not contiguous')
    
    def __add__(self, other):
        return self.union(other)

    def unit(self):
        """
        @return: the index unit used by this C{Location}.  Typical
          units are 'character' and 'word'.
        @rtype: C{string}
        """
        return self._unit
        
    def start_loc(self):
        """
        @return: a C{Location} corresponding to the start of this C{Location}.
        @rtype: C{Location}
        """
        return Location(self.start(), self.start(),
                        unit=self.unit(), source=self.source())

    def end_loc(self):
        """
        @return: a C{Location} corresponding to the end of this C{Location}.
        @rtype: C{Location}
        """
        return Location(self.end(), self.end(),
                        unit=self.unit(), source=self.source())

    def select(self, lst):
        """
        Given the list over which this location is defined, return the
        list of elements specified by the location.  In other words,
        return C{lst[self.start():self.end()]}.
        
        @param lst: The list of elements over which this location is
            defined.
        @type lst: C{list}
        @return: C{lst[self.start():self.end()]}
        @rtype: C{list}
        """
        return lst[self.start():self.end()]

    def __repr__(self):
        """
        @return: A concise string representation of this C{Location}.
        @rtype: string
        """
        ###### TEMPORARY
        return self.__str__()
    
        if self._unit is not None: unit = self._unit
        else: unit = ''
        
        if self._end != self._start+1:
            str = '@[%d%s:%d%s]' % (self._start, unit, self._end, unit)
        else:
            str = '@[%d%s]' % (self._start, unit)

        return str

    def __str__(self):
        """
        @return: A verbose string representation of this C{Location}.
        @rtype: string
        """
        s = '@[%d' % self._start
        
        if self._unit is not None: s += self._unit

        if self._end != self._start+1:
            s += ':%d' % self._end
            if self._unit is not None: s += self._unit

        s += ']'
            
        if self._source is not None:
            if isinstance(self._source, Location):
                s += str(self._source)
            else:
                s += '@'+`self._source`

        return s

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
        @raise ValueError: If this C{Location}'s unit is not equal
            to C{other}'s unit.
        """
        _chkclass(self, other)
        if self._unit != other._unit:
            raise ValueError('Locations have incompatible units')
        if self._source != other._source:
            raise ValueError('Locations have incompatible sources')
        return (self._start == other._start and
                self._end == other._end)
    
    def __ne__(self, other):
        """
        @return: true if this C{Location} is not equal to C{other}.  In
            particular, return false iff this C{Location}'s source,
            unit, start, and end values are equal to C{other}'s;
            raise an exception iff this C{Location}'s source or unit
            are not equal to C{other}'s; return false otherwise.
        @rtype: C{boolean}
        @raise TypeError: if C{other} is not a C{Location}.
        @raise ValueError: If this C{Location}'s source is not equal
            to C{other}'s source.
        @raise ValueError: If this C{Location}'s unit is not equal
            to C{other}'s unit.
        """
        return not (self == other)
        
    def prec(self, other):
        """
        @return: true if this C{Location} occurs entirely before
            C{other}.  In particular:
                - Raise an exception if this C{Location}'s source or
                  unit are not equal to C{other}'s 
                - Return true if this C{Location}'s end is less than
                  or equal to C{other}'s start, and C{self!=other}
                - Return false otherwise.
        @rtype: C{boolean}
        @raise TypeError: if C{other} is not a C{Location}.
        @raise ValueError: If this C{Location}'s source is not equal
            to C{other}'s source.
        @raise ValueError: If this C{Location}'s unit is not equal
            to C{other}'s unit.
        """
        _chkclass(self, other)
        if self._unit != other._unit:
            raise ValueError('Locations have incompatible units')
        if self._source != other._source:
            raise ValueError('Locations have incompatible sources')
        return (self._end <= other._start and
                self._start < other._end)
    
    def succ(self, other):
        """
        @return: true if this C{Location} occurs entirely before
            C{other}.  In particular:
                - Raise an exception if this C{Location}'s source or
                  unit are not equal to C{other}'s 
                - Return true if this C{Location}'s start is greater
                  than or equal to C{other}'s end, and C{self!=other}
                - Return false otherwise.
        @rtype: C{boolean}
        @raise TypeError: if C{other} is not a C{Location}.
        @raise ValueError: If this C{Location}'s source is not equal
            to C{other}'s source.
        @raise ValueError: If this C{Location}'s unit is not equal
            to C{other}'s unit.
        """
        _chkclass(self, other)
        if self._unit != other._unit:
            raise ValueError('Locations have incompatible units')
        if self._source != other._source:
            raise ValueError('Locations have incompatible sources')
        return (self._start >= other._end and
                self._end > other._start)

    def overlaps(self, other):
        """
        @return: true if this C{Location} overlaps C{other}.  In
            particular: 
                - Raise an exception if this C{Location}'s source or
                  unit are not equal to C{other}'s 
                - Return true if ..?
                - Return false otherwise.
        @rtype: C{boolean}
        @raise TypeError: if C{other} is not a C{Location}.
        @raise ValueError: If this C{Location}'s source is not equal
            to C{other}'s source.
        @raise ValueError: If this C{Location}'s unit is not equal
            to C{other}'s unit.
        """
        _chkclass(self, other)
        if self._unit != other._unit:
            raise ValueError('Locations have incompatible units')
        if self._source != other._source:
            raise ValueError('Locations have incompatible sources')
        (s1,e1) = (self._start, self._end)
        (s2,e2) = (other._start, other._end)
        return (s1<e2 and e1>s2) or (s2<e1 and e2>s1)

    def __cmp__(self, other):
        """
        Compare two locations, based on their start locations and end
        locations.  In particular:

            - Raise an exception if C{self}'s source or
              unit are not equal to C{other}'s.
            - First, compare based on the start locations.  I.e., if
              C{self.start<other.start}, then C{self<other}; and if 
              C{self.start>other.start}, then C{self>other}.
            - If C{self.start=other.start}, then compare based on the
              end locations.   I.e., if C{self.end<other.end}, then
              C{self<other}; and if C{self.end>other.end}, then
              C{self>other}.
            - If both the start locations and the end locations are
              equal, then C{self==other}.

        @return: -1 if C{self<other}; +1 if C{self>other}; and 0 if
                 C{self==other}. 
        @raise TypeError: if C{other} is not a C{Location}.
        @raise ValueError: If this C{Location}'s source is not equal
            to C{other}'s source.
        @raise ValueError: If this C{Location}'s unit is not equal
            to C{other}'s unit.
        """
        _chkclass(self, other)
        if self._unit != other._unit:
            raise ValueError('Locations have incompatible units')
        if self._source != other._source:
            raise ValueError('Locations have incompatible sources')
        return cmp( (self._start, self._end), (other._start, other._end) )

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
    #    - loc()
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
            self._location = Location(location_or_start, end, **kwargs)

    def type(self):
        """
        @return: the unit of text of which this token is an
            occurance.  Typically, this will be a string containing a
            word, such as \"dog\".
        @returntype: (any)
        """
        return self._type
    
    def loc(self):
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
        _chkclass(self, other)
        if self.loc() is None or other.loc() is None: return 0
        return (self._location == other._location and
                self._type == other._type)

    def __ne__(self, other):
        """
        @return: true if this C{Token} is not equal to the given
            C{Token}.  In particular, return false iff this C{Token}'s
            type and location are equal to C{other}'s type and location.
        @rtype: C{boolean}
        @raise TypeError: if C{other} is not a C{Token} or subclass of
            C{Token}.
        """
        return not (self == other)

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
        if self.loc() is None:
            return repr(self.type())+'@[?]'
        else:
            return repr(self.type())+repr(self.loc())

    def __str__(self):
        """
        @return: a verbose string representation of this C{Token}
        @rtype: string
        """
        if self.loc() is None:
            return repr(self.type())+'@[?]'
        else:
            return repr(self.type())+str(self.loc())

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
        self.tokenize(str)

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
    def __init__(self, typelist, **kws):
        self._typelist = tuple(typelist)
        self._kws = kws

    def __getitem__(self, index):
        if type(index) == _SliceType:
            if index.stop == sys.maxint:
                return tuple([Token(self._typelist[i], i, **self._kws) for i in
                              range(index.start, len(self))])
            else:
                return tuple([Token(self._typelist[i], i, **self._kws) for i in
                              range(index.start, index.stop)])
        else:
            return Token(self._typelist[index], index, **self._kws)

    def __len__(self):
        return len(self._typelist)

    def __in__(self, token):
        if not isinstance(token, Token): return 0
        loc = token.loc()
        if loc == None:
            return 0
        start = loc.start()
        if Location(start, **self._kws) != loc:
            return 0
        if start<0 or start>=len(self._typelist):
            return 0
        return self._typelist[start] == token.type()

    def __repr__(self):
        return repr(self[0:len(self)])
    
class WSTokenizer(TokenizerI):
    """
    A tokenizer that separates a string of text into words, based on
    whitespace.  Each word is encoded as a C{Token} whose type is a
    C{string}.  Location indices start at zero, and have a unit of
    C{'w'}.
    """
    def __init__(self): pass
    def tokenize(self, str, source=None):
        # Inherit docs from TokenizerI
        _chktype("WSTokenizer.tokenize", 1, str, (_StringType,))
        words = str.split()
        return [Token(words[i], Location(i, unit='w', source=source))
                for i in range(len(words))]

    def xtokenize(self, str, source=None):
        # Inherit docs from TokenizerI
        _chktype("WSTokenizer.xtokenize", 1, str, (_StringType,))
        return _XTokenTuple(str.split(), source=source, unit='w')

class LineTokenizer(TokenizerI):
    """
    A tokenizer that separates a string of text into sentences, based
    on newline characters.  Each sentence is encoded as a C{Token}
    whose type is a C{string}.  Location indices start at zero, and
    have a unit of C{'s'}.
    """
    def __init__(self): pass
    def tokenize(self, str, source=None):
        # Inherit docs from TokenizerI
        _chktype("WSTokenizer.tokenize", 1, str, (_StringType,))
        tokens = []
        i = 0
        for sent in str.split('\n'):
            if sent.strip() != '':
                tok = Token(sent, Location(i, unit='s', source=source))
                tokens.append(tok)
                i += 1
        return tokens

    def xtokenize(self, str, source=None):
        # Inherit docs from TokenizerI
        _chktype("WSTokenizer.xtokenize", 1, str, (_StringType,))
        return _XTokenTuple([s for s in str.split('\n')
                             if s.strip() != ''],
                            source=source, unit='s') 

class RETokenizer(TokenizerI):
    """
    
    A tokenizer that separates a string of text into words, based on a
    regular expression.  The list of tokens returned includes all
    substrings that match the given regular expression.  Each word
    is encoded as a C{Token} whose type is a C{string}.  Location
    indices start at zero, and have a unit of C{'word'}.
    """
    def __init__(self, regexp, positive=1):
        """
        @type regexp: string
        """
        _chktype("RETokenizer", 1, regexp, (_StringType, ))
        self._regexp = re.compile('('+regexp+')')
        self._positive = positive
        
    def tokenize(self, str, **kwargs):
        # Inherit docs from TokenizerI
        _chktype("RETokenizer.tokenize", 1, str, (_StringType,))

        if '\0' in str or '\1' in str:
            raise ValueError("RETokenizer can't handle "+
                             "strings containing '\\0' or '\\1'")

        if self._positive:
            # Surround each match with \0...\1
            str = re.sub(self._regexp, '\0\\1\1', str)

            # Special case: if we found no tokens at all, return an empty list.
            if '\0' not in str: return []

            str = re.sub('(\1[^\0]*\0)|(^[^\0]+\0)|(\1[^\1]*$)',
                         '\0', str)
            words = str.split('\0')
        else:
            words = re.sub(self._regexp, '\0', str).split('\0')
        
        tokens = []
        loc = 0
        for i in range(len(words)):
            if words[i] == '': continue
            tokens.append(Token(words[i], Location(loc, **kwargs)))
            loc += 1
        return tokens

    # Does not handle self._positive!!
    def xtokenize(self, str, **kwargs):
        # Inherit docs from TokenizerI
        _chktype("WSTokenizer.xtokenize", 1, str, (_StringType,))

        if '\0' in str or '\1' in str:
            raise ValueError("RETokenizer can't handle "+
                             "strings containing '\\0' or '\\1'")

        if self._positive:
            str = re.sub(self._regexp, '\0\\1\1', str)
            if '\0' in str:
                str = re.sub('(\1[^\0]*\0)|(^[^\0]+\0)|(\1[^\1]*$)',
                             '\0', str)
        else:
            str = re.sub(self._regexp, '\0', str)
            
        words = [w for w in str.split('\0') if w != '']
        return _XTokenTuple(words, **kwargs)

