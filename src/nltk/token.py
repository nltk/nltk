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

  - C{TEXT}: The token's text content.
  - C{WAVE}: The token's recorded audio content.
  - C{TAG}: The token's part-of-speech tag.
  - C{SPEAKER}: The speaker who uttered the token.
  - C{SENSE}: The token's word sense.
  - C{LOC}: The token's location in its containing text.

The C{LOC} property uses a L{Location<LocationI>} to specify the
position of the token in its containing text.  This location can be
used to distinguish two tokens whose properties are otherwise equal
(e.g., two occurences of the same word in a text).
  
@group Tokens: Token, FrozenToken, SafeToken, ProbabilisticToken
@group Locations: LocationI, SpanLocation, CharSpanLocation,
    IndexLocation, WordIndexLocation, SentIndexLocation,
    ParaIndexLocation
@group Auxilliary Data Types: FrozenDict
@sort: Token, FrozenToken, SafeToken, ProbabilisticToken,
       LocationI, SpanLocation, CharSpanLocation
"""

######################################################################
## Implementation Note
######################################################################
# The Location and Token classes make use of the __slots__ variable.
# This special variable lets Python know which attributes will be
# defined by class instances.  This is done to save space, since we
# may be constructing a large number of tokens.  But be very careful
# before adding a __slots__ variable to any of your own code: there
# are some subtleties that are not immediately obvious.  In fact,
# according to Guido von Rossum, the creator of Python, "__slots__ is
# a terrible hack with nasty, hard-to-fathom side effects that should
# only be used by programmers at grandmaster and wizard levels."

import types, copy
from nltk.chktype import chktype
from nltk.util import FrozenDict

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

        >>> tok = Token(TEXT='fly', TAG='N')
        <TEXT='fly', TAG='N'>

    As this example illustrates, a token's properties are initialized
    using keyword arguments to the constructor.  Properties can be
    accessed and modified using the indexing operator with property
    names:

       >>> tok['TEXT']
       fly
       >>> tok['SPEAKER'] = 'James'

    A property name can be any string; but typically, short upper-case
    words are used.  Property names are case sensitive.  Note that
    some properties only make sense for specific kinds of C{Tokens}.
    For example, only C{Tokens} representing recorded audio will have
    a C{WAVE} property; and only C{Tokens} representing words will
    have a C{TAG} property.
    
    A property value can be...
      - an immutable value (such as a string or a number)
      - a token
      - a container (such as a list, dictionary, or tuple) that
        contains valid property values

    @ivar USE_SAFE_TOKENS: If C{True}, then the L{SafeToken} subclass is
        used to create new tokens.  This subclass includes type checking
        on all operations, and so is significantly slower.

    @group Property Access: properties, has, get, __getitem__, 
        __setitem__, __delitem__
    @group Transformations: exclude, project, freeze, copy
    @group String Representation: __str__, __repr__,
        register_repr
    @undocumented: clear, fromkeys, has_key, items, iteritems,
        iterkeys, itervalues, keys, pop, popitem, setdefault, update,
        values
    @undocumented: __class__, __cmp__, __contains__, __delattr__,
        __eq__, __ge__, __getattribute__, __gt__, __hash__, __iter__,
        __le__, __len__, __lt__, __ne__, __new__, __reduce__,
        __reduce_ex__, __setattr__
    @undocumented: frozen_token_class
    """
    # Don't allocate any extra space for instance variables:
    __slots__ = ('__repr_cyclecheck',)

    # Should we use the type-safe version of tokens?
    USE_SAFE_TOKENS = True

    #/////////////////////////////////////////////////////////////////
    # Constructor
    #/////////////////////////////////////////////////////////////////

    def __new__(cls, propdict=None, **properties):
        """
        Create and return a new C{Token} object.  If
        L{USE_SAFE_TOKENS} is true, then the new token will be a
        L{SafeToken}; otherwise, it will be a L{Token}.
        """
        if cls is Token and Token.USE_SAFE_TOKENS:
            tok = super(Token, cls).__new__(SafeToken, **properties)
        else:
            tok = super(Token, cls).__new__(cls, **properties)
        tok.__repr_cyclecheck = False
        return tok

    def __init__(self, propdict=None, **properties):
        """
        Construct a new token that defines the given set of properties.
        The properties are typically specified using keyword
        arguments:

           >>> typ = Token(TEXT='ni', TAG='excl', SPEAKER='knight2')
           <TEXT='ni', SPEAKER='knight2', TAG='excl'>

        Alternatively, properties can be specified using a dictionary:

           >>> props = {'TEXT':'ni', 'TAG':'excl', 'SPEAKER':'knight2'}
           >>> typ = Token(props)
           <TEXT='ni', SPEAKER='knight2', TAG='excl'>

        @param properties: The initial set of properties that the new
            token should define.  Each element maps a property name to
            its value.
        """
        if propdict is None:
            super(Token, self).__init__(**properties)
        else:
            super(Token, self).__init__(propdict, **properties)

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
        return self.has_key(property)

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
        return self._freeze({})

    def _freeze(self, memo):
        """
        A helper function that implements L{freeze}.

        @param memo: The memoization dicationary, which is used to
            re-use the same FrozenToken for a given Token.  This lets
            C{freeze} deal with cyclic tokens.  C{memo} maps from the
            C{id} of an input Token to the FrozenToken object that
            will replace it.
        """
        if id(self) in memo: return memo[id(self)]
        frozen_token_class = self.frozen_token_class()
        frozen_val = frozen_token_class()
        memo[id(self)] = frozen_val
        
        frozen_properties = {}
        for (key, val) in self.items():
            if id(val) in memo:
                frozen_properties[key] = memo[id(val)]
            else:
                frozenval = self._freezeval(val, memo)
                memo[id(val)] = frozenval
                frozen_properties[key] = frozenval

        frozen_val.__init__(frozen_properties)
        return frozen_val

    def frozen_token_class():
        """
        @rtype: C{class}
        @return: The class that should be used to freeze instances of
            this class.
        """
        return FrozenToken
    frozen_token_class = staticmethod(frozen_token_class)

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

    def project(self, *properties, **options):
        """
        @rtype: L{Token}
        @return: A new token containing only the properties that are
            named in the given list.
        @type properties: C{list} of C{string}
        @param properties: A list of the names of properties to
            include.
        @kwparam deep: If true, then C{project} is recursively
            applied to any tokens contained by this token'S property
            values.  Default value: C{True}.
        @see: L{exclude}, which is used to create a token containing
           only the properties that are I{not} in a given list.
        """
        deep = options.get('deep', True)
        return self._project(properties, deep, {})

    def _project(self, properties, deep, memo):
        if id(self) in memo: return memo[id(self)]
        projected_val = self.__class__()
        memo[id(self)] = projected_val
        
        newprops = {}
        for property in properties:
            if self.has_key(property):
                val = self[property]
                if deep:
                    val = self._deep_restrict(val, properties, True, memo)
                newprops[property] = val
        projected_val.__init__(newprops)
        return projected_val

    def exclude(self, *properties, **options):
        """
        @rtype: L{Token}
        @return: A new token containing only the properties that are
            not named in the given list.
        @type properties: C{list} of C{string}
        @param properties: A list of the names of properties to
            exclude.
            
        @kwparam deep: If true, then C{exclude} is recursively applied
            to any tokens contained by this token'S property values.
            For example, C{tok.exclude('LOC', deep=True)} will remove
            I{all} location information from a token, including
            location information that is contained in nested tokens.
            Default value: C{True}.
            
        @see: L{project}, which is used to create a token containing
            only the properties that I{are} in the given list.
        """
        # Convert the exclude list to a dict for faster access.
        excludeset = dict([(property,1) for property in properties])
        deep = options.get('deep', True)
        return self._exclude(excludeset, deep, {})

    def _exclude(self, excludeset, deep, memo):
        if id(self) in memo: return memo[id(self)]
        excluded_val = self.__class__()
        memo[id(self)] = excluded_val
        
        newprops = {}
        for property in self.keys():
            if not excludeset.has_key(property):
                val = self[property]
                if deep:
                    val = self._deep_restrict(val, excludeset, False, memo)
                newprops[property] = val
        excluded_val.__init__(newprops)
        return excluded_val

    def _deep_restrict(self, val, props, incl, memo):
        """
        @return: A deep copy of the GIVEN property value, with the
        given restriction applied to any contained tokens:
          - if C{incl} is true, then apply C{project(props)} to any
            contained tokens.
          - if C{incl} is false, then apply C{exclude(props)} to any
            contained tokens.

        @param memo: The memoization dicationary, which is used to
            re-use the same output for a given input This lets
            C{_deep_restrict} deal with cyclic tokens.  C{memo} maps
            from the C{id} of an input Token to the output Token that
            will replace it.
        """
        if isinstance(val, Token):
            if incl: return val._project(props, True, memo)
            else: return val._exclude(props, True, memo)
        elif isinstance(val, list):
            restrict = self._deep_restrict
            return [restrict(v, props, incl, memo) for v in val]
        elif isinstance(val, tuple):
            restrict = self._deep_restrict
            return tuple([restrict(v, props, incl, memo) for v in val])
        elif isinstance(val, dict):
            return dict(self._deep_restrict(val.items(), props, incl, memo))
        elif hasattr(val, '__iter__') and hasattr(val, 'next'):
            return self._deep_restrict_iter(val, props, incl, memo)
        else:
            hash(val) # Make sure it's immutable (or at least hashable).
            return val

    def _deep_restrict_iter(self, val, props, incl, memo):
        for item in val:
            yield self._deep_restrict(item, props, incl, memo)

    def _freezeval(self, val, memo):
        """
        A helper for L{_freeze}.
        @param memo: The memoization dicationary.  (See L{_freeze}
            for more info).
        """
        if isinstance(val, Token):
            return val._freeze(memo)
        elif isinstance(val, list) or isinstance(val, tuple):
            freezeval = self._freezeval
            return tuple([freezeval(v, memo) for v in val])
        elif isinstance(val, dict):
            return FrozenDict(self._freezeval(val.items(), memo))
        elif hasattr(val, '__iter__') and hasattr(val, 'next'):
            return tuple([self._freezeval(v, memo) for v in val])
        else:
            hash(val) # Make sure it's immutable (or at least hashable).
            return val

    #/////////////////////////////////////////////////////////////////
    # String representation
    #/////////////////////////////////////////////////////////////////

    # [XX] registry of repr funcs
    _repr_registry = {}
    def register_repr(props, repr):
        """
        Register a string-representation for tokens.  Any tokens that
        contain the specified set of properties will be printed with
        the given representation.  If a representation is already
        registered for the given set of properties, then the old
        representation will be silently discarded.

        @type props: C{list} of C{string}
        @param props: The set OF property names for which this
            representation should be used.  The order of C{props} is
            not significant.
        @type repr: C{string} or C{function}
        @param repr: The representation that should be used for tokens
            with the given properties.  C{repr} may be either a string
            or a function.  If C{repr} is a string, then it specifies
            the representation C{repr%self}.  If it is a function,
            then it specifies the representation C{repr(self)}.
        """
        props = list(props)
        props.sort()
        if repr is None: del Token._repr_registry[tuple(props)]
        else: Token._repr_registry[tuple(props)] = repr
    register_repr = staticmethod(register_repr)

    # Note: the use of __repr_cyclecheck is not threadsafe; but making
    # it threadsafe would be difficult, given that we allow the user to
    # register arbirary repr functions.
    def __repr__(self):
        """
        @return: A string representation of this C{Token}.
        @rtype: C{string}
        @warning: C{__repr__} is I{not} thread-safe.  In particular,
            it uses an instance variable on each token to handle
            printing of cyclic structures.
        """
        if self.__repr_cyclecheck: return '...'
        self.__repr_cyclecheck = True
        
        props = self.keys()
        props.sort()
        repr = self._repr_registry.get(tuple(props), Token._default_repr)
        if isinstance(repr, str):
            s = repr % self
        else:
            s = repr(self)
        self.__repr_cyclecheck = False
        return s

    def _default_repr(self):
        """
        @return: A full string representation of this C{Type}.
        @rtype: C{string}
        """
        # Convert EACH property (except loc) to a string.
        props = []
        items = self.items()
        items.sort()
        for (p,v) in items:
            if p == 'LOC': continue
            else: props.append('%s=%r' % (p,v))
        props = ', '.join(props)
        # If there's a location, then add it to the end.
        if self.has_key('LOC'):
            if not isinstance(self['LOC'], LocationI):
                raise AssertionError("self['LOC'] is not a location!")
            locstr = '@%r' % self['LOC']
        else: locstr = ''
        # Assemble & return the final string.
        return '<%s>%s' % (props, locstr)

    #/////////////////////////////////////////////////////////////////
    # Operators
    #/////////////////////////////////////////////////////////////////

    # The superclass already raises TypeError here; but its error
    # message ("dict objects are unhashable") might be confusing.
    def __hash__(self):
        """
        Raise C{TypeError}, since C{Token} obejcts are unhashable.
        """
        raise TypeError('%s objects are unhashable' %
                        self.__class__.__name__)

    def __len__(self):
        """
        Raise C{TypeError}, since C{Token} objects are unsized.
        """
        raise TypeError('len() of unsized %s object' %
                        self.__class__.__name__)

    def __nonzero__(self):
        """
        Raise C{TypeError}, since C{Token} objects cannot used as
        booleans.
        """
        raise TypeError('%s objects cannot be used as booleans' %
                        self.__class__.__name__)

    #/////////////////////////////////////////////////////////////////
    # Pickling
    #/////////////////////////////////////////////////////////////////

    def __getstate__(self):
        return dict(self)
    def __setstate__(self, state):
        dict.update(self, state)
        self.__repr_cyclecheck = False

# Register some specialized string representations for common
# sets of properties.
Token.register_repr(('TEXT',),
                    lambda t: ('<%s>' %
                               (`t['TEXT']`[1:-1],)))
Token.register_repr(('TEXT', 'LOC'),
                    lambda t: ('<%s>@%r' %
                               (`t['TEXT']`[1:-1], t['LOC'])))
Token.register_repr(('TEXT', 'TAG'),
                    lambda t: ('<%s/%s>' %
                               (`t['TEXT']`[1:-1], t['TAG'])))
Token.register_repr(('TEXT', 'TAG', 'LOC'),
                    lambda t: ('<%s/%s>@%r' %
                               (`t['TEXT']`[1:-1], t['TAG'], t['LOC'])))
Token.register_repr(('SUBTOKENS',),
                    '<%(SUBTOKENS)r>')
Token.register_repr(('TEXT', 'SUBTOKENS'),
                    '<%(SUBTOKENS)r>')
Token.register_repr(('TEXT', 'SUBTOKENS', 'LOC'),
                    '<%(SUBTOKENS)r>')
Token.register_repr(('SUBTOKENS', 'LOC'),
                    '<%(SUBTOKENS)r>')

######################################################################
## Frozen Token
######################################################################

class FrozenToken(Token):
    """
    An immutable (and hashable) version of the L{Token} class.
    """
    def __init__(self, propdict=None, **properties):
        """
        Create a new frozen token that defines the given set of
        properties.
        
        @param properties: The set of properties that the new token
            should define.  Each element maps a property name to its
            value.
        @require: The values for the given properties must be
            immutable.
        """
        if propdict is not None: dict.update(self, propdict)
        dict.update(self, properties)
        self._hash = hash(sum([hash(i) for i in self.items()]))
        
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
    def __hash__(self):
        return self._hash

######################################################################
## Safe Token
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

    def __init__(self, propdict=None, **properties):
        # type checking is handled by self.update().
        if propdict is not None: self.update(propdict)
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
        if ((property == 'LOC') and not isinstance(value, LocationI)
            and value is not None):
            raise TypeError("The 'LOC' property must contain a Location")
        return super(SafeToken, self).__setitem__(property, value)
        
    def __delitem__(self, property):
        assert chktype(1, property, str)
        return super(SafeToken, self).__delitem__(property)

    def exclude(self, *properties, **options):
        for key in options.keys():
            if key != 'deep': raise ValueError('Bad option %r' % key)
        assert chktype('vararg', properties, (self._checkval,))
        return super(SafeToken, self).exclude(*properties, **options)

    def get(self, property, default=None):
        assert chktype(1, property, str)
        return super(SafeToken, self).get(property, default)

    def has(self, property):
        assert chktype(1, property, str)
        return super(SafeToken, self).has(property)

    def has_key(self, property):
        assert chktype(1, property, str)
        return super(SafeToken, self).has_key(property)

    def project(self, *properties, **options):
        for key in options.keys():
            if key != 'deep': raise ValueError('Bad option %r' % key)
        assert chktype('vararg', properties, (self._checkval,))
        return super(SafeToken, self).project(*properties, **options)

    _pop_sentinel = object()
    def pop(self, property, default=_pop_sentinel):
        assert chktype(1, property, str)
        if default is SafeToken._pop_sentinel:
            return super(SafeToken, self).pop(property)
        else:
            return super(SafeToken, self).pop(property, default)
        
    def setdefault(self, property, default=None):
        assert chktype(1, property, str)
        assert chktype(2, default, self._checkval)
        if ((property == 'LOC') and not isinstance(default, LocationI)
            and default is not None):
            raise TypeError("The 'LOC' property must contain a Location")
        return super(SafeToken, self).setdefault(property, default)
        
    def update(self, src):
        assert chktype(1, src, {str:(self._checkval,)})
        if (src.has_key('LOC') and not isinstance(src['LOC'], LocationI)
            and src['LOC'] is not None):
            raise TypeError("The 'LOC' property must contain a Location")
        return super(SafeToken, self).update(src)

    def _checkval(self, value):
        """
        @return: True if the given value is a VALID property value.
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
## Probabilistic Token
######################################################################

# [XX] We may get rid of this!  (Just use a "PROB" property?)

from nltk.probability import ProbabilisticMixIn
class ProbabilisticToken(Token, ProbabilisticMixIn):
    """
    A single occurence of a unit of text that has a probability
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

######################################################################
## Location
######################################################################

class LocationI(object):
    """
    The position of a piece of language, such as a word or a sentence,
    within its containing document.  Each C{Location} consists of a
    X{source}, which names the containing document, and a specification
    of a position within that document.  Typically, this position is
    expressed as a character span (for text corpora) or a time span (for
    audio corpora).  However, in corpora with non-linear structure,
    more complex positional locations are needed.

    Locations are often used as unique identifiers for C{Tokens}.  In
    particular, locations can be used to distinguish two tokens whose
    properties are otherwise equal (e.g., two occurences of the same
    word in a text).

    Locations are immutable and hashable.
    """
    def __init__(self):
        if self.__class__ == LocationI:
            raise AssertionError, "Interfaces can't be instantiated"
    
    def source(self):
        """
        @rtype: C{string}
        @return: The name of the document containing this location.
        """
        raise AssertionError()

    # Locations must be comparable:
    def __cmp__(self, other):
        raise AssertionError()

    # Locations must be hashable:
    def __hash__(self):
        raise AssertionError()

class SpanLocation(LocationI):
    """
    An abstract base class for the location of a token, encoded as a
    span over indices.  This span specifies the text beginning at its
    X{start index}, and ending just before its X{end index}.

    C{SpanLocation} is an abstract base class; individual subclasses
    are used to specify the measure over which the span is defined
    (such as character indices or time).
    """
    __slots__ = ('_start', '_end', '_source')

    class _Infinity:
        def __init__(self, dir): self._dir=dir
        def __repr__(self):
            if self._dir<0: return '-INF'
            else: return '+INF'
        def __cmp__(self, other):
            if self is other: return 0
            else: return self._dir
    MIN = _Infinity(-1)
    MAX = _Infinity(+1)
    
    def __init__(self, start, end, source=None):
        """
        Create a new location that specifies the text beginning at
        C{start} and ending just before C{end}.

        @type source: C{string}
        @param source: A case-sensitive string identifying the text
            containing this location.
        """
        if self.__class__ == SpanLocation:
            raise AssertionError, "Abstract classes can't be instantiated"
        self._start = start
        self._end = end
        self._source = source

    def source(self):
        # Documentation inherited from LocationI
        return self._source
    
    def start(self):
        """
        @return: This location's start index.  This location
            identifies the text beginning at this index, and
            ending just before the end index.
        """
        return self._start
    
    def end(self):
        """
        @return: This location's end index.  This location
            identifies the text beginning at the start index, and
            ending just before this index.
        """
        return self._end

    def length(self):
        """
        @return: the length of this C{Location}.  I.e., return
            C{self.end()-self.start()}.
        """
        return self._end - self._start

    def precedes(self, other):
        """
        @return: true if this C{Location} occurs entirely before
            C{other}.  In particular, return true iff C{self}'s end is
            less than or equal to C{other}'s start, and C{self}'s
            start is not equal to C{other}'s end.
        @rtype: C{boolean}
        @raise ValueError: If C{other} is not a compatible span
            location with the same source as C{self}.
        @seealso: L{succeeds}, L{overlaps}
        """
        if self.__class__ != other.__class__:
            raise ValueError('Locations have incompatible types')
        if self._source != other._source:
            raise ValueError('Locations have incompatible sources')
        return (self._end <= other._start and self._start != other._end)
    
    def succeeds(self, other):
        """
        @return: true if this C{Location} occurs entirely after
            C{other}.  In particular, return true iff C{other}'s end is
            less than or equal to C{self}'s start, and C{other}'s
            start is not equal to C{self}'s end.
        @rtype: C{boolean}
        @raise ValueError: If C{other} is not a compatible span
            location with the same source as C{self}.
        @seealso: L{precedes}, L{overlaps}
        """
        if self.__class__ != other.__class__:
            raise ValueError('Locations have incompatible types')
        if self._source != other._source:
            raise ValueError('Locations have incompatible sources')
        return (other._end <= self._start and other._start != self._end)

    def overlaps(self, other):
        """
        @return: true if this C{Location} overlaps C{other}.  In
            particular, return true if C{self}'s start falls in the
            range M{[C{other}.start, C{other}.end)}; or if C{other}'s
            start falls in the range M{[C{self}.start, C{self}.end)};
            or if C{self==other}.
        @rtype: C{boolean}
        @raise ValueError: If C{other} is not a compatible span
            location with the same source as C{self}.
        @seealso: L{precedes}, L{succeeds}
        """
        if self.__class__ != other.__class__:
            raise ValueError('Locations have incompatible types')
        if self._source != other._source:
            raise ValueError('Locations have incompatible sources')
        (s1,e1) = (self._start, self._end)
        (s2,e2) = (other._start, other._end)
        return (s1 <= s2 < e1) or (s2 <= s1 < e2) or (s1==s2==e1==e2)

    def contiguous(self, other):
        """
        @return: true if this C{Location} is contiguous with C{other}.
            In particular, return true if C{self}'s end is C{other}'s
            start; or if C{other}'s end is C{self}'s start.
        @rtype: C{boolean}
        @raise ValueError: If C{other} is not a compatible span
            location with the same source as C{self}.
        """
        if self.__class__ != other.__class__:
            raise ValueError('Locations have incompatible types')
        if self._source != other._source:
            raise ValueError('Locations have incompatible sources')
        return (self._end == other._start or other._end == self._start)

    def union(self, other):
        """
        @rtype: L{SpanLocation}
        @return: A new location that covers the combined spans
            of C{self} and C{other}.  C{self} and C{other} must be
            contiguous locations.
        @raise ValueError: If C{other} is not a compatible span
            location with the same source as C{self}.
        @raise ValueError: If C{self} and C{other} are not
            contiguous.
        @seealso: L{contiguous}
        """
        if self.__class__ != other.__class__:
            raise ValueError('Locations have incompatible types')
        if self._source != other._source:
            raise ValueError('Locations have incompatible sources')
        if self._end == other._start:
            cls = self.__class__
            return cls(self._start, other._end, source=self._source)
        elif other._end == self._start:
            cls = self.__class__
            return cls(other._start, self._end, source=self._source)
        else:
            raise ValueError('Locations are not contiguous')

    __len__ = length
    __add__ = union
    
    def __cmp__(self, other):
        if self.__class__ != other.__class__: return -1
        return cmp((self._start, self._end, self._source),
                   (other._start, other._end, other._source))
    
    def __hash__(self):
        return hash((self._start, self._end, self._source))

    def __repr__(self):
        if hasattr(self.__class__, 'UNIT'): unit = self.__class__.UNIT
        else: unit = ''
        return '[%s:%s%s]' % (self._start, self._end, unit)

    def __str__(self):
        if hasattr(self.__class__, 'UNIT'): unit = self.__class__.UNIT
        else: unit = ''
        if self._source is None: source = ''
        else: source = '@%s' % self._source
        return '[%s:%s%s]%s' % (self._start, self._end, unit, source)

class CharSpanLocation(SpanLocation):
    """
    The location of a token, encoded as a character span within the
    containing text.  This character span specifies the text beginning
    at its X{start index}, and ending just before its X{end index}.
    I.e., if C{M{text}} is the containing text, then a character span
    with start index C{M{s}} and end index C{M{e}} specifies
    C{M{text}[M{s}:M{e}]}.

    Each C{CharSpanLocation} also contains a X{source}, which
    specifies the source of the containing text.  Typically, the
    source is the name of the file that the containing text was read
    from.
    """
    __slots__ = ()
    UNIT = 'c'
    
    def select(self, text):
        """
        Given the text string over which this location is defined,
        return the substring specified by this token.  I.e., return
        C{text[self.start(), self.end()]}.
        """
        return text[self._start:self._end]

class IndexLocation(LocationI):
    """
    An abstract base class for the location of a token, encoded as a
    single index.

    C{IndexLocation} is an abstract base class; individual subclasses
    are used to specify the unit over which the index is defined (such
    as word indices or time).
    """
    __slots__ = ('index', 'source')
    def __init__(self, index, source=None):
        """
        Construct a new location that specifies the text at X{index}.
        @type source: C{string}
        @param source: A case-sensitive string identifying the text
            containing this location.
        """
        if self.__class__ == IndexLocation:
            raise AssertionError, "Abstract classes can't be instantiated"
        self._index = index
        self._source = source

    def source(self):
        # Documentation inherited from LocationI
        return self._source

    def index(self):
        """
        @return: This location's index.
        """
        return self._index
    
    def __cmp__(self, other):
        if self.__class__ != other.__class__: return -1
        return cmp((self._index, self._source),
                   (other._index, other._source))

    def __hash__(self):
        return hash((self._index, self._source))
        
    def __repr__(self):
        if hasattr(self.__class__, 'UNIT'): unit = self.__class__.UNIT
        else: unit = ''
        return '[%s%s]' % (self._index, unit)

    def __str__(self):
        if hasattr(self.__class__, 'UNIT'): unit = self.__class__.UNIT
        else: unit = ''
        if self._source is None: source = ''
        else: source = '@%s' % self._source
        return '[%s%s]%s' % (self._index, unit, source)

class WordIndexLocation(IndexLocation):
    """
    The location of a word, encoded as a word index within the
    containing text.
    """
    __slots__ = ()
    UNIT = 'w'

class SentIndexLocation(IndexLocation):
    """
    The location of a sentence, encoded as a sentence index within the
    containing text.
    """
    __slots__ = ()
    UNIT = 's'

class ParaIndexLocation(IndexLocation):
    """
    The location of a paragraph, encoded as a paragraph index within the
    containing text.
    """
    __slots__ = ()
    UNIT = 'p'

######################################################################
## Demonstration
######################################################################

def demo():
    """
    A demonstration showing how locations and tokens can be
    used.  This demonstration simply creates two locations and
    two tokens, and shows the results of calling several of their
    methods.
    """
    # Show what locations can do.
    print '_'*70
    print "loc  = CharSpanLocation(3, 13, source='corpus.txt')"
    loc = CharSpanLocation(3, 13, source='corpus.txt')
    print "loc2 = CharSpanLocation(20, 25, source='corpus.txt')"
    loc2 = CharSpanLocation(20, 25, source='corpus.txt')
    print
    print "print loc                      =>", loc
    print "print loc.start                =>", loc.start()
    print "print loc.end                  =>", loc.end()
    print "print loc.length()             =>", loc.length()
    print "print loc.source               =>", loc.source()
    print "print loc2                     =>", loc2
    print "print loc.precedes(loc2)       =>", loc.precedes(loc2)
    print "print loc.succeeds(loc2)       =>", loc.succeeds(loc2)
    print "print loc.overlaps(loc2)       =>", loc.overlaps(loc2)

    # Show what tokens can do.
    print '_'*70
    print "tok  = Token(TEXT='flattening', TAG='VBG', LOC=loc)"
    tok = Token(TEXT='flattening', TAG='VBG', LOC=loc)
    print "tok2 = Token(SIZE=12, WEIGHT=83, LOC=loc2)"
    tok2 = Token(SIZE=12, WEIGHT=83, LOC=loc2)
    print
    print "print tok                      =>", tok
    print "print tok['LOC']               =>", tok['LOC']
    print "print tok.exclude('LOC')       =>", tok.exclude('LOC')
    print "print tok.exclude('TEXT')      =>", tok.exclude('TEXT')
    print "print tok.project('TEXT')      =>", tok.project('TEXT')
    print "print tok2                     =>", tok2
    print "print tok2['LOC']              =>", tok2['LOC']
    print "print tok == tok2              =>", tok == tok2
    print "print tok == tok.copy()        =>", tok == tok.copy()

if __name__ == '__main__': demo()
