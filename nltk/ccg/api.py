# Natural Language Toolkit: CCG Categories
#
# Copyright (C) 2001-2012 NLTK Project
# Author: Graeme Gange <ggange@csse.unimelb.edu.au>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

class AbstractCCGCategory(object):
    '''
    Interface for categories in combinatory grammars.
    '''

    # Returns true if the category is primitive
    def is_primitive(self):
        raise AssertionError, 'AbstractCCGCategory is an abstract interface'

    # Returns true if the category is a function application
    def is_function(self):
        raise AssertionError, 'AbstractCCGCategory is an abstract interface'

    # Returns true if the category is a variable
    def is_var(self):
        raise AssertionError, 'AbstractCCGCategory is an abstract interface'

    # Takes a set of (var, category) substitutions, and replaces every
    # occurrence of the variable with the corresponding category
    def substitute(self,substitutions):
        raise AssertionError, 'AbstractCCGCategory is an abstract interface'

    # Determines whether two categories can be unified.
    #  - Returns None if they cannot be unified
    #  - Returns a list of necessary substitutions if they can.'''
    def can_unify(self,other):
        raise AssertionError, 'AbstractCCGCategory is an abstract interface'

    # Utility functions: comparison, strings and hashing.
    def __cmp__(self,other):
        raise AssertionError, 'AbstractCCGCategory is an abstract interface'

    def __str__(self):
        raise AssertionError, 'AbstractCCGCategory is an abstract interface'

    def __hash__(self):
        raise AssertionError, 'AbstractCCGCategory is an abstract interface'


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

    def __cmp__(self,other):
        if not isinstance(other,CCGVar):
            return -1
        return cmp(self._id,other.id())

    def __hash__(self):
        return hash(self._id)
    def __str__(self):
        return "_var" + str(self._id)

class Direction:
    '''
    Class representing the direction of a function application.
    Also contains maintains information as to which combinators
    may be used with the category.
    '''
    def __init__(self,dir,restrictions):
        self._dir = dir
        self._restrs = restrictions

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
            if var is '_':
                return Direction(self._dir,restrs)
        return self

    # Testing permitted combinators
    def can_compose(self):
        return not ',' in self._restrs

    def can_cross(self):
        return not '.' in self._restrs

    def __cmp__(self,other):
        return cmp((self._dir,self._restrs), (other.dir(),other.restrs()))
        return res

    def __hash__(self):
      return hash((self._dir,tuple(self._restrs)))

    def __str__(self):
        r_str = ""
        for r in self._restrs:
            r_str = r_str + str(r)
        return str(self._dir) + r_str

    # The negation operator reverses the direction of the application
    def __neg__(self):
        if self._dir == '/':
            return Direction('\\',self._restrs)
        else:
            return Direction('/',self._restrs)


class PrimitiveCategory(AbstractCCGCategory):
    '''
    Class representing primitive categories.
    Takes a string representation of the category, and a
    list of strings specifying the morphological subcategories.
    '''
    def __init__(self,categ,restrictions=[]):
        self._categ = categ
        self._restrs = restrictions

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

    def __cmp__(self,other):
        if not isinstance(other,PrimitiveCategory):
            return -1
        return cmp((self._categ,self.restrs()),
                    (other.categ(),other.restrs()))

    def __hash__(self):
        return hash((self._categ,tuple(self._restrs)))

    def __str__(self):
        if self._restrs == []:
            return str(self._categ)
        return str(self._categ) + str(self._restrs)

class FunctionalCategory(AbstractCCGCategory):
    '''
    Class that represents a function application category.
    Consists of argument and result categories, together with
    an application direction.
    '''
    def __init__(self,res,arg,dir,):
        self._res = res
        self._arg = arg
        self._dir = dir

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

    def __cmp__(self,other):
        if not isinstance(other,FunctionalCategory):
            return -1
        return cmp((self._arg,self._dir,self._res),
                    (other.arg(),other.dir(),other.res()))
    def __hash__(self):
        return hash((self._arg,self._dir,self._res))

    def __str__(self):
        return "(" + str(self._res) + str(self._dir) + str(self._arg) + ")"
