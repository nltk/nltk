# Natural Language Toolkit: Tokens
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
#         Steven Bird <sb@ldc.upenn.edu> (minor additions)
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

"""
Basic classes for processing individual elements of text, such
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
In addition, the several simple classes are designed for use as text
types, including:

    - L{TaggedType<nltk.tagger.TaggedType>}: A type consisting of a
      base type and a tag.  For example, this class could be used to
      represent part-of-speech tagged words.
    - C{LabeledText<ntlk.classifier.LabeledText>}: A type consisting
      of a text and a label.  This class is used by the text
      classification package to assign categories to texts.
    - C{Tree<nltk.tree.Tree>}: A type representing a homogenous
      hierarchical structure.  For example, this class could be used
      to represent syntax trees.

@group Data Types: Location, Token
@sort: Location, Token
"""

import re, sys, types
from nltk.chktype import chktype as _chktype 
from nltk.chktype import classeq as _classeq

##//////////////////////////////////////////////////////
##  Locations
##//////////////////////////////////////////////////////
class Location:
    """
    A span over indices in a text.

    The extent of the span is represented by the C{Location}'s X{start
    index} and X{end index}.  A C{Location} identifies the text
    beginning at its start index, and including everything up to (but
    not including) the text at its end index.

    The unit of the indices in the text is specified by the
    C{Location}'s X{unit}.  Typical units are \"w\" (for words) and
    \"c\" (for characters).  The text over which the location is
    defined is identified by the C{Location}'s X{source}.  A typical
    value for a C{Location}'s source would be the name of the file
    containing the text.  A C{Location}'s source and unit fields are
    optional; if not specified, they will default to C{None}.

    A location with a start index of 5 and an end index of 10, a
    source of 'example.txt', and a unit of 'w' is be written::

        @[5w:10w]@'example.txt'

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
    def __init__(self, start, end=None, unit=None, source=None):
        """
        Construct a new C{Location}.

        @param start: The start index of the new C{Location}.
        @type start: C{int}
        @param end: The end index of the new C{Location}.  If not
            specified, the end index defaults to C{start+1}
        @type end: C{int}
        @param unit: The unit of the indices in the text that
            contains this location.
        @type unit: C{string}
        @param source: The source of the text that contains this
            location.
        @type source: (any)

        @group Accessors: start, end, unit, source, length, __len__
        @sort: start, end, unit, source, length, __len__
        @group Comparison: __eq__, __ne__, prec, succ,
            overlaps, __cmp__, __hash__
        @group String Representation: __repr__, __str__
        @group Misc: union, __add__, start_loc, end_loc, select
        """
        # Check types
        assert _chktype(1, start, types.IntType, types.LongType,
                        types.FloatType)
        assert _chktype(2, end, types.IntType, types.LongType,
                        types.FloatType, types.NoneType)
        assert _chktype(3, unit, types.StringType, types.NoneType)
        
        # Set the start and end locations
        self._start = start
        if end is None: self._end = self._start+1
        else: self._end = end

        # Check that the location is valid.
        if self._end<self._start:
            raise ValueError("A Location's start index must be less "+
                             "than or equal to its end index.")

        # Set the source and unit
        self._source = source
        if unit is None: self._unit = None
        else: self._unit = unit.lower()

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
        assert _chktype(1, other, Location)
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
        assert _chktype(1, lst, [], ())
        return lst[self.start():self.end()]

    def __repr__(self):
        """
        @return: A concise string representation of this C{Location}.
        @rtype: string
        """
        if self._unit is not None: unit = self._unit
        else: unit = ''
        
        if self._end != self._start+1:
            str = '@[%s%s:%s%s]' % (self._start, unit, self._end, unit)
        else:
            str = '@[%s%s]' % (self._start, unit)

        return str

    def __str__(self):
        """
        @return: A verbose string representation of this C{Location}.
        @rtype: string
        """
        s = '@[%s' % self._start
        
        if self._unit is not None: s += self._unit

        if self._end != self._start+1:
            s += ':%s' % self._end
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
        """
        return (_classeq(self, other) and
                self._start == other._start and
                self._end == other._end and
                self._unit == other._unit and
                self._source == other._source)
    
    def __ne__(self, other):
        """
        @return: true if this C{Location} is not equal to C{other}.  In
            particular, return false iff this C{Location}'s source,
            unit, start, and end values are equal to C{other}'s;
            raise an exception iff this C{Location}'s source or unit
            are not equal to C{other}'s; return false otherwise.
        @rtype: C{boolean}
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
        assert _chktype(1, other, Location)
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
        assert _chktype(1, other, Location)
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
                - Return true if C{self}'s start falls in the range
                  [C{other}.start, C{other}.end); or if C{other}'s
                  start falls in the range [C{self}.start, C{self}.end).
                - Return false otherwise.
        @rtype: C{boolean}
        @raise TypeError: if C{other} is not a C{Location}.
        @raise ValueError: If this C{Location}'s source is not equal
            to C{other}'s source.
        @raise ValueError: If this C{Location}'s unit is not equal
            to C{other}'s unit.
        """
        assert _chktype(1, other, Location)
        if self._unit != other._unit:
            raise ValueError('Locations have incompatible units')
        if self._source != other._source:
            raise ValueError('Locations have incompatible sources')
        (s1,e1) = (self._start, self._end)
        (s2,e2) = (other._start, other._end)
        return (s1 <= s2 < e1) or (s2 <= s1 < e2) or (s1==s2==e1==e2)

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
        assert _chktype(1, other, Location)
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
    def __init__(self, type, location=None):
        """
        Construct a new Token, with the given type and location.
        
        @param type: The type for the new Token.
        @type type: (any)
        @param location: The location of the new token.  If no value
            is specified, the location defaults to C{None}.
        @type location: C{TextLocation} or C{None}
        """
        assert _chktype(2, location, Location, types.NoneType)
        self._type = type
        self._location = location

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
        if not _classeq(self, other): return 0
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

from nltk.probability import ProbabilisticMixIn
class ProbabilisticToken(Token, ProbabilisticMixIn):
    """
    A single occurance of a unit of text that has a probability
    associated with it.  This probability can represent a variety of
    different likelihoods, such as:

      - The likelihood that this token occured in a specific context.
      - The likelihood that this token is correct for a specific
        context.
      - The likelihood that this token will be generated in a
        specific context.
    """
    def __init__(self, prob, type, location):
        ProbabilisticMixIn.__init__(self, prob)
        Token.__init__(self, type, location)
    def __repr__(self):
        return Token.__repr__(self)+' (p=%s)' % self._prob
    def __str__(self):
        return Token.__str__(self)+' (p=%s)' % self._prob

##//////////////////////////////////////////////////////
##  Demonstration
##//////////////////////////////////////////////////////

def demo():
    """
    A demonstration showing how L{Location}s and L{Token}s can be
    used.  This demonstration simply creates two locations and
    two tokens, and shows the results of calling several of their
    methods.
    """
    print "loc = Location(3, 5, unit='w', source='corpus.txt')"
    loc = Location(3, 5, unit='w', source='corpus.txt')
    
    print "loc2 = Location(10, 11, unit='w', source='corpus.txt')"
    loc2 = Location(10, 11, unit='w', source='corpus.txt')
    
    print "tok = Token('big', loc2)"
    tok = Token('big', loc2)
    
    print "tok = Token((12, 83), loc)  # type can be any immutable"
    tok2 = Token((12, 83), loc)
    print
    
    print "print loc                 =>", loc
    print "print loc.start()         =>", loc.start()
    print "print loc.end()           =>", loc.end()
    print "print loc.length()        =>", loc.length()
    print "print loc.unit()          =>", loc.unit()
    print "print loc.source()        =>", loc.source()
    print "print loc2                =>", loc2
    print "print loc.prec(loc2)      =>", loc.prec(loc2)
    print "print loc.succ(loc2)      =>", loc.succ(loc2)
    print "print loc.overlaps(loc2)  =>", loc.overlaps(loc2)
    print "print tok                 =>", tok
    print "print tok.type()          =>", tok.type
    print "print tok.loc()           =>", tok.loc
    print "print tok2                =>", tok2
    print "print tok2.type()         =>", tok2.type
    print "print tok2.loc()          =>", tok2.loc

if __name__ == '__main__':
    demo()
    
