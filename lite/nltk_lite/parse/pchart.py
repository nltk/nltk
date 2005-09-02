# Natural Language Toolkit: Probabilistic Chart Parsers
#
# Copyright (C) 2001-2005 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
#         Steven Bird <sb@csse.unimelb.edu.au>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""
Classes and interfaces for associating probabilities with tree
structures that represent the internal organization of a text.  The
probabilistic parser module defines C{BottomUpChartParse}.

C{BottomUpChartParse} is an abstract class that implements a
bottom-up chart parser for C{PCFG}s.  It maintains a queue of edges,
and adds them to the chart one at a time.  The ordering of this queue
is based on the probabilities associated with the edges, allowing the
parser to expand more likely edges before less likely ones.  Each
subclass implements a different queue ordering, producing different
search strategies.  Currently the following subclasses are defined:

  - C{InsideParse} searches edges in decreasing order of
    their trees' inside probabilities.
  - C{RandomParse} searches edges in random order.
  - C{LongestParse} searches edges in decreasing order of their
    location's length.
  - C{BeamParse} limits the number of edges in the queue, and
    searches edges in decreasing order of their trees' inside
    probabilities.

"""

##//////////////////////////////////////////////////////
##  Bottom-Up PCFG Chart Parser
##//////////////////////////////////////////////////////

# [XX] This might not be implemented quite right -- it would be better
# to associate probabilities with child pointer lists.

from nltk_lite.parse.chart import *
from nltk_lite.parse.tree import ProbabilisticTree
from nltk_lite.parse.cfg import Nonterminal

# Probabilistic edges
class ProbabilisticLeafEdge(LeafEdge):
    def prob(self): return 1.0

class ProbabilisticTreeEdge(TreeEdge):
    def __init__(self, prob, *args, **kwargs):
        self._prob = prob
        TreeEdge.__init__(self, *args, **kwargs)
    def prob(self): return self._prob
    def __cmp__(self, other):
        if self._prob != other.prob(): return -1
        return TreeEdge.__cmp__(self, other)
    def from_production(production, index, p):
        return ProbabilisticTreeEdge(p, (index, index), production.lhs(),
                                     production.rhs(), 0)
    from_production = staticmethod(from_production)

# Rules using probabilistic edges
class BottomUpInitRule(AbstractChartRule):
    NUM_EDGES=0
    def apply_iter(self, chart, grammar):
        for index in range(chart.num_leaves()):
            new_edge = ProbabilisticLeafEdge(chart.leaf(index), index)
            if chart.insert(new_edge, ()):
                yield new_edge

class BottomUpPredictRule(AbstractChartRule):
    NUM_EDGES=1
    def apply_iter(self, chart, grammar, edge):
        if edge.is_incomplete(): return
        for prod in grammar.productions():
            if edge.lhs() == prod.rhs()[0]:
                new_edge = ProbabilisticTreeEdge.from_production(prod, edge.start(), prod.prob())
                if chart.insert(new_edge, ()):
                    yield new_edge
                    
class FundamentalRule(AbstractChartRule):
    NUM_EDGES=2
    def apply_iter(self, chart, grammar, left_edge, right_edge):
        # Make sure the rule is applicable.
        if not (left_edge.end() == right_edge.start() and
                left_edge.next() == right_edge.lhs() and
                left_edge.is_incomplete() and right_edge.is_complete()):
            return

        # Construct the new edge.
        p = left_edge.prob() * right_edge.prob()
        new_edge = ProbabilisticTreeEdge(p,
                            span=(left_edge.start(), right_edge.end()),
                            lhs=left_edge.lhs(), rhs=left_edge.rhs(),
                            dot=left_edge.dot()+1)

        # Add it to the chart, with appropriate child pointers.
        changed_chart = False
        for cpl1 in chart.child_pointer_lists(left_edge):
            if chart.insert(new_edge, cpl1+(right_edge,)):
                changed_chart = True

        # If we changed the chart, then generate the edge.
        if changed_chart: yield new_edge

class SingleEdgeFundamentalRule(AbstractChartRule):
    NUM_EDGES=1

    _fundamental_rule = FundamentalRule()
    
    def apply_iter(self, chart, grammar, edge1):
        fr = self._fundamental_rule
        if edge1.is_incomplete():
            # edge1 = left_edge; edge2 = right_edge
            for edge2 in chart.select(start=edge1.end(), is_complete=True,
                                     lhs=edge1.next()):
                for new_edge in fr.apply_iter(chart, grammar, edge1, edge2):
                    yield new_edge
        else:
            # edge2 = left_edge; edge1 = right_edge
            for edge2 in chart.select(end=edge1.start(), is_complete=False,
                                     next=edge1.lhs()):
                for new_edge in fr.apply_iter(chart, grammar, edge2, edge1):
                    yield new_edge

    def __str__(self): return 'Fundamental Rule'
    
class BottomUpChartParse(AbstractParse):
    """
    An abstract bottom-up parser for C{PCFG}s that uses a C{Chart} to
    record partial results.  C{BottomUpChartParse} maintains a
    queue of edges that can be added to the chart.  This queue is
    initialized with edges for each token in the text that is being
    parsed.  C{BottomUpChartParse} inserts these edges into the
    chart one at a time, starting with the most likely edges, and
    proceeding to less likely edges.  For each edge that is added to
    the chart, it may become possible to insert additional edges into
    the chart; these are added to the queue.  This process continues
    until enough complete parses have been generated, or until the
    queue is empty.

    The sorting order for the queue is not specified by
    C{BottomUpChartParse}.  Different sorting orders will result
    in different search strategies.  The sorting order for the queue
    is defined by the method C{sort_queue}; subclasses are required
    to provide a definition for this method.

    @type _grammar: C{PCFG}
    @ivar _grammar: The grammar used to parse sentences.
    @type _trace: C{int}
    @ivar _trace: The level of tracing output that should be generated
        when parsing a text.
    """
    def __init__(self, grammar, trace=0):
        """
        Create a new C{BottomUpChartParse}, that uses C{grammar}
        to parse texts.

        @type grammar: C{PCFG}
        @param grammar: The grammar used to parse texts.
        @type trace: C{int}
        @param trace: The level of tracing that should be used when
            parsing a text.  C{0} will generate no tracing output;
            and higher numbers will produce more verbose tracing
            output.
        """
        self._grammar = grammar
        self._trace = trace
        AbstractParse.__init__(self)

    def trace(self, trace=2):
        """
        Set the level of tracing output that should be generated when
        parsing a text.

        @type trace: C{int}
        @param trace: The trace level.  A trace level of C{0} will
            generate no tracing output; and higher trace levels will
            produce more verbose tracing output.
        @rtype: C{None}
        """
        self._trace = trace
        
    def get_parse_list(self, tokens):
        chart = Chart(tokens)
        grammar = self._grammar

        # Chart parser rules.
        bu_init = BottomUpInitRule()
        bu = BottomUpPredictRule()
        fr = SingleEdgeFundamentalRule()

        # Our queue!
        queue = []
        
        # Initialize the chart.
        for e in bu_init.apply_iter(chart, grammar):
            if self._trace>1: chart.pp_edge(e,width=2)
            queue.append(e)

        while len(queue) > 0:
            # Re-sort the queue.
            self.sort_queue(queue, chart)

            # Get the best edge.
            edge = queue.pop()
            if self._trace>0:
                print '  %-50s prob=%s' % (chart.pp_edge(edge,width=2),
                                           edge.prob())
            
            # Apply BU & FR to it.
            queue.extend(bu.apply(chart, grammar, edge))
            queue.extend(fr.apply(chart, grammar, edge))

        # Get a list of complete parses.
        parses = chart.parses(grammar.start(), ProbabilisticTree)

        # Assign probabilities to the trees.
        prod_probs = {}
        for prod in grammar.productions():
            prod_probs[prod.lhs(), prod.rhs()] = prod.prob()
        for parse in parses:
            self._setprob(parse, prod_probs)

        # Sort by probability
        parses.sort(lambda a,b: cmp(b.prob(), a.prob()))
        
        return parses

    def _setprob(self, tree, prod_probs):
        if tree.prob() is not None: return
        
        # Get the prob of the CFG production.
        lhs = Nonterminal(tree.node)
        rhs = []
        for child in tree:
            if isinstance(child, Tree):
                rhs.append(Nonterminal(child.node))
            else:
                rhs.append(child)
        prob = prod_probs[lhs, tuple(rhs)]
        
        # Get the probs of children.
        for child in tree:
            if isinstance(child, Tree):
                self._setprob(child, prod_probs)
                prob *= child.prob()

        tree.set_prob(prob)
        
    def sort_queue(self, queue, chart):
        """
        Sort the given queue of C{Edge}s, placing the edge that should
        be tried first at the beginning of the queue.  This method
        will be called after each C{Edge} is added to the queue.

        @param queue: The queue of C{Edge}s to sort.  Each edge in
            this queue is an edge that could be added to the chart by
            the fundamental rule; but that has not yet been added.
        @type queue: C{list} of C{Edge}
        @param chart: The chart being used to parse the text.  This
            chart can be used to provide extra information for sorting
            the queue.
        @type chart: C{Chart}
        @rtype: C{None}
        """
        raise AssertionError, "BottomUpChartParse is an abstract class"

class InsideParse(BottomUpChartParse):
    """
    A bottom-up parser for C{PCFG}s that tries edges in descending
    order of the inside probabilities of their trees.  The X{inside
    probability} of a tree is simply the
    probability of the entire tree, ignoring its context.  In
    particular, the inside probability of a tree generated by
    production M{p} with children M{c[1]}, M{c[2]}, ..., M{c[n]} is
    P(M{p})*P(M{c[1]})*P(M{c[2]})*M{...}*P(M{c[n]}); and the inside
    probability of a token is 1 if it is present in the text, and 0 if
    it is absent.

    This sorting order results in a type of lowest-cost-first search
    strategy.
    """
    # Inherit constructor.
    def sort_queue(self, queue, chart):
        """
        Sort the given queue of edges, in descending order of the
        inside probabilities of the edges' trees.

        @param queue: The queue of C{Edge}s to sort.  Each edge in
            this queue is an edge that could be added to the chart by
            the fundamental rule; but that has not yet been added.
        @type queue: C{list} of C{Edge}
        @param chart: The chart being used to parse the text.  This
            chart can be used to provide extra information for sorting
            the queue.
        @type chart: C{Chart}
        @rtype: C{None}
        """
        queue.sort(lambda e1,e2:cmp(e1.prob(), e2.prob()))

# Eventually, this will become some sort of inside-outside parser:
# class InsideOutsideParse(BottomUpChartParse):
#     def __init__(self, grammar, trace=0):
#         # Inherit docs.
#         BottomUpChartParse.__init__(self, grammar, trace)
#
#         # Find the best path from S to each nonterminal
#         bestp = {}
#         for production in grammar.productions(): bestp[production.lhs()]=0
#         bestp[grammar.start()] = 1.0
#
#         for i in range(len(grammar.productions())):
#             for production in grammar.productions():
#                 lhs = production.lhs()
#                 for elt in production.rhs():
#                     bestp[elt] = max(bestp[lhs]*production.prob(),
#                                      bestp.get(elt,0))
#
#         self._bestp = bestp
#         for (k,v) in self._bestp.items(): print k,v
#
#     def _cmp(self, e1, e2):
#         return cmp(e1.structure()[PROB]*self._bestp[e1.lhs()],
#                    e2.structure()[PROB]*self._bestp[e2.lhs()])
#        
#     def sort_queue(self, queue, chart):
#         queue.sort(self._cmp)

import random
class RandomParse(BottomUpChartParse):
    """
    A bottom-up parser for C{PCFG}s that tries edges in random order.
    This sorting order results in a random search strategy.
    """
    # Inherit constructor
    def sort_queue(self, queue, chart):
        i = random.randint(0, len(queue)-1)
        (queue[-1], queue[i]) = (queue[i], queue[-1])

class UnsortedParse(BottomUpChartParse):
    """
    A bottom-up parser for C{PCFG}s that tries edges in whatever order.
    """
    # Inherit constructor
    def sort_queue(self, queue, chart): return

class LongestParse(BottomUpChartParse):
    """
    A bottom-up parser for C{PCFG}s that tries longer edges before
    shorter ones.  This sorting order results in a type of best-first
    search strategy.
    """
    # Inherit constructor
    def sort_queue(self, queue, chart):
        queue.sort(lambda e1,e2: cmp(e1.length(), e2.length()))

class BeamParse(BottomUpChartParse):
    """
    A bottom-up parser for C{PCFG}s that limits the number of edges in
    its edge queue.
    """
    def __init__(self, beam_size, grammar, trace=0):
        """
        Create a new C{BottomUpChartParse}, that uses C{grammar}
        to parse texts.

        @type beam_size: C{int}
        @param beam_size: The maximum length for the parser's edge queue.
        @type grammar: C{pcfg.Grammar}
        @param grammar: The grammar used to parse texts.
        @type trace: C{int}
        @param trace: The level of tracing that should be used when
            parsing a text.  C{0} will generate no tracing output;
            and higher numbers will produce more verbose tracing
            output.
        """
        BottomUpChartParse.__init__(self, grammar, trace)
        self._beam_size = beam_size
        
    def sort_queue(self, queue, chart):
        queue.sort(lambda e1,e2:cmp(e1.prob(), e2.prob()))
        if len(queue) > self._beam_size:
            split = len(queue)-self._beam_size
            if self._trace > 2:
                for edge in queue[:split]:
                    print '  %-50s [DISCARDED]' % chart.pp_edge(edge,2)
            queue[:] = queue[split:]

##//////////////////////////////////////////////////////
##  Test Code
##//////////////////////////////////////////////////////

def demo():
    """
    A demonstration of the probabilistic parsers.  The user is
    prompted to select which demo to run, and how many parses should
    be found; and then each parser is run on the same demo, and a
    summary of the results are displayed.
    """
    import sys, time
    from nltk_lite import tokenize
    from nltk_lite.parse import cfg, pcfg, pchart

    # Define two demos.  Each demo has a sentence and a grammar.
    demos = [('I saw John with my cookie', pcfg.toy1),
             ('the boy saw Jack with Bob under the table with a telescope',
              pcfg.toy2)]

    # Ask the user which demo they want to use.
    print
    for i in range(len(demos)):
        print '%3s: %s' % (i+1, demos[i][0])
        print '     %r' % demos[i][1]
        print
    print 'Which demo (%d-%d)? ' % (1, len(demos)),
    try:
        snum = int(sys.stdin.readline().strip())-1
        sent, grammar = demos[snum]
    except:
        print 'Bad sentence number'
        return

    # Tokenize the sentence.
    tokens = list(tokenize.whitespace(sent))

    # Define a list of parsers.  We'll use all parsers.
    parsers = [
        pchart.InsideParse(grammar),
        pchart.RandomParse(grammar),
        pchart.UnsortedParse(grammar),
        pchart.LongestParse(grammar),
        pchart.BeamParse(len(tokens)+1, grammar)
        ]

    # Run the parsers on the tokenized sentence.
    times = []
    average_p = []
    num_parses = []
    all_parses = {}
    for parser in parsers:
        print '\ns: %s\nparser: %s\ngrammar: %s' % (sent,parser,pcfg)
        parser.trace(3)
        t = time.time()
        parses = parser.get_parse_list(tokens)
        times.append(time.time()-t)
        if parses: p = reduce(lambda a,b:a+b.prob(), parses, 0)/len(parses)
        else: p = 0
        average_p.append(p)
        num_parses.append(len(parses))
        for p in parses: all_parses[p.freeze()] = 1

    # Print some summary statistics
    print
    print '       Parser      | Time (secs)   # Parses   Average P(parse)'
    print '-------------------+------------------------------------------'
    for i in range(len(parsers)):
        print '%18s |%11.4f%11d%19.14f' % (parsers[i].__class__.__name__,
                                         times[i],num_parses[i],average_p[i])
    parses = all_parses.keys()
    if parses: p = reduce(lambda a,b:a+b.prob(), parses, 0)/len(parses)
    else: p = 0
    print '-------------------+------------------------------------------'
    print '%18s |%11s%11d%19.14f' % ('(All Parses)', 'n/a', len(parses), p)

    # Ask the user if we should draw the parses.
    print
    print 'Draw parses (y/n)? ',
    if sys.stdin.readline().strip().lower().startswith('y'):
        from nltk_lite import draw
        print '  please wait...'
        draw.tree.draw_trees(*parses)

    # Ask the user if we should print the parses.
    print
    print 'Print parses (y/n)? ',
    if sys.stdin.readline().strip().lower().startswith('y'):
        for parse in parses:
            print parse

if __name__ == '__main__':
    demo()
