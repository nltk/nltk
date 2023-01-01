# Natural Language Toolkit: Context Free Grammars
#
# Copyright (C) 2001-2022 NLTK Project
# Author: Steven Bird <stevenbird1@gmail.com>
#         Edward Loper <edloper@gmail.com>
#         Jason Narad <jason.narad@gmail.com>
#         Peter Ljunglöf <peter.ljunglof@heatherleaf.se>
#         Tom Aarsen <>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
#

"""
Basic data classes for representing context free grammars.  A
"grammar" specifies which trees can represent the structure of a
given text.  Each of these trees is called a "parse tree" for the
text (or simply a "parse").  In a "context free" grammar, the set of
parse trees for any piece of a text can depend only on that piece, and
not on the rest of the text (i.e., the piece's context).  Context free
grammars are often used to find possible syntactic structures for
sentences.  In this context, the leaves of a parse tree are word
tokens; and the node values are phrasal categories, such as ``NP``
and ``VP``.

The ``CFG`` class is used to encode context free grammars.  Each
``CFG`` consists of a start symbol and a set of productions.
The "start symbol" specifies the root node value for parse trees.  For example,
the start symbol for syntactic parsing is usually ``S``.  Start
symbols are encoded using the ``Nonterminal`` class, which is discussed
below.

A Grammar's "productions" specify what parent-child relationships a parse
tree can contain.  Each production specifies that a particular
node can be the parent of a particular set of children.  For example,
the production ``<S> -> <NP> <VP>`` specifies that an ``S`` node can
be the parent of an ``NP`` node and a ``VP`` node.

Grammar productions are implemented by the ``Production`` class.
Each ``Production`` consists of a left hand side and a right hand
side.  The "left hand side" is a ``Nonterminal`` that specifies the
node type for a potential parent; and the "right hand side" is a list
that specifies allowable children for that parent.  This lists
consists of ``Nonterminals`` and text types: each ``Nonterminal``
indicates that the corresponding child may be a ``TreeToken`` with the
specified node type; and each text type indicates that the
corresponding child may be a ``Token`` with the with that type.

The ``Nonterminal`` class is used to distinguish node values from leaf
values.  This prevents the grammar from accidentally using a leaf
value (such as the English word "A") as the node of a subtree.  Within
a ``CFG``, all node values are wrapped in the ``Nonterminal``
class. Note, however, that the trees that are specified by the grammar do
*not* include these ``Nonterminal`` wrappers.

Grammars can also be given a more procedural interpretation.  According to
this interpretation, a Grammar specifies any tree structure *tree* that
can be produced by the following procedure:

| Set tree to the start symbol
| Repeat until tree contains no more nonterminal leaves:
|   Choose a production prod with whose left hand side
|     lhs is a nonterminal leaf of tree.
|   Replace the nonterminal leaf with a subtree, whose node
|     value is the value wrapped by the nonterminal lhs, and
|     whose children are the right hand side of prod.

The operation of replacing the left hand side (*lhs*) of a production
with the right hand side (*rhs*) in a tree (*tree*) is known as
"expanding" *lhs* to *rhs* in *tree*.
"""
import itertools
import re
from functools import total_ordering

from nltk.featstruct import SLASH, TYPE, FeatDict, FeatStruct, FeatStructReader
from nltk.internals import raise_unorderable_types
from nltk.probability import ImmutableProbabilisticMixIn
from nltk.util import invert_graph, transitive_closure

#################################################################
# Nonterminal
#################################################################


@total_ordering
class Nonterminal:
    """
    A non-terminal symbol for a context free grammar.  ``Nonterminal``
    is a wrapper class for node values; it is used by ``Production``
    objects to distinguish node values from leaf values.
    The node value that is wrapped by a ``Nonterminal`` is known as its
    "symbol".  Symbols are typically strings representing phrasal
    categories (such as ``"NP"`` or ``"VP"``).  However, more complex
    symbol types are sometimes used (e.g., for lexicalized grammars).
    Since symbols are node values, they must be immutable and
    hashable.  Two ``Nonterminals`` are considered equal if their
    symbols are equal.

    :see: ``CFG``, ``Production``
    :type _symbol: any
    :ivar _symbol: The node value corresponding to this
        ``Nonterminal``.  This value must be immutable and hashable.
    """

    def __init__(self, symbol):
        """
        Construct a new non-terminal from the given symbol.

        :type symbol: any
        :param symbol: The node value corresponding to this
            ``Nonterminal``.  This value must be immutable and
            hashable.
        """
        self._symbol = symbol

    def symbol(self):
        """
        Return the node value corresponding to this ``Nonterminal``.

        :rtype: (any)
        """
        return self._symbol

    def __eq__(self, other):
        """
        Return True if this non-terminal is equal to ``other``.  In
        particular, return True if ``other`` is a ``Nonterminal``
        and this non-terminal's symbol is equal to ``other`` 's symbol.

        :rtype: bool
        """
        return type(self) == type(other) and self._symbol == other._symbol

    def __ne__(self, other):
        return not self == other

    def __lt__(self, other):
        if not isinstance(other, Nonterminal):
            raise_unorderable_types("<", self, other)
        return self._symbol < other._symbol

    def __hash__(self):
        return hash(self._symbol)

    def __repr__(self):
        """
        Return a string representation for this ``Nonterminal``.

        :rtype: str
        """
        if isinstance(self._symbol, str):
            return "%s" % self._symbol
        else:
            return "%s" % repr(self._symbol)

    def __str__(self):
        """
        Return a string representation for this ``Nonterminal``.

        :rtype: str
        """
        if isinstance(self._symbol, str):
            return "%s" % self._symbol
        else:
            return "%s" % repr(self._symbol)

    def __div__(self, rhs):
        """
        Return a new nonterminal whose symbol is ``A/B``, where ``A`` is
        the symbol for this nonterminal, and ``B`` is the symbol for rhs.

        :param rhs: The nonterminal used to form the right hand side
            of the new nonterminal.
        :type rhs: Nonterminal
        :rtype: Nonterminal
        """
        return Nonterminal(f"{self._symbol}/{rhs._symbol}")

    def __truediv__(self, rhs):
        """
        Return a new nonterminal whose symbol is ``A/B``, where ``A`` is
        the symbol for this nonterminal, and ``B`` is the symbol for rhs.
        This function allows use of the slash ``/`` operator with
        the future import of division.

        :param rhs: The nonterminal used to form the right hand side
            of the new nonterminal.
        :type rhs: Nonterminal
        :rtype: Nonterminal
        """
        return self.__div__(rhs)


def nonterminals(symbols):
    """
    Given a string containing a list of symbol names, return a list of
    ``Nonterminals`` constructed from those symbols.

    :param symbols: The symbol name string.  This string can be
        delimited by either spaces or commas.
    :type symbols: str
    :return: A list of ``Nonterminals`` constructed from the symbol
        names given in ``symbols``.  The ``Nonterminals`` are sorted
        in the same order as the symbols names.
    :rtype: list(Nonterminal)
    """
    if "," in symbols:
        symbol_list = symbols.split(",")
    else:
        symbol_list = symbols.split()
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
    :return: True if the item is a ``Nonterminal``.
    :rtype: bool
    """
    return isinstance(item, Nonterminal)


#################################################################
# Terminals
#################################################################


def is_terminal(item):
    """
    Return True if the item is a terminal, which currently is
    if it is hashable and not a ``Nonterminal``.

    :rtype: bool
    """
    return hasattr(item, "__hash__") and not isinstance(item, Nonterminal)


#################################################################
# Productions
#################################################################


@total_ordering
class Production:
    """
    A grammar production.  Each production maps a single symbol
    on the "left-hand side" to a sequence of symbols on the
    "right-hand side".  (In the case of context-free productions,
    the left-hand side must be a ``Nonterminal``, and the right-hand
    side is a sequence of terminals and ``Nonterminals``.)
    "terminals" can be any immutable hashable object that is
    not a ``Nonterminal``.  Typically, terminals are strings
    representing words, such as ``"dog"`` or ``"under"``.

    :see: ``CFG``
    :see: ``DependencyGrammar``
    :see: ``Nonterminal``
    :type _lhs: Nonterminal
    :ivar _lhs: The left-hand side of the production.
    :type _rhs: tuple(Nonterminal, terminal)
    :ivar _rhs: The right-hand side of the production.
    """

    def __init__(self, lhs, rhs):
        """
        Construct a new ``Production``.

        :param lhs: The left-hand side of the new ``Production``.
        :type lhs: Nonterminal
        :param rhs: The right-hand side of the new ``Production``.
        :type rhs: sequence(Nonterminal and terminal)
        """
        if isinstance(rhs, str):
            raise TypeError(
                "production right hand side should be a list, " "not a string"
            )
        self._lhs = lhs
        self._rhs = tuple(rhs)

    def lhs(self):
        """
        Return the left-hand side of this ``Production``.

        :rtype: Nonterminal
        """
        return self._lhs

    def rhs(self):
        """
        Return the right-hand side of this ``Production``.

        :rtype: sequence(Nonterminal and terminal)
        """
        return self._rhs

    def __len__(self):
        """
        Return the length of the right-hand side.

        :rtype: int
        """
        return len(self._rhs)

    def is_nonlexical(self):
        """
        Return True if the right-hand side only contains ``Nonterminals``

        :rtype: bool
        """
        return all(is_nonterminal(n) for n in self._rhs)

    def is_lexical(self):
        """
        Return True if the right-hand contain at least one terminal token.

        :rtype: bool
        """
        return not self.is_nonlexical()

    def __str__(self):
        """
        Return a verbose string representation of the ``Production``.

        :rtype: str
        """
        result = "%s -> " % repr(self._lhs)
        result += " ".join(repr(el) for el in self._rhs)
        return result

    def __repr__(self):
        """
        Return a concise string representation of the ``Production``.

        :rtype: str
        """
        return "%s" % self

    def __eq__(self, other):
        """
        Return True if this ``Production`` is equal to ``other``.

        :rtype: bool
        """
        return (
            type(self) == type(other)
            and self._lhs == other._lhs
            and self._rhs == other._rhs
        )

    def __ne__(self, other):
        return not self == other

    def __lt__(self, other):
        if not isinstance(other, Production):
            raise_unorderable_types("<", self, other)
        return (self._lhs, self._rhs) < (other._lhs, other._rhs)

    def __hash__(self):
        """
        Return a hash value for the ``Production``.

        :rtype: int
        """
        return hash((self._lhs, self._rhs))


class DependencyProduction(Production):
    """
    A dependency grammar production.  Each production maps a single
    head word to an unordered list of one or more modifier words.
    """

    def __str__(self):
        """
        Return a verbose string representation of the ``DependencyProduction``.

        :rtype: str
        """
        result = f"'{self._lhs}' ->"
        for elt in self._rhs:
            result += f" '{elt}'"
        return result


class ProbabilisticProduction(Production, ImmutableProbabilisticMixIn):
    """
    A probabilistic context free grammar production.
    A PCFG ``ProbabilisticProduction`` is essentially just a ``Production`` that
    has an associated probability, which represents how likely it is that
    this production will be used.  In particular, the probability of a
    ``ProbabilisticProduction`` records the likelihood that its right-hand side is
    the correct instantiation for any given occurrence of its left-hand side.

    :see: ``Production``
    """

    def __init__(self, lhs, rhs, **prob):
        """
        Construct a new ``ProbabilisticProduction``.

        :param lhs: The left-hand side of the new ``ProbabilisticProduction``.
        :type lhs: Nonterminal
        :param rhs: The right-hand side of the new ``ProbabilisticProduction``.
        :type rhs: sequence(Nonterminal and terminal)
        :param prob: Probability parameters of the new ``ProbabilisticProduction``.
        """
        ImmutableProbabilisticMixIn.__init__(self, **prob)
        Production.__init__(self, lhs, rhs)

    def __str__(self):
        return super().__str__() + (
            " [1.0]" if (self.prob() == 1.0) else " [%g]" % self.prob()
        )

    def __eq__(self, other):
        return (
            type(self) == type(other)
            and self._lhs == other._lhs
            and self._rhs == other._rhs
            and self.prob() == other.prob()
        )

    def __ne__(self, other):
        return not self == other

    def __hash__(self):
        return hash((self._lhs, self._rhs, self.prob()))


#################################################################
# Grammars
#################################################################


class CFG:
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
        and set of ``Production`` instances.

        :param start: The start symbol
        :type start: Nonterminal
        :param productions: The list of productions that defines the grammar
        :type productions: list(Production)
        :param calculate_leftcorners: False if we don't want to calculate the
            leftcorner relation. In that case, some optimized chart parsers won't work.
        :type calculate_leftcorners: bool
        """
        if not is_nonterminal(start):
            raise TypeError(
                "start should be a Nonterminal object,"
                " not a %s" % type(start).__name__
            )

        self._start = start
        self._productions = productions
        self._categories = {prod.lhs() for prod in productions}
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
        self._immediate_leftcorner_categories = {cat: {cat} for cat in self._categories}
        self._immediate_leftcorner_words = {cat: set() for cat in self._categories}
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

        nr_leftcorner_categories = sum(
            map(len, self._immediate_leftcorner_categories.values())
        )
        nr_leftcorner_words = sum(map(len, self._immediate_leftcorner_words.values()))
        if nr_leftcorner_words > nr_leftcorner_categories > 10000:
            # If the grammar is big, the leftcorner-word dictionary will be too large.
            # In that case it is better to calculate the relation on demand.
            self._leftcorner_words = None
            return

        self._leftcorner_words = {}
        for cat in self._leftcorners:
            lefts = self._leftcorners[cat]
            lc = self._leftcorner_words[cat] = set()
            for left in lefts:
                lc.update(self._immediate_leftcorner_words.get(left, set()))

    @classmethod
    def fromstring(cls, input, encoding=None):
        """
        Return the grammar instance corresponding to the input string(s).

        :param input: a grammar, either in the form of a string or as a list of strings.
        """
        start, productions = read_grammar(
            input, standard_nonterm_parser, encoding=encoding
        )
        return cls(start, productions)

    def start(self):
        """
        Return the start symbol of the grammar

        :rtype: Nonterminal
        """
        return self._start

    # tricky to balance readability and efficiency here!
    # can't use set operations as they don't preserve ordering
    def productions(self, lhs=None, rhs=None, empty=False):
        """
        Return the grammar productions, filtered by the left-hand side
        or the first item in the right-hand side.

        :param lhs: Only return productions with the given left-hand side.
        :param rhs: Only return productions with the given first item
            in the right-hand side.
        :param empty: Only return productions with an empty right-hand side.
        :return: A list of productions matching the given constraints.
        :rtype: list(Production)
        """
        if rhs and empty:
            raise ValueError(
                "You cannot select empty and non-empty " "productions at the same time."
            )

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
            return [
                prod
                for prod in self._lhs_index.get(lhs, [])
                if prod in self._rhs_index.get(rhs, [])
            ]

    def leftcorners(self, cat):
        """
        Return the set of all nonterminals that the given nonterminal
        can start with, including itself.

        This is the reflexive, transitive closure of the immediate
        leftcorner relation:  (A > B)  iff  (A -> B beta)

        :param cat: the parent of the leftcorners
        :type cat: Nonterminal
        :return: the set of all leftcorners
        :rtype: set(Nonterminal)
        """
        return self._leftcorners.get(cat, {cat})

    def is_leftcorner(self, cat, left):
        """
        True if left is a leftcorner of cat, where left can be a
        terminal or a nonterminal.

        :param cat: the parent of the leftcorner
        :type cat: Nonterminal
        :param left: the suggested leftcorner
        :type left: Terminal or Nonterminal
        :rtype: bool
        """
        if is_nonterminal(left):
            return left in self.leftcorners(cat)
        elif self._leftcorner_words:
            return left in self._leftcorner_words.get(cat, set())
        else:
            return any(
                left in self._immediate_leftcorner_words.get(parent, set())
                for parent in self.leftcorners(cat)
            )

    def leftcorner_parents(self, cat):
        """
        Return the set of all nonterminals for which the given category
        is a left corner. This is the inverse of the leftcorner relation.

        :param cat: the suggested leftcorner
        :type cat: Nonterminal
        :return: the set of all parents to the leftcorner
        :rtype: set(Nonterminal)
        """
        return self._leftcorner_parents.get(cat, {cat})

    def check_coverage(self, tokens):
        """
        Check whether the grammar rules cover the given list of tokens.
        If not, then raise an exception.

        :type tokens: list(str)
        """
        missing = [tok for tok in tokens if not self._lexical_index.get(tok)]
        if missing:
            missing = ", ".join(f"{w!r}" for w in missing)
            raise ValueError(
                "Grammar does not cover some of the " "input words: %r." % missing
            )

    def _calculate_grammar_forms(self):
        """
        Pre-calculate of which form(s) the grammar is.
        """
        prods = self._productions
        self._is_lexical = all(p.is_lexical() for p in prods)
        self._is_nonlexical = all(p.is_nonlexical() for p in prods if len(p) != 1)
        self._min_len = min((len(p) for p in prods), default=None)
        self._max_len = max((len(p) for p in prods), default=None)
        self._all_unary_are_lexical = all(p.is_lexical() for p in prods if len(p) == 1)

    def is_lexical(self):
        """
        Return True if all productions are lexicalised.
        """
        return self._is_lexical

    def is_nonlexical(self):
        """
        Return True if all lexical rules are "preterminals", that is,
        unary rules which can be separated in a preprocessing step.

        This means that all productions are of the forms
        A -> B1 ... Bn (n>=0), or A -> "s".

        Note: is_lexical() and is_nonlexical() are not opposites.
        There are grammars which are neither, and grammars which are both.
        """
        return self._is_nonlexical

    def min_len(self):
        """
        Return the right-hand side length of the shortest grammar production.
        """
        return self._min_len

    def max_len(self):
        """
        Return the right-hand side length of the longest grammar production.
        """
        return self._max_len

    def is_nonempty(self):
        """
        Return True if there are no empty productions.
        """
        return all(len(prod) > 0 for prod in self.productions())

    def is_binarised(self):
        """
        Return True if all productions are at most binary.
        Note that there can still be empty and unary productions.
        """
        return all(len(prod) <= 2 for prod in self.productions())

    def is_flexible_chomsky_normal_form(self):
        """
        Return True if all productions are of the forms
        A -> B C, A -> B, or A -> "s".
        """
        return self.is_nonempty() and self.is_nonlexical() and self.is_binarised()

    def is_chomsky_normal_form(self):
        """
        Return True if the grammar is of Chomsky Normal Form, i.e. all productions
        are of the form A -> B C, or A -> "s".
        """
        return self.is_flexible_chomsky_normal_form() and self._all_unary_are_lexical

    def chomsky_normal_form(self, flexible=False, simplify=True):
        """
        Return an equivalent grammar in Chomsky Normal Form.

        Keyword Parameters:
        flexible -- bool: if True, result may contain unit productions.
        simplify -- bool: if True, remove non-producing and
                                        unreachable symbols.

        The class methods invoked are named following the usage in
        M. Lange and H. Leiß (2009), "To CNF or not to CNF? An efficient
        yet presentable version of the CYK algorithm", Informatica
        Didactica 8:2008-2010.
        """
        if (
            flexible and self.is_flexible_chomsky_normal_form()
        ) or self.is_chomsky_normal_form():
            result = self
            if simplify:
                # remove non-terminals that don't generate output
                result = CFG.PROD(result)
                # remove symbols that are not reachable from the start
                result = CFG.REACH(result)
            return result

        # add a new start symbol if the present one
        # occurs on a right-hand side
        result = CFG.START(self)

        if not result.is_nonempty():
            # remove empty productions (except for startsymbol -> epsilon)
            result = CFG.DEL(result)

        if not flexible:
            # remove unit productions (except with a terminal on the rhs)
            result = CFG.UNIT(result)

        if simplify:
            # remove non-terminals that don't generate output
            result = CFG.PROD(result)
            # remove symbols that are not reachable from the start
            result = CFG.REACH(result)

        if not result.is_binarised():
            # reduce right-hand sides to at most two
            result = CFG.BIN(result)

        if not result.is_nonlexical():
            # replace non-single terminals with non-terminals
            result = CFG.TERM(result)

        # Sort the productions for nice output
        result._productions.sort(
            key=lambda prod: (
                # non-lexical before lexical
                prod.is_lexical(),
                # start symbol lhs before other lhs
                prod.lhs() != result.start(),
                # lhs alphabetically
                str(prod.lhs()),
                # rhs item-wise
                *(
                    (  # nonterminal before terminal
                        is_terminal(child),
                        # alphabetically
                        str(child),
                    )
                    for child in prod.rhs()
                ),
            )
        )

        return result

    @classmethod
    def _new_nonterminal(
        cls, grammar, nonterminals_in_use=None, ctr=itertools.count(), stem="X"
    ):
        """
        Create a new non-terminal symbol that is not yet
        used in the grammar.

        Params:
        grammar -- CFG

        Keyword params:
        nonterminals_in_use -- set of non-terminals currently in the grammar.
        Note: CFG objects have an attribute "_categories", the set of left-hand
        sides in the productions. If the grammar contains no useless symbols,
        categories coincides with the set of non-terminals. Therefore after
        the elimination of useless symbols (see "PROD" below), _categories
        can be passed to _new_nonterminals as the value of nonterminals_in_use.
        But _new_nonterminal is also called prior to the elimination of useless
        symbols (see "START" below). In that case _categories should not be used
        and nonterminals_in_use must be calculated.

        ctr     -- itertools.count
        stem    -- str

        Return: Nonterminal of the form 'stem+n' for some n.
        """
        if nonterminals_in_use == None:
            nonterminals_in_use = grammar._categories.union(
                {
                    child
                    for prod in grammar.productions()
                    for child in prod.rhs()
                    if is_nonterminal(child)
                }
            )
        while True:
            new_nt = Nonterminal(f"{stem}{next(ctr)}")
            if new_nt not in nonterminals_in_use:
                grammar._categories.add(new_nt)
                return new_nt

    @classmethod
    def START(cls, grammar):
        """
        Add a new start symbol if the current start symbol
        appears on the right-hand side of a production.

        Params:
        grammar -- CFG

        Return: CFG whose start symbol does not occur on the
        right-hand side of any production.
        """
        if any(grammar.start() in prod.rhs() for prod in grammar.productions()):
            ctr = itertools.count()
            new_start = cls._new_nonterminal(grammar, ctr=ctr, stem="S")
            return cls(
                new_start,
                grammar.productions() + [Production(new_start, (grammar.start(),))],
            )
        else:
            return grammar

    @classmethod
    def _DEL_multiply(cls, prod, symbol):
        """
        Given a production prod and a (nullable) symbol, generate all
        variants of prod whose right-hand sides contain a (possibly empty)
        subset of the occurrences of the symbol.

        Thus for instance if prod is X -> A B A C A
        then _DEL_multiply( prod, A) generates the productions
        X -> BC, X -> ABC, X -> BAC, X -> BCA,
        X -> ABAC, X -> ABCA, X -> BACA, X -> ABACA

        Parameters:
        prod    -- Production
        symbol  -- terminal or Nonterminal

        Yield: Production with some subset of the occurrences of symbol

        Helper function for DEL_multiply.
        """
        for subset in range(2 ** prod.rhs().count(symbol)):
            new_rhs = []
            nth_occurrence = 0
            for child in prod.rhs():
                if child == symbol:
                    if subset & (1 << nth_occurrence):
                        new_rhs.append(child)
                        nth_occurrence += 1
                else:
                    new_rhs.append(child)
            yield Production(prod.lhs(), new_rhs)

    @classmethod
    def DEL(cls, grammar):
        """
        Return an equivalent grammar without empty productions.
        (Startsymbol -> epsilon is not removed, and may in fact
        be created in the process.)

        Parameter:
        grammar -- CFG
        """
        productions = dict.fromkeys(grammar.productions())
        while True:
            empty_productions = dict.fromkeys(
                prod
                for prod in productions
                if len(prod) == 0
                if prod.lhs() != grammar.start()
            )
            if not empty_productions:
                break
            for prod in empty_productions:
                del productions[prod]
            new_productions = dict()
            for prod in productions:
                for empty_prod in empty_productions:
                    if empty_prod.lhs() in prod.rhs():
                        new_productions.update(
                            (prod, None)
                            for prod in cls._DEL_multiply(prod, empty_prod.lhs())
                        )
            productions.update(new_productions)

        return cls(grammar.start(), list(productions))

    @classmethod
    def _UNIT_paths(cls, grammar, path):
        """
        Given a list 'path' of production rules, generate all
        unit paths containing 'path' as an intial segment.

        A unit path is a list [N1 -> N2, N2 -> N3, ..., Nn -> alpha],
        where all Ni are non-terminals and alpha is not a non-terminal
        (i.e., either a list of length != 1, or a terminal).

        Parameters:
        grammar -- CFG
        path    -- list of productions
        """
        if len(path[-1]) != 1 or path[-1].is_lexical():
            yield path

        else:
            for next_prod in grammar.productions():
                if next_prod.lhs() == path[-1].rhs()[0] and next_prod not in path:
                    yield from cls._UNIT_paths(grammar, path + [next_prod])

    @classmethod
    def UNIT(cls, grammar):
        """
        Return an equivalent grammar without unit productions.

        Parameters:
        grammar -- CFG
        """
        productions = dict.fromkeys(grammar.productions())
        while True:
            new_productions = dict.fromkeys(
                Production(path[0].lhs(), path[-1].rhs())
                for prod in productions
                for path in cls._UNIT_paths(grammar, [prod])
            )
            if all(prod in new_productions for prod in productions):
                break
            else:
                productions = new_productions

        return cls(grammar.start(), list(productions))

    @classmethod
    def PROD(cls, grammar):
        """
        Return an equivalent grammar without non-terminals
        that don't generate any output.

        Parameters:
        grammar -- CFG
        """
        producing = {grammar.start()}.union(
            child
            for prod in grammar.productions()
            for child in prod.rhs()
            if is_terminal(child)
        )
        productions_used = dict()
        while True:
            new_producing = set()
            for prod in grammar.productions():
                if prod not in productions_used and all(
                    child in producing for child in prod.rhs()
                ):
                    new_producing.add(prod.lhs())
                    productions_used[prod] = None
            if new_producing <= producing:
                break
            else:
                producing.update(new_producing)

        return cls(grammar.start(), list(productions_used))

    @classmethod
    def REACH(cls, grammar):
        """
        Returnan equivalent grammar without symbols
        that are not reachable from the start symbol.

        Parameters:
        grammar -- CFG
        """
        reachable = {grammar.start()}
        productions_used = dict()
        while True:
            new_reachable = set()
            for prod in grammar.productions():
                if prod not in productions_used and prod.lhs() in reachable:
                    new_reachable.update(set(prod.rhs()))
                    productions_used[prod] = None
            if new_reachable <= reachable:
                break
            else:
                reachable.update(new_reachable)

        return cls(grammar.start(), list(productions_used))

    @classmethod
    def BIN(cls, grammar):
        """
        Return an equivalent grammar none of whose right-hand sides
        are longer than 2.

        Parameters:
        grammar -- CFG
        """
        new_productions = []
        ctr = itertools.count()
        for prod in grammar.productions():
            if len(prod) <= 2:
                new_productions.append(prod)
            else:
                current_lhs, current_rhs = prod.lhs(), list(prod.rhs())
                while len(current_rhs) > 2:
                    left_child = current_rhs.pop(0)
                    new_parent = cls._new_nonterminal(
                        grammar,
                        nonterminals_in_use=grammar._categories,
                        ctr=ctr,
                        stem="B",
                    )
                    new_productions.append(
                        Production(current_lhs, (left_child, new_parent))
                    )
                    current_lhs = new_parent
                new_productions.append(Production(current_lhs, current_rhs))

        return cls(grammar.start(), new_productions)

    @classmethod
    def TERM(cls, grammar):
        """
        Return an equivalent grammar in which terminals do not have
        siblings (terminals or non-terminals) on right-hand sides.

        Parameters:
        grammar -- CFG
        """
        new_parents = dict()
        new_productions = []
        ctr = itertools.count()
        for prod in grammar.productions():
            if len(prod) > 1 and prod.is_lexical():
                for child in prod.rhs():
                    if is_terminal(child) and child not in new_parents:
                        new_parents[child] = cls._new_nonterminal(
                            grammar,
                            nonterminals_in_use=grammar._categories,
                            ctr=ctr,
                            stem="T",
                        )
                new_productions.append(
                    Production(
                        prod.lhs(),
                        tuple(new_parents.get(child, child) for child in prod.rhs()),
                    )
                )
            else:
                new_productions.append(prod)

        new_productions.extend(
            Production(new_parents[child], (child,)) for child in new_parents
        )

        return cls(grammar.start(), new_productions)

    def __repr__(self):
        return "<Grammar with %d productions>" % len(self._productions)

    def __str__(self):
        result = "Grammar with %d productions" % len(self._productions)
        result += " (start state = %r)" % self._start
        for production in self._productions:
            result += "\n    %s" % production
        return result


class FeatureGrammar(CFG):
    """
    A feature-based grammar.  This is equivalent to a
    ``CFG`` whose nonterminals are all
    ``FeatStructNonterminal``.

    A grammar consists of a start state and a set of
    productions.  The set of terminals and nonterminals
    is implicitly specified by the productions.
    """

    def __init__(self, start, productions):
        """
        Create a new feature-based grammar, from the given start
        state and set of ``Productions``.

        :param start: The start symbol
        :type start: FeatStructNonterminal
        :param productions: The list of productions that defines the grammar
        :type productions: list(Production)
        """
        CFG.__init__(self, start, productions)

    # The difference with CFG is that the productions are
    # indexed on the TYPE feature of the nonterminals.
    # This is calculated by the method _get_type_if_possible().

    def _calculate_indexes(self):
        self._lhs_index = {}
        self._rhs_index = {}
        self._empty_index = {}
        self._empty_productions = []
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
                if lhs not in self._empty_index:
                    self._empty_index[lhs] = []
                self._empty_index[lhs].append(prod)
                self._empty_productions.append(prod)
            # Lexical tokens in the right hand side.
            for token in prod._rhs:
                if is_terminal(token):
                    self._lexical_index.setdefault(token, set()).add(prod)

    @classmethod
    def fromstring(
        cls, input, features=None, logic_parser=None, fstruct_reader=None, encoding=None
    ):
        """
        Return a feature structure based grammar.

        :param input: a grammar, either in the form of a string or else
        as a list of strings.
        :param features: a tuple of features (default: SLASH, TYPE)
        :param logic_parser: a parser for lambda-expressions,
        by default, ``LogicParser()``
        :param fstruct_reader: a feature structure parser
        (only if features and logic_parser is None)
        """
        if features is None:
            features = (SLASH, TYPE)

        if fstruct_reader is None:
            fstruct_reader = FeatStructReader(
                features, FeatStructNonterminal, logic_parser=logic_parser
            )
        elif logic_parser is not None:
            raise Exception(
                "'logic_parser' and 'fstruct_reader' must " "not both be set"
            )

        start, productions = read_grammar(
            input, fstruct_reader.read_partial, encoding=encoding
        )
        return cls(start, productions)

    def productions(self, lhs=None, rhs=None, empty=False):
        """
        Return the grammar productions, filtered by the left-hand side
        or the first item in the right-hand side.

        :param lhs: Only return productions with the given left-hand side.
        :param rhs: Only return productions with the given first item
            in the right-hand side.
        :param empty: Only return productions with an empty right-hand side.
        :rtype: list(Production)
        """
        if rhs and empty:
            raise ValueError(
                "You cannot select empty and non-empty " "productions at the same time."
            )

        # no constraints so return everything
        if not lhs and not rhs:
            if empty:
                return self._empty_productions
            else:
                return self._productions

        # only lhs specified so look up its index
        elif lhs and not rhs:
            if empty:
                return self._empty_index.get(self._get_type_if_possible(lhs), [])
            else:
                return self._lhs_index.get(self._get_type_if_possible(lhs), [])

        # only rhs specified so look up its index
        elif rhs and not lhs:
            return self._rhs_index.get(self._get_type_if_possible(rhs), [])

        # intersect
        else:
            return [
                prod
                for prod in self._lhs_index.get(self._get_type_if_possible(lhs), [])
                if prod in self._rhs_index.get(self._get_type_if_possible(rhs), [])
            ]

    def leftcorners(self, cat):
        """
        Return the set of all words that the given category can start with.
        Also called the "first set" in compiler construction.
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
        Helper function which returns the ``TYPE`` feature of the ``item``,
        if it exists, otherwise it returns the ``item`` itself
        """
        if isinstance(item, dict) and TYPE in item:
            return FeatureValueType(item[TYPE])
        else:
            return item


@total_ordering
class FeatureValueType:
    """
    A helper class for ``FeatureGrammars``, designed to be different
    from ordinary strings.  This is to stop the ``FeatStruct``
    ``FOO[]`` from being compare equal to the terminal "FOO".
    """

    def __init__(self, value):
        self._value = value

    def __repr__(self):
        return "<%s>" % self._value

    def __eq__(self, other):
        return type(self) == type(other) and self._value == other._value

    def __ne__(self, other):
        return not self == other

    def __lt__(self, other):
        if not isinstance(other, FeatureValueType):
            raise_unorderable_types("<", self, other)
        return self._value < other._value

    def __hash__(self):
        return hash(self._value)


class DependencyGrammar:
    """
    A dependency grammar.  A DependencyGrammar consists of a set of
    productions.  Each production specifies a head/modifier relationship
    between a pair of words.
    """

    def __init__(self, productions):
        """
        Create a new dependency grammar, from the set of ``Productions``.

        :param productions: The list of productions that defines the grammar
        :type productions: list(Production)
        """
        self._productions = productions

    @classmethod
    def fromstring(cls, input):
        productions = []
        for linenum, line in enumerate(input.split("\n")):
            line = line.strip()
            if line.startswith("#") or line == "":
                continue
            try:
                productions += _read_dependency_production(line)
            except ValueError as e:
                raise ValueError(f"Unable to parse line {linenum}: {line}") from e
        if len(productions) == 0:
            raise ValueError("No productions found!")
        return cls(productions)

    def contains(self, head, mod):
        """
        :param head: A head word.
        :type head: str
        :param mod: A mod word, to test as a modifier of 'head'.
        :type mod: str

        :return: true if this ``DependencyGrammar`` contains a
            ``DependencyProduction`` mapping 'head' to 'mod'.
        :rtype: bool
        """
        for production in self._productions:
            for possibleMod in production._rhs:
                if production._lhs == head and possibleMod == mod:
                    return True
        return False

    def __contains__(self, head_mod):
        """
        Return True if this ``DependencyGrammar`` contains a
        ``DependencyProduction`` mapping 'head' to 'mod'.

        :param head_mod: A tuple of a head word and a mod word,
            to test as a modifier of 'head'.
        :type head: Tuple[str, str]
        :rtype: bool
        """
        try:
            head, mod = head_mod
        except ValueError as e:
            raise ValueError(
                "Must use a tuple of strings, e.g. `('price', 'of') in grammar`"
            ) from e
        return self.contains(head, mod)

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
        Return a verbose string representation of the ``DependencyGrammar``

        :rtype: str
        """
        str = "Dependency grammar with %d productions" % len(self._productions)
        for production in self._productions:
            str += "\n  %s" % production
        return str

    def __repr__(self):
        """
        Return a concise string representation of the ``DependencyGrammar``
        """
        return "Dependency grammar with %d productions" % len(self._productions)


class ProbabilisticDependencyGrammar:
    """ """

    def __init__(self, productions, events, tags):
        self._productions = productions
        self._events = events
        self._tags = tags

    def contains(self, head, mod):
        """
        Return True if this ``DependencyGrammar`` contains a
        ``DependencyProduction`` mapping 'head' to 'mod'.

        :param head: A head word.
        :type head: str
        :param mod: A mod word, to test as a modifier of 'head'.
        :type mod: str
        :rtype: bool
        """
        for production in self._productions:
            for possibleMod in production._rhs:
                if production._lhs == head and possibleMod == mod:
                    return True
        return False

    def __str__(self):
        """
        Return a verbose string representation of the ``ProbabilisticDependencyGrammar``

        :rtype: str
        """
        str = "Statistical dependency grammar with %d productions" % len(
            self._productions
        )
        for production in self._productions:
            str += "\n  %s" % production
        str += "\nEvents:"
        for event in self._events:
            str += "\n  %d:%s" % (self._events[event], event)
        str += "\nTags:"
        for tag_word in self._tags:
            str += f"\n {tag_word}:\t({self._tags[tag_word]})"
        return str

    def __repr__(self):
        """
        Return a concise string representation of the ``ProbabilisticDependencyGrammar``
        """
        return "Statistical Dependency grammar with %d productions" % len(
            self._productions
        )


class PCFG(CFG):
    """
    A probabilistic context-free grammar.  A PCFG consists of a
    start state and a set of productions with probabilities.  The set of
    terminals and nonterminals is implicitly specified by the productions.

    PCFG productions use the ``ProbabilisticProduction`` class.
    ``PCFGs`` impose the constraint that the set of productions with
    any given left-hand-side must have probabilities that sum to 1
    (allowing for a small margin of error).

    If you need efficient key-based access to productions, you can use
    a subclass to implement it.

    :type EPSILON: float
    :cvar EPSILON: The acceptable margin of error for checking that
        productions with a given left-hand side have probabilities
        that sum to 1.
    """

    EPSILON = 0.01

    def __init__(self, start, productions, calculate_leftcorners=True):
        """
        Create a new context-free grammar, from the given start state
        and set of ``ProbabilisticProductions``.

        :param start: The start symbol
        :type start: Nonterminal
        :param productions: The list of productions that defines the grammar
        :type productions: list(Production)
        :raise ValueError: if the set of productions with any left-hand-side
            do not have probabilities that sum to a value within
            EPSILON of 1.
        :param calculate_leftcorners: False if we don't want to calculate the
            leftcorner relation. In that case, some optimized chart parsers won't work.
        :type calculate_leftcorners: bool
        """
        CFG.__init__(self, start, productions, calculate_leftcorners)

        # Make sure that the probabilities sum to one.
        probs = {}
        for production in productions:
            probs[production.lhs()] = probs.get(production.lhs(), 0) + production.prob()
        for (lhs, p) in probs.items():
            if not ((1 - PCFG.EPSILON) < p < (1 + PCFG.EPSILON)):
                raise ValueError("Productions for %r do not sum to 1" % lhs)

    @classmethod
    def fromstring(cls, input, encoding=None):
        """
        Return a probabilistic context-free grammar corresponding to the
        input string(s).

        :param input: a grammar, either in the form of a string or else
             as a list of strings.
        """
        start, productions = read_grammar(
            input, standard_nonterm_parser, probabilistic=True, encoding=encoding
        )
        return cls(start, productions)


#################################################################
# Inducing Grammars
#################################################################

# Contributed by Nathan Bodenstab <bodenstab@cslu.ogi.edu>


def induce_pcfg(start, productions):
    r"""
    Induce a PCFG grammar from a list of productions.

    The probability of a production A -> B C in a PCFG is:

    |                count(A -> B C)
    |  P(B, C | A) = ---------------       where \* is any right hand side
    |                 count(A -> \*)

    :param start: The start symbol
    :type start: Nonterminal
    :param productions: The list of productions that defines the grammar
    :type productions: list(Production)
    """
    # Production count: the number of times a given production occurs
    pcount = {}

    # LHS-count: counts the number of times a given lhs occurs
    lcount = {}

    for prod in productions:
        lcount[prod.lhs()] = lcount.get(prod.lhs(), 0) + 1
        pcount[prod] = pcount.get(prod, 0) + 1

    prods = [
        ProbabilisticProduction(p.lhs(), p.rhs(), prob=pcount[p] / lcount[p.lhs()])
        for p in pcount
    ]
    return PCFG(start, prods)


#################################################################
# Helper functions for reading productions
#################################################################


def _read_cfg_production(input):
    """
    Return a list of context-free ``Productions``.
    """
    return _read_production(input, standard_nonterm_parser)


def _read_pcfg_production(input):
    """
    Return a list of PCFG ``ProbabilisticProductions``.
    """
    return _read_production(input, standard_nonterm_parser, probabilistic=True)


def _read_fcfg_production(input, fstruct_reader):
    """
    Return a list of feature-based ``Productions``.
    """
    return _read_production(input, fstruct_reader)


# Parsing generic grammars

_ARROW_RE = re.compile(r"\s* -> \s*", re.VERBOSE)
_PROBABILITY_RE = re.compile(r"( \[ [\d\.]+ \] ) \s*", re.VERBOSE)
_TERMINAL_RE = re.compile(r'( "[^"]*" | \'[^\']*\' ) \s*', re.VERBOSE)
_DISJUNCTION_RE = re.compile(r"\| \s*", re.VERBOSE)


def _read_production(line, nonterm_parser, probabilistic=False):
    """
    Parse a grammar rule, given as a string, and return
    a list of productions.
    """
    pos = 0

    # Parse the left-hand side.
    lhs, pos = nonterm_parser(line, pos)

    # Skip over the arrow.
    m = _ARROW_RE.match(line, pos)
    if not m:
        raise ValueError("Expected an arrow")
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
                raise ValueError(
                    "Production probability %f, "
                    "should not be greater than 1.0" % (probabilities[-1],)
                )

        # String -- add terminal.
        elif line[pos] in "'\"":
            m = _TERMINAL_RE.match(line, pos)
            if not m:
                raise ValueError("Unterminated string")
            rhsides[-1].append(m.group(1)[1:-1])
            pos = m.end()

        # Vertical bar -- start new rhside.
        elif line[pos] == "|":
            m = _DISJUNCTION_RE.match(line, pos)
            probabilities.append(0.0)
            rhsides.append([])
            pos = m.end()

        # Anything else -- nonterminal.
        else:
            nonterm, pos = nonterm_parser(line, pos)
            rhsides[-1].append(nonterm)

    if probabilistic:
        return [
            ProbabilisticProduction(lhs, rhs, prob=probability)
            for (rhs, probability) in zip(rhsides, probabilities)
        ]
    else:
        return [Production(lhs, rhs) for rhs in rhsides]


#################################################################
# Reading Phrase Structure Grammars
#################################################################


def read_grammar(input, nonterm_parser, probabilistic=False, encoding=None):
    """
    Return a pair consisting of a starting category and a list of
    ``Productions``.

    :param input: a grammar, either in the form of a string or else
        as a list of strings.
    :param nonterm_parser: a function for parsing nonterminals.
        It should take a ``(string, position)`` as argument and
        return a ``(nonterminal, position)`` as result.
    :param probabilistic: are the grammar rules probabilistic?
    :type probabilistic: bool
    :param encoding: the encoding of the grammar, if it is a binary string
    :type encoding: str
    """
    if encoding is not None:
        input = input.decode(encoding)
    if isinstance(input, str):
        lines = input.split("\n")
    else:
        lines = input

    start = None
    productions = []
    continue_line = ""
    for linenum, line in enumerate(lines):
        line = continue_line + line.strip()
        if line.startswith("#") or line == "":
            continue
        if line.endswith("\\"):
            continue_line = line[:-1].rstrip() + " "
            continue
        continue_line = ""
        try:
            if line[0] == "%":
                directive, args = line[1:].split(None, 1)
                if directive == "start":
                    start, pos = nonterm_parser(args, 0)
                    if pos != len(args):
                        raise ValueError("Bad argument to start directive")
                else:
                    raise ValueError("Bad directive")
            else:
                # expand out the disjunctions on the RHS
                productions += _read_production(line, nonterm_parser, probabilistic)
        except ValueError as e:
            raise ValueError(f"Unable to parse line {linenum + 1}: {line}\n{e}") from e

    if not productions:
        raise ValueError("No productions found!")
    if not start:
        start = productions[0].lhs()
    return (start, productions)


_STANDARD_NONTERM_RE = re.compile(r"( [\w/][\w/^<>-]* ) \s*", re.VERBOSE)


def standard_nonterm_parser(string, pos):
    m = _STANDARD_NONTERM_RE.match(string, pos)
    if not m:
        raise ValueError("Expected a nonterminal, found: " + string[pos:])
    return (Nonterminal(m.group(1)), m.end())


#################################################################
# Reading Dependency Grammars
#################################################################

_READ_DG_RE = re.compile(
    r"""^\s*                # leading whitespace
                              ('[^']+')\s*        # single-quoted lhs
                              (?:[-=]+>)\s*        # arrow
                              (?:(                 # rhs:
                                   "[^"]+"         # doubled-quoted terminal
                                 | '[^']+'         # single-quoted terminal
                                 | \|              # disjunction
                                 )
                                 \s*)              # trailing space
                                 *$""",  # zero or more copies
    re.VERBOSE,
)
_SPLIT_DG_RE = re.compile(r"""('[^']'|[-=]+>|"[^"]+"|'[^']+'|\|)""")


def _read_dependency_production(s):
    if not _READ_DG_RE.match(s):
        raise ValueError("Bad production string")
    pieces = _SPLIT_DG_RE.split(s)
    pieces = [p for i, p in enumerate(pieces) if i % 2 == 1]
    lhside = pieces[0].strip("'\"")
    rhsides = [[]]
    for piece in pieces[2:]:
        if piece == "|":
            rhsides.append([])
        else:
            rhsides[-1].append(piece.strip("'\""))
    return [DependencyProduction(lhside, rhside) for rhside in rhsides]


#################################################################
# Demonstration
#################################################################


def cfg_demo():
    """
    A demonstration showing how ``CFGs`` can be created and used.
    """

    from nltk import CFG, Production, nonterminals

    # Create some nonterminals
    S, NP, VP, PP = nonterminals("S, NP, VP, PP")
    N, V, P, Det = nonterminals("N, V, P, Det")
    VP_slash_NP = VP / NP

    print("Some nonterminals:", [S, NP, VP, PP, N, V, P, Det, VP / NP])
    print("    S.symbol() =>", repr(S.symbol()))
    print()

    print(Production(S, [NP]))

    # Create some Grammar Productions
    grammar = CFG.fromstring(
        """
      S -> NP VP
      PP -> P NP
      NP -> Det N | NP PP
      VP -> V NP | VP PP
      Det -> 'a' | 'the'
      N -> 'dog' | 'cat'
      V -> 'chased' | 'sat'
      P -> 'on' | 'in'
    """
    )

    print("A Grammar:", repr(grammar))
    print("    grammar.start()       =>", repr(grammar.start()))
    print("    grammar.productions() =>", end=" ")
    # Use string.replace(...) is to line-wrap the output.
    print(repr(grammar.productions()).replace(",", ",\n" + " " * 25))
    print()


def pcfg_demo():
    """
    A demonstration showing how a ``PCFG`` can be created and used.
    """

    from nltk import induce_pcfg, treetransforms
    from nltk.corpus import treebank
    from nltk.parse import pchart

    toy_pcfg1 = PCFG.fromstring(
        """
        S -> NP VP [1.0]
        NP -> Det N [0.5] | NP PP [0.25] | 'John' [0.1] | 'I' [0.15]
        Det -> 'the' [0.8] | 'my' [0.2]
        N -> 'man' [0.5] | 'telescope' [0.5]
        VP -> VP PP [0.1] | V NP [0.7] | V [0.2]
        V -> 'ate' [0.35] | 'saw' [0.65]
        PP -> P NP [1.0]
        P -> 'with' [0.61] | 'under' [0.39]
        """
    )

    toy_pcfg2 = PCFG.fromstring(
        """
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
        """
    )

    pcfg_prods = toy_pcfg1.productions()

    pcfg_prod = pcfg_prods[2]
    print("A PCFG production:", repr(pcfg_prod))
    print("    pcfg_prod.lhs()  =>", repr(pcfg_prod.lhs()))
    print("    pcfg_prod.rhs()  =>", repr(pcfg_prod.rhs()))
    print("    pcfg_prod.prob() =>", repr(pcfg_prod.prob()))
    print()

    grammar = toy_pcfg2
    print("A PCFG grammar:", repr(grammar))
    print("    grammar.start()       =>", repr(grammar.start()))
    print("    grammar.productions() =>", end=" ")
    # Use .replace(...) is to line-wrap the output.
    print(repr(grammar.productions()).replace(",", ",\n" + " " * 26))
    print()

    # extract productions from three trees and induce the PCFG
    print("Induce PCFG grammar from treebank data:")

    productions = []
    item = treebank._fileids[0]
    for tree in treebank.parsed_sents(item)[:3]:
        # perform optional tree transformations, e.g.:
        tree.collapse_unary(collapsePOS=False)
        tree.chomsky_normal_form(horzMarkov=2)

        productions += tree.productions()

    S = Nonterminal("S")
    grammar = induce_pcfg(S, productions)
    print(grammar)
    print()

    print("Parse sentence using induced grammar:")

    parser = pchart.InsideChartParser(grammar)
    parser.trace(3)

    # doesn't work as tokens are different:
    # sent = treebank.tokenized('wsj_0001.mrg')[0]

    sent = treebank.parsed_sents(item)[0].leaves()
    print(sent)
    for parse in parser.parse(sent):
        print(parse)


def fcfg_demo():
    import nltk.data

    g = nltk.data.load("grammars/book_grammars/feat0.fcfg")
    print(g)
    print()


def dg_demo():
    """
    A demonstration showing the creation and inspection of a
    ``DependencyGrammar``.
    """
    grammar = DependencyGrammar.fromstring(
        """
    'scratch' -> 'cats' | 'walls'
    'walls' -> 'the'
    'cats' -> 'the'
    """
    )
    print(grammar)


def sdg_demo():
    """
    A demonstration of how to read a string representation of
    a CoNLL format dependency tree.
    """
    from nltk.parse import DependencyGraph

    dg = DependencyGraph(
        """
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
    """
    )
    tree = dg.tree()
    print(tree.pprint())


def demo():
    cfg_demo()
    pcfg_demo()
    fcfg_demo()
    dg_demo()
    sdg_demo()


if __name__ == "__main__":
    demo()

__all__ = [
    "Nonterminal",
    "nonterminals",
    "CFG",
    "Production",
    "PCFG",
    "ProbabilisticProduction",
    "DependencyGrammar",
    "DependencyProduction",
    "ProbabilisticDependencyGrammar",
    "induce_pcfg",
    "read_grammar",
]
