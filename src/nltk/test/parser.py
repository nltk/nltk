# Natural Language Toolkit: Test Code for parsers
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

"""
Unit testing for L{nltk.parser}.
"""

from nltk.parser import *
from nltk.cfg import *
from nltk.tokenizer import WhitespaceTokenizer
from nltk.tagger import TaggedTokenizer
from nltk.token import *

# Build some shared grammars, etc.

cfg1 = CFG.parse("""
# Grammar productions:
S -> NP VP
NP -> Det N
VP -> V NP PP
NP -> Det N PP
PP -> P NP
# Lexical productions:
NP -> 'I'
Det -> 'the' | 'a' | 'an'
N -> 'man' | 'dog' | 'cookie' | 'telescope' | 'park'
V -> 'saw'
P -> 'in' | 'with'
""")

cfg2 = CFG.parse("""
# Grammar productions:
S -> NP VP
NP -> Det N
VP -> V NP PP |V NP
NP -> Det N PP
PP -> P NP
# Lexical productions:
NP -> 'I'
Det -> 'the' | 'a' | 'an'
N -> 'man' | 'dog' | 'cookie' | 'telescope' | 'park'
V -> 'saw'
P -> 'in' | 'with'
""")

S, VP, NP, PP = nonterminals('S, VP, NP, PP')
V, N, P, Name, Det = nonterminals('V, N, P, Name, Det')
grammar_productions1 = [
        PCFGProduction(NP, [Det, N], prob=0.5),
        PCFGProduction(NP, [NP, PP], prob=0.25),
        PCFGProduction(NP, ['John'], prob=0.1),
        PCFGProduction(NP, ['I'], prob=0.15), 
        PCFGProduction(Det, ['the'], prob=0.4),
        PCFGProduction(Det, ['a'], prob=0.4),
        PCFGProduction(Det, ['my'], prob=0.2),
        PCFGProduction(N, ['dog'], prob=0.4),
        PCFGProduction(N, ['man'], prob=0.1),
        PCFGProduction(N, ['cookie'], prob=0.2),
        PCFGProduction(N, ['telescope'], prob=0.1),
        PCFGProduction(N, ['park'], prob=0.2),
        PCFGProduction(VP, [VP, PP], prob=0.1),
        PCFGProduction(VP, [V, NP], prob=0.7),
        PCFGProduction(VP, [V], prob=0.2),
        PCFGProduction(V, ['ate'], prob=0.35),
        PCFGProduction(V, ['saw'], prob=0.65),
        PCFGProduction(S, [NP, VP], prob=1.0),
        PCFGProduction(PP, [P, NP], prob=1.0),
        PCFGProduction(P, ['with'], prob=0.61),
        PCFGProduction(P, ['in'], prob=0.39)]
pcfg1 = PCFG(S, grammar_productions1)

def test_basic_parsers(): r"""
Unit tests for L{nltk.parser.ShiftReduceParser} and
L{nltk.parser.RecursiveDescentParser}.

Create a sample sentence:

    >>> sent = Token(TEXT='I saw a man in the park')
    >>> WhitespaceTokenizer().tokenize(sent)

Create a shift-reduce parser and parse the sentence.

    >>> parser = ShiftReduceParser(cfg1, LEAF='TEXT')
    >>> parser.parse_n(sent)
    >>> for tree in sent['TREES']:
    ...     print tree
    (S:
      (NP: <I>)
      (VP:
        (V: <saw>)
        (NP: (Det: <a>) (N: <man>))
        (PP: (P: <in>) (NP: (Det: <the>) (N: <park>)))))

Create a shift-reduce parser and parse the sentence.

    >>> parser = RecursiveDescentParser(cfg2, LEAF='TEXT')
    >>> parser.parse_n(sent)
    >>> for tree in sent['TREES']:
    ...     print tree
    (S:
      (NP: <I>)
      (VP:
        (V: <saw>)
        (NP: (Det: <a>) (N: <man>))
        (PP: (P: <in>) (NP: (Det: <the>) (N: <park>)))))
    (S:
      (NP: <I>)
      (VP:
        (V: <saw>)
        (NP:
          (Det: <a>)
          (N: <man>)
          (PP: (P: <in>) (NP: (Det: <the>) (N: <park>))))))
"""

def test_chart_parsers(): r"""
Unit tests for L{nltk.parser.chart}

    >>> from nltk.parser.chart import *

Create a sample sentence:

    >>> sent = Token(TEXT='I saw a man in the park')
    >>> WhitespaceTokenizer().tokenize(sent)

Top down parser:

    >>> parser = ChartParser(cfg2, TD_STRATEGY, LEAF='TEXT')
    >>> parser.parse_n(sent)
    >>> for tree in sent['TREES']:
    ...     print tree
    (S:
      (NP: <I>)
      (VP:
        (V: <saw>)
        (NP:
          (Det: <a>)
          (N: <man>)
          (PP: (P: <in>) (NP: (Det: <the>) (N: <park>))))))
    (S:
      (NP: <I>)
      (VP:
        (V: <saw>)
        (NP: (Det: <a>) (N: <man>))
        (PP: (P: <in>) (NP: (Det: <the>) (N: <park>)))))
        
Bottom-up parser:

    >>> from nltk.parser.chart import *
    >>> parser = ChartParser(cfg2, BU_STRATEGY, LEAF='TEXT')
    >>> parser.parse_n(sent)
    >>> for tree in sent['TREES']:
    ...     print tree
    (S:
      (NP: <I>)
      (VP:
        (V: <saw>)
        (NP:
          (Det: <a>)
          (N: <man>)
          (PP: (P: <in>) (NP: (Det: <the>) (N: <park>))))))
    (S:
      (NP: <I>)
      (VP:
        (V: <saw>)
        (NP: (Det: <a>) (N: <man>))
        (PP: (P: <in>) (NP: (Det: <the>) (N: <park>)))))
        
"""

def test_probabilistic_parsers(): r"""
Unit tests for L{nltk.parser.probabilistic}

    >>> from nltk.parser.probabilistic import *

Create a sample sentence:

    >>> sent = Token(TEXT='I saw a man in the park')
    >>> WhitespaceTokenizer().tokenize(sent)

Parse it:

    >>> from nltk.parser.probabilistic import *
    >>> parser = InsidePCFGParser(pcfg1, LEAF='TEXT')
    >>> parser.parse_n(sent)
    >>> for tree in sent['TREES']:
    ...     print tree
    (S:
      (NP: <I>)
      (VP:
        (V: <saw>)
        (NP:
          (NP: (Det: <a>) (N: <man>))
          (PP: (P: <in>) (NP: (Det: <the>) (N: <park>)))))) (p=5.3235e-06)
    (S:
      (NP: <I>)
      (VP:
        (VP: (V: <saw>) (NP: (Det: <a>) (N: <man>)))
        (PP: (P: <in>) (NP: (Det: <the>) (N: <park>))))) (p=2.1294e-06)

    >>> from nltk.parser.probabilistic import *
    >>> parser = ViterbiPCFGParser(pcfg1, LEAF='TEXT')
    >>> parser.parse_n(sent)
    >>> for tree in sent['TREES']:
    ...     print tree
    (S:
      (NP: <I>)
      (VP:
        (V: <saw>)
        (NP:
          (NP: (Det: <a>) (N: <man>))
          (PP: (P: <in>) (NP: (Det: <the>) (N: <park>)))))) (p=5.3235e-06)
"""

def test_regexp_chunk_parser(): r"""
Unit tests for L{nltk.parser.chunk}

    >>> from nltk.parser.chunk import *

Create a sample sentence:

    >>> text = '''
    ... the/DT little/JJ cat/NN sat/VBD on/IN the/DT mat/NN ./.
    ... The/DT cats/NNS ./.
    ... John/NNP saw/VBD the/DT cat/NN the/DT dog/NN liked/VBD ./.'''
    >>> sent = Token(TEXT=text)
    >>> TaggedTokenizer().tokenize(sent)

Do NP chunking with various rules:

    >>> r1 = ChunkRule(r'<DT>?<JJ>*<NN.*>', 'Chunk NPs')
    >>> cp = RegexpChunkParser([r1], chunk_node='NP', top_node='S')
    >>> cp.parse(sent)
    >>> print sent['TREE']
    (S:
      (NP: <the/DT> <little/JJ> <cat/NN>)
      <sat/VBD>
      <on/IN>
      (NP: <the/DT> <mat/NN>)
      <./.>
      (NP: <The/DT> <cats/NNS>)
      <./.>
      (NP: <John/NNP>)
      <saw/VBD>
      (NP: <the/DT> <cat/NN>)
      (NP: <the/DT> <dog/NN>)
      <liked/VBD>
      <./.>)

    >>> r1 = ChunkRule(r'<.*>+', 'Chunk everything')
    >>> r2 = ChinkRule(r'<VB.*>|<IN>|<\.>', 'Unchunk VB and IN and .')
    >>> cp = RegexpChunkParser([r1, r2], chunk_node='NP', top_node='S')
    >>> cp.parse(sent)
    >>> print sent['TREE']
    (S:
      (NP: <the/DT> <little/JJ> <cat/NN>)
      <sat/VBD>
      <on/IN>
      (NP: <the/DT> <mat/NN>)
      <./.>
      (NP: <The/DT> <cats/NNS>)
      <./.>
      (NP: <John/NNP>)
      <saw/VBD>
      (NP: <the/DT> <cat/NN> <the/DT> <dog/NN>)
      <liked/VBD>
      <./.>)

    >>> r1 = ChunkRule(r'(<DT|JJ|NN.*>+)', 'Chunk sequences of DT&JJ&NN')
    >>> r2 = SplitRule('', r'<DT>', 'Split before DT')
    >>> cp = RegexpChunkParser([r1,r2], chunk_node='NP', top_node='S')
    >>> cp.parse(sent)
    >>> print sent['TREE']
    (S:
      (NP: <the/DT> <little/JJ> <cat/NN>)
      <sat/VBD>
      <on/IN>
      (NP: <the/DT> <mat/NN>)
      <./.>
      (NP: <The/DT> <cats/NNS>)
      <./.>
      (NP: <John/NNP>)
      <saw/VBD>
      (NP: <the/DT> <cat/NN>)
      (NP: <the/DT> <dog/NN>)
      <liked/VBD>
      <./.>)
"""

def test_basic_parser_trace(): r"""
Unit tests for L{nltk.parser.ShiftReduceParser} and
L{nltk.parser.RecursiveDescentParser}.

Create a sample sentence:

    >>> sent = Token(TEXT='I saw a man in the park')
    >>> WhitespaceTokenizer().tokenize(sent)

Create a shift-reduce parser and parse the sentence.

    >>> parser = ShiftReduceParser(cfg1, LEAF='TEXT')
    >>> parser.trace()
    >>> parser.parse(sent)
    Parsing 'I saw a man in the park'
        [ * 'I' 'saw' 'a' 'man' 'in' 'the' 'park']
      S [ 'I' * 'saw' 'a' 'man' 'in' 'the' 'park']
      R [ <NP> * 'saw' 'a' 'man' 'in' 'the' 'park']
      S [ <NP> 'saw' * 'a' 'man' 'in' 'the' 'park']
      R [ <NP> <V> * 'a' 'man' 'in' 'the' 'park']
      S [ <NP> <V> 'a' * 'man' 'in' 'the' 'park']
      R [ <NP> <V> <Det> * 'man' 'in' 'the' 'park']
      S [ <NP> <V> <Det> 'man' * 'in' 'the' 'park']
      R [ <NP> <V> <Det> <N> * 'in' 'the' 'park']
      R [ <NP> <V> <NP> * 'in' 'the' 'park']
      S [ <NP> <V> <NP> 'in' * 'the' 'park']
      R [ <NP> <V> <NP> <P> * 'the' 'park']
      S [ <NP> <V> <NP> <P> 'the' * 'park']
      R [ <NP> <V> <NP> <P> <Det> * 'park']
      S [ <NP> <V> <NP> <P> <Det> 'park' * ]
      R [ <NP> <V> <NP> <P> <Det> <N> * ]
      R [ <NP> <V> <NP> <P> <NP> * ]
      R [ <NP> <V> <NP> <PP> * ]
      R [ <NP> <VP> * ]
      R [ <S> * ]
    >>> print sent['TREE']
    (S:
      (NP: <I>)
      (VP:
        (V: <saw>)
        (NP: (Det: <a>) (N: <man>))
        (PP: (P: <in>) (NP: (Det: <the>) (N: <park>)))))

Create a shift-reduce parser and parse the sentence.

    >>> parser = RecursiveDescentParser(cfg2, LEAF='TEXT')
    >>> parser.trace(2)
    >>> parser.parse_n(sent)
    Parsing 'I saw a man in the park'
        [ * <S> ]
      E [ * <NP> <VP> ]
      E [ * <Det> <N> <VP> ]
      E [ * <the> <N> <VP> ]
      E [ * <a> <N> <VP> ]
      E [ * <an> <N> <VP> ]
      E [ * <Det> <N> <PP> <VP> ]
      E [ * <the> <N> <PP> <VP> ]
      E [ * <a> <N> <PP> <VP> ]
      E [ * <an> <N> <PP> <VP> ]
      E [ * <I> <VP> ]
      M [ <I> * <VP> ]
      E [ <I> * <V> <NP> <PP> ]
      E [ <I> * <saw> <NP> <PP> ]
      M [ <I> <saw> * <NP> <PP> ]
      E [ <I> <saw> * <Det> <N> <PP> ]
      E [ <I> <saw> * <the> <N> <PP> ]
      E [ <I> <saw> * <a> <N> <PP> ]
      M [ <I> <saw> <a> * <N> <PP> ]
      E [ <I> <saw> <a> * <man> <PP> ]
      M [ <I> <saw> <a> <man> * <PP> ]
      E [ <I> <saw> <a> <man> * <P> <NP> ]
      E [ <I> <saw> <a> <man> * <in> <NP> ]
      M [ <I> <saw> <a> <man> <in> * <NP> ]
      E [ <I> <saw> <a> <man> <in> * <Det> <N> ]
      E [ <I> <saw> <a> <man> <in> * <the> <N> ]
      M [ <I> <saw> <a> <man> <in> <the> * <N> ]
      E [ <I> <saw> <a> <man> <in> <the> * <man> ]
      E [ <I> <saw> <a> <man> <in> <the> * <dog> ]
      E [ <I> <saw> <a> <man> <in> <the> * <cookie> ]
      E [ <I> <saw> <a> <man> <in> <the> * <telescope> ]
      E [ <I> <saw> <a> <man> <in> <the> * <park> ]
      M [ <I> <saw> <a> <man> <in> <the> <park> ]
      + [ <I> <saw> <a> <man> <in> <the> <park> ]
      E [ <I> <saw> <a> <man> <in> * <a> <N> ]
      E [ <I> <saw> <a> <man> <in> * <an> <N> ]
      E [ <I> <saw> <a> <man> <in> * <Det> <N> <PP> ]
      E [ <I> <saw> <a> <man> <in> * <the> <N> <PP> ]
      M [ <I> <saw> <a> <man> <in> <the> * <N> <PP> ]
      E [ <I> <saw> <a> <man> <in> <the> * <man> <PP> ]
      E [ <I> <saw> <a> <man> <in> <the> * <dog> <PP> ]
      E [ <I> <saw> <a> <man> <in> <the> * <cookie> <PP> ]
      E [ <I> <saw> <a> <man> <in> <the> * <telescope> <PP> ]
      E [ <I> <saw> <a> <man> <in> <the> * <park> <PP> ]
      M [ <I> <saw> <a> <man> <in> <the> <park> * <PP> ]
      E [ <I> <saw> <a> <man> <in> <the> <park> * <P> <NP> ]
      E [ <I> <saw> <a> <man> <in> <the> <park> * <in> <NP> ]
      E [ <I> <saw> <a> <man> <in> <the> <park> * <with> <NP> ]
      E [ <I> <saw> <a> <man> <in> * <a> <N> <PP> ]
      E [ <I> <saw> <a> <man> <in> * <an> <N> <PP> ]
      E [ <I> <saw> <a> <man> <in> * <I> ]
      E [ <I> <saw> <a> <man> * <with> <NP> ]
      E [ <I> <saw> <a> * <dog> <PP> ]
      E [ <I> <saw> <a> * <cookie> <PP> ]
      E [ <I> <saw> <a> * <telescope> <PP> ]
      E [ <I> <saw> <a> * <park> <PP> ]
      E [ <I> <saw> * <an> <N> <PP> ]
      E [ <I> <saw> * <Det> <N> <PP> <PP> ]
      E [ <I> <saw> * <the> <N> <PP> <PP> ]
      E [ <I> <saw> * <a> <N> <PP> <PP> ]
      M [ <I> <saw> <a> * <N> <PP> <PP> ]
      E [ <I> <saw> <a> * <man> <PP> <PP> ]
      M [ <I> <saw> <a> <man> * <PP> <PP> ]
      E [ <I> <saw> <a> <man> * <P> <NP> <PP> ]
      E [ <I> <saw> <a> <man> * <in> <NP> <PP> ]
      M [ <I> <saw> <a> <man> <in> * <NP> <PP> ]
      E [ <I> <saw> <a> <man> <in> * <Det> <N> <PP> ]
      E [ <I> <saw> <a> <man> <in> * <the> <N> <PP> ]
      M [ <I> <saw> <a> <man> <in> <the> * <N> <PP> ]
      E [ <I> <saw> <a> <man> <in> <the> * <man> <PP> ]
      E [ <I> <saw> <a> <man> <in> <the> * <dog> <PP> ]
      E [ <I> <saw> <a> <man> <in> <the> * <cookie> <PP> ]
      E [ <I> <saw> <a> <man> <in> <the> * <telescope> <PP> ]
      E [ <I> <saw> <a> <man> <in> <the> * <park> <PP> ]
      M [ <I> <saw> <a> <man> <in> <the> <park> * <PP> ]
      E [ <I> <saw> <a> <man> <in> <the> <park> * <P> <NP> ]
      E [ <I> <saw> <a> <man> <in> <the> <park> * <in> <NP> ]
      E [ <I> <saw> <a> <man> <in> <the> <park> * <with> <NP> ]
      E [ <I> <saw> <a> <man> <in> * <a> <N> <PP> ]
      E [ <I> <saw> <a> <man> <in> * <an> <N> <PP> ]
      E [ <I> <saw> <a> <man> <in> * <Det> <N> <PP> <PP> ]
      E [ <I> <saw> <a> <man> <in> * <the> <N> <PP> <PP> ]
      M [ <I> <saw> <a> <man> <in> <the> * <N> <PP> <PP> ]
      E [ <I> <saw> <a> <man> <in> <the> * <man> <PP> <PP> ]
      E [ <I> <saw> <a> <man> <in> <the> * <dog> <PP> <PP> ]
      E [ <I> <saw> <a> <man> <in> <the> * <cookie> <PP> <PP> ]
      E [ <I> <saw> <a> <man> <in> <the> * <telescope> <PP> <PP> ]
      E [ <I> <saw> <a> <man> <in> <the> * <park> <PP> <PP> ]
      M [ <I> <saw> <a> <man> <in> <the> <park> * <PP> <PP> ]
      E [ <I> <saw> <a> <man> <in> <the> <park> * <P> <NP> <PP> ]
      E [ <I> <saw> <a> <man> <in> <the> <park> * <in> <NP> <PP> ]
      E [ <I> <saw> <a> <man> <in> <the> <park> * <with> <NP> <PP> ]
      E [ <I> <saw> <a> <man> <in> * <a> <N> <PP> <PP> ]
      E [ <I> <saw> <a> <man> <in> * <an> <N> <PP> <PP> ]
      E [ <I> <saw> <a> <man> <in> * <I> <PP> ]
      E [ <I> <saw> <a> <man> * <with> <NP> <PP> ]
      E [ <I> <saw> <a> * <dog> <PP> <PP> ]
      E [ <I> <saw> <a> * <cookie> <PP> <PP> ]
      E [ <I> <saw> <a> * <telescope> <PP> <PP> ]
      E [ <I> <saw> <a> * <park> <PP> <PP> ]
      E [ <I> <saw> * <an> <N> <PP> <PP> ]
      E [ <I> <saw> * <I> <PP> ]
      E [ <I> * <V> <NP> ]
      E [ <I> * <saw> <NP> ]
      M [ <I> <saw> * <NP> ]
      E [ <I> <saw> * <Det> <N> ]
      E [ <I> <saw> * <the> <N> ]
      E [ <I> <saw> * <a> <N> ]
      M [ <I> <saw> <a> * <N> ]
      E [ <I> <saw> <a> * <man> ]
      M [ <I> <saw> <a> <man> ]
      E [ <I> <saw> <a> * <dog> ]
      E [ <I> <saw> <a> * <cookie> ]
      E [ <I> <saw> <a> * <telescope> ]
      E [ <I> <saw> <a> * <park> ]
      E [ <I> <saw> * <an> <N> ]
      E [ <I> <saw> * <Det> <N> <PP> ]
      E [ <I> <saw> * <the> <N> <PP> ]
      E [ <I> <saw> * <a> <N> <PP> ]
      M [ <I> <saw> <a> * <N> <PP> ]
      E [ <I> <saw> <a> * <man> <PP> ]
      M [ <I> <saw> <a> <man> * <PP> ]
      E [ <I> <saw> <a> <man> * <P> <NP> ]
      E [ <I> <saw> <a> <man> * <in> <NP> ]
      M [ <I> <saw> <a> <man> <in> * <NP> ]
      E [ <I> <saw> <a> <man> <in> * <Det> <N> ]
      E [ <I> <saw> <a> <man> <in> * <the> <N> ]
      M [ <I> <saw> <a> <man> <in> <the> * <N> ]
      E [ <I> <saw> <a> <man> <in> <the> * <man> ]
      E [ <I> <saw> <a> <man> <in> <the> * <dog> ]
      E [ <I> <saw> <a> <man> <in> <the> * <cookie> ]
      E [ <I> <saw> <a> <man> <in> <the> * <telescope> ]
      E [ <I> <saw> <a> <man> <in> <the> * <park> ]
      M [ <I> <saw> <a> <man> <in> <the> <park> ]
      + [ <I> <saw> <a> <man> <in> <the> <park> ]
      E [ <I> <saw> <a> <man> <in> * <a> <N> ]
      E [ <I> <saw> <a> <man> <in> * <an> <N> ]
      E [ <I> <saw> <a> <man> <in> * <Det> <N> <PP> ]
      E [ <I> <saw> <a> <man> <in> * <the> <N> <PP> ]
      M [ <I> <saw> <a> <man> <in> <the> * <N> <PP> ]
      E [ <I> <saw> <a> <man> <in> <the> * <man> <PP> ]
      E [ <I> <saw> <a> <man> <in> <the> * <dog> <PP> ]
      E [ <I> <saw> <a> <man> <in> <the> * <cookie> <PP> ]
      E [ <I> <saw> <a> <man> <in> <the> * <telescope> <PP> ]
      E [ <I> <saw> <a> <man> <in> <the> * <park> <PP> ]
      M [ <I> <saw> <a> <man> <in> <the> <park> * <PP> ]
      E [ <I> <saw> <a> <man> <in> <the> <park> * <P> <NP> ]
      E [ <I> <saw> <a> <man> <in> <the> <park> * <in> <NP> ]
      E [ <I> <saw> <a> <man> <in> <the> <park> * <with> <NP> ]
      E [ <I> <saw> <a> <man> <in> * <a> <N> <PP> ]
      E [ <I> <saw> <a> <man> <in> * <an> <N> <PP> ]
      E [ <I> <saw> <a> <man> <in> * <I> ]
      E [ <I> <saw> <a> <man> * <with> <NP> ]
      E [ <I> <saw> <a> * <dog> <PP> ]
      E [ <I> <saw> <a> * <cookie> <PP> ]
      E [ <I> <saw> <a> * <telescope> <PP> ]
      E [ <I> <saw> <a> * <park> <PP> ]
      E [ <I> <saw> * <an> <N> <PP> ]
      E [ <I> <saw> * <I> ]
    >>> print sent['TREE']
    (S:
      (NP: <I>)
      (VP:
        (V: <saw>)
        (NP: (Det: <a>) (N: <man>))
        (PP: (P: <in>) (NP: (Det: <the>) (N: <park>)))))

"""

#######################################################################
# Test Runner
#######################################################################

import sys, os, os.path
if __name__ == '__main__': sys.path[0] = None
import unittest, doctest, trace

def testsuite():
    import doctest, nltk.test.parser
    reload(nltk.test.parser)
    return doctest.DocTestSuite(nltk.test.parser)

def test(verbosity=2):
    runner = unittest.TextTestRunner(verbosity=verbosity)
    runner.run(testsuite())

if __name__ == '__main__':
    test()
