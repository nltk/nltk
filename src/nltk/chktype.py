# Natural Language Toolkit: Type Checking
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

"""
Manual type checking for the parameters of functions and methods.  The 
primary function defined by this module is C{chktype}, which checks
the type of a parameter against a type specification.  The amount of
type-checking performed by C{chktype} is dependant on the variable
C{type_safety_level}.

This module also defines two utility functions for testing that two
objects have the same class: C{chkclass} and C{classeq}.

@variable type_safety_level: The level of type safety to use when
  checking the input parameters to methods defined by the Natural
  Language Toolkit.  Currently defined values are:

    - 0: no type checking
    - 1: check types only
    - 2: check types and classes
    - 3: check types, classes, list contents, and tuple contents
    - 4: check types, classes, list contents, tuple contents, and
       dictionary contents.
       
  Higher levels of type safety (3-4) can result in signifigant loss of
  efficiency.

@type type_safety_level: int
"""
##//////////////////////////////////////////////////////
##  Type-checking
##//////////////////////////////////////////////////////

# 0 = no type checks
# 1 = just raw types
# 2 = types & classes
# 3 = types, classes, lists, & tuples
# 4 = full type safety (types, classes, lists, tuples, dictionaries)
type_safety_level=4

from types import ListType as _ListType
from types import TupleType as _TupleType
from types import ClassType as _ClassType
from types import TypeType as _TypeType
from types import DictType as _DictType
from types import InstanceType as _InstanceType

def chkclass(self, other):
    """
    Check that C{other} has the same class as C{self}.  If not, raise
    a C{TypeError}.  Note that this exception is not raised when
    C{chkclass} is used improperly, but when the check fails.

    @rtype: C{None}
    @raise TypeError: if C{other} is not an instance, or if C{other}
        does not have the same class as self.
    """
    if (type(other) != _InstanceType or
        other.__class__ != self.__class__):
        raise TypeError("Class mismatch: expected an object of "+\
                        "type "+self.__class__.__name__)

def classeq(instance1, instance2):
    """
    @return: true iff the given objects are classes of the same
        instance.
    @rtype: C{bool}
    """
    if not isinstance(instance1, instance2): return 0
    if not isinstance(instance2, instance1): return 0
    return 1

def _typemsg(types):
    """
    Construct a string naming the given type specification.  This
    function is intended soley for use by chktype.  However, it can
    also be useful in making sure that you got your type
    specification correct.

    @param types: A list of the allowable types.  See C{chktype} for
        more information.
    @type types: C{list} or C{tuple}
    @return: a string naming the given type specification.
    @rtype: C{string}
    """
    typestr = ''
    for typ in types:
        if type(typ) in (_TypeType, _ClassType):
            typestr = typestr + typ.__name__ + ' or '
        elif type(typ) == _ListType:
            typestr = typestr + '(list whose elements are: '+ \
                      _typemsg(typ)+') or '
        elif type(typ) == _TupleType:
            typestr = typestr + '(tuple whose elements are: '+ \
                      _typemsg(typ)+') or '
        elif type(typ) == _DictType:
            for (key, val) in typ.items():
                typestr = typestr + '(dictionary from ' + \
                          _typemsg((key,)) + ' to ' + _typemsg(val) + \
                          ') or '
        else:
            raise AssertionError('Bad arg to typemsg')
    return typestr[:-4]

def chktype(name, n, arg, types):
    """
    Automated type-checking function for parameters of functions and
    methods.  This function will check to ensure that a given argument
    (C{arg} matches a type specification (C{types}).  If it does not,
    it will raise a TypeError containing the name of the function or
    method, the argument number, and the allowable types. 

    This function has a well-defined interface, and is designed for
    efficient use; however, it should not necessarily be used by users 
    of the toolkit, since it is somewhat advanced. 

    This method does NOT handle recursive structures well; in
    particular, recursive arguments may cause it to enter an infinite
    loop. 

    @param name: The name of the function or method whose parameter's
           type is being checked.
    @type name: string

    @param n: The position of the parameter whose type is being
             checked.  If it's not a positional parameter, I'm not
             sure what to do yet.
    @type n: int

    @param arg: The value of the parameter whose type is being
           checked.
    @type arg: any

    @param types: A list of the allowable types.  Each allowable type
           should be either a type (e.g., types.IntType); a class
           (e.g., Token); a list of allowable types; a tuple of
           allowable types; or a dictionary from allowable types to
           lists of allowable types.  If the argument matches any of
           the allowable types, then chktype will return; otherwise,
           a TypeError will be raised.  Matching is defined as
           follows:

             - An argument matches a type if its type is equal to
                  that type.
             - An argument matches a class if it is an instance of
                  that class.
             - An arguent matches a list if the argument is a list
                  and each element of the argument matches any element
                  of the allowable type list.
             - An arguent matches a tuple if the argument is a tuple
                  and each element of the argument matches any element
                  of the allowable type tuple.
             - An argument matches a dictionary if the argument is
                  a dictionary and for each (key, value) pair of the
                  argument, there is some (key_t, value_t) pair in the
                  allowable type dictionary such that key matches
                  key_t and value matches some element of value_t.

    @type types: C{List} or C{Tuple}
    @see: nltk.type_safety_level
    @rtype: C{None}
    """
    # Unfortunately, this code is not really commented right now.
    # It's by far the most complex/advanced code in this module, and
    # isn't really intended to be played with.  It should be possible,
    # if not easy, to figure out how it works, given its definition in 
    # the __doc__ string.  I'll comment it one day, though.
    if type_safety_level <= 0: return
    if type(types) not in (_ListType, _TupleType):
        raise AssertionError("chktype expected a list of types/classes")
    for t in types:
        if type(t) == _TypeType:
            if type(arg) == t: return
        elif type_safety_level <= 1:
            return
        elif type(t) == _ClassType:
            if isinstance(arg, t): return
        elif type(t) == _ListType:
            if type(arg) == _ListType:
                if type_safety_level <= 2: return
                type_ok = 1
                for elt in arg:
                    try: chktype(name, n, elt, t)
                    except: type_ok = 0
                if type_ok: return
        elif type(t) == _TupleType:
            if type(arg) == _TupleType:
                if type_safety_level <= 2: return
                type_ok = 1
                for elt in arg:
                    try: chktype(name, n, elt, t)
                    except: type_ok = 0
                if type_ok: return
        elif type(t) == _DictType:
            if type(arg) == _DictType:
                if type_safety_level <= 3: return
                type_ok = 1
                for key in arg.keys():
                    if t.has_key(type(key)):
                        try: chktype(name, n, arg[key], t[type(key)])
                        except: type_ok = 0
                    elif type(key) in (_ListType, _TupleType, _DictType):
                        subtype_ok = 0
                        for t_key in t.keys():
                            if type(key) == type(t_key):
                                try:
                                    chktype(name, n, key, (t_key,))
                                    chktype(name, n, arg[key],
                                             t[t_key])
                                    subtype_ok = 1
                                except: pass
                        if not subtype_ok: type_ok = 0
                    else:
                        type_ok = 0
                if type_ok: return
        else:
            raise AssertionError("chktype expected a valid "+\
                                 "type specification.")

    # Type mismatch -- construct a user-readable error.
    errstr = "\n  Argument " + `n` + " to " + name + "() must " +\
             "have type: "
    typestr = _typemsg(types)
    if type(arg) == _InstanceType:
        typestr += ' (not %s)' % arg.__class__.__name__
    else:
        typestr += ' (not %s)' % type(arg).__name__
    if len(typestr) + len(errstr) <= 75:
        errstr = errstr+typestr
        raise TypeError(errstr)
    else:
        errstr = errstr+'\n      '+typestr
        raise TypeError(errstr)

