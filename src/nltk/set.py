# Natural Language Toolkit: Sets
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

from chktype import chktype as _chktype
from chktype import chkclass as _chkclass

class Set:
    """
    An unordered container class that contains no duplicate elements.
    In particular, a set contains no elements M{e1} and M{e2} such
    that M{e1=e2}.  Currently, the C{Set} class is given a fairly
    minimal implementation.  However, more members (e.g., to iterate
    over a set) may be defined in the future.

    Although the C{Set} class attempts to ensure that it
    contains no duplicate elements, it can only do so under the
    following circumstances:
    
         - For all elements M{ei}, M{ej} added to the C{Set},
           M{ei=ej} if and only if M{ej=ei}.  This should always be
           the case as long as the elements in the C{Set} use
           well-defined comparison functions.  An example where it
           would not be the case would be if M{ei} defined
           C{__eq__}() to always return 0, and M{ej} defined
           C{__eq__}() to always return 1.
           
         - Mutable elements inserted in the C{Set} are not
           modified after they are inserted.

    If these circumstances are not met, the C{Set} will
    continue to function, but it will no longer guarantee that it
    contains no duplicate elements.
    """
    def __init__(self, *lst):
        """
        Construct a new Set, containing the elements in
        C{lst}.  If C{lst} contains any duplicate
        elements, only one of the elements will be included.  Example
        usage::

          set = Set('apple', 'orange', 'pear')

        @param lst: The elements that will be contained by the new Set.
        @type lst: Any
        """
        self._dict = {}
        for elt in lst:
            self._dict[elt] = 1

    def insert(self, elt):
        """
        Adds the specified element to this Set if it is not already
        present.  Formally, add C{elt} to this Set if and
        only if this set contains no element M{ei} such that
        C{elt}=M{e}.

        @param elt: The element to insert into the Set.
        @type elt: Any
        @rtype: C{boolean}
        @return: C{true} if the C{insert} operation added an element
            to the set; false if C{elt} was already present in the
            set. 
        """
        if self._dict.has_key(elt): return 0
        self._dict[elt] = 1
        return 1

    def union(self, other):
        """
        Return the union of this Set and another Set.  Formally,
        construct and return a new Set containing an element M{e}
        if and only if either C{self} or C{other}
        contain M{e}.
        
        @param other: The Set with which this Set will be unioned.
        @type other: Set
        @return: The union of C{self} and C{other}. 
        @rtype: Set
        """
        _chktype("union", 1, other, (Set,))
        newSet = self.copy()
        newSet._dict.update(other._dict)
        return newSet

    def intersection(self, other):
        """
        Return the intersection of this Set and another Set.
        Formally, construct and return a new Set containing an
        element M{e} if and only if both C{self} and
        C{other} contain M{e}.
        
        @param other: The Set with which this Set will be intersected.
        @type other: Set
        @return: The intersection of C{self} and
                C{other}. 
        @rtype: Set
        """
        _chktype("intersection", 1, other, (Set,))
        newSet = self.copy()
        for elt in self._dict.keys():
            if not other._dict.has_key(elt):
                del newSet._dict[elt]
        return newSet

    def difference(self, other):
        """
        Return the difference between this Set and another Set.
        Formally, construct and return a new Set containing an element
        M{e} if and only if C{self} contains M{e} and C{other} does
        not contain M{e}.

        @param other: The set to subtract from this set.
        @type other: Set
        @return: The difference between this Set and another Set.
        @rtype: Set
        """
        _chktype("difference", 1, other, (Set,))
        newSet = self.copy()
        for elt in self._dict.keys():
            if other._dict.has_key(elt):
                del newSet._dict[elt]
        return newSet

    # set1 & set2
    def __and__(self, other):
        """
        Return the intersection of this Set and another Set.
        Formally, construct and return a new Set containing an
        element M{e} if and only if both C{self} and
        C{other} contain M{e}.

        This method is invoked for expressions of the form::
        
          set1 & set2
        
        @param other: The Set with which this Set will be intersected.
        @type other: Set
        @return: The intersection of C{self} and
                C{other}. 
        @rtype: Set
        """
        return self.intersection(other)

    # set1 | set2
    def __or__(self, other):
        """
        Return the union of this Set and another Set.  Formally,
        construct and return a new Set containing an element M{e}
        if and only if either C{self} or C{other}
        contain M{e}. 
        
        This method is invoked for expressions of the form::
        
          set1 | set2
        
        @param other: The Set with which this Set will be unioned.
        @type other: Set
        @return: The union of C{self} and C{other}. 
        @rtype: Set
        """
        return self.union(other)

    def __minus__(self, other):
        """
        Return the difference between this Set and another Set.
        Formally, construct and return a new Set containing an element
        M{e} if and only if C{self} contains M{e} and C{other} does
        not contain M{e}.

        This method is invoked for expressions of the form::
        
          set1 - set2
        
        @param other: The set to subtract from this set.
        @type other: Set
        @return: The difference between this Set and another Set.
        @rtype: Set
        """
        return self.difference(other)

    def contains(self, elt):
        """
        Return true if this set contains the given element.
        Formally, return true if and only if this Set contains an
        element M{e} such that C{elt}=M{e}.

        @param elt: The element whose presence in the set is to be
               tested.
        @type elt: any
        @return: True if this set contains the given element.
        @rtype: boolean
        """
        return self._dict.has_key(elt)

    # elt in set
    def __contains__(self, elt):
        """
        Return true if this set contains the given element.
        Formally, return true if and only if this Set contains an
        element M{e} such that C{elt}=M{e}.
        
        This method is invoked for expressions of the form::

          elt in set
        
        @param elt: The element whose presence in the set is to be
               tested.
        @type elt: any
        @return: True if this set contains the given element.
        @rtype: boolean
        """
        return self.contains(elt)

    def copy(self):
        """
        Return a copy of this set.  Changes to the copy will not be
        reflected in the original, and vice versa.  However, changes
        to the copy's elements M{will} be reflected in the
        original, and vice versa.

        Currently, Sets are immutable, so this method has little use.
        However, the Set class may eventually be extended to make Sets 
        mutable.
        
        @return: A copy of this set.
        @rtype: Set.
        """
        s=Set()
        s._dict.update(self._dict)
        return s

    def __repr__(self):
        """
        Return the string representation of this Set.  Sets
        are represented by strings of the form::

          {elt1, elt2, ..., eltn}

        For example, the string representation of
        C{Set('apple', 'orange', 'pear')} is::

          {'apple', 'orange', 'pear'}

        @return: The string representation of this Set.
        @rtype: string
        """
        return '{'+str(self._dict.keys())[1:-1]+'}'
    
    def __len__(self):
        """
        @return: The number of elements contained in this Set.
        @rtype: int
        """
        return len(self._dict)
    
    def count(self):
        """
        @return: The number of elements contained in this Set.
        @rtype: int
        """
        return len(self._dict)

    def __eq__(self, other):
        """
        Return 1 if the given object is equal to this Set.  In
        particular, return 1 if and only if C{other} is a
        Set, every member of this set is contained in
        C{other}, and every member of C{other} is
        contained in this Set.  Otherwise, return 0.
        
        @raise TypeError: if C{other} is not a C{Set}.
        @param other: The object to compare this Set to.
        @type other: any
        @return: 1 if the given object is equal to this Set.
        @rtype: int
        """
        _chkclass(self, other)
        return self._dict == other._dict

    def elements(self):
        """
        Return a C{list} of the elements in this
        C{Set}.  Changes to this C{list} will not
        be reflected in the C{Set}, and changes in the
        C{Set} will not be reflected in this
        C{list}.  This function is intended to allow
        iteration over a Set.

        @rtype: list
        @return: A C{list} of the elements in this
            C{Set}.
        """
        # We have to make a copy of the list.
        return self._dict.keys()

    def __hash__(self):
        """
        Return the hash value for this Set.  If two Sets are equal,
        they are guaranteed to have the same hash value.  However, two 
        Sets may have the same hash value and still not be equal.

        @raise TypeError: if some element of the set is not a hashable
               type. 
        @return: The hash value for this Set.
        @rtype: int
        """
        return hash(self._dict)
