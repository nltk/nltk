# Natural Language Toolkit: Grammar Rules
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Steven Bird <sb@ldc.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

# To do:
#    - type checks

"""
The rule module defines the C{Rule} class to represent simple
rewriting rules, and the C{DottedRule} class to represented "dotted"
rules used by chart parsers.
"""

from token import *
from string import join
from chktype import chktype as _chktype
from chktype import chkclass as _chkclass
from types import SliceType as _SliceType
from types import IntType as _IntType

class Rule:
    """
    A context-free grammar rule.

    @type _lhs: C{string}
    @ivar _lhs: The left-hand side of the rule, a non-terminal
    @type _rhs: C{tuple}
    @ivar _rhs: The right-hand side of the rule, a list of terminals
          and non-terminals.
    """
    # [edloper 8/14/01] Do we want to require that lhs is a string?
    # Should rhs be a tuple of strings, or what?  At the very least,
    # we should require that terminals and nonterminals be immutable
    # values.  But it might make sense to have generic Types as
    # terminals, not just strings.  Also, how do we distinguish
    # terminals from non-terminals, esp if the terminals *are* strings?
    def __init__(self, lhs, rhs):
        """
        Construct a new C{Rule}.

        @param lhs: The left-hand side of the new C{Rule}.
        @type lhs: C{string}
        @param rhs: The right-hand side of the new C{Rule}.
        @type rhs: C{tuple}
        """
        # add type checks
        self._lhs = lhs
        self._rhs = rhs

    # [edloper 8/14/01] It might be intuitive to add a rhs function
    # (for symmetry).  Also, note that calling self[:] makes an
    # unnecessary copy, where a rhs() method wouldn't..  But that's
    # just a minor efficiency thing.
    def lhs(self):
        """
        @return: the left-hand side of the C{Rule}.
        @rtype: C{string}
        """
        return self._lhs

    def __getitem__(self, index):
        """
        @return: the specified rhs element (or the whole rhs).
        @rtype: C{string} or C{tuple}
        @param index: An integer or slice indicating which elements to 
            return.
        @type index: C{int} or C{slice}
        @raise IndexError: If the specified element does not exist.
        """
        _chktype("Rule.__getitem__", 1, index, (_IntType, _SliceType))
        if type(index) == _SliceType:
            return self._rhs[index.start:index.stop]
        else:
            return self._rhs[index]

    def __len__(self):
        """
        @return: the number of elements on the right-hand side.
        @rtype: C{int}
        """
        return len(self._rhs)

    def pp(self):
        """
        @return: a pretty-printed version of the C{Rule}.
        @rtype: C{string}
        """
        # [edloper 8/14/01] Are we assuming that terminals and
        # nonterminals are all strings?
        return self._lhs + ' -> ' + join(self._rhs)

    def __repr__(self):
        """
        @return: A concise string representation of the C{Rule}.
        @rtype: C{string}
        """
        str = repr(self._lhs) + ' ->'
        for c in self._rhs:
            str += ' '+repr(c)
        return str

    def __str__(self):
        """
        @return: A verbose string representation of the C{Rule}.
        @rtype: C{string}
        """
        return self.pp()

    def __eq__(self, other):
        """
        @return: true if this C{Rule} is equal to C{other}.
        @rtype: C{boolean}
        """
        return (self._lhs == other._lhs and
                self._rhs == other._rhs)

    def __hash__(self):
        """
        @return: A hash value for the C{Rule}.
        @rtype: C{int}
        """
        return hash((self._lhs, self._rhs))

    # [edloper 8/14/01] This is a circular reference, but I guess it's
    # ok.  :)  Otherwise, you could define an external function..
    def dotted(self):
        """
        @return: A C{DottedRule} corresponding to the C{Rule}, with
          the dot in the leftmost position
        @rtype: C{int}
        """
        return DottedRule(self.lhs(), self[:])


class DottedRule(Rule):
    """
    A dotted context-free grammar rule.

    The "dot" is a distinguished position at the boundary of any
    element on the right-hand side of the rule.

    @type _lhs: C{string}
    @ivar _lhs: The left-hand side of the rule, a non-terminal
    @type _rhs: C{tuple}
    @ivar _rhs: The right-hand side of the rule, a list of terminals
          and non-terminals.
    @type _pos: C{int}
    @ivar _pos: The position of the dot.
    """
    # [edloper 8/14/01] Note that DottedRules are mutable.  Thus,
    # avoid using them as keys.  If we implement Sets with
    # dictionaries, avoid putting them in Sets, too.  (The semantics
    # of putting mutable objects in a Set is shady at best, anyway).
    # Alternatively, incr could be redefined to return a new dotted
    # rule, and dotted rules could be declared immutable.  You seem to
    # always do a copy and then an incr, anyway.
    def __init__(self, lhs, rhs, pos=0):
        """
        Construct a new C{DottedRule}.

        @param lhs: The left-hand side of the new C{Rule}.
        @type lhs: C{string}
        @param rhs: The right-hand side of the new C{Rule}.
        @type rhs: C{tuple}
        @param pos: The position of the dot (defaults to zero).
        @type pos: C{int}
        """
        self._lhs = lhs
        self._rhs = rhs
        self._pos = pos

    def pos(self):
        """
        @return: the position of the dot in the C{DottedRule}.
        @rtype: C{int}
        """
        return self._pos

    def next(self):
        """
        @return: the next element on the right-hand side following the dot.
        @rtype: C{string}
        """
        return self[self._pos]

    # [edloper 8/14/01] Would "shift" or some other name be more
    # intuitive?
    def incr(self):
        """
        Move the dot one position to the right.
        @raise IndexError: If the dot position is beyond the end of
            the rule.
        """
        if self._pos < len(self):
            self._pos += 1
        else:
            raise IndexError('Attempt to move dot position past end of rule')

    # [edloper 8/14/01] This method could also use a more intuitive
    # name. 
    def final(self):
        """
        @return: true if the dot is in the final position on the
            right-hand side.
        @rtype: C{boolean}
        """
        return self._pos == len(self)

    def copy(self):
        """
        @return: a copy of the dotted rule
        @rtype: C{DottedRule}
        """
        return DottedRule(self._lhs, self._rhs, self._pos)

    # [edloper 8/14/01] Again, are we assuming that all
    # terminals/nonterminals are strings?
    def pp(self):
        """
        @return: a pretty-printed version of the C{DottedRule}.
        @rtype: C{string}
        """
        drhs = self._rhs[:self._pos] + ('*',) + self._rhs[self._pos:]
        return self._lhs + ' -> ' + join(drhs)

    def __repr__(self):
        """
        @return: A concise string representation of the C{DottedRule}.
        @rtype: C{string}
        """
        return Rule.__repr__(self) + '[' + `self._pos` + ']'

    def __str__(self):
        """
        @return: A verbose string representation of the C{DottedRule}.
        @rtype: C{string}
        """
        return self.pp()

    def __eq__(self, other):
        """
        @return: true if this C{DottedRule} is equal to C{other}.
        @rtype: C{boolean}
        """
        return (Rule.__eq__(self, other) and
                self._pos == other._pos)

    # [edloper 8/14/01] Mutable data structures shouldn't have hash
    # functions; it's misleading.  If you don't define it, it won't
    # let you put them in dictionaries etc (which is a good thing for
    # mutable datatypes).
    def __hash__(self):
        """
        @return: A hash value for the C{DottedRule}.
        @rtype: C{int}
        """
        return hash((self._lhs, self._rhs, self._pos))
