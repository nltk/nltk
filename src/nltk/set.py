#
# Natural Language Toolkit for Python:
# Sets
# Edward Loper
#
# Created [03/16/01 05:28 PM]
# (extracted from nltk.py, created [02/26/01 11:24 PM])
# $Id$
#

from chktype import chktype as _chktype

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
           C{__cmp__}() to always return 0, and M{ej} defined
           C{__cmp__}() to always return -1.
           
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
        self._lst = []
        for elt in lst:
            self.insert(elt)

    def insert(self, elt):
        """
        Adds the specified element to this Set if it is not already
        present.  Formally, add C{elt} to this Set if and
        only if this set contains no element M{ei} such that
        C{elt}=M{e}.

        @param elt: The element to insert into the Set.
        @type elt: Any
        @rtype: None
        """
        if elt not in self._lst:
            self._lst.append(elt)

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
        newSet = apply(Set, self)
        for elt in other._lst:
            newSet.insert(elt)
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
        newSet = apply(Set, self)
        for elt in self._lst:
            if elt not in other._lst:
                newSet._lst.remove(elt)
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
        return intersection(self, other)

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
        return union(self, other)

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
        return elt in self._lst

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
        s._lst = self._lst[:]
        return s

    def __repr__(self):
        """
        Return the formal string representation of this Set.  Sets
        are formally represented by strings of the form:
        C{Set(elt1, elt2, elt3)}

        @return: The formal string representation of this Set.
        @rtype: string
        """
        return 'Set'+`tuple(self._lst)`

    def __str__(self):
        """
        Return the informal string representation of this Set.  Sets
        are informally represented by strings of the form::

          {elt1, elt2, ..., eltn}

        For example, the informal string representation of
        C{Set('apple', 'orange', 'pear')} is::

          {'apple', 'orange', 'pear'}

        @return: The informal string representation of this Set.
        @rtype: string
        """
        return '{'+str(self._lst)[1:-1]+'}'
    
    def __len__(self):
        """
        @return: The number of elements contained in this Set.
        @rtype: int
        """
        return len(self._lst)
    
    def count(self):
        """
        @return: The number of elements contained in this Set.
        @rtype: int
        """
        return len(self._lst)

    def __cmp__(self, other):
        """
        Return 0 if the given object is equal to this Set.  In
        particular, return 0 if and only if C{other} is a
        Set, every member of this set is contained in
        C{other}, and every member of C{other} is
        contained in this Set.  Otherwise, return a non-zero number.
        
        @param other: The object to compare this Set to.
        @type other: any
        @return: 0 if the given object is equal to this Set.
        @rtype: int
        """
        if not isinstance(other, Set): return -1000
        return cmp(self._lst, other._lst)

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
        return self._lst[:]

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
        h = 0
        for elt in self._lst:
            h = hash(elt)/2 + h/2
        return h
