# Natural Language Toolkit: Type Checking
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

"""
Type checking support for NLTK.

Type checking for the parameters of functions and methods is performed
using the C{chktype} function.  This function should be used in
conjunction with an C{assert} statement::

    assert chktype(...)

This allows the user to bypass type-checking when efficiency is
important, by using optimized Python modules (C{.pyo} files).  For
more fine-grained control over the amount of type checking performed,
use the C{type_safety_level} function.

This module also defines two utility functions for testing that two
objects have the same class: C{chkclass} and C{classeq}.

@variable _type_safety_level: The level of type safety to use when
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
@type _type_safety_level: int
"""

import traceback
from types import *

##//////////////////////////////////////////////////////
##  Type-checking
##//////////////////////////////////////////////////////

_type_safety_level=2
def type_safety_level(level=None):
    """
    Change the level of type safety to use when checking the input
    parameters to methods defined by the Natural Language Toolkit.
    Currently defined values are:

        - 0: no type checking
        - 1: check types only
        - 2: check types and classes
        - 3: check types, classes, list contents, and tuple contents
        - 4: check types, classes, list contents, tuple contents, and
          dictionary contents.

    Higher levels of type safety (3-4) can result in signifigant loss
    of efficiency.  The default type safety level is currently 2.

    If C{type_safety_level} is called with no parameters, then return
    the current type safety level.

    @param level: The new type safety level.
    @type level: C{int} or C{None}
    @return: The old type safety level; or the current type safety
        level, if C{level} is not specified.
    @rtype: C{int}
    """
    assert chktype(1, level, IntType, NoneType)
    global _type_safety_level
    old_type_safety_level = _type_safety_level
    if level is not None:
        _type_safety_level = level
    return old_type_safety_level

def classeq(instance1, instance2):
    """
    @return: true iff the given objects are instances of the same
        class.
    @rtype: C{bool}
    """
    return (type(instance1) == InstanceType and
            type(instance2) == InstanceType and
            instance1.__class__ == instance2.__class__)

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
        if type(typ) in (TypeType, ClassType):
            if ' ' in typ.__name__: typestr += '%r or ' % typ.__name__
            else: typestr += '%s or ' % typ.__name__
                
        elif type(typ) == ListType:
            if typ == []:
                typestr += 'list or '
            else:
                typestr += '(list of '
                typestr += _typemsg(typ)+') or '
        elif type(typ) == TupleType:
            if typ == ():
                typestr += 'tuple or '
            else:
                typestr += '(tuple of '
                typestr += _typemsg(typ)+') or '
        elif type(typ) == DictType:
            if typ == {}:
                typestr += 'dictionary or '
            else:
                typestr += '(dictionary '
                for (key, val) in typ.items():
                    typestr += 'from ' + _typemsg((key,))
                    typestr += ' to ' + _typemsg(val) + ' or '
                typestr = typestr[:-4] + ') or '
        elif type(typ) in (FunctionType, MethodType):
            typestr += '<%s> or ' % typ.__name__
        else:
            raise AssertionError('Bad arg to typemsg')
    if len(types) > 1: return '(%s)' % typestr[:-4]
    else: return typestr[:-4]

def chktype(n, arg, *types):
    """
    Automated type-checking function for parameters of functions and
    methods.  This function will check to ensure that a given argument
    (C{arg}) matches a type specification (C{types}).  If it does not,
    it will raise a TypeError containing the name of the function or
    method, the argument number, and the allowable types.

    This function has a well-defined interface, and is designed for
    efficient use; however, it should not necessarily be used directly
    by students using the toolkit, since it is somewhat advanced.

    The following example demonstrates how this function is typically
    used.  Note the use of C{assert} statements, which ensures that
    typechecking is bypassed when optimized Python modules (C{.pyo}
    files) are used::

        def demo(x, f, lst, dict):
            assert chktype(1, x, IntType)     # integer
            assert chktype(2, f, FloatType)   # float
            assert chktype(3, lst, [IntType]) # list of ints
            assert chktype(4, dict, {})       # any dictionary

    @type n: C{int} or C{string}
    @param n: The position of the parameter whose type is being
        checked.  If the parameter being checked is a varargs
        parameter, then use the string 'vararg'; if the parameter
        being checked is a keyword parameter, then use the string
        'kwarg'.

    @type arg: any
    @param arg: The value of the parameter whose type is being checked. 
        
    @type types: C{List} or C{Tuple}
    @param types: A list of the allowable types.  If the argument
        matches any of the allowable types, then chktype will return;
        otherwise, a TypeError will be raised.  X{Matching} is defined
        as follows:
            - An argument matches a B{type} if its type is equal to
              that type.
            - An argument matches a B{class} if it is an instance of
              that class.
            - An argument matches an B{empty list} if the argument is
              a list.
            - An argument matches an B{empty tuple} if the argument is
              a tuple.
            - An argument matches an B{empty dictionary} if the
              argument is a dictionary.
            - An arguent matches a B{non-empty list} if the argument
              is a list, and each element of the argument matches any
              element of the non-empty list.
            - An arguent matches a B{non-empty tuple} if the argument
              is a tuple, and each element of the argument matches any
              element of the non-empty tuple.
            - An argument matches a B{non-empty dictionary} if the
              argument is a dictionary; and for each (key, value) pair
              in the argument's items, there is some (key_t, value_t)
              pair in the non-empty dictionary such that key matches
              key_t and value matches some element of value_t.
        Note that allowable type dictionaries map from allowable types
        to I{lists} of allowable types, and not directly to allowable
        types.
    
    @return: true
    @rtype: C{boolean}
    @raise TypeError: If C{arg} does not match {types}.
    @see: nltk.type_safety_level
    """
    if _type_safety_level <= 0: return 1
    
    # Check each type spec.  If any of the type specs matches, then
    # return true.  Each type spec can be: a type; a class; a list; a
    # tuple; a dictionary; or some other object.
    for t in types:
        # The type spec is a type; return 1 if the arg's type matches.
        if type(t) == TypeType:
            if isinstance(arg, t): return 1

        # The type spec is a class; return 1 if the arg's class matches.
        elif type(t) == ClassType:
            if _type_safety_level <= 1: return 1
            if isinstance(arg, t): return 1

        # The type spec is a list; check that the arg is a list.  If
        # type safety level > 2, check each element of the list.
        elif type(t) == ListType:
            if type(arg) == ListType:
                if _type_safety_level <= 2: return 1
                if len(t) == 0: return 1
                type_ok = 1
                for elt in arg:
                    try: chktype(n, elt, *t)
                    except: type_ok = 0
                if type_ok: return 1
                
        # The type spec is a tuple; check that the arg is a tuple.  If
        # type safety level > 2, check each element of the tuple.
        elif type(t) == TupleType:
            if type(arg) == TupleType:
                if _type_safety_level <= 2: return 1
                if len(t) == 0: return 1
                type_ok = 1
                for elt in arg:
                    try: chktype(n, elt, *t)
                    except: type_ok = 0
                if type_ok: return 1
                
        # The type spec is a dictionary; check that the arg is a
        # dictionary.  If type safety level > 3, check each key/value
        # pair in the dictionary.
        elif type(t) == DictType:
            if type(arg) == DictType:
                if _type_safety_level <= 3: return 1
                if len(t) == 0: return 1
                type_ok = 1

                for (key,val) in arg.items():
                    # Find a key in the typespec that matches the
                    # item's key.  This can be a type or a class.  Get
                    # the corresponding value typespec.
                    val_typespec = t.get(type(key), None)
                    if val_typespec is None and isinstance(key, InstanceType):
                        val_typespec = t.get(key.__class_, None)
                    if val_typespec is not None:
                        if type(val_typespec) not in (ListType, TupleType):
                            raise AssertionError('Invalid type specification')
                        try: chktype(n, arg[key], *val_typespec)
                        except: type_ok = 0

                    # We didn't find a key in the typespec that
                    # matches the item's key exactly.  Try finding a
                    # key that's a tuple, and use it to match.  Note
                    # that we don't have to check dicts/lists, because
                    # they're not hashable.
                    elif type(key) == TupleType:
                        type_ok_2 = 0
                        for (key_typespec, val_typespec) in t.items():
                            if type(key_typespec) == TupleType:
                                try:
                                    chktype(n, key, key_typespec)
                                    chktype(n, val, *val_typespec)
                                    type_ok_2 = 1
                                except: pass
                        if not type_ok_2: type_ok = 0

                    # If we couldn't find any matches at all, fail.
                    else:
                        type_ok = 0

                # If all of the dict's items were ok, then return 1. 
                if type_ok: return 1

        # The type spec is a function: use it to check the argument.
        elif type(t) in (FunctionType, MethodType):
            if t(arg): return 1

        # They gave us a bad type specification; complain.
        else:
            raise AssertionError("Invalid type specification")

    # What's the name of the function?
    name = traceback.extract_stack()[-2][2]

    # Type mismatch -- construct a user-readable error.
    errstr = '\n\n  Argument %s to %s() must have type: ' % (n, name)
    if type(n) == type('') and n[:1].lower() == 'v':
        errstr = '\n\n  Varargs argument to %s() must have type: ' % name
    if type(n) == type('') and n[:1].lower() == 'k':
        errstr = '\n\n  Keyword argument to %s() must have type: ' % name
    typestr = _typemsg(types)
    gotstr = '\n      (got a %s)' % type(arg).__name__
    if len(typestr) + len(errstr) <= 75:
        errstr = errstr+typestr+gotstr
        raise TypeError(errstr)
    else:
        errstr = errstr+'\n      '+typestr+gotstr
        raise TypeError(errstr)

def demo():
    """
    A demonstration of the C{chktype} type-checking function.
    """
    old_type_safety_level = type_safety_level()
    type_safety_level(4)
    
    demofunc = """def typechk_demo(intparam, listparam, dictparam):
    assert chktype(1, intparam, IntType)
    assert chktype(2, listparam, [IntType, ListType])
    assert chktype(3, dictparam, {})\n"""

    print
    print 'Test function:'
    print '='*70+'\n'+demofunc+'='*70+'\n'
    exec demofunc

    # Demonstrate usage.
    print "typechk_demo(3, [], {})"
    try: typechk_demo(3, [], {})
    except Exception, e: print str(e)[2:]
    print
        
    print "typechk_demo(5, [3,[3,12]], {1:2})"
    try: typechk_demo(5, [3,[3,12]], {1:2})
    except Exception, e: print str(e)[2:]
    print

    print "typechk_demo('x', [], {})"
    try: typechk_demo('x', [], {})
    except Exception, e: print str(e)[2:]
    print
        
    print "typechk_demo(5, 33, {})"
    try: typechk_demo(5, 33, {})
    except Exception, e: print str(e)[2:]
    print
    
    print "typechk_demo(5, [], 'x')"
    try: typechk_demo(5, [], 'x')
    except Exception, e: print str(e)[2:]
    print

    print "typechk_demo(5, [3,(3,12)], {1:2})"
    try: typechk_demo(5, [3,(3,12)], {1:2})
    except Exception, e: print str(e)[2:]
    print

    type_safety_level(old_type_safety_level)

if __name__ == '__main__':
    demo()
