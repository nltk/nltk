# Natural Language Toolkit: CCG Categories
#
# Copyright (C) 2001-2014 NLTK Project
# Author: Graeme Gange <ggange@csse.unimelb.edu.au>
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT
from __future__ import unicode_literals
from nltk.internals import raise_unorderable_types
from nltk.compat import (total_ordering, python_2_unicode_compatible,
                         unicode_repr)

@total_ordering
class AbstractCCGCategory(object):
    '''
    Interface for categories in combinatory grammars.
    '''

    # Returns true if the category is primitive
    def is_primitive(self):
        raise NotImplementedError()

    # Returns true if the category is a function application
    def is_function(self):
        raise NotImplementedError()

    # Returns true if the category is a variable
    def is_var(self):
        raise NotImplementedError()

    # Takes a set of (var, category) substitutions, and replaces every
    # occurrence of the variable with the corresponding category
    def substitute(self,substitutions):
        raise NotImplementedError()

    # Determines whether two categories can be unified.
    #  - Returns None if they cannot be unified
    #  - Returns a list of necessary substitutions if they can.'''
    def can_unify(self,other):
        raise NotImplementedError()

    # Utility functions: comparison, strings and hashing.

    def __str__(self):
        raise NotImplementedError()

    def __eq__(self, other):
        return (self.__class__ is other.__class__ and
                self._comparison_key == other._comparison_key)

    def __ne__(self, other):
        return not self == other

    def __lt__(self, other):
        if not isinstance(other, AbstractCCGCategory):
            raise_unorderable_types("<", self, other)
        if self.__class__ is other.__class__:
            return self._comparison_key < other._comparison_key
        else:
            return self.__class__.__name__ < other.__class__.__name__

    def __hash__(self):
        try:
            return self._hash
        except AttributeError:
            self._hash = hash(self._comparison_key)
            return self._hash


@python_2_unicode_compatible
class CCGVar(AbstractCCGCategory):
    '''
    Class representing a variable CCG category.
    Used for conjunctions (and possibly type-raising, if implemented as a
    unary rule).
    '''
    _maxID = 0

    def __init__(self, prim_only=False):
        """Initialize a variable (selects a new identifier)

        :param prim_only: a boolean that determines whether the variable is restricted to primitives
        :type prim_only: bool
        """
        self._id = self.new_id()
        self._prim_only = prim_only
        self._comparison_key = self._id

    @classmethod
    def new_id(cls):
        """A class method allowing generation of unique variable identifiers."""
        cls._maxID = cls._maxID + 1
        return cls._maxID - 1

    def is_primitive(self):
        return False

    def is_function(self):
        return False

    def is_var(self):
        return True

    def substitute(self, substitutions):
        """If there is a substitution corresponding to this variable,
        return the substituted category.
        """
        for (var,cat) in substitutions:
            if var == self:
                 return cat
        return self

    def can_unify(self, other):
        """ If the variable can be replaced with other
        a substitution is returned.
        """
        if other.is_primitive() or not self._prim_only:
            return [(self,other)]
        return None

    def id(self):
        return self._id

    def __str__(self):
        return "_var" + str(self._id)

@total_ordering
@python_2_unicode_compatible
class Direction(object):
    '''
    Class representing the direction of a function application.
    Also contains maintains information as to which combinators
    may be used with the category.
    '''
    def __init__(self,dir,restrictions):
        self._dir = dir
        self._restrs = restrictions
        self._comparison_key = (dir, tuple(restrictions))

    # Testing the application direction
    def is_forward(self):
        return self._dir == '/'
    def is_backward(self):
        return self._dir == '\\'

    def dir(self):
        return self._dir

    def restrs(self):
        """A list of restrictions on the combinators.
        '.' denotes that permuting operations are disallowed
        ',' denotes that function composition is disallowed
        '_' denotes that the direction has variable restrictions.
        (This is redundant in the current implementation of type-raising)
        """
        return self._restrs

    def is_variable(self):
        return self._restrs == '_'

    # Unification and substitution of variable directions.
    # Used only if type-raising is implemented as a unary rule, as it
    # must inherit restrictions from the argument category.
    def can_unify(self,other):
        if other.is_variable():
            return [('_',self.restrs())]
        elif self.is_variable():
            return [('_',other.restrs())]
        else:
            if self.restrs() == other.restrs():
                return []
        return None

    def substitute(self,subs):
        if not self.is_variable():
            return self

        for (var, restrs) in subs:
            if var == '_':
                return Direction(self._dir,restrs)
        return self

    # Testing permitted combinators
    def can_compose(self):
        return not ',' in self._restrs

    def can_cross(self):
        return not '.' in self._restrs

    def __eq__(self, other):
        return (self.__class__ is other.__class__ and
                self._comparison_key == other._comparison_key)

    def __ne__(self, other):
        return not self == other

    def __lt__(self, other):
        if not isinstance(other, Direction):
            raise_unorderable_types("<", self, other)
        if self.__class__ is other.__class__:
            return self._comparison_key < other._comparison_key
        else:
            return self.__class__.__name__ < other.__class__.__name__

    def __hash__(self):
        try:
            return self._hash
        except AttributeError:
            self._hash = hash(self._comparison_key)
            return self._hash

    def __str__(self):
        r_str = ""
        for r in self._restrs:
            r_str = r_str + "%s" % r
        return "%s%s" % (self._dir, r_str)

    # The negation operator reverses the direction of the application
    def __neg__(self):
        if self._dir == '/':
            return Direction('\\',self._restrs)
        else:
            return Direction('/',self._restrs)


@python_2_unicode_compatible
class PrimitiveCategory(AbstractCCGCategory):
    '''
    Class representing primitive categories.
    Takes a string representation of the category, and a
    list of strings specifying the morphological subcategories.
    '''
    def __init__(self, categ, restrictions=[]):
        self._categ = categ
        self._restrs = restrictions
        self._comparison_key = (categ, tuple(restrictions))

    def is_primitive(self):
        return True

    def is_function(self):
        return False

    def is_var(self):
        return False

    def restrs(self):
        return self._restrs

    def categ(self):
        return self._categ

    # Substitution does nothing to a primitive category
    def substitute(self,subs):
        return self

    # A primitive can be unified with a class of the same
    # base category, given that the other category shares all
    # of its subclasses, or with a variable.
    def can_unify(self,other):
        if not other.is_primitive():
            return None
        if other.is_var():
            return [(other,self)]
        if other.categ() == self.categ():
            for restr in self._restrs:
                if restr not in other.restrs():
                    return None
            return []
        return None

    def __str__(self):
        if self._restrs == []:
            return "%s" % self._categ
        restrictions = "[%s]" % ",".join(unicode_repr(r) for r in self._restrs)
        return "%s%s" % (self._categ, restrictions)


@python_2_unicode_compatible
class FunctionalCategory(AbstractCCGCategory):
    '''
    Class that represents a function application category.
    Consists of argument and result categories, together with
    an application direction.
    '''
    def __init__(self, res, arg, dir):
        self._res = res
        self._arg = arg
        self._dir = dir
        self._comparison_key = (arg, dir, res)

    def is_primitive(self):
        return False

    def is_function(self):
        return True

    def is_var(self):
        return False

    # Substitution returns the category consisting of the
    # substitution applied to each of its constituents.
    def substitute(self,subs):
        sub_res = self._res.substitute(subs)
        sub_dir = self._dir.substitute(subs)
        sub_arg = self._arg.substitute(subs)
        return FunctionalCategory(sub_res,sub_arg,self._dir)

    # A function can unify with another function, so long as its
    # constituents can unify, or with an unrestricted variable.
    def can_unify(self,other):
        if other.is_var():
            return [(other,self)]
        if other.is_function():
            sa = self._res.can_unify(other.res())
            sd = self._dir.can_unify(other.dir())
            if sa is not None and sd is not None:
               sb = self._arg.substitute(sa).can_unify(other.arg().substitute(sa))
               if sb is not None:
                   return sa + sb
        return None

    # Constituent accessors
    def arg(self):
        return self._arg

    def res(self):
        return self._res

    def dir(self):
        return self._dir

    def __str__(self):
        return "(%s%s%s)" % (self._res, self._dir, self._arg)


