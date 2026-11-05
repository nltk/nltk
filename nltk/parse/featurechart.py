# Natural Language Toolkit: Chart Parser for Feature-Based Grammars
#
# Copyright (C) 2001-2026 NLTK Project
# Author: Rob Speer <rspeer@mit.edu>
#         Peter Ljunglöf <peter.ljunglof@heatherleaf.se>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
Extension of chart parsing implementation to handle grammars with
feature structures as nodes.
"""

import copy
import functools
import os
import weakref
from time import perf_counter

from nltk.data import make_staging_dir
from nltk.featstruct import (
    TYPE,
    FeatStruct,
    Feature,
    SlashFeature,
    _is_mapping,
    _rename_variable,
    _rename_variables,
    find_variables,
    unify,
)
from nltk.grammar import (
    CFG,
    FeatStructNonterminal,
    Nonterminal,
    Production,
    is_nonterminal,
    is_terminal,
)
from nltk.parse.chart import (
    BottomUpPredictCombineRule,
    BottomUpPredictRule,
    CachedTopDownPredictRule,
    Chart,
    ChartParser,
    EdgeI,
    EmptyPredictRule,
    FundamentalRule,
    LeafInitRule,
    SingleEdgeFundamentalRule,
    TopDownInitRule,
    TreeEdge,
)
from nltk.sem import logic
from nltk.sem.logic import Variable
from nltk.termsec import safe_print
from nltk.tree import Tree

# ////////////////////////////////////////////////////////////
# Tree Edge
# ////////////////////////////////////////////////////////////


class FeatureTreeEdge(TreeEdge):
    """
    A specialized tree edge that allows shared variable bindings
    between nonterminals on the left-hand side and right-hand side.

    Each ``FeatureTreeEdge`` contains a set of ``bindings``, i.e., a
    dictionary mapping from variables to values.  If the edge is not
    complete, then these bindings are simply stored.  However, if the
    edge is complete, then the constructor applies these bindings to
    every nonterminal in the edge whose symbol implements the
    interface ``SubstituteBindingsI``.
    """

    def __init__(self, span, lhs, rhs, dot=0, bindings=None):
        """
        Construct a new edge.  If the edge is incomplete (i.e., if
        ``dot<len(rhs)``), then store the bindings as-is.  If the edge
        is complete (i.e., if ``dot==len(rhs)``), then apply the
        bindings to all nonterminals in ``lhs`` and ``rhs``, and then
        clear the bindings.  See ``TreeEdge`` for a description of
        the other arguments.
        """
        if bindings is None:
            bindings = {}

        # If the edge is complete, then substitute in the bindings,
        # and then throw them away.  (If we didn't throw them away, we
        # might think that 2 complete edges are different just because
        # they have different bindings, even though all bindings have
        # already been applied.)
        if dot == len(rhs) and bindings:
            lhs = self._bind(lhs, bindings)
            rhs = [self._bind(elt, bindings) for elt in rhs]
            bindings = {}

        # Initialize the edge.
        TreeEdge.__init__(self, span, lhs, rhs, dot)
        self._bindings = bindings
        self._comparison_key = (self._comparison_key, tuple(sorted(bindings.items())))

    @staticmethod
    def from_production(production, index):
        """
        :return: A new ``TreeEdge`` formed from the given production.
            The new edge's left-hand side and right-hand side will
            be taken from ``production``; its span will be
            ``(index,index)``; and its dot position will be ``0``.
        :rtype: TreeEdge
        """
        return FeatureTreeEdge(
            span=(index, index), lhs=production.lhs(), rhs=production.rhs(), dot=0
        )

    def move_dot_forward(self, new_end, bindings=None):
        """
        :return: A new ``FeatureTreeEdge`` formed from this edge.
            The new edge's dot position is increased by ``1``,
            and its end index will be replaced by ``new_end``.
        :rtype: FeatureTreeEdge
        :param new_end: The new end index.
        :type new_end: int
        :param bindings: Bindings for the new edge.
        :type bindings: dict
        """
        return FeatureTreeEdge(
            span=(self._span[0], new_end),
            lhs=self._lhs,
            rhs=self._rhs,
            dot=self._dot + 1,
            bindings=bindings,
        )

    def _bind(self, nt, bindings):
        if not isinstance(nt, FeatStructNonterminal):
            return nt
        return nt.substitute_bindings(bindings)

    def next_with_bindings(self):
        return self._bind(self.nextsym(), self._bindings)

    def bindings(self):
        """
        Return a copy of this edge's bindings dictionary.
        """
        return self._bindings.copy()

    def variables(self):
        """
        :return: The set of variables used by this edge.
        :rtype: set(Variable)
        """
        return find_variables(
            [self._lhs]
            + list(self._rhs)
            + list(self._bindings.keys())
            + list(self._bindings.values()),
            fs_class=FeatStruct,
        )

    def __str__(self):
        if self.is_complete():
            return super().__str__()
        else:
            bindings = "{%s}" % ", ".join(
                "%s: %r" % item for item in sorted(self._bindings.items())
            )
            return f"{super().__str__()} {bindings}"


# ////////////////////////////////////////////////////////////
# A specialized Chart for feature grammars
# ////////////////////////////////////////////////////////////

# TODO: subsumes check when adding new edges


class FeatureChart(Chart):
    """
    A Chart for feature grammars.
    :see: ``Chart`` for more information.
    """

    def select(self, **restrictions):
        """
        Returns an iterator over the edges in this chart.
        See ``Chart.select`` for more information about the
        ``restrictions`` on the edges.
        """
        # If there are no restrictions, then return all edges.
        if restrictions == {}:
            return iter(self._edges)

        # Find the index corresponding to the given restrictions.
        restr_keys = sorted(restrictions.keys())
        restr_keys = tuple(restr_keys)

        # If it doesn't exist, then create it.
        if restr_keys not in self._indexes:
            self._add_index(restr_keys)

        vals = tuple(
            self._get_type_if_possible(restrictions[key]) for key in restr_keys
        )
        return iter(self._indexes[restr_keys].get(vals, []))

    def _add_index(self, restr_keys):
        """
        A helper function for ``select``, which creates a new index for
        a given set of attributes (aka restriction keys).
        """
        # Make sure it's a valid index.
        for key in restr_keys:
            if not hasattr(EdgeI, key):
                raise ValueError("Bad restriction: %s" % key)

        # Create the index.
        index = self._indexes[restr_keys] = {}

        # Add all existing edges to the index.
        for edge in self._edges:
            vals = tuple(
                self._get_type_if_possible(getattr(edge, key)()) for key in restr_keys
            )
            index.setdefault(vals, []).append(edge)

    def _register_with_indexes(self, edge):
        """
        A helper function for ``insert``, which registers the new
        edge with all existing indexes.
        """
        for restr_keys, index in self._indexes.items():
            vals = tuple(
                self._get_type_if_possible(getattr(edge, key)()) for key in restr_keys
            )
            index.setdefault(vals, []).append(edge)

    def _get_type_if_possible(self, item):
        """
        Helper function which returns the ``TYPE`` feature of the ``item``,
        if it exists, otherwise it returns the ``item`` itself
        """
        if isinstance(item, dict) and TYPE in item:
            return item[TYPE]
        else:
            return item

    def parses(self, start, tree_class=Tree):
        for edge in self.select(start=0, end=self._num_leaves):
            if (
                (isinstance(edge, FeatureTreeEdge))
                and (edge.lhs()[TYPE] == start[TYPE])
                and (unify(edge.lhs(), start, rename_vars=True))
            ):
                yield from self.trees(edge, complete=True, tree_class=tree_class)


# ////////////////////////////////////////////////////////////
# Shortcuts for Plain Grammars
# ////////////////////////////////////////////////////////////

#: Types of feature value that unify only with an equal value.
_PLAIN_VALUES = (str, int, float, bool, type(None))

#: Types of feature name that unify two such values by equality.
_PLAIN_NAMES = (str, Feature, SlashFeature)

_plain_grammars = weakref.WeakKeyDictionary()


def _plain_fstruct(fstruct, visited):
    if id(fstruct) in visited:
        return True
    visited.add(id(fstruct))
    if _is_mapping(fstruct):
        if any(type(fname) not in _PLAIN_NAMES for fname in fstruct):
            return False
        values = fstruct.values()
    else:
        values = fstruct
    for fval in values:
        if type(fval) in _PLAIN_VALUES or type(fval) is Variable:
            continue
        if not isinstance(fval, FeatStruct) or not _plain_fstruct(fval, visited):
            return False
    return True


def _plain_grammar(grammar):
    """
    Return True if every feature in ``grammar`` has a plain value, a variable
    or a feature structure as its value, and is named by a string or a plain
    ``Feature``.  Unifying such structures fails or succeeds, and never raises
    or draws a new variable name (as a logic expression can), so the shortcuts
    below leave every edge as it was.
    """
    try:
        return _plain_grammars[grammar]
    except KeyError:
        pass
    except TypeError:  # a grammar that can't be weakly referenced
        return _all_plain(grammar)
    plain = _plain_grammars[grammar] = _all_plain(grammar)
    return plain


def _all_plain(grammar):
    visited = set()
    for production in grammar.productions():
        for symbol in (production.lhs(),) + production.rhs():
            if isinstance(symbol, FeatStruct):
                if not _plain_fstruct(symbol, visited):
                    return False
            elif not isinstance(symbol, str):
                return False
    return True


def _plain_clash(fstruct1, fstruct2):
    """
    Return True if a feature named by a string has unequal plain values in
    ``fstruct1`` and ``fstruct2``.  ``unify(fstruct1, fstruct2)`` then fails,
    so on a plain grammar the copies it and ``rename_variables`` make can be
    skipped.
    """
    for fname, fval2 in fstruct2.items():
        if type(fname) is str and fname in fstruct1:
            fval1 = fstruct1[fname]
            if (
                type(fval1) in _PLAIN_VALUES
                and type(fval2) in _PLAIN_VALUES
                and fval1 != fval2
            ):
                return True
    return False


@functools.lru_cache(maxsize=2**14)
def _frozen_production_variables(production):
    return frozenset(
        find_variables((production.lhs(),) + production.rhs(), fs_class=FeatStruct)
    )


def _production_variables(production):
    """
    The variables of a production's nonterminals.  A frozen production can't
    change, so its variables are cached.
    """
    symbols = (production.lhs(),) + production.rhs()
    if all(not isinstance(s, FeatStruct) or s.frozen() for s in symbols):
        return _frozen_production_variables(production)
    return find_variables(symbols, fs_class=FeatStruct)


def _rename_order(fstruct, order, visited):
    # Add the variables of a plain ``fstruct`` to the dict ``order``, in the
    # order ``_rename_variables`` first meets them.
    if id(fstruct) in visited:
        return
    visited.add(id(fstruct))
    items = fstruct.items() if _is_mapping(fstruct) else enumerate(fstruct)
    for fname, fval in items:
        if isinstance(fval, Variable):
            order.setdefault(fval, fval)
        elif isinstance(fval, FeatStruct):
            _rename_order(fval, order, visited)


class _RenameChain:
    """
    Stands in for ``fstruct = fstruct.rename_variables(used_vars=...)`` done
    over and over.  On a plain grammar the renames are worked out on the
    variable names alone, and ``fstruct`` is copied only when ``current()``
    asks for it.
    """

    def __init__(self, fstruct, plain):
        self.plain = plain
        self._fstruct = self._current = fstruct
        # Each variable of ``fstruct`` mapped to its name after the renames.
        self._names = {}
        if plain:
            _rename_order(fstruct, self._names, set())

    def rename(self, used_vars):
        if not self.plain:
            self._current = self._current.rename_variables(used_vars=used_vars)
            return
        # rename_variables renames every variable, in the order it meets them,
        # to a name not in ``used_vars``, in ``fstruct`` or given out before.
        used = set(self._names.values()).union(used_vars)
        for var, name in self._names.items():
            new_name = _rename_variable(name, used)
            self._names[var] = new_name
            used.add(new_name)
        self._current = None

    def current(self):
        if self._current is None:
            self._current = _rename_variables(
                copy.deepcopy(self._fstruct),
                set(),
                set(),
                dict(self._names),
                FeatStruct,
                set(),
            )
        return self._current


# ////////////////////////////////////////////////////////////
# Fundamental Rule
# ////////////////////////////////////////////////////////////


class FeatureFundamentalRule(FundamentalRule):
    r"""
    A specialized version of the fundamental rule that operates on
    nonterminals whose symbols are ``FeatStructNonterminal``s.  Rather
    than simply comparing the nonterminals for equality, they are
    unified.  Variable bindings from these unifications are collected
    and stored in the chart using a ``FeatureTreeEdge``.  When a
    complete edge is generated, these bindings are applied to all
    nonterminals in the edge.

    The fundamental rule states that:

    - ``[A -> alpha \* B1 beta][i:j]``
    - ``[B2 -> gamma \*][j:k]``

    licenses the edge:

    - ``[A -> alpha B3 \* beta][i:j]``

    assuming that B1 and B2 can be unified to generate B3.
    """

    def apply(self, chart, grammar, left_edge, right_edge):
        # Make sure the rule is applicable.
        if not (
            left_edge.end() == right_edge.start()
            and left_edge.is_incomplete()
            and right_edge.is_complete()
            and isinstance(left_edge, FeatureTreeEdge)
        ):
            return
        found = right_edge.lhs()
        nextsym = left_edge.nextsym()
        if isinstance(right_edge, FeatureTreeEdge):
            if not is_nonterminal(nextsym):
                return
            if left_edge.nextsym()[TYPE] != right_edge.lhs()[TYPE]:
                return
            if _plain_grammar(grammar) and _plain_clash(nextsym, found):
                return
            # Create a copy of the bindings.
            bindings = left_edge.bindings()
            # We rename vars here, because we don't want variables
            # from the two different productions to match.
            found = found.rename_variables(used_vars=left_edge.variables())
            # Unify B1 (left_edge.nextsym) with B2 (right_edge.lhs) to
            # generate B3 (result).
            result = unify(nextsym, found, bindings, rename_vars=False)
            if result is None:
                return
        else:
            if nextsym != found:
                return
            # Create a copy of the bindings.
            bindings = left_edge.bindings()

        # Construct the new edge.
        new_edge = left_edge.move_dot_forward(right_edge.end(), bindings)

        # Add it to the chart, with appropriate child pointers.
        if chart.insert_with_backpointer(new_edge, left_edge, right_edge):
            yield new_edge


class FeatureSingleEdgeFundamentalRule(SingleEdgeFundamentalRule):
    """
    A specialized version of the completer / single edge fundamental rule
    that operates on nonterminals whose symbols are ``FeatStructNonterminal``.
    Rather than simply comparing the nonterminals for equality, they are
    unified.
    """

    _fundamental_rule = FeatureFundamentalRule()

    def _apply_complete(self, chart, grammar, right_edge):
        fr = self._fundamental_rule
        for left_edge in chart.select(
            end=right_edge.start(), is_complete=False, nextsym=right_edge.lhs()
        ):
            yield from fr.apply(chart, grammar, left_edge, right_edge)

    def _apply_incomplete(self, chart, grammar, left_edge):
        fr = self._fundamental_rule
        for right_edge in chart.select(
            start=left_edge.end(), is_complete=True, lhs=left_edge.nextsym()
        ):
            yield from fr.apply(chart, grammar, left_edge, right_edge)


# ////////////////////////////////////////////////////////////
# Top-Down Prediction
# ////////////////////////////////////////////////////////////


class FeatureTopDownInitRule(TopDownInitRule):
    def apply(self, chart, grammar):
        for prod in grammar.productions(lhs=grammar.start()):
            new_edge = FeatureTreeEdge.from_production(prod, 0)
            if chart.insert(new_edge, ()):
                yield new_edge


class FeatureTopDownPredictRule(CachedTopDownPredictRule):
    r"""
    A specialized version of the (cached) top down predict rule that operates
    on nonterminals whose symbols are ``FeatStructNonterminal``.  Rather
    than simply comparing the nonterminals for equality, they are
    unified.

    The top down expand rule states that:

    - ``[A -> alpha \* B1 beta][i:j]``

    licenses the edge:

    - ``[B2 -> \* gamma][j:j]``

    for each grammar production ``B2 -> gamma``, assuming that B1
    and B2 can be unified.
    """

    def apply(self, chart, grammar, edge):
        if edge.is_complete():
            return
        nextsym, index = edge.nextsym(), edge.end()
        if not is_nonterminal(nextsym):
            return

        # If we've already applied this rule to an edge with the same
        # next & end, and the chart & grammar have not changed, then
        # just return (no new edges to add).
        nextsym_with_bindings = edge.next_with_bindings()
        done = self._done.get((nextsym_with_bindings, index), (None, None))
        if done[0] is chart and done[1] is grammar:
            return

        plain = _plain_grammar(grammar)
        for prod in grammar.productions(lhs=nextsym):
            # If the left corner in the predicted production is
            # leaf, it must match with the input.
            if prod.rhs():
                first = prod.rhs()[0]
                if is_terminal(first):
                    if index >= chart.num_leaves():
                        continue
                    if first != chart.leaf(index):
                        continue

            # We rename vars here, because we don't want variables
            # from the two different productions to match.
            if plain and _plain_clash(prod.lhs(), nextsym_with_bindings):
                continue
            if unify(prod.lhs(), nextsym_with_bindings, rename_vars=True):
                new_edge = FeatureTreeEdge.from_production(prod, edge.end())
                if chart.insert(new_edge, ()):
                    yield new_edge

        # Record the fact that we've applied this rule.
        self._done[nextsym_with_bindings, index] = (chart, grammar)


# ////////////////////////////////////////////////////////////
# Bottom-Up Prediction
# ////////////////////////////////////////////////////////////


class FeatureBottomUpPredictRule(BottomUpPredictRule):
    def apply(self, chart, grammar, edge):
        if edge.is_incomplete():
            return
        for prod in grammar.productions(rhs=edge.lhs()):
            if isinstance(edge, FeatureTreeEdge):
                _next = prod.rhs()[0]
                if not is_nonterminal(_next):
                    continue

            new_edge = FeatureTreeEdge.from_production(prod, edge.start())
            if chart.insert(new_edge, ()):
                yield new_edge


class FeatureBottomUpPredictCombineRule(BottomUpPredictCombineRule):
    def apply(self, chart, grammar, edge):
        if edge.is_incomplete():
            return
        found = edge.lhs()
        renamed = None
        for prod in grammar.productions(rhs=found):
            bindings = {}
            if isinstance(edge, FeatureTreeEdge):
                _next = prod.rhs()[0]
                if not is_nonterminal(_next):
                    continue

                # We rename vars here, because we don't want variables
                # from the two different productions to match.
                if renamed is None:
                    renamed = _RenameChain(found, _plain_grammar(grammar))
                renamed.rename(_production_variables(prod))
                if renamed.plain and _plain_clash(_next, found):
                    continue

                result = unify(_next, renamed.current(), bindings, rename_vars=False)
                if result is None:
                    continue

            new_edge = FeatureTreeEdge.from_production(
                prod, edge.start()
            ).move_dot_forward(edge.end(), bindings)
            if chart.insert(new_edge, (edge,)):
                yield new_edge


class FeatureEmptyPredictRule(EmptyPredictRule):
    def apply(self, chart, grammar):
        for prod in grammar.productions(empty=True):
            for index in range(chart.num_leaves() + 1):
                new_edge = FeatureTreeEdge.from_production(prod, index)
                if chart.insert(new_edge, ()):
                    yield new_edge


# ////////////////////////////////////////////////////////////
# Feature Chart Parser
# ////////////////////////////////////////////////////////////

TD_FEATURE_STRATEGY = [
    LeafInitRule(),
    FeatureTopDownInitRule(),
    FeatureTopDownPredictRule(),
    FeatureSingleEdgeFundamentalRule(),
]
BU_FEATURE_STRATEGY = [
    LeafInitRule(),
    FeatureEmptyPredictRule(),
    FeatureBottomUpPredictRule(),
    FeatureSingleEdgeFundamentalRule(),
]
BU_LC_FEATURE_STRATEGY = [
    LeafInitRule(),
    FeatureEmptyPredictRule(),
    FeatureBottomUpPredictCombineRule(),
    FeatureSingleEdgeFundamentalRule(),
]


class FeatureChartParser(ChartParser):
    def __init__(
        self,
        grammar,
        strategy=BU_LC_FEATURE_STRATEGY,
        trace_chart_width=20,
        chart_class=FeatureChart,
        **parser_args,
    ):
        ChartParser.__init__(
            self,
            grammar,
            strategy=strategy,
            trace_chart_width=trace_chart_width,
            chart_class=chart_class,
            **parser_args,
        )


class FeatureTopDownChartParser(FeatureChartParser):
    def __init__(self, grammar, **parser_args):
        FeatureChartParser.__init__(self, grammar, TD_FEATURE_STRATEGY, **parser_args)


class FeatureBottomUpChartParser(FeatureChartParser):
    def __init__(self, grammar, **parser_args):
        FeatureChartParser.__init__(self, grammar, BU_FEATURE_STRATEGY, **parser_args)


class FeatureBottomUpLeftCornerChartParser(FeatureChartParser):
    def __init__(self, grammar, **parser_args):
        FeatureChartParser.__init__(
            self, grammar, BU_LC_FEATURE_STRATEGY, **parser_args
        )


# ////////////////////////////////////////////////////////////
# Instantiate Variable Chart
# ////////////////////////////////////////////////////////////


class InstantiateVarsChart(FeatureChart):
    """
    A specialized chart that 'instantiates' variables whose names
    start with '@', by replacing them with unique new variables.
    In particular, whenever a complete edge is added to the chart, any
    variables in the edge's ``lhs`` whose names start with '@' will be
    replaced by unique new ``Variable``.
    """

    def __init__(self, tokens):
        FeatureChart.__init__(self, tokens)

    def initialize(self):
        self._instantiated = set()
        FeatureChart.initialize(self)

    def insert(self, edge, child_pointer_list):
        if edge in self._instantiated:
            return False
        self.instantiate_edge(edge)
        return FeatureChart.insert(self, edge, child_pointer_list)

    def instantiate_edge(self, edge):
        """
        If the edge is a ``FeatureTreeEdge``, and it is complete,
        then instantiate all variables whose names start with '@',
        by replacing them with unique new variables.

        Note that instantiation is done in-place, since the
        parsing algorithms might already hold a reference to
        the edge for future use.
        """
        # If the edge is a leaf, or is not complete, or is
        # already in the chart, then just return it as-is.
        if not isinstance(edge, FeatureTreeEdge):
            return
        if not edge.is_complete():
            return
        if edge in self._edge_to_cpls:
            return

        # Get a list of variables that need to be instantiated.
        # If there are none, then return as-is.
        inst_vars = self.inst_vars(edge)
        if not inst_vars:
            return

        # Instantiate the edge!
        self._instantiated.add(edge)
        edge._lhs = edge.lhs().substitute_bindings(inst_vars)

    def inst_vars(self, edge):
        return {
            var: logic.unique_variable()
            for var in edge.lhs().variables()
            if var.name.startswith("@")
        }


# ////////////////////////////////////////////////////////////
# Demo
# ////////////////////////////////////////////////////////////


def demo_grammar():
    from nltk.grammar import FeatureGrammar

    return FeatureGrammar.fromstring(
        """
S  -> NP VP
PP -> Prep NP
NP -> NP PP
VP -> VP PP
VP -> Verb NP
VP -> Verb
NP -> Det[pl=?x] Noun[pl=?x]
NP -> "John"
NP -> "I"
Det -> "the"
Det -> "my"
Det[-pl] -> "a"
Noun[-pl] -> "dog"
Noun[-pl] -> "cookie"
Verb -> "ate"
Verb -> "saw"
Prep -> "with"
Prep -> "under"
"""
    )


def demo(
    print_times=True,
    print_grammar=True,
    print_trees=True,
    print_sentence=True,
    trace=1,
    parser=FeatureChartParser,
    sent="I saw John with a dog with my cookie",
):
    import sys
    import time

    safe_print()
    grammar = demo_grammar()
    if print_grammar:
        safe_print(grammar)
        safe_print()
    safe_print("*", parser.__name__)
    if print_sentence:
        safe_print("Sentence:", sent)
    tokens = sent.split()
    t = perf_counter()
    cp = parser(grammar, trace=trace)
    chart = cp.chart_parse(tokens)
    trees = list(chart.parses(grammar.start()))
    if print_times:
        safe_print("Time: %s" % (perf_counter() - t))
    if print_trees:
        for tree in trees:
            safe_print(tree)
    else:
        safe_print("Nr trees:", len(trees))


def run_profile():
    import profile
    import pstats

    # A private staging dir under a data root, not a guessable /tmp path.
    stats_file = os.path.join(make_staging_dir(prefix="nltk_profile_"), "profile.out")
    profile.run("for i in range(1): demo()", stats_file)
    p = pstats.Stats(stats_file)
    p.strip_dirs().sort_stats("time", "cum").print_stats(60)
    p.strip_dirs().sort_stats("cum", "time").print_stats(60)


if __name__ == "__main__":
    from nltk.data import load

    demo()
    safe_print()
    grammar = load("grammars/book_grammars/feat0.fcfg")
    cp = FeatureChartParser(grammar, trace=2)
    sent = "Kim likes children"
    tokens = sent.split()
    trees = cp.parse(tokens)
    for tree in trees:
        safe_print(tree)
