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
    """##
    An unordered container class that contains no duplicate elements.
    In particular, a set contains no elements e1 and e2 such that
    e1==e2.  Currently, the <CODE>Set</CODE> class is given a fairly
    minimal implementation.  However, more members (e.g., to iterate
    over a set) may be defined in the future.

    Although the <CODE>Set</CODE> class attempts to ensure that it
    contains no duplicate elements, it can only do so under the
    following circumstances:
    
    <UL>
      <LI> For all elements ei, ej added to the <CODE>Set</CODE>,
           ei==ej if and only if ej==ei.  This should always be the
           case as long as the elements in the <CODE>Set</CODE> use
           well-defined comparison functions.  An example where it
           would not be the case would be if ei defined
           <CODE>__cmp__</CODE>() to always return 0, and ej defined
           <CODE>__cmp__</CODE>() to always return -1.
           
      <LI> Mutable elements inserted in the <CODE>Set</CODE> are not
           modified after they are inserted.
    </UL>

    If these circumstances are not met, the <CODE>Set</CODE> will
    continue to function, but it will no longer guarantee that it
    contains no duplicate elements.
    """
    def __init__(self, *lst):
        """##
        Construct a new Set, containing the elements in
        <CODE>lst</CODE>.  If <CODE>lst</CODE> contains any duplicate
        elements, only one of the elements will be included.  Example
        usage:
          <PRE>
          set = Set('apple', 'orange', 'pear')
          </PRE>
        @param lst The elements that will be contained by the new Set.
        @type lst Any
        """
        self._lst = []
        for elt in lst:
            self.insert(elt)

    def insert(self, elt):
        """##
        Adds the specified element to this Set if it is not already
        present.  Formally, add <CODE>elt</CODE> to this Set if and
        only if this set contains no element <I>ei</I> such that
        <CODE>elt</CODE>==<I>e</I>.

        @param elt The element to insert into the Set.
        @type elt Any
        @returntype None
        """
        if elt not in self._lst:
            self._lst.append(elt)

    def union(self, other):
        """##
        Return the union of this Set and another Set.  Formally,
        construct and return a new Set containing an element <I>e</I>
        if and only if either <CODE>self</CODE> or <CODE>other</CODE>
        contain <I>e</I>.
        
        @param other The Set with which this Set will be unioned.
        @type other Set
        @return The union of <CODE>self</CODE> and <CODE>other</CODE>. 
        @returntype Set
        """
        _chktype("union", 1, other, (Set,))
        newSet = apply(Set, self)
        for elt in other._lst:
            newSet.insert(elt)
        return newSet

    def intersection(self, other):
        """##
        Return the intersection of this Set and another Set.
        Formally, construct and return a new Set containing an
        element <I>e</I> if and only if both <CODE>self</CODE> and
        <CODE>other</CODE> contain <I>e</I>.
        
        @param other The Set with which this Set will be intersected.
        @type other Set
        @return The intersection of <CODE>self</CODE> and
                <CODE>other</CODE>. 
        @returntype Set
        """
        _chktype("intersection", 1, other, (Set,))
        newSet = apply(Set, self)
        for elt in self._lst:
            if elt not in other._lst:
                newSet._lst.remove(elt)
        return newSet

    # set1 & set2
    def __and__(self, other):
        """##
        Return the intersection of this Set and another Set.
        Formally, construct and return a new Set containing an
        element <I>e</I> if and only if both <CODE>self</CODE> and
        <CODE>other</CODE> contain <I>e</I>. <P>

        This method is invoked for expressions of the form:
        <PRE>
          set1 & set2
        </PRE>.
        
        @param other The Set with which this Set will be intersected.
        @type other Set
        @return The intersection of <CODE>self</CODE> and
                <CODE>other</CODE>. 
        @returntype Set
        """
        return intersection(self, other)

    # set1 | set2
    def __or__(self, other):
        """##
        Return the union of this Set and another Set.  Formally,
        construct and return a new Set containing an element <I>e</I>
        if and only if either <CODE>self</CODE> or <CODE>other</CODE>
        contain <I>e</I>. <P>
        
        This method is invoked for expressions of the form:
        <PRE>
          set1 | set2
        </PRE>.
        
        @param other The Set with which this Set will be unioned.
        @type other Set
        @return The union of <CODE>self</CODE> and <CODE>other</CODE>. 
        @returntype Set
        """
        return union(self, other)

    def contains(self, elt):
        """##
        Return true if this set contains the given element.
        Formally, return true if and only if this Set contains an
        element <I>e</I> such that <CODE>elt</CODE>==<I>e</I>.
        
        @param elt The element whose presence in the set is to be
               tested.
        @type elt any
        @return True if this set contains the given element.
        @returntype boolean
        """
        return elt in self._lst

    # elt in set
    def __contains__(self, elt):
        """##
        Return true if this set contains the given element.
        Formally, return true if and only if this Set contains an
        element <I>e</I> such that <CODE>elt</CODE>==<I>e</I>.
        
        This method is invoked for expressions of the form:
        <PRE>
          elt in set
        </PRE>
        
        @param elt The element whose presence in the set is to be
               tested.
        @type elt any
        @return True if this set contains the given element.
        @returntype boolean
        """
        return self.contains(elt)

    def copy(self):
        """##
        Return a copy of this set.  Changes to the copy will not be
        reflected in the original, and vice versa.  However, changes
        to the copy's elements <I>will</I> be reflected in the
        original, and vice versa.  <P>

        Currently, Sets are immutable, so this method has little use.
        However, the Set class may eventually be extended to make Sets 
        mutable.
        
        @return A copy of this set.
        @returntype Set.
        """
        s=Set()
        s._lst = self._lst[:]
        return s

    def __repr__(self):
        """##
        Return the formal string representation of this Set.  Sets
        are formally represented by strings of the form:
        <CODE>Set(elt1, elt2, elt3)</CODE>

        @return The formal string representation of this Set.
        @returntype string
        """
        return 'Set'+`tuple(self._lst)`

    def __str__(self):
        """##
        Return the informal string representation of this Set.  Sets
        are informally represented by strings of the form:
        <PRE>
          {elt1, elt2, ..., eltn}
        </PRE>. 
        For example, the informal string representation of
        <CODE>Set('apple', 'orange', 'pear')</CODE> is:
        <PRE>
          {'apple', 'orange', 'pear'}
        </PRE>

        @return The informal string representation of this Set.
        @returntype string
        """
        return '{'+str(self._lst)[1:-1]+'}'
    
    def __len__(self):
        """##
        Return the number of elements contained in this Set.
        @return The number of elements contained in this Set.
        @returntype int
        """
        return len(self._lst)
    
    def count(self):
        """##
        Return the number of elements contained in this Set.
        @return The number of elements contained in this Set.
        @returntype int
        """
        return len(self._lst)

    def __cmp__(self, other):
        """##
        Return 0 if the given object is equal to this Set.  In
        particular, return 0 if and only if <CODE>other</CODE> is a
        Set, every member of this set is contained in
        <CODE>other</CODE>, and every member of <CODE>other</CODE> is
        contained in this Set.  Otherwise, return a non-zero number.
        
        @param other The object to compare this Set to.
        @type other any
        @return 0 if the given object is equal to this Set.
        @returntype int
        """
        if not isinstance(other, Set): return -1000
        return cmp(self._lst, other._lst)

    def elements(self):
        """##
        Return a <CODE>list</CODE> of the elements in this
        <CODE>Set</CODE>.  Changes to this <CODE>list</CODE> will not
        be reflected in the <CODE>Set</CODE>, and changes in the
        <CODE>Set</CODE> will not be reflected in this
        <CODE>list</CODE>.  This function is intended to allow
        iteration over a Set.

        @returntype list
        @return A <CODE>list</CODE> of the elements in this
        <CODE>Set</CODE>.
        """
        # We have to make a copy of the list.
        return self._lst[:]

    def __hash__(self):
        """##
        Return the hash value for this Set.  If two Sets are equal,
        they are guaranteed to have the same hash value.  However, two 
        Sets may have the same hash value and still not be equal.

        @raise TypeError if some element of the set is not a hashable
               type. 
        @return The hash value for this Set.
        @returntype int
        """
        h = 0
        for elt in self._lst:
            h = hash(elt)/2 + h/2
        return h
