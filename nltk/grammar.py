# -*- coding: utf-8 -*-
# Natural Language Toolkit: Context Free Grammars
#
# Copyright (C) 2001-2010 NLTK Project
# Author: Steven Bird <sb@csse.unimelb.edu.au>
#         Edward Loper <edloper@seas.upenn.edu>
#         Jason Narad <jason.narad@gmail.com>
#         Peter Ljunglöf <peter.ljunglof@heatherleaf.se>
# URL: <http://www.nltk.org/>
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

The L{ContextFreeGrammar} class is used to encode context free grammars.  Each
C{ContextFreeGrammar} consists of a start symbol and a set of productions.
The X{start symbol} specifies the root node value for parse trees.  For example,
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
a C{ContextFreeGrammar}, all node values are wrapped in the C{Nonterminal} class.
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

from nltk.internals import deprecated
from nltk.compat import all
from nltk.util import transitive_closure, invert_graph

from probability import ImmutableProbabilisticMixIn
from featstruct import FeatStruct, FeatDict, FeatStructParser, SLASH, TYPE

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

    @see: L{ContextFreeGrammar}
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
        try: 
            return cmp(self._symbol, other._symbol)
        except: 
            return -1

    def __hash__(self):
        return self._hash

    def __repr__(self):
        """
        @return: A string representation for this C{Nonterminal}.
        @rtype: C{string}
        """
        if isinstance(self._symbol, basestring):
            return '%s' % (self._symbol,)
        else:
            return '%r' % (self._symbol,)

    def __str__(self):
        """
        @return: A string representation for this C{Nonterminal}.
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

class FeatStructNonterminal(FeatDict, Nonterminal):
    """A feature structure that's also a nonterminal.  It acts as its
    own symbol, and automatically freezes itself when hashed."""
    def __hash__(self):
        self.freeze()
        return FeatStruct.__hash__(self)
    def symbol(self):
        return self

def is_nonterminal(item):
    """
    @return: True if the item is a C{Nonterminal}.
    @rtype: C{bool}
    """
    return isinstance(item, Nonterminal)


#################################################################
# Terminals
#################################################################

def is_terminal(item):
    """
    @return: True if the item is a terminal, which currently is 
    if it is hashable and not a C{Nonterminal}.
    @rtype: C{bool}
    """
    return hasattr(item, '__hash__') and not isinstance(item, Nonterminal)


#################################################################
# Productions
#################################################################

class Production(object):
    """
    A grammar production.  Each production maps a single symbol
    on the X{left-hand side} to a sequence of symbols on the
    X{right-hand side}.  (In the case of context-free productions,
    the left-hand side must be a C{Nonterminal}, and the right-hand
    side is a sequence of terminals and C{Nonterminals}.)
    X{terminals} can be any immutable hashable object that is
    not a C{Nonterminal}.  Typically, terminals are strings
    representing words, such as C{"dog"} or C{"under"}.

    @see: L{ContextFreeGrammar}
    @see: L{DependencyGrammar}
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
    
    def __len__(self):
        """
        @return: the length of the right-hand side.
        @rtype: C{integer}
        """
        return len(self._rhs)
    
    def is_nonlexical(self):
        """
        @return: True if the right-hand side only contains C{Nonterminal}s
        @rtype: C{bool}
        """
        return all([is_nonterminal(n) for n in self._rhs])

    def is_lexical(self):
        """
        @return: True if the right-hand contain at least one terminal token
        @rtype: C{bool}
        """
        return not self.is_nonlexical()

    def __str__(self):
        """
        @return: A verbose string representation of the
            C{Production}.
        @rtype: C{string}
        """
        str = '%r ->' % (self._lhs,)
        for elt in self._rhs:
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


class DependencyProduction(Production):
    """
    A dependency grammar production.  Each production maps a single
    head word to an unordered list of one or more modifier words.
    """
    def __str__(self):
        """
        @return: A verbose string representation of the 
            C{DependencyProduction}.
        @rtype: C{string}
        """
        str = '\'%s\' ->' % (self._lhs,)
        for elt in self._rhs:
                str += ' \'%s\'' % (elt,)
        return str


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
        @param prob: Probability parameters of the new C{WeightedProduction}.
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

#################################################################
# Grammars
#################################################################

class ContextFreeGrammar(object):
    """
    A context-free grammar.  A grammar consists of a start state and 
    a set of productions.  The set of terminals and nonterminals is
    implicitly specified by the productions.

    If you need efficient key-based access to productions, you
    can use a subclass to implement it.
    """
    def __init__(self, start, productions, calculate_leftcorners=True):
        """
        Create a new context-free grammar, from the given start state
        and set of C{Production}s.
        
        @param start: The start symbol
        @type start: L{Nonterminal}
        @param productions: The list of productions that defines the grammar
        @type productions: C{list} of L{Production}
        @param calculate_leftcorners: False if we don't want to calculate the 
        leftcorner relation. In that case, some optimized chart parsers won't work.
        @type calculate_leftcorners: C{bool}
        """
        self._start = start
        self._productions = productions
        self._categories = set(prod.lhs() for prod in productions)
        self._calculate_indexes()
        self._calculate_grammar_forms()
        if calculate_leftcorners:
            self._calculate_leftcorners()
    
    def _calculate_indexes(self):
        self._lhs_index = {}
        self._rhs_index = {}
        self._empty_index = {}
        self._lexical_index = {}
        for prod in self._productions:
            # Left hand side.
            lhs = prod._lhs
            if lhs not in self._lhs_index:
                self._lhs_index[lhs] = []
            self._lhs_index[lhs].append(prod)
            if prod._rhs:
                # First item in right hand side.
                rhs0 = prod._rhs[0]
                if rhs0 not in self._rhs_index:
                    self._rhs_index[rhs0] = []
                self._rhs_index[rhs0].append(prod)
            else:
                # The right hand side is empty.
                self._empty_index[prod.lhs()] = prod
            # Lexical tokens in the right hand side.
            for token in prod._rhs:
                if is_terminal(token):
                    self._lexical_index.setdefault(token, set()).add(prod)
    
    def _calculate_leftcorners(self):
        # Calculate leftcorner relations, for use in optimized parsing.
        self._immediate_leftcorner_categories = dict((cat, set([cat])) for cat in self._categories)
        self._immediate_leftcorner_words = dict((cat, set()) for cat in self._categories)
        for prod in self.productions():
            if len(prod) > 0:
                cat, left = prod.lhs(), prod.rhs()[0]
                if is_nonterminal(left):
                    self._immediate_leftcorner_categories[cat].add(left)
                else:
                    self._immediate_leftcorner_words[cat].add(left)
        
        lc = transitive_closure(self._immediate_leftcorner_categories, reflexive=True)
        self._leftcorners = lc
        self._leftcorner_parents = invert_graph(lc)
        
        nr_leftcorner_categories = sum(map(len, self._immediate_leftcorner_categories.values()))
        nr_leftcorner_words = sum(map(len, self._immediate_leftcorner_words.values()))
        if nr_leftcorner_words > nr_leftcorner_categories > 10000:
            # If the grammar is big, the leftcorner-word dictionary will be too large.
            # In that case it is better to calculate the relation on demand.
            self._leftcorner_words = None
            return
        
        self._leftcorner_words = {}
        for cat, lefts in self._leftcorners.iteritems():
            lc = self._leftcorner_words[cat] = set()
            for left in lefts:
                lc.update(self._immediate_leftcorner_words.get(left, set()))
        
    
    def start(self):
        """
        @return: The start symbol of the grammar
        @rtype: L{Nonterminal}
        """
        return self._start

    # tricky to balance readability and efficiency here!
    # can't use set operations as they don't preserve ordering
    def productions(self, lhs=None, rhs=None, empty=False):
        """
        Return the grammar productions, filtered by the left-hand side
        or the first item in the right-hand side.
        
        @param lhs: Only return productions with the given left-hand side.
        @param rhs: Only return productions with the given first item 
        in the right-hand side.
        @param empty: Only return productions with an empty right-hand side.
        @return: A list of productions matching the given constraints.
        @rtype: C{list} of C{Production}
        """
        if rhs and empty:
            raise ValueError("You cannot select empty and non-empty "
                             "productions at the same time.")
        
        # no constraints so return everything
        if not lhs and not rhs:
            if not empty:
                return self._productions
            else:
                return self._empty_index.values()

        # only lhs specified so look up its index
        elif lhs and not rhs:
            if not empty:
                return self._lhs_index.get(lhs, [])
            elif lhs in self._empty_index:
                return [self._empty_index[lhs]]
            else:
                return []

        # only rhs specified so look up its index
        elif rhs and not lhs:
            return self._rhs_index.get(rhs, [])

        # intersect
        else:
            return [prod for prod in self._lhs_index.get(lhs, [])
                    if prod in self._rhs_index.get(rhs, [])]
    
    def leftcorners(self, cat):
        """
        Return the set of all nonterminals that the given nonterminal 
        can start with, including itself.
        
        This is the reflexive, transitive closure of the immediate
        leftcorner relation:  (A > B)  iff  (A -> B beta)
        
        @param cat: the parent of the leftcorners
        @type cat: C{Nonterminal}
        @return: the set of all leftcorners
        @rtype: C{set} of C{Nonterminal}
        """
        return self._leftcorners.get(cat, set([cat]))
    
    def is_leftcorner(self, cat, left):
        """
        True if left is a leftcorner of cat, where left can be a
        terminal or a nonterminal. 
        
        @param cat: the parent of the leftcorner
        @type cat: C{Nonterminal}
        @param left: the suggested leftcorner
        @type left: C{Terminal} or C{Nonterminal}
        @rtype: C{bool}
        """
        if is_nonterminal(left):
            return left in self.leftcorners(cat)            
        elif self._leftcorner_words:
            return left in self._leftcorner_words.get(cat, set())
        else:
            return any([left in _immediate_leftcorner_words.get(parent, set())
                        for parent in self.leftcorners(cat)])
    
    def leftcorner_parents(self, cat):
        """
        Return the set of all nonterminals for which the given category
        is a left corner. This is the inverse of the leftcorner relation.

        @param cat: the suggested leftcorner
        @type cat: C{Nonterminal}
        @return: the set of all parents to the leftcorner
        @rtype: C{set} of C{Nonterminal}
        """
        return self._leftcorner_parents.get(cat, set([cat]))
    
    def check_coverage(self, tokens):
        """
        Check whether the grammar rules cover the given list of tokens.
        If not, then raise an exception.
        
        @type tokens: C{list} of C{str}
        """
        missing = [tok for tok in tokens 
                   if not self._lexical_index.get(tok)]
        if missing:
            missing = ', '.join('%r' % (w,) for w in missing)
            raise ValueError("Grammar does not cover some of the "
                             "input words: %r." % missing)

    # [xx] does this still get used anywhere, or does check_coverage
    # replace it?
    @deprecated("Use ContextFreeGrammar.check_coverage instead.")
    def covers(self, tokens):
        """
        Check whether the grammar rules cover the given list of tokens.

        @param tokens: the given list of tokens.
        @type tokens: a C{list} of C{string} objects.
        @return: True/False
        """
        for token in tokens:
            if self._lexical_index.get(token):
                return False
        return True
    
    def _calculate_grammar_forms(self):
        """
        Pre-calculate of which form(s) the grammar is.
        """
        prods = self._productions
        self._is_lexical = all([p.is_lexical() for p in prods])
        self._is_nonlexical = all([p.is_nonlexical() for p in prods 
                                  if len(p) != 1])
        self._min_len = min(len(p) for p in prods)
        self._max_len = max(len(p) for p in prods)
        self._all_unary_are_lexical = all([p.is_lexical() for p in prods 
                                          if len(p) == 1])
    
    def is_lexical(self):
        """
        True if all productions are lexicalised.
        """
        return self._is_lexical
    
    def is_nonlexical(self):
        """
        True if all lexical rules are "preterminals", that is,
        unary rules which can be separated in a preprocessing step.
        
        This means that all productions are of the forms
        A -> B1 ... Bn (n>=0), or A -> "s".
        
        Note: is_lexical() and is_nonlexical() are not opposites.
        There are grammars which are neither, and grammars which are both.
        """
        return self._is_nonlexical
    
    def min_len(self):
        """
        The right-hand side length of the shortest grammar production.
        """
        return self._min_len
    
    def max_len(self):
        """
        The right-hand side length of the longest grammar production.
        """
        return self._max_len
    
    def is_nonempty(self):
        """
        True if there are no empty productions.
        """
        return self._min_len > 0
    
    def is_binarised(self):
        """
        True if all productions are at most binary.
        Note that there can still be empty and unary productions.
        """
        return self._max_len <= 2
    
    def is_flexible_chomsky_normal_form(self):
        """
        True if all productions are of the forms
        A -> B C, A -> B, or A -> "s".
        """
        return self.is_nonempty() and self.is_nonlexical() and self.is_binarised()
    
    def is_chomsky_normal_form(self):
        """
        A grammar is of Chomsky normal form if all productions
        are of the forms A -> B C, or A -> "s".
        """
        return (self.is_flexible_chomsky_normal_form() and 
                self._all_unary_are_lexical)

    def __repr__(self):
        return '<Grammar with %d productions>' % len(self._productions)

    def __str__(self):
        str = 'Grammar with %d productions' % len(self._productions)
        str += ' (start state = %r)' % self._start
        for production in self._productions:
            str += '\n    %s' % production
        return str

from nltk.internals import Deprecated
class Grammar(ContextFreeGrammar, Deprecated):
    """Use nltk.ContextFreeGrammar instead."""
        

class FeatureGrammar(ContextFreeGrammar):
    """
    A feature-based grammar.  This is equivalent to a 
    L{ContextFreeGrammar} whose nonterminals are
    L{FeatStructNonterminal}s.

    A grammar consists of a start state and a set of 
    productions.  The set of terminals and nonterminals 
    is implicitly specified by the productions.
    """
    def __init__(self, start, productions):
        """
        Create a new feature-based grammar, from the given start 
        state and set of C{Production}s.
        
        @param start: The start symbol
        @type start: L{FeatStructNonterminal}
        @param productions: The list of productions that defines the grammar
        @type productions: C{list} of L{Production}
        """
        ContextFreeGrammar.__init__(self, start, productions)
    
    # The difference with CFG is that the productions are
    # indexed on the TYPE feature of the nonterminals.
    # This is calculated by the method _get_type_if_possible().
    
    def _calculate_indexes(self):
        self._lhs_index = {}
        self._rhs_index = {}
        self._empty_index = {}
        self._lexical_index = {}
        for prod in self._productions:
            # Left hand side.
            lhs = self._get_type_if_possible(prod._lhs)
            if lhs not in self._lhs_index:
                self._lhs_index[lhs] = []
            self._lhs_index[lhs].append(prod)
            if prod._rhs:
                # First item in right hand side.
                rhs0 = self._get_type_if_possible(prod._rhs[0])
                if rhs0 not in self._rhs_index:
                    self._rhs_index[rhs0] = []
                self._rhs_index[rhs0].append(prod)
            else:
                # The right hand side is empty.
                self._empty_index[self._get_type_if_possible(prod._lhs)] = prod
            # Lexical tokens in the right hand side.
            for token in prod._rhs:
                if is_terminal(token):
                    self._lexical_index.setdefault(token, set()).add(prod)

    def productions(self, lhs=None, rhs=None, empty=False):
        """
        Return the grammar productions, filtered by the left-hand side
        or the first item in the right-hand side.
        
        @param lhs: Only return productions with the given left-hand side.
        @param rhs: Only return productions with the given first item 
        in the right-hand side.
        @param empty: Only return productions with an empty right-hand side.
        @return: A list of productions matching the given constraints.
        @rtype: C{list} of C{Production}
        """
        if rhs and empty:
            raise ValueError("You cannot select empty and non-empty "
                             "productions at the same time.")
        
        # no constraints so return everything
        if not lhs and not rhs:
            if not empty:
                return self._productions
            else:
                return self._empty_index.values()

        # only lhs specified so look up its index
        elif lhs and not rhs:
            if not empty:
                return self._lhs_index.get(self._get_type_if_possible(lhs), [])
            elif lhs in self._empty_index:
                return [self._empty_index[self._get_type_if_possible(lhs)]]
            else:
                return []

        # only rhs specified so look up its index
        elif rhs and not lhs:
            return self._rhs_index.get(self._get_type_if_possible(rhs), [])

        # intersect
        else:
            return [prod for prod in self._lhs_index.get(self._get_type_if_possible(lhs), [])
                    if prod in self._rhs_index.get(self._get_type_if_possible(rhs), [])]
    
    def leftcorners(self, cat):
        """
        Return the set of all words that the given category can start with.
        Also called the I{first set} in compiler construction.
        """
        raise NotImplementedError("Not implemented yet")
    
    def leftcorner_parents(self, cat):
        """
        Return the set of all categories for which the given category
        is a left corner.
        """
        raise NotImplementedError("Not implemented yet")
    
    def _get_type_if_possible(self, item):
        """
        Helper function which returns the C{TYPE} feature of the C{item}, 
        if it exists, otherwise it returns the C{item} itself
        """
        if isinstance(item, dict) and TYPE in item:
            return FeatureValueType(item[TYPE])
        else:
            return item

class FeatureValueType(object):
    """
    A helper class for L{FeatureGrammar}s, designed to be different
    from ordinary strings.  This is to stop the C{FeatStruct}
    C{FOO[]} from being compare equal to the terminal "FOO".
    """
    def __init__(self, value):
        self._value = value
        self._hash = hash(value)
    def __repr__(self):
        return '<%s>' % self.value
    def __cmp__(self, other):
        return cmp(FeatureValueType, type(other)) or cmp(self._value, other._value)
    def __hash__(self):
        return self._hash

class DependencyGrammar(object):
    """
    A dependency grammar.  A DependencyGrammar consists of a set of
    productions.  Each production specifies a head/modifier relationship
    between a pair of words.
    """
    def __init__(self, productions):
        """
        Create a new dependency grammar, from the set of C{Production}s.
        
        @param productions: The list of productions that defines the grammar
        @type productions: C{list} of L{Production}
        """
        self._productions = productions

    def contains(self, head, mod):
        """
        @param head: A head word.
        @type head: C{string}.
        @param mod: A mod word, to test as a modifier of 'head'.
        @type mod: C{string}.

        @return: true if this C{DependencyGrammar} contains a 
            C{DependencyProduction} mapping 'head' to 'mod'.
        @rtype: C{boolean}.
        """
        for production in self._productions:
            for possibleMod in production._rhs:
                if(production._lhs == head and possibleMod == mod):
                    return True
        return False

    def __contains__(self, head, mod):
        """
        @param head: A head word.
        @type head: C{string}.
        @param mod: A mod word, to test as a modifier of 'head'.
        @type mod: C{string}.

        @return: true if this C{DependencyGrammar} contains a 
            C{DependencyProduction} mapping 'head' to 'mod'.
        @rtype: C{boolean}.
        """
        for production in self._productions:
            for possibleMod in production._rhs:
                if(production._lhs == head and possibleMod == mod):
                    return True
        return False

    #   # should be rewritten, the set comp won't work in all comparisons
    # def contains_exactly(self, head, modlist):
    #   for production in self._productions:
    #       if(len(production._rhs) == len(modlist)):
    #           if(production._lhs == head):
    #               set1 = Set(production._rhs)
    #               set2 = Set(modlist)
    #               if(set1 == set2):
    #                   return True
    #   return False


    def __str__(self):
        """
        @return: A verbose string representation of the
            C{DependencyGrammar}
        @rtype: C{string}
        """
        str = 'Dependency grammar with %d productions' % len(self._productions)
        for production in self._productions:
            str += '\n  %s' % production
        return str
            
    def __repr__(self):
        """
        @return: A concise string representation of the
            C{DependencyGrammar}
        """
        return 'Dependency grammar with %d productions' % len(self._productions)
    

class StatisticalDependencyGrammar(object):
    """

    """

    def __init__(self, productions, events, tags):
        self._productions = productions
        self._events = events
        self._tags = tags

    def contains(self, head, mod):
        """
        @param head: A head word.
        @type head: C{string}.
        @param mod: A mod word, to test as a modifier of 'head'.
        @type mod: C{string}.

        @return: true if this C{DependencyGrammar} contains a 
            C{DependencyProduction} mapping 'head' to 'mod'.
        @rtype: C{boolean}.
        """
        for production in self._productions:
            for possibleMod in production._rhs:
                if(production._lhs == head and possibleMod == mod):
                    return True
        return False

    def __str__(self):
        """
        @return: A verbose string representation of the
            C{StatisticalDependencyGrammar}
        @rtype: C{string}
        """
        str = 'Statistical dependency grammar with %d productions' % len(self._productions)
        for production in self._productions:
            str += '\n  %s' % production
        str += '\nEvents:'
        for event in self._events:
            str += '\n  %d:%s' % (self._events[event], event)
        str += '\nTags:'
        for tag_word in self._tags:
            str += '\n %s:\t(%s)' % (tag_word, self._tags[tag_word])
        return str

    def __repr__(self):
        """
        @return: A concise string representation of the
            C{StatisticalDependencyGrammar}
        """
        return 'Statistical Dependency grammar with %d productions' % len(self._productions)


class WeightedGrammar(ContextFreeGrammar):
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

    def __init__(self, start, productions, calculate_leftcorners=True):
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
        @param calculate_leftcorners: False if we don't want to calculate the 
        leftcorner relation. In that case, some optimized chart parsers won't work.
        @type calculate_leftcorners: C{bool}
        """
        ContextFreeGrammar.__init__(self, start, productions, calculate_leftcorners)

        # Make sure that the probabilities sum to one.
        probs = {}
        for production in productions:
            probs[production.lhs()] = (probs.get(production.lhs(), 0) +
                                       production.prob())
        for (lhs, p) in probs.items():
            if not ((1-WeightedGrammar.EPSILON) < p <
                    (1+WeightedGrammar.EPSILON)):
                raise ValueError("Productions for %r do not sum to 1" % lhs)


#################################################################
# Inducing Grammars
#################################################################

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
# Parsing Grammars
#################################################################

# Parsing CFGs

def parse_cfg_production(input):
    """
    @return: a C{list} of context-free L{Production}s.
    """
    return parse_production(input, standard_nonterm_parser)

def parse_cfg(input):
    """
    @return: a L{ContextFreeGrammar}.
    
    @param input: a grammar, either in the form of a string or else 
    as a list of strings.
    """
    start, productions = parse_grammar(input, standard_nonterm_parser)
    return ContextFreeGrammar(start, productions)

# Parsing Probabilistic CFGs

def parse_pcfg_production(input):
    """
    @return: a C{list} of PCFG L{WeightedProduction}s.
    """
    return parse_production(input, standard_nonterm_parser, probabilistic=True)

def parse_pcfg(input):
    """
    @return: a probabilistic L{WeightedGrammar}.
    
    @param input: a grammar, either in the form of a string or else 
    as a list of strings.
    """
    start, productions = parse_grammar(input, standard_nonterm_parser, 
                                       probabilistic=True)
    return WeightedGrammar(start, productions)

# Parsing Feature-based CFGs

def parse_fcfg_production(input, fstruct_parser):
    """
    @return: a C{list} of feature-based L{Production}s.
    """
    return parse_production(input, fstruct_parser)

def parse_fcfg(input, features=None, logic_parser=None, fstruct_parser=None):
    """
    @return: a feature structure based L{FeatureGrammar}.
    
    @param input: a grammar, either in the form of a string or else 
    as a list of strings.
    @param features: a tuple of features (default: SLASH, TYPE)
    @param logic_parser: a parser for lambda-expressions 
                         (default: LogicParser())
    @param fstruct_parser: a feature structure parser 
                           (only if features and logic_parser is None)
    """
    if features is None:
        features = (SLASH, TYPE)
    
    if fstruct_parser is None:
        fstruct_parser = FeatStructParser(features, FeatStructNonterminal, 
                                          logic_parser=logic_parser)
    elif logic_parser is not None:
        raise Exception('\'logic_parser\' and \'fstruct_parser\' must '
                        'not both be set')

    start, productions = parse_grammar(input, fstruct_parser.partial_parse)
    return FeatureGrammar(start, productions)

@deprecated("Use nltk.parse_fcfg() instead.")
def parse_featcfg(input): 
    return parse_fcfg(input)

# Parsing generic grammars

_ARROW_RE = re.compile(r'\s* -> \s*', re.VERBOSE)
_PROBABILITY_RE = re.compile(r'( \[ [\d\.]+ \] ) \s*', re.VERBOSE)
_TERMINAL_RE = re.compile(r'( "[^"]+" | \'[^\']+\' ) \s*', re.VERBOSE)
_DISJUNCTION_RE = re.compile(r'\| \s*', re.VERBOSE)

def parse_production(line, nonterm_parser, probabilistic=False):
    """
    Parse a grammar rule, given as a string, and return
    a list of productions.
    """
    pos = 0
    
    # Parse the left-hand side.
    lhs, pos = nonterm_parser(line, pos)

    # Skip over the arrow.
    m = _ARROW_RE.match(line, pos)
    if not m: raise ValueError('Expected an arrow')
    pos = m.end()

    # Parse the right hand side.
    probabilities = [0.0]
    rhsides = [[]]
    while pos < len(line):
        # Probability.
        m = _PROBABILITY_RE.match(line, pos) 
        if probabilistic and m:
            pos = m.end()
            probabilities[-1] = float(m.group(1)[1:-1])
            if probabilities[-1] > 1.0:
                raise ValueError('Production probability %f, '
                                 'should not be greater than 1.0' %
                                 (probabilities[-1],))

        # String -- add terminal.
        elif line[pos] in "\'\"":
            m = _TERMINAL_RE.match(line, pos)
            if not m: raise ValueError('Unterminated string')
            rhsides[-1].append(m.group(1)[1:-1])
            pos = m.end()

        # Vertical bar -- start new rhside.
        elif line[pos] == '|':
            m = _DISJUNCTION_RE.match(line, pos)
            probabilities.append(0.0)
            rhsides.append([])
            pos = m.end()

        # Anything else -- nonterminal.
        else:
            nonterm, pos = nonterm_parser(line, pos)
            rhsides[-1].append(nonterm)

    if probabilistic:
        return [WeightedProduction(lhs, rhs, prob=probability) 
                for (rhs, probability) in zip(rhsides, probabilities)]
    else:
        return [Production(lhs, rhs) for rhs in rhsides]


def parse_grammar(input, nonterm_parser, probabilistic=False):
    """
    @return: a pair of 
      - a starting category 
      - a list of C{Production}s
    
    @param input: a grammar, either in the form of a string or else 
        as a list of strings.
    @param nonterm_parser: a function for parsing nonterminals.
        It should take a C{(string,position)} as argument and 
        return a C{(nonterminal,position)} as result. 
    @param probabilistic: are the grammar rules probabilistic?
    """
    if isinstance(input, str):
        lines = input.split('\n')
    else:
        lines = input

    start = None
    productions = []
    continue_line = ''
    for linenum, line in enumerate(lines):
        line = continue_line + line.strip()
        if line.startswith('#') or line=='': continue
        if line.endswith('\\'):
            continue_line = line[:-1].rstrip()+' '
            continue
        continue_line = ''
        try:
            if line[0] == '%':
                directive, args = line[1:].split(None, 1)
                if directive == 'start':
                    start, pos = nonterm_parser(args, 0)
                    if pos != len(args):
                        raise ValueError('Bad argument to start directive')
                else:
                    raise ValueError('Bad directive')
            else:
                # expand out the disjunctions on the RHS
                productions += parse_production(line, nonterm_parser, probabilistic)
        except ValueError, e:
            raise ValueError('Unable to parse line %s: %s\n%s' %
                             (linenum+1, line, e))

    if not productions:
        raise ValueError, 'No productions found!'
    if not start:
        start = productions[0].lhs()
    return (start, productions)

_STANDARD_NONTERM_RE = re.compile('( [\w/][\w/^<>-]* ) \s*', re.VERBOSE)

def standard_nonterm_parser(string, pos):
    m = _STANDARD_NONTERM_RE.match(string, pos)
    if not m: raise ValueError('Expected a nonterminal, found: ' 
                               + string[pos:])
    return (Nonterminal(m.group(1)), m.end())


#################################################################
# Parsing Dependency Grammars
#################################################################

_PARSE_DG_RE = re.compile(r'''^\s*                # leading whitespace
                              ('[^']+')\s*        # single-quoted lhs
                              (?:[-=]+>)\s*        # arrow
                              (?:(                 # rhs:
                                   "[^"]+"         # doubled-quoted terminal
                                 | '[^']+'         # single-quoted terminal
                                 | \|              # disjunction
                                 )
                                 \s*)              # trailing space
                                 *$''',            # zero or more copies
                             re.VERBOSE)
_SPLIT_DG_RE = re.compile(r'''('[^']'|[-=]+>|"[^"]+"|'[^']+'|\|)''')

def parse_dependency_grammar(s):
    productions = []
    for linenum, line in enumerate(s.split('\n')):
        line = line.strip()
        if line.startswith('#') or line=='': continue
        try: productions += parse_dependency_production(line)
        except ValueError:
            raise ValueError, 'Unable to parse line %s: %s' % (linenum, line)
    if len(productions) == 0:
        raise ValueError, 'No productions found!'
    return DependencyGrammar(productions)

def parse_dependency_production(s):
    if not _PARSE_DG_RE.match(s):
        raise ValueError, 'Bad production string'
    pieces = _SPLIT_DG_RE.split(s)
    pieces = [p for i,p in enumerate(pieces) if i%2==1]
    lhside = pieces[0].strip('\'\"')
    rhsides = [[]]
    for piece in pieces[2:]:
        if piece == '|':
            rhsides.append([])
        else:
            rhsides[-1].append(piece.strip('\'\"'))
    return [DependencyProduction(lhside, rhside) for rhside in rhsides]


#################################################################
# Demonstration
#################################################################

def cfg_demo():
    """
    A demonstration showing how C{ContextFreeGrammar}s can be created and used.
    """

    from nltk import nonterminals, Production, parse_cfg

    # Create some nonterminals
    S, NP, VP, PP = nonterminals('S, NP, VP, PP')
    N, V, P, Det = nonterminals('N, V, P, Det')
    VP_slash_NP = VP/NP

    print 'Some nonterminals:', [S, NP, VP, PP, N, V, P, Det, VP/NP]
    print '    S.symbol() =>', `S.symbol()`
    print

    print Production(S, [NP])

    # Create some Grammar Productions
    grammar = parse_cfg("""
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
    A demonstration showing how C{WeightedGrammar}s can be created and used.
    """

    from nltk.corpus import treebank
    from nltk import treetransforms
    from nltk import induce_pcfg
    from nltk.parse import pchart

    pcfg_prods = toy_pcfg1.productions()

    pcfg_prod = pcfg_prods[2]
    print 'A PCFG production:', `pcfg_prod`
    print '    pcfg_prod.lhs()  =>', `pcfg_prod.lhs()`
    print '    pcfg_prod.rhs()  =>', `pcfg_prod.rhs()`
    print '    pcfg_prod.prob() =>', `pcfg_prod.prob()`
    print

    grammar = toy_pcfg2
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
    grammar = induce_pcfg(S, productions)
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
    g = nltk.data.load('grammars/book_grammars/feat0.fcfg')
    print g
    print 
    
def dg_demo():
    """
    A demonstration showing the creation and inspection of a 
    C{DependencyGrammar}.
    """
    grammar = parse_dependency_grammar("""
    'scratch' -> 'cats' | 'walls'
    'walls' -> 'the'
    'cats' -> 'the'
    """)
    print grammar
    
def sdg_demo():
    """
    A demonstration of how to read a string representation of 
    a CoNLL format dependency tree.
    """
    dg = DependencyGraph("""
    1   Ze                ze                Pron  Pron  per|3|evofmv|nom                 2   su      _  _
    2   had               heb               V     V     trans|ovt|1of2of3|ev             0   ROOT    _  _
    3   met               met               Prep  Prep  voor                             8   mod     _  _
    4   haar              haar              Pron  Pron  bez|3|ev|neut|attr               5   det     _  _
    5   moeder            moeder            N     N     soort|ev|neut                    3   obj1    _  _
    6   kunnen            kan               V     V     hulp|ott|1of2of3|mv              2   vc      _  _
    7   gaan              ga                V     V     hulp|inf                         6   vc      _  _
    8   winkelen          winkel            V     V     intrans|inf                      11  cnj     _  _
    9   ,                 ,                 Punc  Punc  komma                            8   punct   _  _
    10  zwemmen           zwem              V     V     intrans|inf                      11  cnj     _  _
    11  of                of                Conj  Conj  neven                            7   vc      _  _
    12  terrassen         terras            N     N     soort|mv|neut                    11  cnj     _  _
    13  .                 .                 Punc  Punc  punt                             12  punct   _  _
    """)
    tree = dg.tree()
    print tree.pprint()

def demo():
    cfg_demo()
    pcfg_demo()
    fcfg_demo()
    dg_demo()
    sdg_demo()

if __name__ == '__main__':
    demo()

__all__ = ['Nonterminal', 'nonterminals',
           'Production', 'DependencyProduction', 'WeightedProduction',
           'ContextFreeGrammar', 'WeightedGrammar', 'DependencyGrammar',
           'StatisticalDependencyGrammar', 
           'induce_pcfg', 'parse_cfg', 'parse_cfg_production',
           'parse_pcfg', 'parse_pcfg_production',
           'parse_fcfg', 'parse_fcfg_production',
           'parse_grammar', 'parse_production',
           'parse_dependency_grammar', 'parse_dependency_production',
           'demo', 'cfg_demo', 'pcfg_demo', 'dg_demo', 'sdg_demo',
           'toy_pcfg1', 'toy_pcfg2']

