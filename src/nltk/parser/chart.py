# Natural Language Toolkit: A Chart Parser
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
# Author: Steven Bird <sb@ldc.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$

"""
Data classes and parser implementations for \"chart parsers\", which
use dynamic programming to efficiently parse a text.  A X{chart
parser} derives parse trees for a text by iteratively adding \"edges\"
to a \"chart.\"  Each X{edge} represents a hypothesis about the tree
structure for a subsequence of the text.  The X{chart} is a
\"blackboard\" for composing and combining these hypotheses.

When a chart parser begins parsing a text, it creates a new (empty)
chart, spanning the text.  It then incrementally adds new edges to the
chart.  A set of X{chart rules} specifies the conditions under which
new edges should be added to the chart.  Once the chart reaches a
stage where none of the chart rules adds any new edges, parsing is
complete.

Charts are encoded with the L{Chart} class, and edges are encoded with
the L{TreeEdge} and L{LeafEdge} classes.  The chart parser module
defines three chart parsers:

  - C{ChartParser} is a simple and flexible chart parser.  Given a
    set of chart rules, it will apply those rules to the chart until
    no more edges are added.

  - C{SteppingChartParser} is a subclass of C{ChartParser} that can
    be used to step through the parsing process.

  - C{EarleyParser} is an implementation of the Earley chart parsing
    algorithm.  It makes a single left-to-right pass through the
    chart, and applies one of three rules (predictor, scanner, and
    completer) to each edge it encounters.
"""
"""
@group Data Types: Chart, EdgeI, ProductionEdge, TokenEdge, FRChart
@group Chart Parsers: ChartParser, SteppingChartParser,
    IncrementalChartParser
@group Chart Rules: ChartRuleI, BottomUpRule, FundamentalRule,
    TopDownRule, TopDownInitRule, IncrementalChartRuleI,
    IncrementalBottomUpRule, IncrementalFundamentalRule,
    IncrementalTopDownRule, IncrementalTopDownInitRule
@sort: ChartParser, SteppingChartParser, IncrementalChartParser,
    Chart, EdgeI, ProductionEdge, TokenEdge, FRChart,
    ChartRuleI, BottomUpRule, FundamentalRule,
    TopDownRule, TopDownInitRule, IncrementalChartRuleI,
    IncrementalBottomUpRule, IncrementalFundamentalRule,
    IncrementalTopDownRule, IncrementalTopDownInitRule, demo
"""

from nltk.chktype import chktype
from nltk.token import Token
from nltk.parser import ParserI
from nltk.tree import TreeToken
from nltk.cfg import CFG, CFGProduction, Nonterminal, nonterminals

########################################################################
##  Edges
########################################################################

class EdgeI:
    """
    A hypothesis about the structure of part of a sentence.
    Each edge records the fact that a structure is (partially)
    consistent with the sentence.  An edge contains:

        - A X{span}, indicating what part of the sentence is
          consistent with the hypothesized structure.
          
        - A X{left-hand side}, specifying what kind of structure is
          hypothesized.

        - A X{right-hand side}, specifying the contents of the
          hypothesized structure.

        - A X{dot position}, indicating how much of the hypothesized
          structure is consistent with the sentence.

    Every edge is either X{complete} or X{incomplete}:

      - An edge is X{complete} if its structure is fully consistent
        with the sentence.

      - An edge is X{incomplete} if its structure is partially
        consistent with the sentence.  For every incomplete edge, the
        span specifies a possible prefix for the edge's structure.
    
    There are two kinds of edge:

        - C{TreeEdges<TreeEdge>} record which trees have been found to
          be (partially) consistent with the text.
          
        - C{LeafEdges<leafEdge>} record the tokens occur in the text.

    The C{EdgeI} interface provides a common interface to both types
    of edge, allowing chart parsers to treat them in a uniform manner.
    """
    def __init__(self):
        if self.__class__ == EdgeI: 
            raise TypeError('Edge is an abstract interface')
        
    #////////////////////////////////////////////////////////////
    # Span
    #////////////////////////////////////////////////////////////

    def span(self):
        """
        @return: A tuple C{(s,e)}, where C{subtokens[s:e]} is the
            portion of the sentence that is consistent with this
            edge's structure.
        @rtype: C{(int, int)}
        """
        raise AssertionError('EdgeI is an abstract interface')

    def start(self):
        """
        @return: The start index of this edge's span.
        @rtype: C{int}
        """
        raise AssertionError('EdgeI is an abstract interface')

    def end(self):
        """
        @return: The end index of this edge's span.
        @rtype: C{int}
        """
        raise AssertionError('EdgeI is an abstract interface')

    def length(self):
        """
        @return: The length of this edge's span.
        @rtype: C{int}
        """
        raise AssertionError('EdgeI is an abstract interface')

    #////////////////////////////////////////////////////////////
    # Left Hand Side
    #////////////////////////////////////////////////////////////

    def lhs(self):
        """
        @return: This edge's left-hand side, which specifies what kind
            of structure is hypothesized by this edge.
        @see: L{TreeEdge} and L{LeafEdge} for a description of
            the left-hand side values for each edge type.
        """
        raise AssertionError('EdgeI is an abstract interface')

    #////////////////////////////////////////////////////////////
    # Right Hand Side
    #////////////////////////////////////////////////////////////

    def rhs(self):
        """
        @return: This edge's right-hand side, which specifies
            the content of the structure hypothesized by this
            edge.
        @see: L{TreeEdge} and L{LeafEdge} for a description of
            the right-hand side values for each edge type.
        """
        raise AssertionError('EdgeI is an abstract interface')

    def dot(self):
        """
        @rtype: C{int}
        @return: This edge's dot position, which indicates how much of
            the hypothesized structure is consistent with the
            sentence.  In particular, C{self.rhs[:dot]} is consistent
            with C{subtoks[self.start():self.end()]}.
        """
        raise AssertionError('EdgeI is an abstract interface')

    def next(self):
        """
        @rtype: C{Nonterminal} or terminal
        @return: The element of this edge's right-hand side that
            immediately follows its dot.
        """
        raise AssertionError('EdgeI is an abstract interface')

    def is_complete(self):
        """
        @rtype: C{boolean}
        @return: True if this edge's structure is fully consistent
            with the text.
        """
        raise AssertionError('EdgeI is an abstract interface')

    def is_incomplete(self):
        """
        @rtype: C{boolean}
        @return: True if this edge's structure is partially consistent
            with the text.
        """
        raise AssertionError('EdgeI is an abstract interface')

    #////////////////////////////////////////////////////////////
    # Comparisons
    #////////////////////////////////////////////////////////////
    def __cmp__(self, other):
        raise AssertionError('EdgeI is an abstract interface')

    def __hash__(self, other):
        raise AssertionError('EdgeI is an abstract interface')

class TreeEdge(EdgeI):
    """
    An edge that records the fact that a tree is (partially)
    consistent with the sentence.  A tree edge consists of:

        - A span, indicating what part of the sentence is consistent
          with the hypothesized tree.
          
        - A left-hand side, specifying the hypothesized tree's node
          value.

        - A X{right-hand side}, specifying the hypothesized tree's
          children.  Each element of the right-hand side is either a
          terminal, specifying a token with that terminal as its leaf
          value; or a nonterminal, specifying a subtree with that
          nonterminal's root value

        - A X{dot position}, indicating which children are consistent
          with the part of the sentence.  In particular, if C{dot}
          is the dot position, C{rhs} is the right-hand size,
          C{(start,end)} is the span, and C{sentence} is the list
          of subtokens in the sentence, then C{subtokens[start:end]}
          can be spanned by the children specified by C{rhs[:dot]}.

    For more information about edges, see the L{EdgeI} interface.
    """
    def __init__(self, span, lhs, rhs, dot=0):
        """
        Construct a new C{TreeEdge}.
        
        @type span: C{(int, int)}
        @param span: A tuple C{(s,e)}, where C{subtokens[s:e]} is the
            portion of the sentence that is consistent with the new
            edge's structure.
        @type lhs: L{Nonterminal}
        @param lhs: The new edge's left-hand side, specifying the
            hypothesized tree's node value.
        @type rhs: C{list} of (L{Nonterminal} and C{string})
        @param rhs: The new edge's right-hand side, specifying the
            hypothesized tree's children.
        @type dot: C{int}
        @param dot: The position of the new edge's dot.  This position
            specifies what prefix of the production's right hand side
            is consistent with the text.  In particular, if
            C{sentence} is the list of subtokens in the sentence, then
            C{subtokens[span[0]:span[1]]} can be spanned by the
            children specified by C{rhs[:dot]}.
        """
        assert chktype(1, span, (int,))
        assert chktype(2, lhs, Nonterminal)
        assert chktype(3, rhs, (Nonterminal, str), [Nonterminal, str])
        assert chktype(4, dot, int)
        self._lhs = lhs
        self._rhs = rhs
        self._span = span
        self._dot = dot

    # Accessors
    def lhs(self): return self._lhs
    def span(self): return self._span
    def start(self): return self._span[0]
    def end(self): return self._span[1]
    def length(self): return self._span[1] - self._span[0]
    def rhs(self): return self._rhs
    def dot(self): return self._dot
    def is_complete(self): return self._dot == len(self._rhs)
    def is_incomplete(self): return self._dot != len(self._rhs)
    def next(self):
        if self._dot >= len(self._rhs): return None
        else: return self._rhs[self._dot]
        

    # Comparisons & hashing
    def __cmp__(self, other):
        if not isinstance(other, TreeEdge): return -1
        return cmp((self._span, self._lhs, self._rhs, self._dot),
                   (other._span, other._lhs, other._rhs, other._dot))
    def __hash__(self):
        return hash((self._lhs, self._rhs, self._span, self._dot))

    # String representation
    def __str__(self):
        str = '%-2s ->' % (self._lhs.symbol(),)
            
        for i in range(len(self._rhs)):
            if i == self._dot: str += ' *'
            if isinstance(self._rhs[i], Nonterminal):
                str += ' %s' % (self._rhs[i].symbol(),)
            else:
                str += ' %r' % (self._rhs[i],)
        if len(self._rhs) == self._dot: str += ' *'
        return str
        
    def __repr__(self):
        return '[Edge: %s]@[%s:%sw]' % (self, self._span[0], self._span[1])

    # Helper constructors
    def from_production(production, index):
        return TreeEdge(span=(index, index), lhs=production.lhs(),
                        rhs=production.rhs(), dot=0)
    from_production = staticmethod(from_production)

class LeafEdge(EdgeI):
    def __init__(self, leaf, index):
        assert chktype(1, leaf, str)
        assert chktype(2, index, int)
        self._leaf = leaf
        self._index = index

    # Accessors
    def lhs(self): return self._leaf
    def span(self): return (self._index, self._index+1)
    def start(self): return self._index
    def end(self): return self._index+1
    def length(self): return 1
    def rhs(self): return ()
    def dot(self): return 0
    def is_complete(self): return True
    def is_incomplete(self): return False
    def next(self): return None

    # Comparisons & hasing
    def __cmp__(self, other):
        if not isinstance(other, LeafEdge): return -1
        return cmp((self._index, self._leaf), (other._index, other._leaf))
    def __hash__(self):
        return hash((self._index, self._leaf))

    # String representations
    def __str__(self):
        return '%r.' % self._leaf
        
    def __repr__(self):
        return '[Edge: %s]@[%s:%sw]' % (self, self._index, self._index+1)

########################################################################
##  Chart
########################################################################

class Chart:
    """
    A blackboard for hypotheses about the syntactic constituents of a
    sentence.  A chart contains a set of edges, where each edge
    encodes a single hypothesis about the structure of some portion of
    the sentence.

    In order to reconstruct the trees that are associated with an
    edge, the chart associates each edge with a set of child pointer
    lists.  A X{child pointer list} is a list of the edges that were
    used to form each edge.  These lists can be used used to
    reconstruct the trees (or partial trees) that are associated with
    each edge.

    The L{select} method can be used to select a specific collection
    of edges.  For example C{chart.select(is_complete=True, start=0)}
    yields all complete edges whose start indices are 0.  To ensure
    the efficiency of these selection operations, C{Chart} dynamically
    creates and maintains an index for each set of attributes that
    have been selected on.
    """
    def __init__(self, token):
        """
        @ivar token: The sentence token whose subtokens are the words
            in this chart.
        """
        self._length = len(token['subtokens'])
        self._token = token

        # A list of edges contained in this chart.
        self._edges = []
        
        # The child pointer list associated with each edge.
        self._edge_to_cpls = {}

        # The edge indexes, used by
        self._indexes = {}

    #////////////////////////////////////////////////////////////
    # Sentence Access
    #////////////////////////////////////////////////////////////

    def length(self):
        return self._length

    def leaf(self, index):
        return self._token['subtokens'][index]['text']

    #////////////////////////////////////////////////////////////
    # Edge access
    #////////////////////////////////////////////////////////////

    def edges(self):
        """
        @return: A list of all edges in this chart.
        @rtype: C{list} of L{EdgeI}
        """
        return self._edges[:]

    def iteredges(self):
        """
        @return: An iterator over the edges in this chart.
        @rtype: C{iter} of L{EdgeI}
        """
        return iter(self._edges)

    # Iterating over the chart gives the edges.
    __iter__ = iteredges

    def num_edges(self):
        """
        @return: The number of edges contained in this chart.
        @rtype: C{int}
        """
        return len(self._edge_to_cpls)

    def select(self, **restrictions):
        """
        @return: An iterator over the edges in this chart.  Any
            new edges that are added to the chart before the iterator
            is exahusted will also be generated.
        @rtype: C{iter} of L{EdgeI}

        @kwarg span: Only generate edges C{e} where C{e.span()==span}
        @kwarg start: Only generate edges C{e} where C{e.start()==start}
        @kwarg end: Only generate edges C{e} where C{e.end()==end}
        @kwarg length: Only generate edges C{e} where C{e.length()==length}
        @kwarg lhs: Only generate edges C{e} where C{e.lhs()==lhs}
        @kwarg rhs: Only generate edges C{e} where C{e.rhs()==rhs}
        @kwarg next: Only generate edges C{e} where C{e.next()==next}
        @kwarg dot: Only generate edges C{e} where C{e.dot()==dot}
        @kwarg is_complete: Only generate edges C{e} where
            C{e.is_complete()==is_complete}
        @kwarg is_incomplete: Only generate edges C{e} where
            C{e.is_incomplete()==is_incomplete}
        """
        # If there are no restrictions, then return all edges.
        if restrictions=={}: return iter(self._edges)
            
        # Find the index corresponding to the given restrictions.
        restr_keys = restrictions.keys()
        restr_keys.sort()
        restr_keys = tuple(restr_keys)

        # If it doesn't exist, then create it.
        if not self._indexes.has_key(restr_keys):
            self._add_index(restr_keys)
                
        vals = [restrictions[k] for k in restr_keys]
        return iter(self._indexes[restr_keys].get(tuple(vals), []))

    def _add_index(self, restr_keys):
        # Make sure it's a valid index.
        for k in restr_keys:
            if not hasattr(EdgeI, k):
                raise ValueError, 'Bad restriction: %s' % k

        # Create the index.
        self._indexes[restr_keys] = {}

        # Add all existing edges to the index.
        for edge in self._edges:
            vals = [getattr(edge, k)() for k in restr_keys]
            index = self._indexes[restr_keys]
            index.setdefault(tuple(vals),[]).append(edge)

    #////////////////////////////////////////////////////////////
    # Edge Insertion
    #////////////////////////////////////////////////////////////

    def insert(self, edge, child_pointer_list):
        """
        Add a new edge to the chart.

        @type edge: L{Edge}
        @param edge: The new edge
        @type child_pointer_list: C{list} of L{Edge}
        @param child_pointer_list: A list of the edges that were used to
            form this edge.  This list is used to reconstruct the trees
            (or partial trees) that are associated with C{edge}.
        """
        # Is it a new edge?
        if not self._edge_to_cpls.has_key(edge):
            # Add it to the list of edges.
            self._edges.append(edge)

            # Register with any generic indices
            for (restr_keys, index) in self._indexes.items():
                vals = [getattr(edge, k)() for k in restr_keys]
                index = self._indexes[restr_keys]
                index.setdefault(tuple(vals),[]).append(edge)
            
        child_pointer_list = tuple(child_pointer_list)
        self._edge_to_cpls.setdefault(edge,{})[child_pointer_list] = 1


    #////////////////////////////////////////////////////////////
    # Tree extraction & child pointer lists
    #////////////////////////////////////////////////////////////

    def parses(self, root):
        """
        @return: A list of the complete tree structures that span
        the entire chart, and whose root node is C{root}.
        """
        trees = []
        for edge in self.edges_spanning((0,self._length)):
            if edge.lhs() == root:
                trees += self.trees(edge)
        return trees

    def trees(self, edge):
        """
        @return: A list of the complete tree structures that are
        associated with C{edge}.
        @rtype: C{list} of L{TreeToken}
        """
        # Memo is a dictionary used to record the trees that we've
        # generated for each edge, so that when we see an edge more
        # than once, we can reuse the same list.
        return self._trees(edge, memo={})

    def _trees(self, edge, memo):
        "A helper function for L{edge_to_trees}."
        trees = []
        
        # Incomplete edges don't stand for any trees.
        if not edge.is_complete(): return []

        # Leaf edges.
        if isinstance(edge, LeafEdge):
            return [self._token['subtokens'][edge.start()]]
        
        # If we've seen this edge before, then reuse our old answer.
        if memo.has_key(edge): return memo[edge]

        # Each child pointer list can be used to form trees.
        for cpl in self.child_pointer_lists(edge):
            # Get the set of child choices for each child pointer.
            # child_choices[i] is the set of choices for the tree's
            # ith child.
            child_choices = [self._trees(cp, memo) for cp in cpl]

            # For each combination of children, add a tree.
            for children in self._choose_children(child_choices):
                lhs = edge.lhs().symbol()
                trees.append(TreeToken(node=lhs, children=children))

        return trees

    def _choose_children(self, child_choices):
        "A helper function for L{_trees}."
        children_lists = [[]]
        for child_choice in child_choices:
            children_lists = [child_list+[child]
                              for child in child_choice
                              for child_list in children_lists]
        return children_lists
    
    def child_pointer_lists(self, edge):
        """
        @rtype: C{list} of C{list} of C{Edge}
        @return: The set of child pointer lists for the given edge.
            Each child pointer list is a list of edges that have
            been used to form this edge.
        """
        # Make a copy, in case they modify it.
        return self._edge_to_cpls.get(edge, {}).keys()

    #////////////////////////////////////////////////////////////
    # Display
    #////////////////////////////////////////////////////////////
    def pp_edge(self, edge, width=3):
        (start, end) = (edge.start(), edge.end())

        str = '|' + ('.'+' '*(width-1))*start

        # Zero-width edges are "#" if complete, ">" if incomplete
        if start == end:
            if edge.is_complete(): str += '#'
            else: str += '>'

        # Spanning complete edges are "[===]"; Other edges are
        # "[---]" if complete, "[--->" if incomplete
        elif edge.is_complete() and edge.span() == (0,self._length):
            str += '['+('='*width)*(end-start-1) + '='*(width-1)+']'
        elif edge.is_complete():
            str += '['+('-'*width)*(end-start-1) + '-'*(width-1)+']'
        else:
            str += '['+('-'*width)*(end-start-1) + '-'*(width-1)+'>'
        
        str += (' '*(width-1)+'.')*(self._length-end)
        return str + '| %s ' % edge #FIXME

    def pp(self, width=5):
        # Draw a header.
        if self._token and width>1:
            header = '|.'
            for tok in self._token['subtokens']:
                header += tok['text'][:width-1].center(width-1)+'.'
            header += '|\n'
            header += '|'+'-'*(self._length*width+1)+'|\n'
        else:
            header = ''
        
        # sort edges: primary key=length, secondary key=start index.
        # (and filter out the token edges)
        edges = [(e.length(), e.start(), e) for e in self]# if len(e.rhs())>0]
        edges.sort()
        edges = [e for (_,_,e) in edges]
        
        return header + '\n'.join([self.pp_edge(edge, width)
                                   for edge in edges])


########################################################################
##  Chart Rules
########################################################################

class ChartRuleI:
    """
    A rule that specifies what new edges are licensed by any given set
    of existing edges.

    @type EDGES: C{int}
    @cvar EDGES: The number of existing edges that this rule uses
        to license new edges.  Typically, this number ranges from
        zero to two.
    """
    def __init__(self):
        # This is a sanity check, to make sure that our definitions of
        # apply() and applicable() are consistant with our definition
        # of EDGES:
        for func in self.apply, self.applicable:
            if func.im_func.func_code.co_argcount != self.EDGES+3:
                raise AssertionError('EDGES is incorrect in for %s.%s' %
                                     (self.__class__, func.__name__))
    
    def apply(self, chart, grammar, *edges):
        """
        Add the edges licensed by this rule and the given edges to the
        chart.

        @type edges: C{list} of L{EdgeI}
        @param edges: A set of existing edges.  The number of edges
            that should be passed to C{apply} is specified by the
            L{EDGES} class variable.
        @rtype: C{list} of L{EdgeI}
        @return: A list of the edges that were added.
        """
        raise AssertionError
    
    def applicable(self, chart, grammar, *edges):
        """
        @rtype: C{boolean}
        @return: True if any edges are licensed by this rule and the
            given edges.
        @type edges: C{list} of L{EdgeI}
        @param edges: A set of existing edges.  The number of edges
            that should be passed to C{apply} is specified by the
            L{EDGES} class variable.
        """
        raise AssertionError

#////////////////////////////////////////////////////////////
# Fundamental Rule
#////////////////////////////////////////////////////////////
class FundamentalRule(ChartRuleI):
    """
    A rule specifying that any pair of edges in the configuration:
        - C{[A->E{alpha}*BE{beta}]@[i:j]
        - C{[B->E{gamma}*]@[j:k]
    licenses the edge::
        - C{[A->E{alpha}B*E{beta}]@[i:j]
    """
    EDGES=2
    def apply(self, chart, grammar, left_edge, right_edge):
        if self.applicable(chart, grammar, left_edge, right_edge):
            span = (left_edge.start(), right_edge.end())
            dot = left_edge.dot()+1
            new_edge = TreeEdge(span, left_edge.lhs(), left_edge.rhs(), dot)
            for cpl1 in chart.child_pointer_lists(left_edge):
                chart.insert(new_edge, cpl1+(right_edge,))
            yield new_edge
    
    def applicable(self, chart, grammar, left_edge, right_edge):
        return (left_edge.end() == right_edge.start() and
                left_edge.next() == right_edge.lhs() and
                left_edge.is_incomplete() and right_edge.is_complete())
    
    def __str__(self): return 'Fundamental Rule'

class FR2(ChartRuleI):
    EDGES=1
    def apply(self, chart, grammar, edge1):
        fr = FundamentalRule()
        if edge1.is_incomplete():
            for edge2 in chart.select(start=edge1.end(), is_complete=True,
                                     lhs=edge1.next()):
                for new_edge in fr.apply(chart, grammar, edge1, edge2):
                    yield new_edge
        else:
            for edge2 in chart.select(end=edge1.start(), is_complete=False,
                                     next=edge1.lhs()):
                for new_edge in fr.apply(chart, grammar, edge2, edge1):
                    yield new_edge
    def applicable(self, chart, grammar, edge1): return True
    
#////////////////////////////////////////////////////////////
# Top-Down Parsing
#////////////////////////////////////////////////////////////
class TopDownInitRule(ChartRuleI):
    """
    A rule specifying that:
        - C{[S->*E{alpha}]@[0:i]}
    is licensed for each grammar production C{S->E{alpha}}, where
    C{S} is the grammar's start symbol.
    """
    EDGES=0
    def apply(self, chart, grammar):
        for prod in grammar.productions():
            if prod.lhs() == grammar.start():
                new_edge = TreeEdge.from_production(prod, 0)
                chart.insert(new_edge, ())
                yield new_edge
    def applicable(self, chart, grammar): return True
    def __str__(self): return 'Top Down Init Rule'

class TopDownExpandRule(ChartRuleI):
    """
    A rule specifying that any edge in the configuration:
        - C{[A->E{alpha}*BE{beta}]@[i:j]}
    licenses the edge:
        - C{[B->*E{gamma}]@[j:j]}
    for each grammar production C{B->E{gamma}}.
    """
    EDGES=1
    def apply(self, chart, grammar, edge):
        for prod in grammar.productions():
            if edge.next() == prod.lhs():
                new_edge = TreeEdge.from_production(prod, edge.end())
                chart.insert(new_edge, ())
                yield new_edge
    def applicable(self, chart, grammar, edge):
        return edge.is_incomplete()
    def __str__(self): return 'Top Down Expand Rule'

class TopDownMatchRule(ChartRuleI):
    EDGES = 1
    def apply(self, chart, grammar, edge):
        index = edge.end()
        if index >= chart.length(): return
        leaf = chart.leaf(index)
        if edge.next() == leaf:
            new_edge = LeafEdge(leaf, index)
            chart.insert(new_edge, ())
            yield new_edge
    def applicable(self, chart, grammar, edge):
        return edge.is_incomplete() and edge.end()<chart.length()
    def __str__(self): return 'Top Down Match Rule'

# Add a cache, to prevent recalculating.
class CachedTopDownInitRule(TopDownInitRule):
    def __init__(self):
        ChartRuleI.__init__(self)
        self._seen = False

    def apply(self, chart, grammar):
        if self._seen: return
        self._seen = True
        for e in TopDownInitRule.apply(self, chart, grammar):
            yield e

class CachedTopDownExpandRule(TopDownExpandRule):
    def __init__(self):
        ChartRuleI.__init__(self)
        self._seen = {}
        
    def apply(self, chart, grammar, edge):
        if self._seen.has_key((edge.next(), edge.end())): return
        self._seen[edge.next(), edge.end()] = 1
        for e in TopDownExpandRule.apply(self, chart, grammar, edge):
            yield e
    

#////////////////////////////////////////////////////////////
# Bottom-Up Parsing
#////////////////////////////////////////////////////////////

class BottomUpInitRule(ChartRuleI):
    EDGES=0
    def apply(self, chart, grammar):
        for index in range(chart.length()):
            new_edge = LeafEdge(chart.leaf(index), index)
            chart.insert(new_edge, ())
            yield new_edge
    def applicable(self, chart, grammar): return True
    def __str__(self): return 'Bottom Up Init Rule'

class BottomUpRule(ChartRuleI):
    EDGES=1
    def apply(self, chart, grammar, edge):
        for prod in grammar.productions():
            if edge.lhs() == prod.rhs()[0]:
                new_edge = TreeEdge.from_production(prod, edge.start())
                chart.insert(new_edge, ())
                yield new_edge
    def applicable(self, chart, grammar, edge): return edge.is_complete()
    def __str__(self): return 'Bottom Up Rule'

#////////////////////////////////////////////////////////////
# Earley Parsing
#////////////////////////////////////////////////////////////

class CompleterRule(ChartRuleI):
    """
    A rule specifying that any complete edge in the configuration:
        - C{[B->E{gamma}*]@[j:k]
    licenses the edge:
        - C{[A->E{alpha}B*E{beta}]@[i:j]
    given an edge of the form:
        - C{[A->E{alpha}*BE{beta}]@[i:j]
    @note: This is basically L{FundamentalRule}, where the left
        edge is left unspecified.
    """
    EDGES=1
    def apply(self, chart, grammar, right_edge):
        fr = FundamentalRule()
        for left_edge in chart.select(end=right_edge.start(),
                                     is_complete=False,
                                     next=right_edge.lhs()):
            for new_edge in fr.apply(chart, grammar, left_edge, right_edge):
                yield new_edge
    def applicable(self, chart, grammar, right_edge):
        return right_edge.is_complete()
    def __str__(self): return 'Completer Rule'

# Strictly speaking, we need this for Earley:
class ScannerRule(ChartRuleI):
    EDGES=1
    def __init__(self, word_to_pos):
        self._word_to_pos = word_to_pos

    def apply(self, chart, gramar, edge):
        index = edge.end()
        if index >= chart.length(): return
        leaf = chart.leaf(index)
        if edge.next() in self._word_to_pos[leaf]:
            new_edge = LeafEdge(leaf, index)
            chart.insert(new_edge, ())
            yield new_edge
    def applicable(self, chart, grammar, edge):
        return edge.is_incomplete() and edge.end()<chart.length()
    def __str__(self): return 'Scanner Rule'

# This is just another name for TopDownExpandRule:
class PredictorRule(TopDownExpandRule):
    def __str__(self): return 'Predictor Rule'

########################################################################
##  Simple Earley Chart Parser
########################################################################

class EarleyChartParser(ParserI):
    def __init__(self, grammar, root_node, lexicon):
        self._grammar = grammar
        self._root_node = root_node
        self._lexicon = lexicon

    def parse(self, token):
        chart = Chart(token)
        self._parse(chart, self._grammar)
        for tree in chart.parses(self._root_node):
            print tree
    
    def _parse(self, chart, grammar):
        root = Nonterminal('-ROOT-')
        edge = TreeEdge((0,0), root, (self._root_node,))
        chart.insert(edge, ())

        predictor = PredictorRule()
        completer = CompleterRule()
        scanner = ScannerRule(self._lexicon)
        
        for end in range(chart.length()+1):
            # Deep trickiness going on here:
            for edge in chart.edges_ending_at(end):
                if edge.is_incomplete():
                    for e in predictor.apply(chart, grammar, edge):
                        print 'P', chart.pp_edge(e)
                    for e in scanner.apply(chart, grammar, edge):
                        print 'S', chart.pp_edge(e)
                elif edge.is_complete():
                    for e in completer.apply(chart, grammar, edge):
                        print 'C', chart.pp_edge(e)

########################################################################
##  Generic Chart Parser
########################################################################
# Apply rules until nothing else gets added.

TD_STRATEGY = [CachedTopDownInitRule(), CachedTopDownExpandRule(), 
               TopDownMatchRule(), CompleterRule()]
BU_STRATEGY = [BottomUpInitRule(), BottomUpRule(), CompleterRule()]

class ChartParser(ParserI):
    def __init__(self, grammar, root_node, strategy):
        self._grammar = grammar
        self._root_node = root_node
        self._strategy = strategy

    def parse(self, token):
        chart = Chart(token)
        self._parse(chart, self._grammar)
        for tree in chart.parses(self._root_node):
            print tree
    
    def _parse(self, chart, grammar):
        num_edges = -1
        while num_edges < chart.num_edges():
            if num_edges >= 0:
                print 'added %d edges' % (chart.num_edges()-num_edges)
            num_edges = chart.num_edges()
            for rule in self._strategy:
                self.apply_everywhere(rule, chart, grammar)

    def apply_everywhere(self, rule, chart, grammar):
        edgelists = [()]
        for i in range(rule.EDGES):
            edgelists = [(edge,)+edgelist
                         for edgelist in edgelists for edge in chart]
        for edgelist in edgelists:
            if rule.applicable(chart, grammar, *edgelist):
                for e in rule.apply(chart, grammar, *edgelist): 
                    #print '%-55s%s' % (chart.pp_edge(e), rule)
                    pass

class QueueChartParser(ParserI):
    """
    Look at each edge exactly once.
    """
        

########################################################################
##  Demo Code
########################################################################

def demo():
    # Define some nonterminals
    S, VP, NP, PP = nonterminals('S, VP, NP, PP')
    V, N, P, Name, Det = nonterminals('V, N, P, Name, Det')

    # Define a gramar.
    productions = [
        CFGProduction(NP, 'John'), CFGProduction(NP, 'I'), 
        CFGProduction(Det, 'the'), CFGProduction(Det, 'my'),
        CFGProduction(Det, 'a'),
        CFGProduction(N, 'dog'),   CFGProduction(N, 'cookie'),
        CFGProduction(V, 'ate'),  CFGProduction(V, 'saw'),
        CFGProduction(P, 'with'), CFGProduction(P, 'under'),
        CFGProduction(S, NP, VP),  CFGProduction(PP, P, NP),
        CFGProduction(NP, Det, N), CFGProduction(NP, NP, PP),
        CFGProduction(VP, VP, PP), CFGProduction(VP, V, NP),
        CFGProduction(VP, V),
        ]
    grammar = CFG(S, productions)

    class PretendLexicon:
        def __getitem__(self, item):
            return [item]

    from nltk.tokenizer import WSTokenizer
    tok = Token(text='John saw the dog with a cookie with a dog')
    #tok = Token(text='John saw')
    WSTokenizer().tokenize(tok)
    #parser = EarleyChartParser(grammar, S, PretendLexicon())
    parser = ChartParser(grammar, S, TD_STRATEGY)
    parser.parse(tok)

import profile
profile.run('demo()')
