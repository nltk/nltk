#
# Natural Language Toolkit for Python:
# Type Checking
# Edward Loper
#
# Created [03/16/01 05:25 PM]
# (extracted from nltk.py, created [02/26/01 11:24 PM])
# $Id$
#
"""
@variable _type_safety_level The level of type safety to use when
checking the input parameters to methods defined by the Natural
Language Toolkit.  Currently defined values are:
<UL>
  <LI> 0: no type checking
  <LI> 1: check types only
  <LI> 2: check types and classes
  <LI> 3: check types, classes, list contents, and tuple contents
  <LI> 4: check types, classes, list contents, tuple contents, and
       dictionary contents.
</UL>
Higher levels of type safety (3-4) can result in signifigant loss of
efficiency.

@type type_safety_level int
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
    
from types import ListType, TupleType, ClassType, DictType, TypeType
from types import InstanceType

def chkclass(self, other):
    """
    Check that C{other} has the same class as C{self}
    
    @raise TypeError: if other is not an instance, or if other does
        not have the same class as self.
    """
    if (type(other) != InstanceType or
        other.__class__ != self.__class__):
        raise TypeError("Class mismatch: expected an object of "+\
                        "type "+self.__class__.__name__)

def classeq(instance1, instance2):
    """
    Return true iff the given objects are classes of the same instance.
    """
    if not isinstance(instance1, instance2): return 0
    if not isinstance(instance2, instance1): return 0
    return 1

def _typemsg(types):
    """##
    Construct a string naming the given type specification.  This
    function is intended soley for use by chktype.  However, it can
    also be useful in making sure that you got your type
    specification correct.
    """
    typestr = ''
    for typ in types:
        if type(typ) in (TypeType, ClassType):
            typestr = typestr + typ.__name__ + ' or'
        elif type(typ) == ListType:
            typestr = typestr + '(list whose elements are: '+ \
                      _typemsg(typ)+') or'
        elif type(typ) == TupleType:
            typestr = typestr + '(tuple whose elements are: '+ \
                      _typemsg(typ)+') or'
        elif type(typ) == DictType:
            for (key, val) in typ.items():
                typestr = typestr + '(dictionary from ' + \
                          _typemsg((key,)) + ' to ' + _typemsg(val) + \
                          ') or'
        else:
            raise AssertionError('Bad arg to typemsg')
    return typestr[:-3]

def chktype(name, n, arg, types):
    """##
    Automated type-checking function for parameters of functions and
    methods.  This function will check to ensure that a given argument
    (<CODE>arg</CODE> matches a type specification
    (<CODE>types</CODE>).  If it does not, it will raise a TypeError
    containing the name of the function or method, the argument
    number, and the allowable types. <P>

    This function has a well-defined interface, and is designed for
    efficient use; however, it should not necessarily be used by users 
    of the toolkit, since it is somewhat advanced. <P>

    This method does NOT handle recursive structures well; in
    particular, recursive arguments may cause it to enter an infinite
    loop. 

    @param name The name of the function or method whose parameter's
           type is being checked.
    @type name string

    @param n The position of the parameter whose type is being
             checked.  If it's not a positional parameter, I'm not
             sure what to do yet.
    @type n int

    @param arg The value of the parameter whose type is being
           checked.
    @type arg any

    @param types A list of the allowable types.  Each allowable type
           should be either a type (e.g., types.IntType); a class
           (e.g., Token); a list of allowable types; a tuple of
           allowable types; or a dictionary from allowable types to
           lists of allowable types.  If the argument matches any of
           the allowable types, then chktype will return; otherwise,
           a TypeError will be raised.  Matching is defined as
           follows:
           <UL>
             <LI> An argument matches a type if its type is equal to
                  that type.
             <LI> An argument matches a class if it is an instance of
                  that class.
             <LI> An arguent matches a list if the argument is a list
                  and each element of the argument matches any element
                  of the allowable type list.
             <LI> An arguent matches a tuple if the argument is a tuple
                  and each element of the argument matches any element
                  of the allowable type tuple.
             <LI> An argument matches a dictionary if the argument is
                  a dictionary and for each (key, value) pair of the
                  argument, there is some (key_t, value_t) pair in the
                  allowable type dictionary such that key matches
                  key_t and value matches some element of value_t.
           </UL>
    @type types List or Tuple
    @see nltk.type_safety_level type_safety_level
    @returntype None
    """
    # Unfortunately, this code is not really commented right now.
    # It's by far the most complex/advanced code in this module, and
    # isn't really intended to be played with.  It should be possible,
    # if not easy, to figure out how it works, given its definition in 
    # the __doc__ string.  I'll comment it one day, though.
    if type_safety_level <= 0: return
    if type(types) not in (ListType, TupleType):
        raise AssertionError("chktype expected a list of types/classes")
    for t in types:
        if type(t) == TypeType:
            if type(arg) == t: return
        elif type_safety_level <= 1:
            return
        elif type(t) == ClassType:
            if isinstance(arg, t): return
        elif type(t) == ListType:
            if type(arg) == ListType:
                if type_safety_level <= 2: return
                type_ok = 1
                for elt in arg:
                    try: chktype(name, n, elt, t, d+4)
                    except: type_ok = 0
                if type_ok: return
        elif type(t) == TupleType:
            if type(arg) == TupleType:
                if type_safety_level <= 2: return
                type_ok = 1
                for elt in arg:
                    try: chktype(name, n, elt, t, d+4)
                    except: type_ok = 0
                if type_ok: return
        elif type(t) == DictType:
            if type(arg) == DictType:
                if type_safety_level <= 3: return
                type_ok = 1
                for key in arg.keys():
                    if t.has_key(type(key)):
                        try: chktype(name, n, arg[key], t[type(key)], 
                                      d+4)
                        except: type_ok = 0
                    elif type(key) in (ListType, TupleType, DictType):
                        subtype_ok = 0
                        for t_key in t.keys():
                            if type(key) == type(t_key):
                                try:
                                    chktype(name, n, key, (t_key,), d+4)
                                    chktype(name, n, arg[key],
                                             t[t_key], d+4)
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
    if len(typestr) + len(errstr) <= 75:
        raise TypeError(errstr+typestr)
    else:
        raise TypeError(errstr+'\n      '+typestr)

