# Natural Language Toolkit: Restructured version of token.py
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

"""
Proposed replacements for the current C{nltk.token} module.

Types
=====
In the new architecture, all text types are encoded using a single
class, C{Type}.  A type is a read-only objects that defines a set of
named properties, such as C{'text'}, C{'pos'}, or C{'waveform'}.

I propose 3 alternative implementations of the L{Type} class:

  - With L{Type1}, properties are accessed exclusively via the
    L{Type.get<Type1.get>} method:

        >>> print typ.get('text')
        
  - With L{Type2} and L{Type3}, properties can also be accessed
    via attributes:

        >>> print typ.text

    C{Type2} and C{Type3} are functionally equivalant, but C{Type3} is
    more efficient (but possibly harder to read).

Tokens
======
A token is basically defined as a C{Type} plus a C{Location}.  I
propose 5 alernative implementations of the L{Token} class:

  - In L{Token1}, the token's type and location are accessed using
    the C{type()} and C{loc()} methods:

        >>> print tok.type(), tok.loc()

  - In L{Token2}, the token's type and location are accessed using
    C{type} and C{loc} attributes:

        >>> print tok.type, tok.loc

  - L{Token3} is similar to C{Token1}; but it also defines a wrapper
    for each C{Type} method, that delegates to the token's type:

        >>> print tok.type().get('text')
        >>> print tok.get('text')

  - L{Token4} and L{Token5} are similar to C{Token2}; but they also
    define a wrapper for each C{Type} method; and they delegate all
    attribute accesses to the token's type.  Used in conjunction with
    C{Type2} or L{Type3}, this lets you access a property of a token's
    type with simple attribute access:

        >>> print tok.type.get('text')
        >>> print tok.get('text')
        >>> print tok.text

    C{Token4} and C{Token5} are functionally equivalant, but C{Token5}
    is more efficient (but definitely harder to read).

Combinations that are under consideration are::

 ==================================
 |        | Type1 | Type2 | Type3 |
 ----------------------------------
 | Token1 |   X   |       |       |
 | Token2 |   X   |   X   |   X   |
 | Token3 |   X   |       |       |
 | Token4 |       |   X   |   X   |
 | Token5 |       |   X   |   X   |
 ==================================
 
The following table summarizes some of the differences between the
alternatives, in terms of functionality, complexity, and speed::

  ===================================================================
  |            | Function. |  Complexity   |    Speed (in usecs.)   |
  +------------+-----------+---------------+------------------------+
  |   System     Attr  Fwd   Lines  Tricks   t(a)  t(g)  t(c)  t(e) |
  -------------------------------------------------------------------
   Token1+Type1    -    -      24      0      N/A    24   225   470
   Token2+Type1    -    -      26      1      N/A    17   465   463
   Token2+Type2    +    -      31      1       44    17   479   472
   Token2+Type3    +    -      33      2        5    17   332   359
   Token3+Type1    -    +      31      1      N/A    31   415   510
   Token4+Type2    +    +      40      2       58    25   473   503
   Token4+Type3    +    +      42      3       58    24   332   436
   Token5+Type2    +    +      56      4        4    16   252   220
   Token5+Type3    +    +      58      4        4    15   218   217
  ===================================================================

  Key:
    - Attr: Supports direct attribute access.
    - Fwd: Tokens forwards methods/attribute access to their types.
    - Lines: Lines of code in implementation.
    - Tricks: Number of advanced python features used.
    - t(a): Avg. time to access a property as an attribute.
    - t(g): Avg. time to access a property, using get().
    - t(c): Avg. time to create a new token.
    - t(e): Avg. time to extend a token with a new property.

Note that the implementations are not totally comple; e.g., they don't
define equality operators or hash operators.  These will need to be
implemented eventually, but for the purposes of comparing different
implementations, they would just clutter things up.
"""

import time

# Location might be modified some (e.g., methods replaced by
# attributes); but the changes would be made to be consistant with the
# changes to Token, and would be fairly streight-forward.
from nltk.token import Location

############################################################
## TYPE
############################################################

# For now, this class is just used to define shared docstrings.
# Later, it will be replaced by one of its implementations (when we
# decide which one is best), and the docstrings will be moved to that
# implementation's method. 
class Type:
    """
    A unit of language, such as a word or a sentence.  Types should be
    contrasted with L{Tokens<Token>}, which represent individual
    occurances of types; types are the unit of language themselves,
    abstracted away from their from context.

    A type is defined by a set of named X{properties}, each of which
    has a value.  Types can differ in the set of properties they
    define, and in their values for those properties.  Examples of
    common properties for types are:

      - C{text}: The text contents of the type.
      - C{pos}: The part-of-speech of the type.
      - C{sense}: The disambiguated sense intended for the type.
      - C{wave}: The sound waveform of the type.
      - etc..

    Note that some properties only make sense for specific kinds of
    C{Types}.  For example, only C{Types} representing auditory units
    of language will have waveforms; and only C{Types} representing
    words will have part-of-speech tags.
    """
    def __init__(self, **properties):
        """
        Construct a new type that defines the given set of properties.
        """
        raise AssertionError, 'abstract class'

    def get(self, property):
        """
        @return: the value of the given property.
        """
        raise AssertionError, 'abstract class'

    def has(self, property):
        """
        @return: true if this C{Type} defines the given property.
        @rtype: C{boolean}
        """
        raise AssertionError, 'abstract class'

    # Should this be given a different name?  (Because in most other
    # places, we use the word "properties" to refer to a dictionary
    # from property name to value; and not to a list of property
    # names).  Perhaps "property_names" or "defined_properties"?
    def properties(self):
        """
        @return: A list of the names of the properties that are
            defined for this Type.
        @rtype: C{list} of C{string}
        """
        raise AssertionError, 'abstract class'

    def extend(self, **properties):
        """
        @return: A new C{Type} with all the properties of this type,
        plus given set of properties.  If a property that is defined
        by this type is also given a value by C{properties}, then the
        value specified by C{properties} will override this Type's
        value.
        
        Note that this method does returns a new type; it does I{not}
        modify this Type.
            
        @rtype: L{Type}
        """
        raise AssertionError, 'abstract class'

    def select(self, *property_list):
        """
        @return: A new C{Type} that only contains the given set of
            properties.
        @rtype: C{Type}
        @param property_list: The list of properties that the returned
            type should have.  This list must be a subset of the
            properties that are defined by this type.
        @type property_list: C{list} of C{string}
        @note: This is included for completeness, but I don't
               anticipate that it will be used very much.
        @raise KeyError: If this type does not define one or more of
            the given properties.
        """
        raise AssertionError, 'abstract class'

    def __repr__(self):
        """
        @return: A string representation of this C{Type}.
        @rtype: C{string}
        """
        raise AssertionError, 'abstract class'

#////////////////////////////////////////////////////////////
# Type: Implementation 1
#////////////////////////////////////////////////////////////
class Type1(Type):
    """
    A simple implementation of the Type class, where properties are
    accessed exclusively via the C{get} method.
    """
    def __init__(self, **properties):
        # We don't need to call ".copy()" here because Python already
        # does it for us (with the **kwargs construction).
        self._properties = properties

    # These just delegate to self._properties:
    def get(self, property): return self._properties[property]
    def has(self, property): return self._properties.has_key(property)
    def properties(self): return self._properties.keys()

    def extend(self, **properties):
        typ = Type1(**self._properties)
        typ._properties.update(properties)
        return typ

    def select(self, *property_list):
        properties = {}
        for property in property_list:
            properties[property] = self._properties[property]
        return Type1(**properties)

    def __repr__(self):
        items = ', '.join(['%s=%r' % (p,v)
                           for (p,v) in self._properties.items()])
        return '<%s>' % items

#////////////////////////////////////////////////////////////
# Type: Implementation 2
#////////////////////////////////////////////////////////////
class Type2(Type):
    """
    An implementation of the Type class that defines __getattr__, in
    order to allow properties to be accessed as attributes; and
    defines __setattr__ and __delattr__ to prevent users from
    accidentally modifying properties.

    This implementation is identical to Type1, except:
        - We define __getattr__ = get.
        - We define new __setattr__ and __delattr__ methods that
          raise TypeError exceptions (since types are immutable).
        - The constructor defines self._properties by directly
          editing self.__dict__, rather than setting it the normal
          way, since setting it the normal way would just call
          __setattr__ (which raises an exception, since Types are
          immutable).
    """
    def __init__(self, **properties):
        # We don't need to call ".copy()" here because Python already
        # does it for us (with the **kwargs construction).
        self.__dict__['_properties'] = properties

    # These are the same as Type1: just delegate to _properties.
    def get(self, property): return self._properties[property]
    def has(self, property): return self._properties.has_key(property)
    def properties(self): return self._properties.keys()

    # Overload __getattr__ to return a property
    __getattr__ = get

    # Overload __setattr__ and __delattr__ to raise exceptions
    def __setattr__(self, property, value):
        raise TypeError('Types are immutable')
    def __delattr__(self, property):
        raise TypeError('Types are immutable')

    # Everything below is identical to Type1.
    def extend(self, **properties):
        typ = Type2(**self._properties)
        typ._properties.update(properties)
        return typ

    def select(self, *property_list):
        properties = {}
        for property in property_list:
            properties[property] = self._properties[property]
        return Type2(**properties)

    def __repr__(self):
        items = ', '.join(['%s=%r' % (p,v)
                           for (p,v) in self._properties.items()])
        return '<%s>' % items

#////////////////////////////////////////////////////////////
# Type: Implementation 3
#////////////////////////////////////////////////////////////
class Type3(Type):
    """
    An implementation of the Type class that uses the object's
    dictionary (C{self.__dict__}) to store properties, rather than an
    instance variable (C{self._properties}).  This has 2 efficiency
    advantages over the Type2:
    
      - It's more space efficient, since we only use one dictionary
        per type (instead of two dictionaries for type for Type2).
      - Property lookup via attribute access is much more efficient,
        since the properties are stored as true attributes (rather
        than using __getattr__ to make them I{look} like attributes).
        In fact, for this implementation __getattr__ will only be
        called for attributes that are I{not} defined by the object's
        dictionary; therefore, it always raises an exception.

    The implementation is almost identical, except that:
      - \"C{self._properties}\" is replaced by \"C{self.__dict__}\"
      - The constructor directly updates C{self.__dict__}, rather than
        creating a new C{self._properties} variable.
      - C{__getattr__} is defined to always raise an exception.
    """
    def __init__(self, **properties):
        self.__dict__.update(properties)

    # Delegate property lookups to self.__dict__.
    def get(self, property): return self.__dict__[property]
    def has(self, property): return self.__dict__.has_key(property)
    def properties(self): return self.__dict__.keys()

    # __getattr__ is only called if a property is *not* defined by
    # self.__dict__; so it should always raise an exception.
    def __getattr__(self, property):
        raise KeyError('The type %r does not define the %r property.' %
                       (self, property))

    # Overload __setattr__ and __delattr__ to raise exceptions
    def __setattr__(self, property, value):
        raise TypeError('Types are immutable')
    def __delattr__(self, property):
        raise TypeError('Types are immutable')

    def extend(self, **properties):
        typ = Type3(**self.__dict__)
        typ.__dict__.update(properties)
        return typ

    def select(self, *property_list):
        properties = {}
        for property in property_list:
            properties[property] = self.__dict__[property]
        return Type3(**properties)

    def __repr__(self):
        items = ', '.join(['%s=%r' % (p,v)
                           for (p,v) in self.__dict__.items()])
        return '<%s>' % items

############################################################
## TOKEN
############################################################

# For now, this class is just used to define shared docstrings.
# Later, it will be replaced by one of its implementations (when we
# decide which one is best), and the docstrings will be moved to that
# implementation's method.
class Token:
    """
    A single occurance of a unit of language, such as a word or a
    sentence.  Tokens should be contrasted with L{Types<Type>}, which
    represent the units of language themselves, abstracted away from
    their context.
    """

#////////////////////////////////////////////////////////////
# Token: Implementation 1
#////////////////////////////////////////////////////////////
class Token1(Token):
    """
    This implementation of the Token class defines C{type()} and
    C{loc()} methods to access the type and location; and does not do
    any \"forwarding\" of methods/attribute access to the Token's
    type.
    """
    def __init__(self, type, loc=None):
        self._type = type
        self._loc = loc

    def type(self): return self._type
    def loc(self): return self._loc
    def __repr__(self): return '%r%r' % (self._type, self._loc)

#////////////////////////////////////////////////////////////
# Token: Implementation 2
#////////////////////////////////////////////////////////////
class Token2(Token):
    """
    This implementation of the Token class defines C{type} and C{loc}
    attributes to access the type and location; and does not do any
    \"forwarding\" of methods/attribute access to the Token's type.

    This gives faster access to the type and loc than C{Token1}, since
    no accessor method is used.

    @ivar type: The token's type.
    @ivar loc: The token's location.
    """
    def __init__(self, type, loc=None):
        self.__dict__['type'] = type
        self.__dict__['loc'] = loc

    # Enforce the immutability of tokens:
    def __setattr__(self, property, value):
        raise TypeError('Types are immutable')
    def __delattr__(self, property):
        raise TypeError('Types are immutable')
        
    def __repr__(self): return '%r%r' % (self.type, self.loc)

#////////////////////////////////////////////////////////////
# Token: Implementation 3
#////////////////////////////////////////////////////////////
class Token3(Token):
    """
    This implementation of the Token class defines C{type} and C{loc}
    attributes to access the type and location; and \"forwards\" type
    methods to the token's type.  In other words, for most methods
    C{M{m}(...)} defined by C{Type}, the token defines a method that
    returns C{self.type.M{m}(...)}.  The two exceptions are L{extend}
    and L{select}, which returns C{Token(self.type.M{m}(...),
    self.loc)}.  An example usage of forwarded methods is:

        >>> print tok.get('text')
        'the'
        >>> print tok.has('pos')
        1

    This class does I{not} \"forward\" attribute accesses to the
    token's type.
    
    @ivar _type: The token's type.
    @ivar _loc: The token's location.
    """
    def get(self, property): return self.type().get(property)
    def has(self, property): return self.type().has(property)
    def properties(self): return self.type().properties()
    def extend(self, **properties):
        return Token3(self.type().extend(**properties), self.loc())
    def select(self, *property_list):
        return Token3(self.type().select(*property_list), self.loc())

    # Everything below is identical to Token1.
    def __init__(self, type, loc=None):
        self._type = type
        self._loc = loc
    def type(self): return self._type
    def loc(self): return self._loc
    def __repr__(self): return '%r%r' % (self._type, self._loc)

#////////////////////////////////////////////////////////////
# Token: Implementation 4
#////////////////////////////////////////////////////////////
class Token4(Token):
    """    
    This implementation of the Token class defines C{type} and C{loc}
    attributes to access the type and location; and \"forwards\" type
    methods and attribute accesses to the token's type.  I.e., for
    most methods C{M{m}(...)} defined by C{Type}, the token defines a
    method that returns C{self.type.M{m}(...)}.  The two exceptions
    are L{extend} and L{select}, which returns
    C{Token(self.type.M{m}(...), self.loc)}.  Additionally, attribute
    accesses are forwarded to the type.  For implementations L{Type2}
    and L{Type3}, this means that the properties of a token's type can
    be accessed as attributes on the token.  For example:

        >>> print tok.text, tok.pos
        ('the', 'Det')
        
    @ivar type: The token's type.
    @ivar loc: The token's location.
    """
    def __getattr__(self, property):
        return self.type.get(property)

    # Everything below is a cross between Token2 & Token3.
    def __init__(self, type, loc=None):
        self.__dict__['type'] = type
        self.__dict__['loc'] = loc
    def get(self, property): return self.type.get(property)
    def has(self, property): return self.type.has(property)
    def properties(self): return self.type.properties()
    def extend(self, **properties):
        return Token4(self.type.extend(**properties), self.loc)
    def select(self, *property_list):
        return Token4(self.type.select(*property_list), self.loc)
    def __setattr__(self, property, value):
        raise TypeError('Types are immutable')
    def __delattr__(self, property):
        raise TypeError('Types are immutable')
    def __repr__(self): return '%r%r' % (self.type, self.loc)

#////////////////////////////////////////////////////////////
# Token: Implementation 5
#////////////////////////////////////////////////////////////
class Token5(Token):
    """
    This implementation of the Token class defines C{type} and C{loc}
    attributes to access the type and location; and \"forwards\" type
    methods and attribute accesses to the token's type.  Functionally,
    it is identical to L{Token4}.  But it uses several advanced Python
    techniques to increase efficiency.  In particular...
    """
    def __init__(self, type, loc=None):
        # Copy the dictionary from the type.
        if isinstance(type, Type3):
            self.__dict__.update(type.__dict__)
        elif isinstance(type, dict):
            self.__dict__.update(type)
        else:
            self.__dict__.update(type._properties)

        # Add the location.
        self.__dict__['loc'] = loc

    # Delegate to self.__dict__
    def get(self, property): return self.__dict__[property]
    def has(self, property): return self.__dict__.has_key(property)
    def properties(self): return self.__dict__.keys()
    
    def extend(self, **properties):
        tok = Token5(self.__dict__, self.loc)
        tok.__dict__.update(properties)
        return tok

    def select(self, *property_list):
        properties = {}
        for property in property_list:
            properties[property] = self.__dict__[property]
        return Token5(properties, self.loc)
    
    def __setattr__(self, property, value):
        raise TypeError('Types are immutable')
    def __delattr__(self, property):
        raise TypeError('Types are immutable')
        
    def __getattr__(self, property):
        # If the type is requested, then create it on-the-fly, and
        # cache it.
        if property == 'type':
            properties = self.__dict__.copy()
            del properties['loc']
            self.__dict__['type'] = Type(**properties)
            return self.type
        # For any other attribute, raise an exception.
        raise KeyError('The type %r does not define the %r property.' %
                       (self, property))
    
    def __repr__(self): return '%r%r' % (self.type, self.loc)



############################################################
## DEMONSTRATION TEST
############################################################
def demotest():
    """
    A test function that demonstrates the usage of each type/token
    definition.
    """
    global Type, Token
    
    def _testeval(tok, str):
        try:
            v = eval(str)
            print '    %-30s = %r' % (str, v)
        except Exception, e:
            return
            print '    %-30s = %s' % (str, e.__class__)
            
    
    for Token in Token1, Token2, Token3, Token4, Token5:
        for Type in Type1, Type2, Type3:
            print '='*70
            print 'Implementations:', Token.__name__, 'and', Type.__name__
            print '-'*70
            t_a = Token(Type(text='foo'), Location(0, unit='w'))
            try:
                t_b = t_a.extend(pos='bar')
                t_c = t_b.select('pos')
            except:
                try:
                    t_b = Token(t_a.type.extend(pos='bar'), t_a.loc)
                    t_c = Token(t_b.type.select('pos'), t_a.loc)
                except: 
                    t_b = Token(t_a.type().extend(pos='bar'), t_a.loc())
                    t_c = Token(t_b.type().select('pos'), t_a.loc())
            print 'Original token............... %r' % t_a
            print 'Extended with pos="bar"...... %r' % t_b
            print 'Selected for pos............. %r' % t_c
            print 
            print 'Example uses of %r:' % t_b
            _testeval(t_b, 'tok.type().properties()')
            _testeval(t_b, 'tok.type.properties()')
            _testeval(t_b, 'tok.properties()')
            for p in 'text pos bar'.split():
                _testeval(t_b, 'tok.type().get(%r)' % p)
                _testeval(t_b, 'tok.type.get(%r)' % p)
                _testeval(t_b, 'tok.get(%r)' % p)
                _testeval(t_b, 'tok.type().%s' % p)
                _testeval(t_b, 'tok.type.%s' % p)
                _testeval(t_b, 'tok.%s' % p)
    
############################################################
## TIMING TEST
############################################################

def timetest():
    """
    A test function that times various operations on the set of
    token/type implementation combinations that are under
    consideration.
    """
    global Type, Token
    N = 100 * 1000
    
    combos = [(Token1, Type1), (Token2, Type1), (Token2, Type2),
              (Token2, Type3), (Token3, Type1), (Token4, Type2),
              (Token4, Type3), (Token5, Type2), (Token5, Type3)]
    times = []
    for (Token, Type) in combos:
        # Creation time.
        s = 'the'
        loc = Location(0, unit='w')
        t0 = time.time()
        toks = [Token(Type(text=s), loc) for i in range(N)]
        cspd = time.time()-t0

        # Property access time, using get()
        tok = toks[0]
        try:
            # Token.get()
            t0 = time.time()
            for i in range(N):
                x = tok.get('text')
            gspd = time.time()-t0
        except:
            try:
                # Token.type.get()
                t0 = time.time()
                for i in range(N):
                    x = tok.type.get('text')
                gspd = time.time()-t0
            except:
                # Token.type().get()
                t0 = time.time()
                for i in range(N):
                    x = tok.type().get('text')
                gspd = time.time()-t0

        # Property access time, using attributes
        try:
            # Token.text
            t0 = time.time()
            for i in range(N):
                x = tok.text
            aspd = time.time()-t0
        except:
            try:
                # Token.type.text
                t0 = time.time()
                for i in range(N):
                    x = tok.type.text
                aspd = time.time()-t0
            except:
                try:
                    # Token.type().text
                    t0 = time.time()
                    for i in range(N):
                        x = tok.type().text
                    aspd = time.time()-t0
                except:
                    aspd = 0

        # Token extension speed
        try: 
            t0 = time.time()
            toks = [t.extend(pos='Det') for t in toks]
            espd = time.time() - t0
        except:
            try:
                t0 = time.time()
                toks = [Token(t.type.extend(pos='Det'), t.loc)
                        for t in toks]
                espd = time.time() - t0
            except:
                t0 = time.time()
                toks = [Token(t.type().extend(pos='Det'), t.loc())
                        for t in toks]
                espd = time.time() - t0

        times.append([name, aspd, gspd, cspd, espd])

if 1:
    # Print speeds
    print 'Combination      ASpeed  GSpeed  CSpeed  ESpeed'
    print '-----------------------------------------------'
    norm = float(1000*1000)/N
    for (name, aspd, gspd, cspd, espd) in times:
        name = Token.__name__+'+'+Type.__name__
        if aspd == 0:
            #print ('%-15s %7s %7.1f %7.1f %7.1f' %
            print ('%-15s %7s %7d %7d %7d' %
                   (name, 'N/A', gspd*norm, cspd*norm, espd*norm))
        else:
            #print ('%-15s %7.1f %7.1f %7.1f %7.1f' %
            print ('%-15s %7d %7d %7d %7d' %
                   (name, aspd*norm, gspd*norm, cspd*norm, espd*norm))
    #return times
            
#if __name__ == '__main__':
#    demotest()
#    times = timetest()
