# Natural Language Toolkit: Tokens
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
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

The token module defines classes to represent types, locations, and
tokens:

  - The L{Type} class encodes a type as a collection of X{properties}.
    For example, the type for a word might include properties for its
    original text, its word stem, and its part of speech.
    
  - The L{Location} class encodes a location as a span over indices in
    a text.  Each C{Location} consists of a start index and an end
    index, and optionally specifies a unit for the indices and the
    source over which the indices are defined.

  - The L{Token} class encodes a token as a C{Type} plus a
    C{Location}.

Types, locations, and tokens are all X{immutable} values: they can not
be modified.  However, they each define methods that return I{new}
objects that are derived from their values.  For example, the
L{Type.extend} method returns a new type that is formed by adding
properties to an existing type.

Subclassing
===========
C{Type} and C{Token} may be subclassed to add new methods.  For
example, L{TreeType<nltk.tree.TreeType>} defines methods for
performing operations on tree-structured types.  However, these
subclasses may only define new methods; they may not define new
attributes.

C{Location} may not be subclassed.

@group Data Types: Type, Location, Token
@sort: Type, Location, Token
"""

######################################################################
## Implementation Notes
######################################################################
# The classes defined by this module make use of three advanced Python
# constructions, to ensure immutability:
#
#   1. The __getattr__ and __setattr__ methods are overridden to
#      raise exceptions.  This causes any attempt to change or delete
#      an instance's attributes to fail.
#
#   2. In the class constructors, attributes are set using
#      "object.__setattr__(self, name, val)".  This bypasses the
#      normal __setattr__ function (which would raise an exception).
#
#   3. The Type class directly modifies its instance's dictionaries,
#      which are accessed with "self.__dict__".
#
# The Location and Token classes also make use of the __slots__
# variable.  This special variable lets Python know which attributes
# will be defined by class instances.  This is done to save space,
# since we may be constructing a large number of tokens.  But be very
# careful before adding a __slots__ variable to any of your own code:
# there are some subtleties that are not immediately obvious.  In
# fact, according to Guido von Rossum, the creator of Python,
# "__slots__ is a terrible hack with nasty, hard-to-fathom side
# effects that should only be used by programmers at grandmaster and
# wizard levels."

import types
from nltk.chktype import chktype

######################################################################
## Location
######################################################################

class Location(object):
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
    containing the text.  A C{Location}'s unit and source fields are
    optional; if not specified, they will default to C{None}.

    A location with a start index M{i}, an end index M{j}, a unit
    M{u}, and a source M{s}, is written
    \"C{@[M{i}M{u}:M{j}M{u}]@M{s}}\".  For locations with a length of
    one, this can be shortened to \"C{@[M{i}M{u}]@M{s}}\".  For
    brevity, the source is sometimes also omitted: \"C{@[M{i}M{u}]\".

    C{Location}s are immutable.

    @type start: C{int}
    @ivar start: The index at which a C{Location} begins.  The
        C{Location} identifies the text beginning at (and including)
        this value.
    @type end: C{int}
    @ivar end: The index at which a C{Location} ends.  The C{Location}
          identifies the text up to (but not including) this value.
    @type unit: C{string}
    @ivar unit: The index unit used by this C{Location}.  Typical
          units are 'character' and 'word'.
    @type source: (any)
    @ivar source: An identifier naming the text over which this
          location is defined.  A typical example of a source would be
          a string containing the name of the file containing the
          text.  Sources may also be represented as C{Location}s; for
          example, the source for the location of a word within a
          sentence might be the location of the sentence.
    """
    __slots__ = ['start', 'end', 'unit', 'source']
    
    def __init__(self, start, end=None, unit=None, source=None):
        """
        Construct the new C{Location}
        C{[startM{unit}:endM{unit}]@M{source}}.

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
        assert chktype(1, start, types.IntType, types.LongType,
                        types.FloatType)
        assert chktype(2, end, types.IntType, types.LongType,
                        types.FloatType, types.NoneType)
        assert chktype(3, unit, types.StringType, types.NoneType)
        
        # Check that the location is valid.
        if end is not None and end<start:
            raise ValueError("A Location's start index must be less "+
                             "than or equal to its end index.")

        # Set the start and end locations
        object.__setattr__(self, 'start', start)
        if end is None: object.__setattr__(self, 'end', start+1)
        else: object.__setattr__(self, 'end', end)

        # Set the unit and source
        if unit is not None: unit = unit.lower()
        object.__setattr__(self, 'unit', unit)
        object.__setattr__(self, 'source', source)

    def length(self):
        """
        @return: the length of this C{Location}.  I.e., return
            C{self.end-self.start}.
        @rtype: int
        """
        return self.end - self.start

    # len(loc) is a synonym for loc.length()
    __len__ = length
    
    def union(self, other):
        """
        @rtype: L{Location}
        @return: A new union that covers the combined spans of C{self}
        and C{other}.  C{self} and C{other} must be contiguous
        locations.  I.e., they must have equal start indices or equal
        end indices.
        @type other: L{Location}
        @raise ValueError: If C{self} and C{other} are not contiguous.
        """
        assert chktype(1, other, Location)
        if self.unit != other.unit:
            raise ValueError('Locations have incompatible units')
        if self.source != other.source:
            raise ValueError('Locations have incompatible sources')
        if self.end == other.start:
            return Location(self.start, other.end, unit=self.unit,
                            source=self.source)
        elif self.start == other.end:
            return Location(other.start, self.end, unit=self.unit,
                            source=self.source)
        else:
            raise ValueError('Locations are not contiguous')

    # loc1+loc2 is a synonym for loc1.union(loc2)
    __add__ = union

    def start_loc(self):
        """
        @return: a zero-length C{Location} whose start and end indices
            are equal to this location's start index.  I.e., return
            the location C{@[self.start:self.start]}.
        @rtype: L{Location}
        """
        return Location(self.start, self.start, self.unit, self.source)

    def end_loc(self):
        """
        @return: a zero-length C{Location} whose start and end indices
            are equal to this location's end index.  I.e., return
            the location C{@[self.end:self.end]}.
        @rtype: L{Location}
        """
        return Location(self.end, self.end, self.unit, self.source)

    def select(self, lst):
        """
        Given a list of elements over which this location is defined,
        return the sublist specified by the location.  I.e., return
        C{lst[self.start:self.end]}.
        
        @param lst: The list of elements over which this location is
            defined.
        @type lst: C{list}
        @return: C{lst[self.start:self.end]}
        @rtype: C{list}
        """
        assert chktype(1, lst, [], ())
        return lst[self.start:self.end]

    def __repr__(self):
        """
        @return: A concise string representation of this C{Location}.
        @rtype: string
        """
        if self.unit is not None: unit = self.unit
        else: unit = ''
        
        if self.end != self.start+1:
            str = '@[%s%s:%s%s]' % (self.start, unit, self.end, unit)
        else:
            str = '@[%s%s]' % (self.start, unit)

        return str

    def __str__(self):
        """
        @return: A verbose string representation of this C{Location}.
        @rtype: string
        """
        if self.source is None:
            return repr(self)
        elif isinstance(self.source, Location):
            return repr(self)+repr(self.source)
        else:
            return repr(self)+'@'+repr(self.source)

    def __eq__(self, other):
        """
        @return: true if this C{Location} is equal to C{other}.  In
            particular, return true iff this C{Location}'s source,
            unit, start, and end values are equal to C{other}'s.
        @rtype: C{boolean}
        """
        return (isinstance(other, Location) and
                self.start == other.start and
                self.end == other.end and
                self.unit == other.unit and
                self.source == other.source)
    
    def __ne__(self, other):
        """
        @return: true if this C{Location} is not equal to C{other}.  In
            particular, return false iff this C{Location}'s source,
            unit, start, and end values are equal to C{other}'s.
        @rtype: C{boolean}
        """
        return (not isinstance(other, Location) or
                self.start != other.start or
                self.end != other.end or
                self.unit != other.unit or
                self.source != other.source)
        
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
        assert chktype(1, other, Location)
        if self.unit != other.unit:
            raise ValueError('Locations have incompatible units')
        if self.source != other.source:
            raise ValueError('Locations have incompatible sources')
        return (self.end <= other.start and
                self.start < other.end)
    
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
        assert chktype(1, other, Location)
        if self.unit != other.unit:
            raise ValueError('Locations have incompatible units')
        if self.source != other.source:
            raise ValueError('Locations have incompatible sources')
        return (self.start >= other.end and
                self.end > other.start)

    def overlaps(self, other):
        """
        @return: true if this C{Location} overlaps C{other}.  In
            particular: 
                - Raise an exception if this C{Location}'s source or
                  unit are not equal to C{other}'s 
                - Return true if C{self}'s start falls in the range
                  M{[C{other}.start, C{other}.end)}; or if C{other}'s
                  start falls in the range M{[C{self}.start,
                  C{self}.end)}; or if C{self==other}.
                - Return false otherwise.
            Note that two contiguous locations M{@[a:b]} and M{@[b:c]}
            are only considered to overlap if M{a=b} and M{b=c}.
        @rtype: C{boolean}
        @raise TypeError: if C{other} is not a C{Location}.
        @raise ValueError: If this C{Location}'s source is not equal
            to C{other}'s source.
        @raise ValueError: If this C{Location}'s unit is not equal
            to C{other}'s unit.
        """
        assert chktype(1, other, Location)
        if self.unit != other.unit:
            raise ValueError('Locations have incompatible units')
        if self.source != other.source:
            raise ValueError('Locations have incompatible sources')
        (s1,e1) = (self.start, self.end)
        (s2,e2) = (other.start, other.end)
        return (s1 <= s2 <= e1) or (s2 <= s1 < e2) or (s1==s2==e1==e2)

    def __cmp__(self, other):
        """
        Compare two locations, based on their start locations and end
        locations.  In particular:
            - if C{other} is not a location, or C{self}'s unit and
              source are not equal to C{other}'s, then the two
              locations are not comperable, so return -1
            - otherwise if C{self.start} < C{other.start}, return -1
            - otherwise if C{self.start} > C{other.start}, return 1
            - otherwise if C{self.end} < C{other.end}, return -1
            - otherwise if C{self.end} > C{other.end}, return 1
            - otherwise, return 0

        @return: -1 if C{self<other}; +1 if C{self>other}; and 0 if
                 C{self==other}. 
        """
        # Make sure the locations are comperable.
        if not (isinstance(other, Location) and
                self.unit == other.unit and
                self.source == other.source):
            return -1
        # Compare, based on start & end location.
        return cmp( (self.start, self.end), (other.start, other.end) )

    def __hash__(self):
        """
        @return: A hash value for this C{Location}.
        @rtype: C{int}
        """
        return self.start + 5003*self.end

    # Locations are immutable; so disable attribute modification 
    # and deletion.
    def __setattr__(self, property, value):
        "Raise C{TypeError}, since locations are immutable"
        raise TypeError('Locations are immutable')
    def __delattr__(self, property):
        "Raise C{TypeError}, since locations are immutable"
        raise TypeError('Locations are immutable')


######################################################################
## Type
######################################################################

class Type(object):
    """
    A unit of language, such as a word or a sentence.  Types should be
    contrasted with L{Tokens<Token>}, which represent individual
    occurances of types.  Types can be thought of as the units of
    language themselves, abstracted away from their from context.
    The precise defintion of what counts as a type can vary for
    different analyses of the same text.  For example, in a simple
    word counting application all occurances of the word \"fly\" could
    be considered the same type; but for a parsing system we would
    want to distinguish the noun \"fly\" from the verb \"fly.\"

    A type is defined by a set of named X{properties}, each of which
    associates a name with a value.  For example, the following type
    defines the text content and part-of-speech tag for a single word:

        >>> typ = Type(text='fly', pos='N')
        <text='fly', pos='N'>

    As this example illustrates, properties are defined using keyword
    arguments to the C{Type} constructor.
    
    Any string can be used as a property name, but typically short
    lower-case words are used.  Property names are case sensitive.
    Any immutable object can be used as a property value.  Examples of
    valid property values are strings, numbers, and tuples of
    immutable objects.  Notable invalid property values include lists
    and dictionaries.

    Note that some properties only make sense for specific kinds of
    C{Types}.  For example, only C{Types} representing recorded audio
    will have a C{wave} property; and only C{Types} representing words
    will have a C{pos} property.

    C{Type}s are immutable.

    Accessing Properties
    ====================
    There are two ways to access property values.  The C{get()} method
    the property value corresponding to a given property name:

        >>> typ.get('text')
        'fly'

    Properies whose names are valid Python identifiers can also be
    accessed via X{attribute access}:

        >>> typ.text
        'fly'

    @group Property Access: get, has, properties, __getattr__
    @group Derived Types: extend, select
    @group String Representation: __repr__
    @group Immutability: __setattr__, __delattr__
    @sort: __init__, get, has, properties, __getattr__, extend, 
           select, __setattr__, __delattr__, __repr__
    """
    def __init__(self, **properties):
        """
        Construct a new type that defines the given set of properties.
        The properties are typically specified using keyword
        arguments:

           >>> typ = Type(text='ni', pos='excl', speaker='knight2')
           <text='ni', speaker='knight2', pos='excl'>

        Alternatively, properties can be specified using a dictionary,
        with Python's C{**} syntax:

           >>> props = {'text':'ni', 'pos':'excl', 'speaker':'knight2'}
           >>> typ = Type(**props)
           <text='ni', speaker='knight2', pos='excl'>

        Or a mix of the two:

           >>> props = {'speaker':'knight2'}
           >>> typ = Type(text='ni', pos='excl', **props)
           <text='ni', speaker='knight2', pos='excl'>
        
        @param properties: The set of properties that the new type
            should define.  Each element should map a property name to
            a single immutable value.
        """
        self.__dict__.update(properties)

    def get(self, prop_name):
        """
        @return: the value of the given property.
        @rtype: immutable
        @type prop_name: C{string}
        @param prop_name: The name of the property whose value should
            be returned.
        @raise KeyError: If the specified property is not defined by
            this type.
        """
        try:
            return self.__dict__[prop_name]
        except KeyError:
            raise KeyError('The type %r does not define the %r property.' %
                           (self, prop_name))

    # tok.prop is a synonym for tok.get('prop').
    # (Note: this does not get called for attributes that are stored
    # directly in self.__dict__).
    __getattr__ = get
    
    def has(self, prop_name):
        """
        @return: true if this C{Type} defines the given property.
        @rtype: C{boolean}
        @type prop_name: C{string}
        @param prop_name: The name of the property to check for.
        """
        return self.__dict__.has_key(prop_name)

    # Should this be renamed?  Perhaps to property_names()?
    def properties(self):
        """
        @return: A list of the names of the properties that are
            defined for this Type.
        @rtype: C{list} of C{string}
        """
        return self.__dict__.keys()

    def extend(self, **properties):
        """
        @return: A new C{Type} with all the properties defined by this
            type, plus given set of properties.  If a property that is
            defined by this type is also given a value by
            C{properties}, then the value specified by C{properties}
            will override this Type's value.
        @rtype: L{Type}
        @param properties: The set of additional properties that the
            returned type should define.  Each element should map a
            property name to a single immutable value.
        @note: This method returns a new type; it does I{not}
            modify this type.
        """
        typ = Type(**self.__dict__)
        typ.__dict__.update(properties)
        return typ

    def select(self, *property_names):
        """
        @return: A new C{Type} that defines a subset of the properties
            defined by this type.  In particular, the new type will
            map each property name specified by C{property_names} to
            the corresponding value in this type.
        @rtype: C{Type}
        @param property_names: A list of the names of the properties
            that the returned type should define.  This list must be a
            subset of the properties that are defined by this type.
        @type property_names: C{list} of C{string}
        @raise KeyError: If this type does not define one or more of
            the given properties.
        @note: This method returns a new type; it does I{not}
            modify this type.
        """
        properties = {}
        for property in property_names:
            properties[property] = self.__dict__[property]
        return Type(**properties)

    def __repr__(self):
        """
        @return: A string representation of this C{Type}.
        @rtype: C{string}
        """
        if len(self.__dict__) == 0:
            return '<Empty Type>'
        items = ', '.join(['%s=%r' % (p,v)
                           for (p,v) in self.__dict__.items()])
        return '<%s>' % items

    def __cmp__(self, other):
        """
        Compare two types.  In particular:
            - If C{self} and C{other} define the same set of properties,
              and assign the same values to each property, then return 0.
            - Otherwise, return -1.
            
        @return: -1 if C{self<other}; +1 if C{self>other}; and 0 if
                 C{self==other}. 
        """
        if not isinstance(other, Type): return -1
        
        # Ordering is not a well-defined notion for types; just return
        # -1 if they're not equal.
        if self.__dict__ == other.__dict__: return -1

        return 0

    def __hash__(self):
        """
        @return: A hash value for this C{Type}.
        @rtype: C{int}
        """
        return hash(tuple(self.__dict__.values()))

    # Types are immutable; so disable attribute modification and
    # deletion.
    def __setattr__(self, property, value):
        "Raise C{TypeError}, since types are immutable"
        raise TypeError('Types are immutable')
    def __delattr__(self, property):
        "Raise C{TypeError}, since types are immutable"
        raise TypeError('Types are immutable')

######################################################################
## Token
######################################################################

class Token(object):
    """
    A single occurance of a unit of language, such as a word or a
    sentence.  Tokens should be contrasted with L{Types<Type>}, which
    represent the units of language themselves, abstracted away from
    their context.

    A token consists of a type, which specifies information about the
    unit of language, and a location, which specifies which occurance
    the token encodes.  A token's type and location can be accessed
    directly, using the C{type} and C{loc} attributes:

        >>> tok.type
        <text='fly', pos='N'>
        >>> tok.loc
        @[8w]

    As a convenience, the properties of the token's type can also be
    accessed from the token.  In other words, for any property M{p},
    C{tok.M{p} == tok.type.M{p}}.  For example, the following two
    expressions are equivalant:

        >>> tok.type.text
        'fly'
        >>> tok.text
        'fly'
    
    A token's location may have the special value C{None}, which
    specifies that the token's location is unknown or unimportant.  A
    token with a location of C{None} is not equal to any other token,
    even if their types are equal.

    C{Token}s are immutable.
        
    @ivar type: The token's type.
    @ivar loc: The token's location.
    
    @group Property Access: get, has, properties
    @group Derived Tokens: extend, select
    @group String Representation: __repr__
    @group Immutability: __setattr__, __delattr__
    @sort: __init__, get, has, properties, __getattr__, extend, 
           select, __setattr__, __delattr__, __repr__
    """
    __slots__ = ['type', 'loc']
    
    def __init__(self, type, loc=None):
        """
        Construct a new token from the given type and location.

        @param type: The new token's type.
        @type type: L{Type}
        @param location: The location of the new token.  If no value
            is specified, the location defaults to C{None}.
        @type location: L{Location} or C{None}
        """
        object.__setattr__(self, 'type', type)
        object.__setattr__(self, 'loc', loc)

    def get(self, property):
        """
        @return: the value of the given property in this token's type.
        @rtype: immutable
        @type prop_name: C{string}
        @param prop_name: The name of the property whose value should
            be returned.
        @raise KeyError: If the specified property is not defined by
            this token's type.
        """
        return self.type.get(property)
    
    # tok.prop is a synonym for tok.get('prop')
    __getattr__ = get
    
    def has(self, property):
        """
        @return: true if this token's type defines the given property.
        @rtype: C{boolean}
        @type prop_name: C{string}
        @param prop_name: The name of the property to check for.
        """
        return self.type.has(property)
    
    def properties(self):
        """
        @return: A list of the names of the properties that are
            defined for this token's type.
        @rtype: C{list} of C{string}
        """
        return self.type.properties()
    
    def extend(self, **properties):
        """
        @return: A new C{Token} whose location is equal to this
            token's location, and whose type is formed by extending
            this token's type with the given set of properties.  If a
            property that is defined by this token's type is also
            given a value by C{properties}, then the value specified
            by C{properties} takes precedence.
        @rtype: L{Token}
        @param properties: The set of additional properties that the
            returned token's type should define.  Each element should
            map a property name to a single immutable value.
        @note: This method returns a new token; it does I{not}
            modify this token.
        """
        return Token(self.type.extend(**properties), self.loc)
    
    def select(self, *property_names):
        """
        @return: A new C{Token} whose location is equal to this
            token's location, and whose type is formed by selecting
            the given list of properties from this token's type.
            In particular, the new token's type will map each property
            name specified by C{property_names} to the corresponding
            value in this token's type.
        @rtype: C{Token}
        @param property_names: A list of the names of the properties
            that the returned token's type should define.  This list
            must be a subset of the properties that are defined by
            this token's type.
        @type property_names: C{list} of C{string}
        @raise KeyError: If this token's type does not define one or
            more of the given properties.
        @note: This method returns a new token; it does I{not}
            modify this token.
        """
        return Token(self.type.select(*property_names), self.loc)

    def __repr__(self):
        """
        @return: A string representation of this C{Token}.
        @rtype: C{string}
        """
        if self.loc is None:
            return '%r@[?]' % self.type
        else:
            return '%r%r' % (self.type, self.loc)

    def __cmp__(self, other):
        """
        Compare two tokens, based on their locations and types.  In
        particular, return 0 iff C{self} and C{other} have equal
        locations and equal types.  Otherwise, return -1 or 1.
            
        @return: -1 if C{self<other}; +1 if C{self>other}; and 0 if
                 C{self==other}. 
        """
        if not isinstance(other, Token): return -1

        # Compare based on locations first, since it's faster.
        r = cmp(self.loc, other.loc)
        if r != 0: return r

        # If locations match, then compare based on types.
        return cmp(self.type, other.type)

    def __hash__(self):
        """
        @return: A hash value for this C{Type}.
        @rtype: C{int}
        """
        # Hash based on the location (when possible), since it's
        # usually unique to a token.
        if self.loc is not None:
            return hash(self.loc)
        else:
            return hash(self.type)

    # Types are immutable; so disable attribute modification and
    # deletion.
    def __setattr__(self, property, value):
        "Raise C{TypeError}, since tokens are immutable"
        raise TypeError('Tokens are immutable')
    def __delattr__(self, property):
        "Raise C{TypeError}, since tokens are immutable"
        raise TypeError('Tokens are immutable')
    
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
    
    print "tok = Token(Type(text='big'), loc2)"
    tok = Token('big', loc2)
    
    print "tok = Token(Type(size=12, weight=83), loc)"
    tok2 = Token((12, 83), loc)
    print
    
    print "print loc                 =>", loc
    print "print loc.start           =>", loc.start
    print "print loc.end             =>", loc.end
    print "print loc.length()        =>", loc.length
    print "print loc.unit            =>", loc.unit
    print "print loc.source          =>", loc.source
    print "print loc2                =>", loc2
    print "print loc.prec(loc2)      =>", loc.prec(loc2)
    print "print loc.succ(loc2)      =>", loc.succ(loc2)
    print "print loc.overlaps(loc2)  =>", loc.overlaps(loc2)
    print "print tok                 =>", tok
    print "print tok.type            =>", tok.type
    print "print tok.loc             =>", tok.loc
    print "print tok2                =>", tok2
    print "print tok2.type           =>", tok2.type
    print "print tok2.loc            =>", tok2.loc

if __name__ == '__main__':
    demo()
    
