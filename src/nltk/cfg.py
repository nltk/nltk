# Natural Language Toolkit: Context Free Grammars
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Steven Bird <sb@ldc.upenn.edu>
#         Edward Loper <edloper@ldc.upenn.edu> (minor additions)
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

"""
Context free grammars.  This module will eventually replace C{Rule}.
"""

from nltk.token import *
from chktype import chktype as _chktype
from chktype import chkclass as _chkclass
from types import SliceType as _SliceType
from types import IntType as _IntType

#################################################################
# Nonterminal
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
        return self._symbol

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
        return '<%s>' % self._symbol

    def __str__(self):
        return str(self._symbol)

#################################################################
# CFGRule and CFG
#################################################################

class CFG_Rule:
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
        Construct a new C{CFG_Rule}.

        @param lhs: The left-hand side of the new C{CFG_Rule}.
        @type lhs: C{Nonterminal}
        @param rhs: The right-hand side of the new C{CFG_Rule}.
        @type rhs: sequence of (C{Nonterminal} and (terminal))
        """
        self._lhs = lhs
        self._rhs = tuple(rhs)

    def lhs(self):
        """
        @return: the left-hand side of this C{CFG_Rule}.
        @rtype: C{Nonterminal}
        """
        return self._lhs

    def rhs(self):
        """
        @return: the right-hand side of this C{CFG_Rule}.
        @rtype: sequence of (C{Nonterminal} and (terminal))
        """
        return self._rhs

    def __str__(self):
        """
        @return: A verbose string representation of the C{Rule}.
        @rtype: C{string}
        """
        str = '<%s> ->' % self._lhs
        for elt in self._rhs:
            if isinstance(elt, Nonterminal): str += ' <%s>' % elt
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
        return (isinstance(other, CFG_Rule) and
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

class CFG:
    """
    A context-free grammar.  A CFG consists of a start state and a set
    of rules.  The set of terminals and nonterminals is implicitly
    specified by the rules.

    If you need efficient key-based access to rules, you can use a
    subclass to implement it.
    """
    def __init__(self, start, rules):
        """
        @param start: The start symbol
        @type start: C{Nonterminal}
        @param rules: The list of rules that defines the grammar
        @type rules: C{list} of C{CFG_Rule}
        """
        self._start = start
        self._rules = rules

    def rules(self):
        return self._rules

    def start(self):
        return self._start

#################################################################
# PCFGs and PCFG rules
#################################################################

from nltk.probability import ProbablisticMixIn
class PCFG_Rule(CFG_Rule, ProbablisticMixIn):
    """
    A probablistic context free grammar rule.  C{PCFG_Rule}s are
    essentially just C{CFG_Rule}s that have probabilities associated
    with them.  These probabilities are used to record how likely it
    is that a given rule will be used.  In particular, the probability
    of a C{PCFG_Rule} records the likelihood that its right-hand side
    is the correct instantiation for any given occurance of its
    left-hand side.

    @see: C{CFG_Rule}
    """
    def __init__(self, p, lhs, *rhs):
        """
        Construct a new C{PCFG_Rule}.

        @param p: The probability of the new C{PCFG_Rule}.
        @param lhs: The left-hand side of the new C{PCFG_Rule}.
        @type lhs: C{Nonterminal}
        @param rhs: The right-hand side of the new C{PCFG_Rule}.
        @type rhs: sequence of (C{Nonterminal} and (terminal))
        """
        ProbablisticMixIn.__init__(self, p)
        CFG_Rule.__init__(self, lhs, *rhs)

    def __str__(self):
        return CFG_Rule.__str__(self) + ' (p=%s)' % self._p

    def __eq__(self, other):
        return (isinstance(other, PCFG_Rule) and
                self._lhs == other._lhs and
                self._rhs == other._rhs and
                self._p == other._p)

    def __hash__(self):
        return hash((self._lhs, self._rhs, self._p))

class PCFG:
    """
    A probablistic context-free grammar.  A PCFG consists of a start
    state and a set of rules.  The set of terminals and nonterminals
    is implicitly specified by the rules.

    PCFG rules should be C{PCFG_Rule}s.  C{PCFG} imposes the
    constraint that the set of rules with any given left-hand-side
    must have probabilities that sum to 1.

    If you need efficient key-based access to rules, you can use a
    subclass to implement it.
    """
    def __init__(self, start, rules):
        """
        @param start: The start symbol
        @type start: C{Nonterminal}
        @param rules: The list of rules that defines the grammar
        @type rules: C{list} of C{PCFG_Rule}
        """
        self._start = start
        self._rules = rules

    def rules(self):
        return self._rules

    def start(self):
        return self._start

#################################################################
# Test code
#################################################################

# Run some quick-and-dirty tests to make sure everything's working
# right.  Eventually we need unit testing..
if __name__ == '__main__':
    (S, VP, NP, PP) = [Nonterminal(s) for s in ('S', 'VP', 'NP', 'PP')]
    rules = [CFG_Rule(S, VP, NP),
             CFG_Rule(VP, 'saw', NP),
             CFG_Rule(VP, 'ate'),
             CFG_Rule(NP, 'the', 'boy'),
             CFG_Rule(PP, 'under', NP),
             CFG_Rule(VP, VP, PP)]

    for rule in rules:
        print '%-18s %r' % (rule,rule)
        hash(rule)

    S2 = Nonterminal('S')
    VP2 = Nonterminal('VP')

    for (A,B) in [(S,S), (S,NP), (PP,VP), (VP2, S), (VP2, VP), (S,S2)]:
        if A == B: print '%3s == %-3s' % (A,B)
        else: print '%3s != %-3s' % (A,B)
             
    prules = [PCFG_Rule(1, S, VP, NP),
              PCFG_Rule(0.4, VP, 'saw', NP),
              PCFG_Rule(0.4, VP, 'ate'),
              PCFG_Rule(0.2, VP, VP, PP),
              PCFG_Rule(0.8, NP, 'the', 'boy'),
              PCFG_Rule(0.2, NP, 'Jack'),
              PCFG_Rule(1.0, PP, 'under', NP)]

    for rule in prules:
        print '%-30s %r' % (rule,rule)
        hash(rule)

                 
