# Natural Language Toolkit: Tokens
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

"""
Basic classes for encoding pieces of language, such as words,
sentences, and documents.  These pieces of language are known as
X{tokens}.  Each token is defined by set of X{properties}, each of
which describes a specific aspect of the token.  Typical properties
include:

  - C{text}: The token's text content.
  - C{wave}: The token's recorded audio content.
  - C{pos}: The token's part-of-speech tag.
  - C{speaker}: The speaker who uttered the token.
  - C{sense}: The token's word sense.
  - C{loc}: The token's location in its containing text.

The C{loc} property, which is defined by most tokens, uses a
L{Location} to specify the position of the token in its containing
text.  This property has two important uses:

  1. It serves as a unique identifier that distinguishes each token
     from any other tokens that have the same properties (e.g., two
     occurances of the same word).
  2. It provides a pointer to the token's context.
  
See the L{Token} class for more information.

@group Tokens: Token, FrozenToken, SafeToken, ProbabilisticToken
@group Locations: Location
@group Auxilliary Data Types: FrozenDict
@sort: Token, FrozenToken, SafeToken, ProbabilisticToken

@todo: Clean up the location class.
@todo: Decide how we use a location to get at a token's context.
Some ideas:

  - does the location provide a "parent pointer" to the containing
    token?  If so, then can locations still be hashable??
    
  - does the token define a "context" property that provides the
    parent pointer?  This might look something like:
    
      >>> context = tok['context']
      >>> start = tok['loc'].start()
      >>> prevword = context[start-1]
    
  - or is there some other mechanism?
"""

######################################################################
## Implementation Note
######################################################################
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

import types, copy
from nltk.chktype import chktype

######################################################################
## Token
######################################################################

class Token(dict):
    """
    A single a piece of language, such as a word, a sentence, or a
    document.  A token is defined by a set of X{properties}, each of
    which associates a name with a value.  For example, the following
    token defines the text content and part-of-speech tag for a single
    word:

        >>> tok = Token(text='fly', pos='N')
        <text='fly', pos='N'>

    As this example illustrates, a token's properties are initialized
    using keyword arguments to the constructor.  Properties can be
    accessed and modified using the indexing operator with property
    names:

       >>> print tok['text']
       'fly'
       >>> tok['speaker'] = 'James'

    A property name can be any string; but typically, short lower-case
    words are used.  Property names are case sensitive.  Note that
    some properties only make sense for specific kinds of C{Tokens}.
    For example, only C{Tokens} representing recorded audio will have
    a C{wave} property; and only C{Tokens} representing words will
    have a C{pos} property.
    
    A property value can be...
      - an immutable value (such as a string or a number)
      - a token
      - a container (such as a list, dictionary, or tuple) that
        contains valid property values

    The special property C{'loc'} is used to record a token's location
    in its containing text.  This property has two important uses:
    
      - It serves as a unique identifier that distinguishes each token
        from any other tokens that have the same properties.  For
        example, if the word "dog" appears twice in a document, then
        the two ocurances of the word can be distinguished based on
        their location.

      - It provides a pointer to the token's context.  (We haven't quite
        fleshed out how this will be used yet.)

    @ivar USE_SAFE_TOKENS: If C{True}, then the L{SafeToken} subclass is
        used to create new tokens.  This subclass includes type checking
        on all operations, and so is significantly slower.

    @group Transformations: including, excluding, freeze, copy
    @group Accessors: properties, has
    @group Operators: __*__, __len__
    """
    # Don't allocate any extra space for instance variables:
    __slots__ = ()

    # Should we use the type-safe version of tokens?
    USE_SAFE_TOKENS = True

    #/////////////////////////////////////////////////////////////////
    # Constructor
    #/////////////////////////////////////////////////////////////////

    def __new__(cls, *args, **kwargs):
        if cls is Token and Token.USE_SAFE_TOKENS:
            return super(Token, cls).__new__(SafeToken, *args, **kwargs)
        else:
            return super(Token, cls).__new__(cls, *args, **kwargs)

    def __init__(self, **properties):
        """
        Construct a new token that defines the given set of properties.
        The properties are typically specified using keyword
        arguments:

           >>> typ = Token(text='ni', pos='excl', speaker='knight2')
           <text='ni', speaker='knight2', pos='excl'>

        Alternatively, properties can be specified using a dictionary,
        with Python's C{**} syntax:

           >>> props = {'text':'ni', 'pos':'excl', 'speaker':'knight2'}
           >>> typ = Token(**props)
           <text='ni', speaker='knight2', pos='excl'>

        @param properties: The initial set of properties that the new
            token should define.  Each element maps a property name to
            its value.
        """
        self.update(properties)

    #/////////////////////////////////////////////////////////////////
    # Accessors
    #/////////////////////////////////////////////////////////////////
    # These are basically just new names for existing methods.
    

    def properties(self):
        """
        @return: A list of the names of properties that are defined
            for this token.
        @rtype: C{list} of C{string}
        """
        return self.keys()
    
    def has(self, property):
        """
        @return: True if this token defines the given property.
        @rtype: C{bool}
        """
        return self.has_attr(property)

    #/////////////////////////////////////////////////////////////////
    # Transformations
    #/////////////////////////////////////////////////////////////////
    # These return a "transformed" version of self.

    def freeze(self):
        """
        @rtype: L{FrozenToken}
        @return: An immutable (or "frozen") copy of this token.  The
            frozen copy is hashable, and can therefore be used as a
            dictionary key or a set element.  However, it cannot be
            modified; and any modifications made to the original token
            after the frozen copy is generated will not be propagated
            to the frozen copy.
        """
        frozen_properties = {}
        for (key, val) in self.items():
            frozen_properties[key] = self._freezeval(val)
        print 'new frozentok', frozen_properties
        return FrozenToken(**frozen_properties)

    def copy(self, deep=True):
        """
        @rtype: L{Token}
        @return: A new copy of this token.
        @param deep: If false, then the new token will use the same
            objects to encode feature values that the original token
            did.  If true, then the new token will use deep copies of
            the original token's feature values.  The default value
            of C{True} is almost always the correct choice.
        """
        assert chktype(1, deep, bool)
        if deep: return copy.deepcopy(self)
        else: return copy.copy(self)

    def including(self, *properties, **options):
        """
        @rtype: L{Token}
        @return: A new token containing only the properties that are
            in the given list.
        @type properties: C{list} of C{string}
        @param properties: A list of the names of properties to
            include.
        @kwparam deep: If true, then C{select} is recursively applied
            to any nested tokens included in this token's property
            values.  For example, C{tok.select(exclude='loc',
            deep=True)} will remove C{all} location information from a
            token, including location information that is included in
            nested tokens.  Default value: C{True}.
        @see: L{excluding}, which is used to create a token containing
           only the properties that are I{not} in a given list.
        """
        deep = options.get('deep', True)
        return self._including(properties, deep)

    def _including(self, properties, deep):
        newprops = {}
        for property in properties:
            if self.has_key(property):
                val = self[property]
                if deep:
                    val = self._deep_restrict(val, properties, incl=True)
                newprops[property] = val
        return self.__class__(**newprops)

    def excluding(self, *properties, **options):
        """
        @rtype: L{Token}
        @return: A new token containing only the properties that are
            not in the given list.
        @type properties: C{list} of C{string}
        @param properties: A list of the names of properties to
            exclude.
        @kwparam deep: If true, then C{select} is recursively applied
            to any nested tokens included in this token's property
            values.  For example, C{tok.select(exclude='loc',
            deep=True)} will remove C{all} location information from a
            token, including location information that is included in
            nested tokens.  Default value: C{True}.
        @see: L{including}, which is used to create a token containing
            only the properties that I{are} in the given list.
        """
        # Convert the exclude list to a dict for faster access.
        excludeset = dict([(property,1) for property in properties])
        deep = options.get('deep', True)
        return self._excluding(excludeset, deep)

    def _excluding(self, excludeset, deep):
        newprops = {}
        for property in self.keys():
            if not excludeset.has_key(property):
                val = self[property]
                if deep:
                    val = self._deep_restrict(val, excludeset, incl=False)
                newprops[property] = val
        return self.__class__(**newprops)

    def _deep_restrict(self, val, props, incl):
        """
        @return: A deep copy of the given property value, with the
        given restriction applied to any contained tokens:
          - if C{incl} is true, then apply C{including(props)} to any
            contained tokens.
          - if C{incl} is false, then apply C{excluding(props)} to any
            contained tokens.
        """
        if isinstance(val, Token):
            if incl: return val._including(props, True)
            else: return val._excluding(props, True)
        elif isinstance(val, list):
            restrict = self._deep_restrict
            return [restrict(v, props, incl) for v in val]
        elif isinstance(val, tuple):
            restrict = self._deep_restrict
            return tuple([restrict(v, props, incl) for v in val])
        elif isinstance(val, dict):
            return dict(self._deep_restrict(val.items(), props, incl))
        else:
            hash(val) # Make sure it's immutable (or at least hashable).
            return val

    def _freezeval(self, val):
        if isinstance(val, Token):
            return val.freeze()
        elif isinstance(val, list) or isinstance(val, tuple):
            freezeval = self._freezeval
            return tuple([freezeval(v) for v in val])
        elif isinstance(val, dict):
            return FrozenDict(self._freezeval(val.items()))
        else:
            hash(val) # Make sure it's immutable (or at least hashable).
            return val

    #/////////////////////////////////////////////////////////////////
    # Basic operators
    #/////////////////////////////////////////////////////////////////

    def __repr__(self):
        """
        @return: A condensed string representation of this C{Type}.
            Any feature values whose string representations are longer
            than 30 characters will be abbreviated.
        @rtype: C{string}
        """
        # Abbreviate any values that are longer than 30 characters.
        # [XX] does this look good in practice?  What should MAXLEN be?
        MAXLEN = 30
        items = self.items()
        for i in range(len(items)):
            items[i] = (str(items[i][0]), repr(items[i][1]))
            if len(items[i][1]) > MAXLEN:
                items[i] = (items[i][0],
                            items[i][1][:MAXLEN-6]+'...'+items[i][1][-3:])
        # Convert each property (except loc) to a string.
        items = ', '.join(['%s=%s' % (p,v)
                           for (p,v) in items
                           if p != 'loc'])
        # If there are no properties, use "<empty>" instead.
        if len(items) == 0: items = 'empty'
        # If there's a location, then add it to the end.
        if self.has_key('loc'):
            if not isinstance(self['loc'], Location):
                raise AssertionError("self['loc'] is not a location!")
            locstr = '%r' % self['loc']
        else: locstr = ''
        # Assemble & return the final string.
        return '<%s>%s' % (items, locstr)

    def __str__(self):
        """
        @return: A full string representation of this C{Type}.
        @rtype: C{string}
        """
        # Convert each property (except loc) to a string.
        items = ', '.join(['%s=%r' % (p,v)
                           for (p,v) in self.items()
                           if p != 'loc'])
        # If there are no properties, use "<empty>" instead.
        if len(items) == 0: items = 'empty'
        # If there's a location, then add it to the end.
        if self.has_key('loc'):
            if not isinstance(self['loc'], Location):
                raise AssertionError("self['loc'] is not a location!")
            locstr = '%r' % self['loc']
        else: locstr = ''
        # Assemble & return the final string.
        return '<%s>%s' % (items, locstr)

    # The superclass already raises TypeError here; but its error
    # message ("dict objects are unhashable") might be confusing.
    def __hash__(self):
        """
        Raise C{TypeError}, since C{Token} obejcts are unhashable.
        """
        raise TypeError('%s objects are unhashable' %
                        self.__class__.__name__)

######################################################################
## FrozenToken
######################################################################

class FrozenToken(Token):
    """
    An immutable (and hashable) version of the L{Token} class.
    """
    def __init__(self, **properties):
        """
        Create a new frozen token that defines the given set of
        properties.
        
        @param properties: The set of properties that the new token
            should define.  Each element maps a property name to its
            value.
        @require: The values for the given properties must be
            immutable.
        """
        super(FrozenToken, self).update(properties)
    
        # Generate a hash value:
        items = self.items()
        items.sort()
        self._hash = hash(tuple(items))
        
    def __setitem__(self, property, value):
        raise TypeError('FrozenToken objects are immutable')
    def __delitem__(self, property):
        raise TypeError('FrozenToken objects are immutable')
    def clear(self):
        raise TypeError('FrozenToken objects are immutable')
    def pop(self, property, default=None):
        raise TypeError('FrozenToken objects are immutable')
    def popitem(self):
        raise TypeError('FrozenToken objects are immutable')
    def setdefault(self, property, default=None):
        raise TypeError('FrozenToken objects are immutable')
    def update(self, src):
        raise TypeError('FrozenToken objects are immutable')
    def copy(self, deep=True):
        return self.__class__(self)
    def __hash__(self):
        return self._hash

class FrozenDict(dict):
    """
    An immutable (and hashable) dictionary.
    """
    def __init__(self, **keys):
        super(FrozenDict, self).update(keys)

        # Generate a hash value:
        items = self.items()
        items.sort()
        self._hash = hash(tuple(items))
        
    def __setitem__(self, key, value):
        raise TypeError('FrozenToken objects are immutable')
    def __delitem__(self, key):
        raise TypeError('FrozenToken objects are immutable')
    def clear(self):
        raise TypeError('FrozenToken objects are immutable')
    def pop(self, key, default=None):
        raise TypeError('FrozenToken objects are immutable')
    def popitem(self):
        raise TypeError('FrozenToken objects are immutable')
    def setdefault(self, key, default=None):
        raise TypeError('FrozenToken objects are immutable')
    def update(self, src):
        raise TypeError('FrozenToken objects are immutable')
    def copy(self):
        return self.__class__(self)
    def __hash__(self):
        return self._hash
        
######################################################################
## SafeToken
######################################################################

class SafeToken(Token):
    """
    A version of the L{Token} class that adds type checking (at the
    expense of speed).  Since all operations are type checked,
    C{SafeToken} can be significantly slower than C{Token}.  However,
    it can be useful for tracking down bugs.

    C{SafeToken}s are not usually created directly; instead, the
    L{Token.USE_SAFE_TOKENS} variable is used to instruct the C{Token}
    constructor to create C{SafeToken}s instead of C{Token}s.
    """
    #/////////////////////////////////////////////////////////////////
    # Constructor
    #/////////////////////////////////////////////////////////////////

    def __init__(self, **properties):
        # type checking is handled by self.update().
        self.update(properties)
    
    #/////////////////////////////////////////////////////////////////
    # Argument checking
    #/////////////////////////////////////////////////////////////////
    # Make sure that we only add valid properties.

    def __getitem__(self, property):
        assert chktype(1, property, str)
        return super(SafeToken, self).__getitem__(property)
    
    def __setitem__(self, property, value):
        assert chktype(1, property, str)
        assert chktype(2, value, self._checkval)
        if (property == 'loc') and not isinstance(value, Location):
            raise TypeError("The 'loc' property must contain a Location")
        return super(SafeToken, self).__setitem__(property, value)
        
    def __delitem__(self, property):
        assert chktype(1, property, str)
        return super(SafeToken, self).__delitem__(property)

    def excluding(self, *properties, **options):
        for key in options.keys():
            if key != 'deep': raise ValueError('Bad option %r' % key)
        assert chktype('vararg', properties, (self._checkval,))
        return super(SafeToken, self).excluding(*properties, **options)

    def get(self, property):
        assert chktype(1, property, str)
        return super(SafeToken, self).get(property)

    def has(self, property):
        assert chktype(1, property, str)
        return super(SafeToken, self).has(property)

    def has_key(self, property):
        assert chktype(1, property, str)
        return super(SafeToken, self).has_key(property)

    def including(self, *properties, **options):
        for key in options.keys():
            if key != 'deep': raise ValueError('Bad option %r' % key)
        assert chktype('vararg', properties, (self._checkval,))
        return super(SafeToken, self).including(*properties, **options)

    def pop(self, property, default=None):
        assert chktype(1, property, str)
        return super(SafeToken, self).pop(property, default=None)
        
    def setdefault(self, property, default=None):
        assert chktype(1, property, str)
        assert chktype(2, default, self._checkval)
        if (property == 'loc') and not isinstance(value, Location):
            raise TypeError("The 'loc' property must contain a Location")
        return super(SafeToken, self).setdefault(property, default=None)
        
    def update(self, src):
        assert chktype(1, src, {str:self._checkval})
        if src.has_key('loc') and not isinstance(src['loc'], Location):
            raise TypeError("The 'loc' property must contain a Location")
        return super(SafeToken, self).update(src)

    def _checkval(self, value):
        """
        @return: True if the given value is a valid property value.
        """
        # Is it a token or a container object?
        if (isinstance(value, Token) or
            isinstance(value, list) or
            isinstance(value, tuple) or
            isinstance(value, dict)): return True

        # Is it immutable (or at least hashable)?
        try: hash(value); return True
        except TypeError: return False
    



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
    brevity, the source is sometimes also omitted: \"C{@[M{i}M{u}]}\".

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
    #def __setattr__(self, property, value):
    #    "Raise C{TypeError}, since locations are immutable"
    #    raise TypeError('Locations are immutable')
    def __delattr__(self, property):
        "Raise C{TypeError}, since locations are immutable"
        raise TypeError('Locations are immutable')


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
    def __init__(self, prob, **properties):
        ProbabilisticMixIn.__init__(self, prob)
        Token.__init__(self, **properties)
    def __repr__(self):
        return Token.__repr__(self)+' (p=%s)' % self._prob
    def __str__(self):
        return Token.__str__(self)+' (p=%s)' % self._prob

######################################################################
## Demonstration
######################################################################

def demo():
    """
    A demonstration showing how L{Location}s and L{Token}s can be
    used.  This demonstration simply creates two locations and
    two tokens, and shows the results of calling several of their
    methods.
    """
    print "loc  = Location(3, 5, unit='w', source='corpus.txt')"
    loc = Location(3, 5, unit='w', source='corpus.txt')
    
    print "tok  = Token(Type(text='flattening'), loc)"
    tok = Token(text='flattening', loc=loc)
    
    print "loc2 = Location(10, 11, unit='w', source='corpus.txt')"
    loc2 = Location(10, 11, unit='w', source='corpus.txt')
    
    print "tok2 = Token(Type(size=12, weight=83), loc2)"
    tok2 = Token(size=12, weight=83, loc=loc2)
    print
    
    print "print loc                      =>", loc
    print "print loc.start                =>", loc.start
    print "print loc.end                  =>", loc.end
    print "print loc.length()             =>", loc.length()
    print "print loc.unit                 =>", loc.unit
    print "print loc.source               =>", loc.source
    print "print loc2                     =>", loc2
    print "print loc.prec(loc2)           =>", loc.prec(loc2)
    print "print loc.succ(loc2)           =>", loc.succ(loc2)
    print "print loc.overlaps(loc2)       =>", loc.overlaps(loc2)
    print "print tok                      =>", tok
    print "print tok['loc']               =>", tok['loc']
    print "print tok.excluding('loc')     =>", tok.excluding('loc')
    print "print tok.excluding('text')    =>", tok.excluding('text')
    print "print tok2                     =>", tok2
    print "print tok2['loc']              =>", tok2['loc']
    print "print tok == tok2              =>", tok == tok2
    print "print tok == tok.copy()        =>", tok == tok.copy()
    print "print type(tok)                =>", type(tok)
    print "print type(tok2)               =>", type(tok2)

if __name__ == '__main__':
    demo()
    
