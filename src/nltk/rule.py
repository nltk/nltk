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

    def __hash__(self):
        """
        @return: A hash value for the C{DottedRule}.
        @rtype: C{int}
        """
        return hash((self._lhs, self._rhs, self._pos))
