# Natural Language Toolkit: Grammar Rules
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Steven Bird <sb@ldc.upenn.edu>
#         Edward Loper <edloper@ldc.upenn.edu> (minor additions)
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""
The rule module defines the C{Rule} class to represent simple
rewriting rules, and the C{DottedRule} class to represented "dotted"
rules used by chart parsers.  Both kinds of rule are immutable.
"""

from token import *
from chktype import chktype as _chktype
from chktype import chkclass as _chkclass
from types import SliceType as _SliceType
from types import IntType as _IntType

from string import join

class Rule:
    """
    A context-free grammar rule.

    We do not hardcode any distinction between lexical and grammatical
    rules.  The terminals and non-terminals can be any Python type.

    @type _lhs: C{object}
    @ivar _lhs: The left-hand side of the rule, a non-terminal
    @type _rhs: C{tuple} of C{objects}s
    @ivar _rhs: The right-hand side of the rule, a list of terminals
          and non-terminals.
    """

    def __init__(self, lhs, rhs):
        """
        Construct a new C{Rule}.

        @param lhs: The left-hand side of the new C{Rule}.
        @type lhs: C{object}
        @param rhs: The right-hand side of the new C{Rule}.
        @type rhs: C{tuple} of C{objects}s
        """
        self._lhs = lhs
        self._rhs = rhs

    def lhs(self):
        """
        @return: the left-hand side of the C{Rule}.
        @rtype: C{object}
        """
        return self._lhs

    def rhs(self):
        """
        @return: the right-hand side of the C{Rule}.
        @rtype: C{object}
        """
        return self._rhs

    def __getitem__(self, index):
        """
        @return: the specified rhs element (or the whole rhs).
        @rtype: C{object} or C{tuple} of C{objects}s
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
        return str(self._lhs) + ' -> ' + join([str(s) for s in self._rhs])

    def __repr__(self):
        """
        @return: A concise string representation of the C{Rule}.
        @rtype: C{string}
        """
        return 'Rule(' + repr(self._lhs) + ', ' + repr(self._rhs) + ')'

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

    def __ne__(self, other):
        return not (self == other)

    def __hash__(self):
        """
        @return: A hash value for the C{Rule}.
        @rtype: C{int}
        """
        return hash((self._lhs, self._rhs))

    def drule(self):
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

    @type _lhs: C{object}
    @ivar _lhs: The left-hand side of the rule, a non-terminal
    @type _rhs: C{tuple} of C{object}s
    @ivar _rhs: The right-hand side of the rule, a list of terminals
          and non-terminals.
    @type _pos: C{int}
    @ivar _pos: The position of the dot.
    """

    def __init__(self, lhs, rhs, pos=0):
        """
        Construct a new C{DottedRule}.

        @param lhs: The left-hand side of the new C{Rule}.
        @type lhs: C{object}
        @param rhs: The right-hand side of the new C{Rule}.
        @type rhs: C{tuple} of C{objects}s
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
        @rtype: C{object}
        """
        return self[self._pos]

    def shift(self):
        """
        Shift the dot one position to the right (returns a new
        DottedRule).
        @raise IndexError: If the dot position is beyond the end of
            the rule.
        """
        if self._pos < len(self):
            return DottedRule(self._lhs, self._rhs, self._pos + 1)
        else:
            raise IndexError('Attempt to move dot position past end of rule')

    def complete(self):
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
        return str(self._lhs) + ' -> ' +\
               join([str(item) for item in self._rhs[:self._pos]]) +\
               ' * ' +\
               join([str(item) for item in self._rhs[self._pos:]])

    def __repr__(self):
        """
        @return: A concise string representation of the C{DottedRule}.
        @rtype: C{string}
        """
        return 'Rule(' + repr(self._lhs) + ', ' +\
               repr(self._rhs) + ', ' + `self._pos` + ')'

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

    def __ne__(self, other):
        return not (self == other)

    def __hash__(self):
        """
        @return: A hash value for the C{DottedRule}.
        @rtype: C{int}
        """
        return hash((self._lhs, self._rhs, self._pos))
