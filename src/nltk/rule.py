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
from chktype import chktype as _chktype
from chktype import chkclass as _chkclass
from types import SliceType as _SliceType
from types import IntType as _IntType

class Rule:
    """
    A context-free grammar rule.

    @type _lhs: C{string}
    @ivar _lhs: The left-hand side of the rule, a non-terminal
    @type _rhs: C{tuple} of C{string}s
    @ivar _rhs: The right-hand side of the rule, a list of terminals
          and non-terminals.
    """
    # [edloper 8/14/01] Do we want to require that lhs is a string?
    # Should rhs be a tuple of strings, or what?  At the very least,
    # we should require that terminals and nonterminals be immutable
    # values.  But it might make sense to have generic Types as
    # terminals, not just strings.  Also, how do we distinguish
    # terminals from non-terminals, esp if the terminals *are* strings?
    # [edloper 09/27/01] This isn't a problem if we assume that
    # everything Rule is either a lexical rule or a non-lexical rule,
    # and non-lexical rules have only nonterminals on the right..  But
    # although that's fine for chart parsing, it might be annoying
    # later if we decide to use Rule in other contexts..

    def __init__(self, lhs, rhs):
        """
        Construct a new C{Rule}.

        @param lhs: The left-hand side of the new C{Rule}.
        @type lhs: C{string}
        @param rhs: The right-hand side of the new C{Rule}.
        @type rhs: C{tuple} of C{string}s
        """
        # add type checks?
        self._lhs = lhs
        self._rhs = rhs

    def lhs(self):
        """
        @return: the left-hand side of the C{Rule}.
        @rtype: C{string}
        """
        return self._lhs

    def rhs(self):
        """
        @return: the right-hand side of the C{Rule}.
        @rtype: C{string}
        """
        return self._rhs

    def __getitem__(self, index):
        """
        @return: the specified rhs element (or the whole rhs).
        @rtype: C{string} or C{tuple} of C{string}s
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
        return str(self._lhs) + ' -> ' + ''.join([str(s) for s in self._rhs])

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

    def __ne__(self, other):
        return not (self == other)

    def __hash__(self):
        """
        @return: A hash value for the C{Rule}.
        @rtype: C{int}
        """
        return hash((self._lhs, self._rhs))

    # [edloper 8/14/01] This is a circular reference, but I guess it's
    # ok.  :)  Otherwise, you could define an external function..
    # [sb 8/14/01] Nothing wrong with the circular dependency, though
    # I'd actually prefer this to be a second initializer in
    # DottedRule - i.e. initializing a DottedRule from a Rule.
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
    @type _rhs: C{tuple} of C{string}s
    @ivar _rhs: The right-hand side of the rule, a list of terminals
          and non-terminals.
    @type _pos: C{int}
    @ivar _pos: The position of the dot.
    """
    # [edloper 09/27/01] DottedRule is now immutable.
    def __init__(self, lhs, rhs, pos=0):
        """
        Construct a new C{DottedRule}.

        @param lhs: The left-hand side of the new C{Rule}.
        @type lhs: C{string}
        @param rhs: The right-hand side of the new C{Rule}.
        @type rhs: C{tuple} of C{string}s
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

    # [edloper 8/14/01] Again, are we assuming that all
    # terminals/nonterminals are strings?
    def pp(self):
        """
        @return: a pretty-printed version of the C{DottedRule}.
        @rtype: C{string}
        """
        drhs = self._rhs[:self._pos] + ('*',) + self._rhs[self._pos:]
        return self._lhs + ' -> ' + ''.join(drhs)

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

    def __ne__(self, other):
        return not (self == other)

    def __hash__(self):
        """
        @return: A hash value for the C{DottedRule}.
        @rtype: C{int}
        """
        return hash((self._lhs, self._rhs, self._pos))
