# Natural Language Toolkit: Context Free Grammars
#
# Copyright (C) 2001-2005 University of Pennsylvania
# Author: Steven Bird <sb@ldc.upenn.edu>
#         Edward Loper <edloper@ldc.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#

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

The L{Grammar} class is used to encode context free grammars.  Each C{Grammar}
consists of a start symbol and a set of productions.  The X{start
symbol} specifies the root node value for parse trees.  For example,
the start symbol for syntactic parsing is usually C{S}.  Start
symbols are encoded using the C{Nonterminal} class, which is discussed
below.

A Grammar's X{productions} specify what parent-child relationships a parse
tree can contain.  Each production specifies that a particular
node can be the parent of a particular set of children.  For example,
the production C{<S> -> <NP> <VP>} specifies that an C{S} node can
be the parent of an C{NP} node and a C{VP} node.

Grammar productions are implemented by the C{Production} class.
Each C{Production} consists of a left hand side and a right hand
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
a C{Grammar}, all node values are wrapped in the C{Nonterminal} class.
Note, however, that the trees that are specified by the grammar do
B{not} include these C{Nonterminal} wrappers.

Grammars can also be given a more procedural interpretation.  According to
this interpretation, a Grammar specifies any tree structure M{tree} that
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
"""

from types import InstanceType
import re


def _classeq(instance1, instance2):
    """
    @return: true iff the given objects are instances of the same
        class.
    @rtype: C{bool}
    """
    return (type(instance1) == InstanceType and
            type(instance2) == InstanceType and
            instance1.__class__ == instance2.__class__)


#################################################################
# Nonterminal
#################################################################

class Nonterminal:
    """
    A non-terminal symbol for a context free grammar.  C{Nonterminal}
    is a wrapper class for node values; it is used by
    C{Production}s to distinguish node values from leaf values.
    The node value that is wrapped by a C{Nonterminal} is known as its
    X{symbol}.  Symbols are typically strings representing phrasal
    categories (such as C{"NP"} or C{"VP"}).  However, more complex
    symbol types are sometimes used (e.g., for lexicalized grammars).
    Since symbols are node values, they must be immutable and
    hashable.  Two C{Nonterminal}s are considered equal if their
    symbols are equal.

    @see: L{Grammar}
    @see: L{Production}
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
        return (self is other or _classeq(self, other) and
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
        # [XX] not a good repr!  Token uses this now!!
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
        return Nonterminal('%s/%s' % (self._symbol, rhs._symbol))

def nonterminals(symbols):
    """
    Given a string containing a list of symbol names, return a list of
    C{Nonterminals} constructed from those symbols.  

    @param symbols: The symbol name string.  This string can be
        delimited by either spaces or commas.
    @type symbols: C{string}
    @return: A list of C{Nonterminals} constructed from the symbol
        names given in C{symbols}.  The C{Nonterminals} are sorted
        in the same order as the symbols names.
    @rtype: C{list} of L{Nonterminal}
    """
    if ',' in symbols: symbol_list = symbols.split(',')
    else: symbol_list = symbols.split()
    return [Nonterminal(s.strip()) for s in symbol_list]

#################################################################
# Production and Grammar
#################################################################

class Production:
    """
    A context-free grammar production.  Each production
    expands a single C{Nonterminal} (the X{left-hand side}) to a
    sequence of terminals and C{Nonterminals} (the X{right-hand
    side}).  X{terminals} can be any immutable hashable object that is
    not a C{Nonterminal}.  Typically, terminals are strings
    representing word types, such as C{"dog"} or C{"under"}.

    Abstractly, a Grammar production indicates that the right-hand side is
    a possible X{instantiation} of the left-hand side.  Grammar
    productions are X{context-free}, in the sense that this
    instantiation should not depend on the context of the left-hand
    side or of the right-hand side.

    @see: L{Grammar}
    @see: L{Nonterminal}
    @type _lhs: L{Nonterminal}
    @ivar _lhs: The left-hand side of the production.
    @type _rhs: C{tuple} of (C{Nonterminal} and (terminal))
    @ivar _rhs: The right-hand side of the production.
    """

    def __init__(self, lhs, rhs):
        """
        Construct a new C{Production}.

        @param lhs: The left-hand side of the new C{Production}.
        @type lhs: L{Nonterminal}
        @param rhs: The right-hand side of the new C{Production}.
        @type rhs: sequence of (C{Nonterminal} and (terminal))
        """
        self._lhs = lhs
        self._rhs = tuple(rhs)

    def lhs(self):
        """
        @return: the left-hand side of this C{Production}.
        @rtype: L{Nonterminal}
        """
        return self._lhs

    def rhs(self):
        """
        @return: the right-hand side of this C{Production}.
        @rtype: sequence of (C{Nonterminal} and (terminal))
        """
        return self._rhs

    def __str__(self):
        """
        @return: A verbose string representation of the
            C{Production}.
        @rtype: C{string}
        """
        str = '%s ->' % (self._lhs.symbol(),)
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
        return '%s' % self

    def __eq__(self, other):
        """
        @return: true if this C{Production} is equal to C{other}.
        @rtype: C{boolean}
        """
        return (_classeq(self, other) and
                self._lhs == other._lhs and
                self._rhs == other._rhs)

    def __ne__(self, other):
        return not (self == other)

    def __cmp__(self, other):
        if not _classeq(self, other): return -1
        return cmp((self._lhs, self._rhs), (other._lhs, other._rhs))

    def __hash__(self):
        """
        @return: A hash value for the C{Production}.
        @rtype: C{int}
        """
        return hash((self._lhs, self._rhs))


class Grammar:
    """
    A context-free grammar.  A Grammar consists of a start state and a set
    of productions.  The set of terminals and nonterminals is
    implicitly specified by the productions.

    If you need efficient key-based access to productions, you
    can use a subclass to implement it.
    """
    def __init__(self, start, productions):
        """
        Create a new context-free grammar, from the given start state
        and set of C{Production}s.
        
        @param start: The start symbol
        @type start: L{Nonterminal}
        @param productions: The list of productions that defines the grammar
        @type productions: C{list} of L{Production}
        """
        self._start = start
        self._productions = tuple(productions)

    def productions(self):
        return self._productions

    def start(self):
        return self._start

    def __repr__(self):
        return '<Grammar with %d productions>' % len(self._productions)

    def __str__(self):
        str = 'Grammar with %d productions' % len(self._productions)
        str += ' (start state = %s)' % self._start
        for production in self._productions:
            str += '\n    %s' % production
        return str

_PARSE_RE = re.compile(r'^(\w+)\s*' + r'(?:-+>|=+>)\s*' + 
                       r'(?:("[\w ]+"|\'[\w ]+\'|\w+|\|)\s*)*$')
_SPLIT_RE = re.compile(r'(\w+|-+>|=+>|"[\w ]+"|\'[\w ]+\'|\|)')

def parse_production(s):
    """
    Returns a list of productions
    """
    # Use _PARSE_RE to check that it's valid.
    if not _PARSE_RE.match(s):
        raise ValueError, 'Bad production string'
    # Use _SPLIT_RE to process it.
    pieces = _SPLIT_RE.split(s)
    pieces = [p for i,p in enumerate(pieces) if i%2==1]
    lhside = Nonterminal(pieces[0])
    rhsides = [[]]
    for piece in pieces[2:]:
        if piece == '|':
            rhsides.append([])                     # Vertical bar
        elif piece[0] in ('"', "'"):
            rhsides[-1].append(piece[1:-1])        # Terminal
        else:
            rhsides[-1].append(Nonterminal(piece)) # Nonterminal
    return [Production(lhside, rhside) for rhside in rhsides]

def parse(s):
    productions = []
    for linenum, line in enumerate(s.split('\n')):
        line = line.strip()
        if line.startswith('#') or line=='': continue
        try: productions += parse_production(line)
        except ValueError:
            raise ValueError, 'Unable to parse line %s' % linenum
    if len(productions) == 0:
        raise ValueError, 'No productions found!'
    start = productions[0].lhs()
    return Grammar(start, productions)

#################################################################
# Demonstration
#################################################################

def demo():
    """
    A demonstration showing how C{Grammar}s can be created and used.
    """

    from nltk_lite.parse import cfg

    # Create some nonterminals
    S, NP, VP, PP = cfg.nonterminals('S, NP, VP, PP')
    N, V, P, Det = cfg.nonterminals('N, V, P, Det')
    VP_slash_NP = VP/NP

    print 'Some nonterminals:', [S, NP, VP, PP, N, V, P, Det, VP/NP]
    print '    S.symbol() =>', `S.symbol()`
    print

    # Create some Grammar Productions
    grammar = Grammar.parse("""
    S -> NP VP
    PP -> P NP
    NP -> Det N
    NP -> NP PP
    VP -> V NP
    VP -> VP PP
    Det -> 'a'
    Det -> 'the'
    N -> 'dog'
    N -> 'cat'
    V -> 'chased'
    V -> 'sat'
    P -> 'on'
    P -> 'in'
    """)

    print 'A Grammar:', `grammar`
    print '    grammar.start()       =>', `grammar.start()`
    print '    grammar.productions() =>',
    # Use string.replace(...) is to line-wrap the output.
    print `grammar.productions()`.replace(',', ',\n'+' '*25)
    print

if __name__ == '__main__': demo()
