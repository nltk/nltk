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
tokens; and the node values are phrasal categories, such as C{NP}
and C{VP}.

The L{CFG} class is used to encode context free grammars.  Each C{CFG}
consists of a start symbol and a set of productions.  The X{start
symbol} specifies the root node value for parse trees.  For example,
the start symbol for syntactic parsing is usually C{S}.  Start
symbols are encoded using the C{Nonterminal} class, which is discussed
below.

A CFG's X{productions} specify what parent-child relationships a parse
tree can contain.  Each production specifies that a particular
node can be the parent of a particular set of children.  For example,
the production C{<S> -> <NP> <VP>} specifies that an C{S} node can
be the parent of an C{NP} node and a C{VP} node.

CFG productions are implemented by the C{CFGProduction} class.
Each C{CFGProduction} consists of a left hand side and a right hand
side.  The X{left hand side} is a C{Nonterminal} that specifies the
node type for a potential parent; and the X{right hand side} is a list
that specifies allowable children for that parent.  This lists
consists of C{Nonterminals} and text types: each C{Nonterminal}
indicates that the corresponding child may be a C{TreeToken} with the
specified node type; and each text type indicates that the
corresponding child may be a C{Token} with the with that type.

The C{Nonterminal} class is used to distinguish node values from leaf
values.  This prevents the grammar from accidentally using a leaf
value (such as the English word "A") as the node of a subtree.  Within
a C{CFG}, all node values are wrapped in the C{Nonterminal} class.
Note, however, that the trees that are specified by the grammar do
B{not} include these C{Nonterminal} wrappers.

CFGs can also be given a more procedural interpretation.  According to
this interpretation, a CFG specifies any tree structure M{tree} that
can be produced by the following procedure:

    - Set M{tree} to the start symbol
    - Repeat until M{tree} contains no more nonterminal leaves:
      - Choose a production M{prod} with whose left hand side
        M{lhs} is a nonterminal leaf of M{tree}.
      - Replace the nonterminal leaf with a subtree, whose node
        value is the value wrapped by the nonterminal M{lhs}, and
        whose children are the right hand side of M{prod}.

The operation of replacing the left hand side (M{lhs}) of a production
with the right hand side (M{rhs}) in a tree (M{tree}) is known as
X{expanding} M{lhs} to M{rhs} in M{tree}.

@group Context Free Grammars: CFG, CFGProduction, Nonterminal
@group Probabilistic CFGs: PCFG, PCFGProduction
@sort: CFG, CFGProduction, Nonterminal, PCFG, PCFGProduction
"""

from nltk.token import *
from nltk.chktype import chktype as _chktype
from nltk.chktype import classeq as _classeq

#################################################################
# Nonterminal
#################################################################

class Nonterminal:
    """
    A non-terminal symbol for a context free grammar.  C{Nonterminal}
    is a wrapper class for node values; it is used by
    C{CFGProduction}s to distinguish node values from leaf values.
    The node value that is wrapped by a C{Nonterminal} is known as its
    X{symbol}.  Symbols are typically strings representing phrasal
    categories (such as C{"NP"} or C{"VP"}).  However, more complex
    symbol types are sometimes used (e.g., for lexicalized grammars).
    Since symbols are node values, they must be immutable and
    hashable.  Two C{Nonterminal}s are considered equal if their
    symbols are equal.

    @see: L{CFG}
    @see: L{CFGProduction}
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
        return (_classeq(self, other) and
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
        @return: A string representation for this C{Nonterminal}.
            The string representation for a C{Nonterminal} whose
            symbol is C{M{s}} is C{<M{s}>}.
        @rtype: C{string}
        """
        return '<%s>' % (self._symbol,)

    def __str__(self):
        """
        @return: A string representation for this C{Nonterminal}.
            The string representation for a C{Nonterminal} whose
            symbol is C{M{s}} is C{M{s}}.
        @rtype: C{string}
        """
        return '%s' % (self._symbol,)

    def __div__(self, rhs):
        """
        @return: A new nonterminal whose symbol is C{M{A}/M{B}}, where
            C{M{A}} is the symbol for this nonterminal, and C{M{B}}
            is the symbol for rhs.
        @rtype: L{Nonterminal}
        @param rhs: The nonterminal used to form the right hand side
            of the new nonterminal.
        @type rhs: L{Nonterminal}
        """
        _chktype(1, rhs, Nonterminal)
        return Nonterminal('%s/%s' % (self._symbol, rhs._symbol))


#################################################################
# CFGProduction and CFG
#################################################################

class CFGProduction:
    """
    A context-free grammar production.  Each production
    expands a single C{Nonterminal} (the X{left-hand side}) to a
    sequence of terminals and C{Nonterminals} (the X{right-hand
    side}).  X{terminals} can be any immutable hashable object that is
    not a C{Nonterminal}.  Typically, terminals are strings
    representing word types, such as C{"dog"} or C{"under"}.

    Abstractly, a CFG production indicates that the right-hand side is
    a possible X{instantiation} of the left-hand side.  CFG
    productions are X{context-free}, in the sense that this
    instantiation should not depend on the context of the left-hand
    side or of the right-hand side.

    @see: L{CFG}
    @see: L{Nonterminal}
    @type _lhs: L{Nonterminal}
    @ivar _lhs: The left-hand side of the production.
    @type _rhs: C{tuple} of (C{Nonterminal} and (terminal))
    @ivar _rhs: The right-hand side of the production.
    """

    def __init__(self, lhs, *rhs):
        """
        Construct a new C{CFGProduction}.

        @param lhs: The left-hand side of the new C{CFGProduction}.
        @type lhs: L{Nonterminal}
        @param rhs: The right-hand side of the new C{CFGProduction}.
        @type rhs: sequence of (C{Nonterminal} and (terminal))
        """
        assert _chktype(1, lhs, Nonterminal)
        self._lhs = lhs
        self._rhs = tuple(rhs)

    def lhs(self):
        """
        @return: the left-hand side of this C{CFGProduction}.
        @rtype: L{Nonterminal}
        """
        return self._lhs

    def rhs(self):
        """
        @return: the right-hand side of this C{CFGProduction}.
        @rtype: sequence of (C{Nonterminal} and (terminal))
        """
        return self._rhs

    def __str__(self):
        """
        @return: A verbose string representation of the
            C{CFGProduction}.
        @rtype: C{string}
        """
        if isinstance(self._lhs, Nonterminal):
            str = '%s ->' % (self._lhs.symbol(),)
        else:
            str = '%r ->' % (self._lhs,)
        for elt in self._rhs:
            if isinstance(elt, Nonterminal):
                str += ' %s' % (elt.symbol(),)
            else:
                str += ' %r' % (elt,)
        return str

    def __repr__(self):
        """
        @return: A concise string representation of the
            C{Production}. 
        @rtype: C{string}
        """
        return '[Production: %s]' % self

    def __eq__(self, other):
        """
        @return: true if this C{CFGProduction} is equal to C{other}.
        @rtype: C{boolean}
        """
        return (_classeq(self, other) and
                self._lhs == other._lhs and
                self._rhs == other._rhs)

    def __ne__(self, other):
        return not (self == other)

    def __hash__(self):
        """
        @return: A hash value for the C{CFGProduction}.
        @rtype: C{int}
        """
        return hash((self._lhs, self._rhs))

class CFG:
    """
    A context-free grammar.  A CFG consists of a start state and a set
    of productions.  The set of terminals and nonterminals is
    implicitly specified by the productions.

    If you need efficient key-based access to productions, you
    can use a subclass to implement it.

    @see: L{CFGProduction}
    @see: L{Nonterminal}
    @see: L{nltk.parser}
    """
    def __init__(self, start, productions):
        """
        Create a new context-free grammar, from the given start state
        and set of C{CFGProduction}s.
        
        @param start: The start symbol
        @type start: L{Nonterminal}
        @param productions: The list of productions that defines the grammar
        @type productions: C{list} of L{CFGProduction}
        """
        assert _chktype(1, start, Nonterminal)
        assert _chktype(2, productions, (CFGProduction,), [CFGProduction])
        self._start = start
        self._productions = tuple(productions)

    def productions(self):
        return self._productions

    def start(self):
        return self._start

    def __repr__(self):
        return '<CFG with %d productions>' % len(self._productions)

    def __str__(self):
        str = 'CFG with %d productions' % len(self._productions)
        str += ' (start state = %s)' % self._start
        for production in self._productions:
            str += '\n    %s' % production
        return str

#################################################################
# PCFGs and PCFG productions
#################################################################

from nltk.probability import ProbabilisticMixIn
class PCFGProduction(CFGProduction, ProbabilisticMixIn):
    """
    A probabilistic context free grammar production.
    C{PCFGProduction}s are essentially just C{CFGProduction}s that
    have probabilities associated with them.  These probabilities are
    used to record how likely it is that a given production will
    be used.  In particular, the probability of a C{PCFGProduction}
    records the likelihood that its right-hand side is the correct
    instantiation for any given occurance of its left-hand side.

    @see: L{CFGProduction}
    """
    def __init__(self, p, lhs, *rhs):
        """
        Construct a new C{PCFGProduction}.

        @param p: The probability of the new C{PCFGProduction}.
        @param lhs: The left-hand side of the new C{PCFGProduction}.
        @type lhs: L{Nonterminal}
        @param rhs: The right-hand side of the new C{PCFGProduction}.
        @type rhs: sequence of (C{Nonterminal} and (terminal))
        """
        ProbabilisticMixIn.__init__(self, p)
        CFGProduction.__init__(self, lhs, *rhs)

    def __str__(self):
        return CFGProduction.__str__(self) + ' (p=%s)' % self._p

    def __eq__(self, other):
        return (_classeq(self, other) and
                self._lhs == other._lhs and
                self._rhs == other._rhs and
                self._p == other._p)

    def __hash__(self):
        return hash((self._lhs, self._rhs, self._p))

class PCFG(CFG):
    """
    A probabilistic context-free grammar.  A PCFG consists of a start
    state and a set of productions.  The set of terminals and
    nonterminals is implicitly specified by the productions.

    PCFG productions should be C{PCFGProduction}s.  C{PCFG} imposes
    the constraint that the set of productions with any given
    left-hand-side must have probabilities that sum to 1.

    If you need efficient key-based access to productions, you can use
    a subclass to implement it.

    @type EPSILON: C{float}
    @cvar EPSILON: The acceptable margin of error for checking that
        productions with a given left-hand side have probabilities
        that sum to 1.
    """
    EPSILON = 0.01
    
    def __init__(self, start, productions):
        """
        Create a new context-free grammar, from the given start state
        and set of C{CFGProduction}s.
        
        @param start: The start symbol
        @type start: L{Nonterminal}
        @param productions: The list of productions that defines the grammar
        @type productions: C{list} of C{PCFGProduction}
        @raise ValueError: if the set of productions with any left-hand-side
            do not have probabilities that sum to a value within
            PCFG.EPSILON of 1.
        """
        assert _chktype(1, start, Nonterminal)
        assert _chktype(2, productions, (PCFGProduction,), [PCFGProduction])
        CFG.__init__(self, start, productions)

        # Make sure that the probabilities sum to one.
        probs = {}
        for production in productions:
            probs[production.lhs()] = (probs.get(production.lhs(), 0) +
                                       production.p())
        for (lhs, p) in probs.items():
            if not ((1-PCFG.EPSILON) < p < (1+PCFG.EPSILON)):
                raise ValueError("CFGProductions for %r do not sum to 1" % lhs)

