# Natural Language Toolkit: Grammar Rules
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Steven Bird <sb@ldc.upenn.edu>
#         Edward Loper <edloper@ldc.upenn.edu> (minor additions)
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

"""
The rule module defines the C{Rule} class to represent simple
rewriting rules, and the C{DottedRule} class to represented "dotted"
rules used by chart parsers.  Both kinds of rule are immutable.
"""

from nltk.token import *
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

#################################################################
# New rule datatype.
#################################################################

class Nonterminal:
    """
    A non-terminal symbol for a grammar rule.  Non-terminals are used
    to represent elements that can be expanded to zero or more
    terminals.  

    Each non-terminal is based on a X{symbol}, which must be immutable
    and hashable.  Two non-terminals are considered equal if their
    symbols are equal.  Symbols are typically strings representing
    phrasal categories (such as C{"NP"} or C{"VP"}).  However, more
    complex symbol types are sometimes used (e.g., for lexicalized
    grammars).

    @type _symbol: immutable
    @ivar _symbol: This non-terminal's base symbol.  Two nonterminals
        are considered equal if their symbols are equal.
    """
    def __init__(self, symbol):
        """
        Construct a new non-terminal from the given symbol.

        @type symbol: (any)
        @param symbol: The new non-terminal's symbol.  The new
            non-terminal is considered equal to another non-terminal
            if their symbols are equal.
        """
        self._symbol = symbol

    def symbol(self):
        """
        @return: This non-terminal's symbol.
        @rtype: (any)
        """
        return symbol

    def __eq__(self, other):
        """
        @return: True if this non-terminal is equal to C{other}.  In
            particular, return true iff C{other} is a C{Nonterminal}
            and this non-terminal's symbol is equal to C{other}'s
            symbol.
        @rtype: C{boolean}
        """
        return (isinstance(other, Nonterminal) and
                self._symbol == other._symbol)

    def __ne__(self, other):
        """
        @return: True if this non-terminal is not equal to C{other}.  In
            particular, return true iff C{other} is not a C{Nonterminal}
            or this non-terminal's symbol is not equal to C{other}'s
            symbol.
        @rtype: C{boolean}
        """
        return not (self==other)

    def __cmp__(self, other):
        if self == other: return 0
        else: return -1

    def __hash__(self):
        return hash(self._symbol)

    def __repr__(self):
        return 'Nonterminal(%r)' % self._symbol

    def __str__(self):
        return str(self._symbol)

class CFGRule:
    """
    A context-free grammar rule.  Each grammar rule expands a single
    C{Nonterminal} (the X{left-hand side}) to a sequence of terminals
    and C{Nonterminals} (the X{right-hand side}).  X{terminals} can be
    any immutable hashable object that is not a C{Nonterminal}.
    Typically, terminals are strings representing word types, such as
    C{"dog"} or C{"under"}.

    Abstractly, a CFG rule indicates that the right-hand side is a
    possible X{instantiation} of the left-hand side.  CFG rules are
    X{context-free}, in the sense that this instantiation should not
    depend on the context of the left-hand side or of the right-hand
    side.  

    @type _lhs: C{Nonterminal}
    @ivar _lhs: The left-hand side of the rule.
    @type _rhs: sequence of (C{Nonterminal} and (terminal))
    @ivar _rhs: The right-hand side of the rule.
    """

    def __init__(self, lhs, *rhs):
        """
        Construct a new C{CFGRule}.

        @param lhs: The left-hand side of the new C{CFGRule}.
        @type lhs: C{Nonterminal}
        @param rhs: The right-hand side of the new C{CFGRule}.
        @type rhs: sequence of (C{Nonterminal} and (terminal))
        """
        self._lhs = lhs
        self._rhs = tuple(rhs)

    def lhs(self):
        """
        @return: the left-hand side of this C{CFGRule}.
        @rtype: C{Nonterminal}
        """
        return self._lhs

    def rhs(self):
        """
        @return: the right-hand side of this C{CFGRule}.
        @rtype: sequence of (C{Nonterminal} and (terminal))
        """
        return self._rhs

    def __str__(self):
        """
        @return: A verbose string representation of the C{Rule}.
        @rtype: C{string}
        """
        str = '%s ->' % self._lhs
        for elt in self._rhs:
            if isinstance(elt, Nonterminal): str += ' %s' % elt
            else: str += ' %r' % elt
        return str

    def __repr__(self):
        """
        @return: A concise string representation of the C{Rule}.
        @rtype: C{string}
        """
        return '[Rule: %s]' % self

    def __eq__(self, other):
        """
        @return: true if this C{Rule} is equal to C{other}.
        @rtype: C{boolean}
        """
        return (isinstance(other, CFGRule) and
                self._lhs == other._lhs and
                self._rhs == other._rhs)

    def __ne__(self, other):
        return not (self == other)

    def __hash__(self):
        """
        @return: A hash value for the C{Rule}.
        @rtype: C{int}
        """
        return hash((self._lhs, self._rhs))

from nltk.probability import ProbablisticMixIn
class PCFGRule(CFGRule, ProbablisticMixIn):
    """
    A probablistic context free grammar rule.  C{PCFGRule}s are
    essentially just C{CFGRule}s that have probabilities associated
    with them.  These probabilities are used to record how likely it
    is that a given rule will be used.  In particular, the probability
    of a C{PCFGRule} records the likelihood that its right-hand side
    is the correct instantiation for any given occurance of its
    left-hand side.

    @see: C{CFGRule}
    """
    def __init__(self, p, lhs, *rhs):
        """
        Construct a new C{PCFGRule}.

        @param p: The probability of the new C{PCFGRule}.
        @param lhs: The left-hand side of the new C{PCFGRule}.
        @type lhs: C{Nonterminal}
        @param rhs: The right-hand side of the new C{PCFGRule}.
        @type rhs: sequence of (C{Nonterminal} and (terminal))
        """
        ProbablisticMixIn.__init__(self, p)
        CFGRule.__init__(self, lhs, *rhs)

    def __str__(self):
        """
        @return: A verbose string representation of the C{Rule}.
        @rtype: C{string}
        """
        str = '%s ->' % self._lhs
        for elt in self._rhs:
            if isinstance(elt, Nonterminal): str += ' %s' % elt
            else: str += ' %r' % elt
        return str + ' (p=%s)' % self._p

    def __eq__(self, other):
        """
        @return: true if this C{Rule} is equal to C{other}.
        @rtype: C{boolean}
        """
        return (isinstance(other, PCFGRule) and
                self._lhs == other._lhs and
                self._rhs == other._rhs and
                self._p == other._p)

    def __hash__(self):
        """
        @return: A hash value for the C{Rule}.
        @rtype: C{int}
        """
        return hash((self._lhs, self._rhs, self._p))

# Run some quick-and-dirty tests to make sure everything's working
# right.  Eventually we need unit testing..
if __name__ == '__main__':
    (S, VP, NP, PP) = [Nonterminal(s) for s in ('S', 'VP', 'NP', 'PP')]
    rules = [CFGRule(S, VP, NP),
             CFGRule(VP, 'saw', NP),
             CFGRule(VP, 'ate'),
             CFGRule(NP, 'the', 'boy'),
             CFGRule(PP, 'under', NP),
             CFGRule(VP, VP, PP)]

    for rule in rules:
        print '%-18s %r' % (rule,rule)
        hash(rule)

    S2 = Nonterminal('S')
    VP2 = Nonterminal('VP')

    for (A,B) in [(S,S), (S,NP), (PP,VP), (VP2, S), (VP2, VP), (S,S2)]:
        if A == B: print '%3s == %-3s' % (A,B)
        else: print '%3s != %-3s' % (A,B)
             
    prules = [PCFGRule(1, S, VP, NP),
              PCFGRule(0.4, VP, 'saw', NP),
              PCFGRule(0.4, VP, 'ate'),
              PCFGRule(0.2, VP, VP, PP),
              PCFGRule(0.8, NP, 'the', 'boy'),
              PCFGRule(0.2, NP, 'Jack'),
              PCFGRule(1.0, PP, 'under', NP)]

    for rule in prules:
        print '%-30s %r' % (rule,rule)
        hash(rule)

                 
