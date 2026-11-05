"""
The feature chart parsers take shortcuts on plain grammars: they skip a
unification that a clash of plain values dooms, and they work out the bottom-up
rule's chain of renames on variable names alone.  Every chart must come out
exactly as it does without them, edge for edge and tree for tree.
"""

import pytest

from nltk.featstruct import FeatStruct, find_variables, unify
from nltk.grammar import FeatureGrammar
from nltk.parse import earleychart, featurechart
from nltk.sem import logic
from nltk.sem.logic import Variable

PARSERS = [
    featurechart.FeatureChartParser,
    featurechart.FeatureBottomUpChartParser,
    featurechart.FeatureBottomUpLeftCornerChartParser,
    featurechart.FeatureTopDownChartParser,
    earleychart.FeatureIncrementalChartParser,
    earleychart.FeatureEarleyChartParser,
    earleychart.FeatureIncrementalTopDownChartParser,
    earleychart.FeatureIncrementalBottomUpChartParser,
    earleychart.FeatureIncrementalBottomUpLeftCornerChartParser,
]

# Agreement through variables (some named ?n2, so renames must step past it),
# a gap through SLASH, an empty production, and left recursion.
PLAIN = FeatureGrammar.fromstring(
    """
% start S
S -> NP[NUM=?n] VP[NUM=?n]
S -> NP[NUM=?n2] VP[NUM=?n2, GAP=?g]/NP
NP[NUM=?n] -> Det[NUM=?n] N[NUM=?n]
NP[NUM=?n] -> NP[NUM=?n] PP
NP[NUM=?n2]/NP ->
VP[NUM=?n, TENSE=?t] -> TV[NUM=?n, TENSE=?t] NP
VP[NUM=?n, TENSE=?t]/NP -> TV[NUM=?n, TENSE=?t] NP/NP
VP[NUM=?n] -> VP[NUM=?n] PP
PP -> P NP
Det[NUM=sg] -> 'this' | 'a'
Det[NUM=pl] -> 'these' | 'all'
Det -> 'the'
N[NUM=sg] -> 'dog' | 'park'
N[NUM=pl] -> 'dogs' | 'parks'
TV[NUM=sg, TENSE=pres] -> 'sees' | 'likes'
TV[NUM=pl, TENSE=pres] -> 'see' | 'like'
TV[TENSE=past] -> 'saw' | 'liked'
P -> 'in' | 'with'
"""
)

SENTENCES = [
    "the dog sees the dogs in the park",
    "these dogs saw a park with all parks",
    "the dog liked",
    "all dogs in the park with the dog like this dog",
]

# Unifications fail on number here, and the sentence has no parse.
UNPARSED = "this dogs see the park"

# From book_grammars/storage.fcfg: its variables also sit inside logic
# expressions and tuples, where the shortcuts would name them wrongly.
STORAGE = FeatureGrammar.fromstring(
    r"""
% start S
S[SEM=[CORE=<?vp(?subj)>, STORE=(?b1+?b2)]] -> NP[SEM=[CORE=?subj, STORE=?b1]] VP[SEM=[CORE=?vp, STORE=?b2]]
VP[SEM=?s] -> IV[SEM=?s]
VP[SEM=[CORE=<?v(?obj)>, STORE=(?b1+?b2)]] -> TV[SEM=[CORE=?v, STORE=?b1]] NP[SEM=[CORE=?obj, STORE=?b2]]
NP[SEM=[CORE=<@x>, STORE=((<bo(?det(?n),@x)>)+?b1+?b2)]] -> Det[SEM=[CORE=?det, STORE=?b1]] N[SEM=[CORE=?n, STORE=?b2]]
Det[SEM=[CORE=<\Q P.exists x.(Q(x) & P(x))>, STORE=(/)]] -> 'a'
Det[SEM=[CORE=<\Q P.all x.(Q(x) implies P(x))>, STORE=(/)]] -> 'every'
N[SEM=[CORE=<dog>, STORE=(/)]] -> 'dog'
N[SEM=[CORE=<girl>, STORE=(/)]] -> 'girl'
IV[SEM=[CORE=<\x.smile(x)>, STORE=(/)]] -> 'smiles'
TV[SEM=[CORE=<\y x.chase(x,y)>, STORE=(/)]] -> 'chases'
NP[SEM=[CORE=<@x>, STORE=(<bo(\P.P(angus),@x)>)]] -> 'Angus'
"""
)

STORAGE_SENTENCES = ["a dog smiles", "every girl chases a dog", "Angus chases Angus"]

CASES = (
    [(PLAIN, s, True) for s in SENTENCES]
    + [(PLAIN, UNPARSED, False)]
    + [(STORAGE, s, True) for s in STORAGE_SENTENCES]
)


def _chart(parser_class, grammar, words):
    # Fresh logic variables are numbered by a counter that outlives a parse.
    logic._counter._value = 0
    chart = parser_class(grammar).chart_parse(words)
    edges = sorted(str(edge) for edge in chart.edges())
    trees = [str(tree) for tree in chart.parses(grammar.start())]
    return edges, trees


@pytest.mark.parametrize("parser_class", PARSERS, ids=lambda c: c.__name__)
@pytest.mark.parametrize("grammar, sentence, parses", CASES)
def test_shortcuts_leave_every_edge_and_tree(
    parser_class, grammar, sentence, parses, monkeypatch
):
    words = sentence.split()
    fast = _chart(parser_class, grammar, words)
    assert bool(fast[1]) == parses, sentence
    monkeypatch.setattr(
        featurechart.PlainGrammar, "is_plain", staticmethod(lambda grammar: False)
    )
    assert fast == _chart(parser_class, grammar, words)


def test_plain_grammars_are_told_apart():
    assert featurechart.PlainGrammar.is_plain(PLAIN)
    assert not featurechart.PlainGrammar.is_plain(STORAGE)
    # The answer is kept for the grammar's lifetime, keyed by the grammar.
    assert PLAIN in featurechart.PlainGrammar._known


def test_plain_clash_only_where_unify_fails():
    symbols = {
        symbol
        for production in PLAIN.productions()
        for symbol in (production.lhs(),) + production.rhs()
        if isinstance(symbol, FeatStruct)
    }
    clashes = 0
    for fstruct1 in symbols:
        for fstruct2 in symbols:
            if featurechart.PlainGrammar.clash(fstruct1, fstruct2):
                clashes += 1
                assert unify(fstruct1, fstruct2) is None, (fstruct1, fstruct2)
    assert clashes


@pytest.mark.parametrize(
    "text",
    [
        "[a=?x, b=[c=?x, d=?y2], e=(1)[f=?y], g->(1)]",
        "[a=?x2, b=?x, c=?x3, d=[e=?x2]]",
        "[a=1, b=[c=sg]]",
    ],
)
def test_rename_chain_names_variables_as_rename_variables_does(text):
    fstruct = FeatStruct(text)
    fstruct.freeze()
    used = [
        {Variable("?x"), Variable("?x2")},
        set(),
        {Variable("?y3"), Variable("?x4")},
        {Variable("?y")},
    ]
    chain = featurechart.PlainGrammar.RenameChain(fstruct, True)
    expected = fstruct
    for used_vars in used:
        chain.rename(used_vars)
        expected = expected.rename_variables(used_vars=used_vars)
        assert repr(chain.current()) == repr(expected)
    # Renames left unbuilt in between still end at the same names.
    chain = featurechart.PlainGrammar.RenameChain(fstruct, True)
    for used_vars in used:
        chain.rename(used_vars)
    assert repr(chain.current()) == repr(expected)


def test_production_variables_match_find_variables():
    for production in PLAIN.productions():
        symbols = (production.lhs(),) + production.rhs()
        expected = find_variables(symbols, fs_class=FeatStruct)
        assert featurechart._production_variables(production) == expected
