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
Basic data classes for representing context free grammars.  A
X{grammar} specifies which trees can represent the structure of a
given text.  Each of these trees is called a X{parse tree} for the
text (or simply a X{parse}).  In a X{context free} grammar, the set of
parse trees for any piece of a text can depend only on that piece, and
not on the rest of the text (i.e., the piece's context).  Context free
grammars are often used to find possible syntactic structures for
sentences.  In this context, the leaves of a parse tree are word
tokens; and the node values are phrasal categories, such as C{"NP"}
and C{"VP"}.

The C{CFG} class is used to encode context free grammars.  Each C{CFG}
consists of a start symbol and a set of rules.  The X{start symbol}
specifies the root node value for parse trees.  For example, the start
symbol for syntactic parsing is usually C{"S"}.  Start symbols are
encoded using the C{Nonterminal} class, which is discussed below.

A CFG's X{rules} specify what parent-child relationships a parse tree
can contain.  Each rule specifies that a particular node can be the
parent of a particular set of children.  For example, the rule C{"<S>
-> <NP> <VP>"} specifies that an C{"S"} node can be the parent of an
C{"NP"} node and a C{"VP"} node.

CFG rules are implemented by the C{CFG_Rule} class.  Each C{CFG_Rule}
consists of a left hand side and a right hand side.  The X{left hand
side} is a C{Nonterminal} that specifies the node type for a potential
parent; and the X{right hand side} is a list that specifies allowable
children for that parent.  This lists consists of C{Nonterminals} and
text tokens: each C{Nonterminal} indicates that the corresponding
child may be a C{TreeToken} with the specified node type; and each
text type indicates that the corresponding child may be a C{Token}
with the with that type.

The C{Nonterminal} class is used to distinguish node values from leaf
values.  This prevents the grammar from accidentally using a leaf
value (such as the English word "A") as the node of a subtree.  Within
a C{CFG}, all node values are wrapped in the C{Nonterminal} class.
Note, however, that the trees that are specified by the grammar do
E{not} include these C{Nonterminal} wrappers.

CFGs can also be given a more procedural interpretation.  According to
this interpretation, a CFG specifies any tree structure M{tree} that
can be produced by the following procedure:

    - Set M{tree} to the start symbol
    - Repeat until M{tree} contains no more nonterminals:
      - Choose a rule M{rule} with whose left hand side M{lhs} is a
        nonterminal in M{tree}.
      - Replace one occurance of M{lhs} with a subtree, whose node
        value is the value wrapped by the nonterminal M{lhs}, and
        whose children are the right hand side of {rule}.

The operation of replacing the left hand side (M{lhs}) of a rule with
the right hand side (M{rhs}) in a tree (M{tree}) is known as
X{expanding} M{lhs} to M{rhs} in {tree}.

Probablistic CFGs
=================


String Representaitons
======================
A C{CFG_Rule} whose left hand side is C{M{lhs}} and whose right hand
side is C{M{rhs}} is written "C{M{lhs}->M{rhs}}".  A C{Nonterminal}
with symbol M{s} is written "C{<M{s}>}" Thus, for example, the
C{CFG_Rule} that specifies that a tree with node value C{"NP"} can
have children that are subtrees with node values C{"Det"} and C{"N"}
is written::

    <NP> -> Det N

And the rule that specifies that a tree with node value C{"N"} can
have a leaf with text type C{"dog"} is::

    <N> -> 'dog'

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
    A non-terminal symbol for a context free grammar.  C{Nonterminal}
    is a wrapper class for node values; it is used by C{CFG_Rule}s to
    distinguish node values from leaf values.  The node value that is
    wrapped by a C{Nonterminal} is known as its X{symbol}.  Symbols
    are typically strings representing phrasal categories (such as
    C{"NP"} or C{"VP"}).  However, more complex symbol types are
    sometimes used (e.g., for lexicalized grammars).  Since symbols
    are node values, they must be immutable and hashable.  Two
    C{Nonterminal}s are considered equal if their symbols are equal.

    @type _symbol: (any)
    @ivar _symbol: The node value corresponding to this
        C{Nonterminal}.  This value must be immutable and hashable. 
    """
    def __init__(self, symbol):
        """
        Construct a new non-terminal from the given symbol.

        @type symbol: (any)
        @param symbol: The node value corresponding to this
            C{Nonterminal}.  This value must be immutable and
            hashable. 
        """
        self._symbol = symbol

    def symbol(self):
        """
        @return: The node value corresponding to this C{Nonterminal}. 
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
        """
        @return: A verbose representation for this C{Nonterminal}.
            The verbose representation for a C{Nonterminal} whose
            symbol is C{M{s}} is C{<M{s}>}.
        @rtype: C{string}
        """
        return '<%s>' % self._symbol

    def __str__(self):
        """
        TEMPORARY
        """
        return '%s' % self._symbol

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
        str = '%r ->' % self._lhs
        for elt in self._rhs:
            if isinstance(elt, Nonterminal): str += ' %r' % elt
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

                 
