# Natural Language Toolkit: Context Free Grammars
#
# Copyright (C) 2001-2008 University of Pennsylvania
# Author: Steven Bird <sb@csse.unimelb.edu.au>
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

import re
import nltk.featstruct
from nltk.featstruct import FeatStruct, FeatStructParser

#################################################################
# Nonterminal
#################################################################

class Nonterminal(object):
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
        self._hash = hash(symbol)

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
        try:
            return ((self._symbol == other._symbol) \
                    and isinstance(other, self.__class__))
        except AttributeError:
            return False

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
        return self._hash

    def __repr__(self):
        """
        @return: A string representation for this C{Nonterminal}.
            The string representation for a C{Nonterminal} whose
            symbol is C{M{s}} is C{<M{s}>}.
        @rtype: C{string}
        """
        if isinstance(self._symbol, basestring):
            return '<%s>' % (self._symbol,)
        else:
            return '<%r>' % (self._symbol,)

    def __str__(self):
        """
        @return: A string representation for this C{Nonterminal}.
            The string representation for a C{Nonterminal} whose
            symbol is C{M{s}} is C{M{s}}.
        @rtype: C{string}
        """
        if isinstance(self._symbol, basestring):
            return '%s' % (self._symbol,)
        else:
            return '%r' % (self._symbol,)

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

class Production(object):
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
        if isinstance(rhs, (str, unicode)):
            raise TypeError('production right hand side should be a list, '
                            'not a string')
        self._lhs = lhs
        self._rhs = tuple(rhs)
        self._hash = hash((self._lhs, self._rhs))

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
        str = '%s ->' % (self._lhs,)
        for elt in self._rhs:
            if isinstance(elt, Nonterminal):
                str += ' %s' % (elt,)
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
        return (isinstance(other, self.__class__) and
                self._lhs == other._lhs and
                self._rhs == other._rhs)
                 
    def __ne__(self, other):
        return not (self == other)

    def __cmp__(self, other):
        if not isinstance(other, self.__class__): return -1
        return cmp((self._lhs, self._rhs), (other._lhs, other._rhs))

    def __hash__(self):
        """
        @return: A hash value for the C{Production}.
        @rtype: C{int}
        """
        return self._hash


class Grammar(object):
    """
    A context-free grammar.  A Grammar consists of a start state and a set
    of productions.  The set of terminals and nonterminals is
    implicitly specified by the productions.

    If you need efficient key-based access to productions, you
    can use a subclass to implement it.
    """
    def __init__(self, start, productions, lexicon=None):
        """
        Create a new context-free grammar, from the given start state
        and set of C{Production}s.
        
        @param start: The start symbol
        @type start: L{Nonterminal}
        @param productions: The list of productions that defines the grammar
        @type productions: C{list} of L{Production}
        """
        self._start = start
        self._productions = productions
        self._lexicon = lexicon
        self._lhs_index = {}
        self._rhs_index = {}
        for prod in self._productions:
            if prod._lhs not in self._lhs_index:
                self._lhs_index[prod._lhs] = []
            if prod._rhs and prod._rhs[0] not in self._rhs_index:
                self._rhs_index[prod._rhs[0]] = []
            self._lhs_index[prod._lhs].append(prod)
            if prod._rhs:
                self._rhs_index[prod._rhs[0]].append(prod)
        
    def start(self):
        return self._start

    # tricky to balance readability and efficiency here!
    # can't use set operations as they don't preserve ordering
    def productions(self, lhs=None, rhs=None):
        # no constraints so return everything
        if not lhs and not rhs:
            return self._productions

        # only lhs specified so look up its index
        elif lhs and not rhs:
            if lhs in self._lhs_index:
                return self._lhs_index[lhs]
            else:
                return []

        # only rhs specified so look up its index
        elif rhs and not lhs:
            if rhs in self._rhs_index:
                return self._rhs_index[rhs]
            else:
                return []

        # intersect
        else:
            if lhs in self._lhs_index:
                return [prod for prod in self._lhs_index[lhs]
                        if prod in self._rhs_index[rhs]]
            else:
                return []
            
    def lexicon(self):
        return self._lexicon
        

    def check_coverage(self, tokens):
        """
        Check whether the grammar rules cover the given list of tokens.
        If not, then raise an exception.
        """
        missing = [tok for tok in tokens
                   if len(self.productions(rhs=tok))==0]
        if missing:
            missing = ', '.join('%r' % (w,) for w in missing)
            raise ValueError("Grammar does not cover some of the "
                             "input words: %r." +missing)

    # [xx] does this still get used anywhere, or does check_coverage
    # replace it?
    def covers(self, tokens):
        """
        Check whether the grammar rules cover the given list of tokens.

        @param tokens: the given list of tokens.
        @type sentence: a C{list} of C{string} objects.
        @return: True/False
        """
        for token in tokens:
            if len(self.productions(rhs=token)) == 0:
                return False
        return True

    def __repr__(self):
        return '<Grammar with %d productions>' % len(self._productions)

    def __str__(self):
        str = 'Grammar with %d productions' % len(self._productions)
        str += ' (start state = %s)' % self._start
        for production in self._productions:
            str += '\n    %s' % production
        if self._lexicon:
            str += '\n\n    Lexical Entries\n    ==============='
            for word in sorted(self._lexicon):
                str += '\n    %-15s: %s' % (word, self._lexicon[word])
        return str

#################################################################
# Parsing CFGs
#################################################################

_PARSE_CFG_RE = re.compile(r'''^\s*                # leading whitespace
                              (\w+(?:/\w+)?)\s*    # lhs
                              (?:[-=]+>)\s*        # arrow
                              (?:(                 # rhs:
                                   "[^"]+"         # doubled-quoted terminal
                                 | '[^']+'         # single-quoted terminal
                                 | \w+(?:/\w+)?    # non-terminal
                                 | \|              # disjunction
                                 )
                                 \s*)              # trailing space
                                 *$''',            # zero or more copies
                             re.VERBOSE)
_SPLIT_CFG_RE = re.compile(r'''(\w+(?:/\w+)?|[-=]+>|"[^"]+"|'[^']+'|\|)''')


def parse_cfg_production(s):
    """
    Returns a list of productions
    """
    # Use _PARSE_CFG_RE to check that it's valid.
    if not _PARSE_CFG_RE.match(s):
        raise ValueError, 'Bad production string'
    # Use _SPLIT_CFG_RE to process it.
    pieces = _SPLIT_CFG_RE.split(s)
    pieces = [p for i,p in enumerate(pieces) if i%2==1]
    lhside = Nonterminal(pieces[0])
    rhsides = [[]]
    found_terminal = found_non_terminal = False
    for piece in pieces[2:]:
        if piece == '|':
            rhsides.append([])                     # Vertical bar
            found_terminal = found_non_terminal = False
        elif piece[0] in ('"', "'"):
            rhsides[-1].append(piece[1:-1])        # Terminal
            found_terminal = True
        else:
            rhsides[-1].append(Nonterminal(piece)) # Nonterminal
            found_non_terminal = True
        if found_terminal and found_non_terminal:
            raise ValueError('Bad right-hand-side: do not mix '
                             'terminals and non-terminals')
    return [Production(lhside, rhside) for rhside in rhsides]

def parse_cfg(s):
    productions = []
    for linenum, line in enumerate(s.split('\n')):
        line = line.strip()
        if line.startswith('#') or line=='': continue
        try: productions += parse_cfg_production(line)
        except ValueError:
            raise ValueError, 'Unable to parse line %s: %s' % (linenum, line)
    if len(productions) == 0:
        raise ValueError, 'No productions found!'
    start = productions[0].lhs()
    return Grammar(start, productions)


#################################################################
# Weighted Production and Grammar
#################################################################

from nltk.probability import ImmutableProbabilisticMixIn

class WeightedProduction(Production, ImmutableProbabilisticMixIn):
    """
    A probabilistic context free grammar production.
    PCFG C{WeightedProduction}s are essentially just C{Production}s that
    have probabilities associated with them.  These probabilities are
    used to record how likely it is that a given production will
    be used.  In particular, the probability of a C{WeightedProduction}
    records the likelihood that its right-hand side is the correct
    instantiation for any given occurance of its left-hand side.

    @see: L{Production}
    """
    def __init__(self, lhs, rhs, **prob):
        """
        Construct a new C{WeightedProduction}.

        @param lhs: The left-hand side of the new C{WeightedProduction}.
        @type lhs: L{Nonterminal}
        @param rhs: The right-hand side of the new C{WeightedProduction}.
        @type rhs: sequence of (C{Nonterminal} and (terminal))
        @param **prob: Probability parameters of the new C{WeightedProduction}.
        """
        ImmutableProbabilisticMixIn.__init__(self, **prob)
        Production.__init__(self, lhs, rhs)

    def __str__(self):
        return Production.__str__(self) + ' [%s]' % self.prob()

    def __eq__(self, other):
        return (isinstance(other, self.__class__) and
                self._lhs == other._lhs and
                self._rhs == other._rhs and
                self.prob() == other.prob())

    def __ne__(self, other):
        return not (self == other)

    def __hash__(self):
        return hash((self._lhs, self._rhs, self.prob()))

class WeightedGrammar(Grammar):
    """
    A probabilistic context-free grammar.  A Weighted Grammar consists
    of a start state and a set of weighted productions.  The set of
    terminals and nonterminals is implicitly specified by the
    productions.

    PCFG productions should be C{WeightedProduction}s.
    C{WeightedGrammar}s impose the constraint that the set of
    productions with any given left-hand-side must have probabilities
    that sum to 1.

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
        and set of C{WeightedProduction}s.

        @param start: The start symbol
        @type start: L{Nonterminal}
        @param productions: The list of productions that defines the grammar
        @type productions: C{list} of C{Production}
        @raise ValueError: if the set of productions with any left-hand-side
            do not have probabilities that sum to a value within
            EPSILON of 1.
        """
        Grammar.__init__(self, start, productions)

        # Make sure that the probabilities sum to one.
        probs = {}
        for production in productions:
            probs[production.lhs()] = (probs.get(production.lhs(), 0) +
                                       production.prob())
        for (lhs, p) in probs.items():
            if not ((1-WeightedGrammar.EPSILON) < p <
                    (1+WeightedGrammar.EPSILON)):
                raise ValueError("Productions for %r do not sum to 1" % lhs)

# Contributed by Nathan Bodenstab <bodenstab@cslu.ogi.edu>

def induce_pcfg(start, productions):
    """
    Induce a PCFG grammar from a list of productions.

    The probability of a production A -> B C in a PCFG is:

    |                count(A -> B C)
    |  P(B, C | A) = ---------------       where * is any right hand side
    |                 count(A -> *)

    @param start: The start symbol
    @type start: L{Nonterminal}
    @param productions: The list of productions that defines the grammar
    @type productions: C{list} of L{Production}
    """

    # Production count: the number of times a given production occurs
    pcount = {}
    
    # LHS-count: counts the number of times a given lhs occurs
    lcount = {} 

    for prod in productions:
        lcount[prod.lhs()] = lcount.get(prod.lhs(), 0) + 1
        pcount[prod]       = pcount.get(prod,       0) + 1

    prods = [WeightedProduction(p.lhs(), p.rhs(),
                                prob=float(pcount[p]) / lcount[p.lhs()])
             for p in pcount]
    return WeightedGrammar(start, prods)

#################################################################
# Parsing PCFGs
#################################################################

_PARSE_PCFG_RE = re.compile(r'''^\s*                 # leading whitespace
                               (\w+(?:/\w+)?)\s*     # lhs
                               (?:[-=]+>)\s*         # arrow
                               (?:(                  # rhs:
                                    "[^"]+"          # doubled-quoted terminal
                                  | '[^']+'          # single-quoted terminal
                                  | \w+(?:/\w+)?     # non-terminal
                                  | \[[01]?\.\d+\]   # probability
                                  | \|               # disjunction
                                  )
                                  \s*)               # trailing space
                                  *$''',             # zero or more copies
                            re.VERBOSE)
_SPLIT_PCFG_RE = re.compile(r'(\w+(?:/\w+)?|\[[01]?\.\d+\]|[-=]+>|"[^"]+"'
                            r"|'[^']+'|\|)")

def parse_pcfg_production(s):
    """
    Returns a list of PCFG productions
    """
    # Use _PARSE_PCFG_RE to check that it's valid.
    if not _PARSE_PCFG_RE.match(s):
        raise ValueError, 'Bad production string'
    # Use _SPLIT_PCFG_RE to process it.
    pieces = _SPLIT_PCFG_RE.split(s)
    pieces = [p for i,p in enumerate(pieces) if i%2==1]
    lhside = Nonterminal(pieces[0])
    rhsides = [[]]
    probabilities = [0.0]
    found_terminal = found_non_terminal = False
    for piece in pieces[2:]:
        if piece == '|':
            rhsides.append([])                     # Vertical bar
            probabilities.append(0.0)
            found_terminal = found_non_terminal = False
        elif piece[0] in ('"', "'"):
            if found_terminal:
                raise ValueError('Bad right-hand-side: do not use '
                                 'a sequence of terminals')
            rhsides[-1].append(piece[1:-1])        # Terminal
            found_terminal = True
        elif piece[0] in "[":
            probabilities[-1] = float(piece[1:-1]) # Probability
        else:
            rhsides[-1].append(Nonterminal(piece)) # Nonterminal
            found_non_terminal = True
        if found_terminal and found_non_terminal:
            raise ValueError('Bad right-hand-side: do not mix '
                             'terminals and non-terminals')
    return [WeightedProduction(lhside, rhside, prob=probability)
            for (rhside, probability) in zip(rhsides, probabilities)]

def parse_pcfg(s):
    productions = []
    for linenum, line in enumerate(s.split('\n')):
        line = line.strip()
        if line.startswith('#') or line=='': continue
        try: productions += parse_pcfg_production(line)
        except ValueError:
            raise ValueError, 'Unable to parse line %s: %s' % (linenum, line)
    if len(productions) == 0:
        raise ValueError, 'No productions found!'
    start = productions[0].lhs()
    return WeightedGrammar(start, productions)

#################################################################
# Parsing Feature-based CFGs
#################################################################

def earley_lexicon(productions):
    """
    Convert CFG lexical productions into a dictionary indexed 
    by the lexical string. 
    """
    from nltk import defaultdict
    lexicon = defaultdict(list)
    for prod in productions:
        lexicon[prod.rhs()[0]].append(prod.lhs())
    return lexicon

class FeatStructNonterminal(FeatStruct, Nonterminal):
    """A feature structure that's also a nonterminal.  It acts as its
    own symbol, and automatically freezes itself when hashed."""
    def __hash__(self):
        self.freeze()
        return FeatStruct.__hash__(self)
    def symbol(self):
        return self

def parse_fcfg_production(line, fstruct_parser):
    pos = 0
    
    # Parse the left-hand side.
    lhs, pos = fstruct_parser.partial_parse(line, pos)

    # Skip over the arrow.
    m = re.compile('\s*->\s*').match(line, pos)
    if not m: raise ValueError('Expected an arrow')
    pos = m.end()

    # Parse the right hand side.
    rhsides = [[]]
    while pos < len(line):
        # String -- add nonterminal.
        if line[pos] in "\'\"":
            m = re.compile('("[^"]*"|'+"'[^']+')\s*").match(line, pos)
            if not m: raise ValueError('Unterminated string')
            if rhsides[-1] != []: raise ValueError('Bad right-hand-side')
            rhsides[-1].append(m.group(1)[1:-1])
            pos = m.end()

        # Vertical bar -- start new rhside.
        elif line[pos] == '|':
            if len(rhsides[-1])==1 and isinstance(rhsides[-1], basestring):
                raise ValueError('Bad right-hand-side')
            rhsides.append([])
            pos = re.compile('\\|\s*').match(line,pos).end()

        # Anything else -- feature structure nonterminal.
        else:
            fstruct, pos = fstruct_parser.partial_parse(line, pos)
            rhsides[-1].append(fstruct)
            
    return [Production(lhs, rhs) for rhs in rhsides]

def parse_fcfg(input, features=None):
    """
    Return a tuple (list of grammatical productions,
    lexicon dict).
    
    @param input: a grammar, either in the form of a string or else 
    as a list of strings.
    """
    if features is None:
        features = (nltk.featstruct.SLASH, nltk.featstruct.TYPE)
    fstruct_parser = FeatStructParser(features, FeatStructNonterminal)
    if isinstance(input, str):
        lines = input.split('\n')
    else:
        lines = input

    start = None
    productions = []
    for linenum, line in enumerate(lines):
        line = line.strip()
        if line.startswith('#') or line=='': continue
        if line[0] == '%':
            parts = line[1:].split()
            directive, args = line[1:].split(None, 1)
            if directive == 'start':
                start = fstruct_parser.parse(args)
#             elif directive == 'include':
#                 filename = args.strip('"')
#                 # [XX] This is almost certainly a bug: [XX]
#                 self.apply_file(filename)
        else:
            try:
                # expand out the disjunctions on the RHS
                productions += parse_fcfg_production(line, fstruct_parser)
            except ValueError, e:
                raise ValueError('Unable to parse line %s: %s\n%s' %
                                 (linenum+1, line, e))

    if not productions:
        raise ValueError, 'No productions found!'
    grammatical_productions = [prod for prod in productions if not
            (len(prod.rhs()) == 1 and isinstance(prod.rhs()[0], str))]
    lexical_productions = [prod for prod in productions if
            (len(prod.rhs()) == 1 and isinstance(prod.rhs()[0], str))]
    if not start:
        start = productions[0].lhs()
    lexicon = earley_lexicon(lexical_productions)
    grammar = Grammar(start, grammatical_productions, lexicon)
    return grammar

from nltk.internals import deprecated
@deprecated("Use nltk.cfg.parse_fcfg() instead.")
def parse_featcfg(input): 
    return parse_fcfg(input)

#################################################################
# Demonstration
#################################################################

def cfg_demo():
    """
    A demonstration showing how C{Grammar}s can be created and used.
    """

    from nltk import cfg

    # Create some nonterminals
    S, NP, VP, PP = cfg.nonterminals('S, NP, VP, PP')
    N, V, P, Det = cfg.nonterminals('N, V, P, Det')
    VP_slash_NP = VP/NP

    print 'Some nonterminals:', [S, NP, VP, PP, N, V, P, Det, VP/NP]
    print '    S.symbol() =>', `S.symbol()`
    print

    print cfg.Production(S, [NP])

    # Create some Grammar Productions
    grammar = cfg.parse_cfg("""
      S -> NP VP
      PP -> P NP
      NP -> Det N | NP PP
      VP -> V NP | VP PP
      Det -> 'a' | 'the'
      N -> 'dog' | 'cat'
      V -> 'chased' | 'sat'
      P -> 'on' | 'in'
    """)

    print 'A Grammar:', `grammar`
    print '    grammar.start()       =>', `grammar.start()`
    print '    grammar.productions() =>',
    # Use string.replace(...) is to line-wrap the output.
    print `grammar.productions()`.replace(',', ',\n'+' '*25)
    print
    
    print 'Coverage of input words by a grammar:'
    print grammar.covers(['a','dog'])
    print grammar.covers(['a','toy'])

toy_pcfg1 = parse_pcfg("""
    S -> NP VP [1.0]
    NP -> Det N [0.5] | NP PP [0.25] | 'John' [0.1] | 'I' [0.15]
    Det -> 'the' [0.8] | 'my' [0.2]
    N -> 'man' [0.5] | 'telescope' [0.5]
    VP -> VP PP [0.1] | V NP [0.7] | V [0.2]
    V -> 'ate' [0.35] | 'saw' [0.65]
    PP -> P NP [1.0]
    P -> 'with' [0.61] | 'under' [0.39]
    """)

toy_pcfg2 = parse_pcfg("""
    S    -> NP VP         [1.0]
    VP   -> V NP          [.59]
    VP   -> V             [.40]
    VP   -> VP PP         [.01]
    NP   -> Det N         [.41]
    NP   -> Name          [.28]
    NP   -> NP PP         [.31]
    PP   -> P NP          [1.0]
    V    -> 'saw'         [.21]
    V    -> 'ate'         [.51]
    V    -> 'ran'         [.28]
    N    -> 'boy'         [.11]
    N    -> 'cookie'      [.12]
    N    -> 'table'       [.13]
    N    -> 'telescope'   [.14]
    N    -> 'hill'        [.5]
    Name -> 'Jack'        [.52]
    Name -> 'Bob'         [.48]
    P    -> 'with'        [.61]
    P    -> 'under'       [.39]
    Det  -> 'the'         [.41]
    Det  -> 'a'           [.31]
    Det  -> 'my'          [.28]
    """)

def pcfg_demo():
    """
    A demonstration showing how PCFG C{Grammar}s can be created and used.
    """

    from nltk.corpus import treebank
    from nltk import cfg, treetransforms
    from nltk.parse import pchart

    pcfg_prods = cfg.toy_pcfg1.productions()

    pcfg_prod = pcfg_prods[2]
    print 'A PCFG production:', `pcfg_prod`
    print '    pcfg_prod.lhs()  =>', `pcfg_prod.lhs()`
    print '    pcfg_prod.rhs()  =>', `pcfg_prod.rhs()`
    print '    pcfg_prod.prob() =>', `pcfg_prod.prob()`
    print

    grammar = cfg.toy_pcfg2
    print 'A PCFG grammar:', `grammar`
    print '    grammar.start()       =>', `grammar.start()`
    print '    grammar.productions() =>',
    # Use string.replace(...) is to line-wrap the output.
    print `grammar.productions()`.replace(',', ',\n'+' '*26)
    print

    print 'Coverage of input words by a grammar:'
    print grammar.covers(['a','boy'])
    print grammar.covers(['a','girl'])

    # extract productions from three trees and induce the PCFG
    print "Induce PCFG grammar from treebank data:"

    productions = []
    for item in treebank.items[:2]:
        for tree in treebank.parsed_sents(item):
            # perform optional tree transformations, e.g.:
            tree.collapse_unary(collapsePOS = False)
            tree.chomsky_normal_form(horzMarkov = 2)

            productions += tree.productions()

    S = Nonterminal('S')
    grammar = cfg.induce_pcfg(S, productions)
    print grammar
    print

    print "Parse sentence using induced grammar:"

    parser = pchart.InsideChartParser(grammar)
    parser.trace(3)

    # doesn't work as tokens are different:
    #sent = treebank.tokenized('wsj_0001.mrg')[0]

    sent = treebank.parsed_sents('wsj_0001.mrg')[0].leaves()
    print sent
    for parse in parser.nbest_parse(sent):
        print parse

def fcfg_demo():
    import nltk.data
    g = nltk.data.load('grammars/feat0.fcfg')
    print g
    print 
    
def demo():
    cfg_demo()
    pcfg_demo()
    fcfg_demo()

if __name__ == '__main__':
    demo()

__all__ = ['Grammar', 'ImmutableProbabilisticMixIn', 'Nonterminal',
           'Production', 'WeightedGrammar', 'WeightedProduction',
           'cfg_demo', 'demo', 'induce_pcfg', 'nonterminals', 'parse_cfg',
           'parse_cfg_production', 'parse_pcfg', 'parse_fcfg',
           'parse_pcfg_production', 'pcfg_demo', 'toy_pcfg1', 'toy_pcfg2']
