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

import re
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
        @return: This edge's dot position, which indicates how much of
            the hypothesized structure is consistent with the
            sentence.  In particular, C{self.rhs[:dot]} is consistent
            with C{subtoks[self.start():self.end()]}.
        @rtype: C{int}
        """
        raise AssertionError('EdgeI is an abstract interface')

    def next(self):
        """
        @return: The element of this edge's right-hand side that
            immediately follows its dot.
        @rtype: C{Nonterminal} or X{terminal} or C{None}
        """
        raise AssertionError('EdgeI is an abstract interface')

    def is_complete(self):
        """
        @return: True if this edge's structure is fully consistent
            with the text.
        @rtype: C{boolean}
        """
        raise AssertionError('EdgeI is an abstract interface')

    def is_incomplete(self):
        """
        @return: True if this edge's structure is partially consistent
            with the text.
        @rtype: C{boolean}
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

        - A X{span}, indicating what part of the sentence is
          consistent with the hypothesized tree.
          
        - A X{left-hand side}, specifying the hypothesized tree's node
          value.

        - A X{right-hand side}, specifying the hypothesized tree's
          children.  Each element of the right-hand side is either a
          terminal, specifying a token with that terminal as its leaf
          value; or a nonterminal, specifying a subtree with that
          nonterminal's symbol as its node value.

        - A X{dot position}, indicating which children are consistent
          with part of the sentence.  In particular, if C{dot} is the
          dot position, C{rhs} is the right-hand size, C{(start,end)}
          is the span, and C{sentence} is the list of subtokens in the
          sentence, then C{subtokens[start:end]} can be spanned by the
          children specified by C{rhs[:dot]}.

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
        self._rhs = tuple(rhs)
        self._span = span
        self._dot = dot

    # [staticmethod]
    def from_production(production, index):
        """
        @return: A new C{TreeEdge} formed from the given production.
            The new edge's left-hand side and right-hand side will
            be taken from C{production}; its span will be C{(index,
            index)}; and its dot position will be C{0}.
        @rtype: L{TreeEdge}
        """
        return TreeEdge(span=(index, index), lhs=production.lhs(),
                        rhs=production.rhs(), dot=0)
    from_production = staticmethod(from_production)

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

class LeafEdge(EdgeI):
    """
    An edge that records the fact that a leaf value is consistent with
    a word in the sentence.  A leaf edge consists of:

      - An X{index}, indicating the position of the word.
      - A X{leaf}, specifying the word's leaf property.

    A leaf edge's left-hand side is its leaf value, and its right hand
    side is C{()}.  Its span is C{[index, index+1]}, and its dot
    position is C{0}.
    """
    def __init__(self, leaf, index):
        """
        Construct a new C{LeafEdge}.

        @param leaf: The new edge's leaf value, specifying the leaf
            property of the word that is recorded by this edge.
        @param index: The new edge's index, specifying the position of
            the word that is recorded by this edge.
        """
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
    def __str__(self): return '%r.' % self._leaf
    def __repr__(self):
        return '[Edge: %s]@[%s:%sw]' % (self, self._index, self._index+1)

########################################################################
##  Chart
########################################################################

class Chart:
    """
    A blackboard for hypotheses about the syntactic constituents of a
    sentence.  A chart contains a set of edges, and each edge encodes
    a single hypothesis about the structure of some portion of the
    sentence.

    The L{select} method can be used to select a specific collection
    of edges.  For example C{chart.select(is_complete=True, start=0)}
    yields all complete edges whose start indices are 0.  To ensure
    the efficiency of these selection operations, C{Chart} dynamically
    creates and maintains an index for each set of attributes that
    have been selected on.

    In order to reconstruct the trees that are represented by an edge,
    the chart associates each edge with a set of child pointer lists.
    A X{child pointer list} is a list of the edges that license an
    edge's right-hand side.

    @inprop: C{subtokens}: The list of subtokens to be parsed.
    @inprop: C{leaf}: The string content of the subtokens.
    @outprop: C{node}: The subtrees' constituent label.
    
    @ivar _token: The sentence that the chart covers.
    @ivar _num_leaves: The number of subtokens in L{_token}.
    @ivar _propnames: The property names that should be used to
        access L{_token}.
    @ivar _edges: A list of the edges in the chart
    @ivar _edge_to_cpls: A dictionary mapping each edge to a set
        of child pointer lists that are associated with that edge.
    @ivar _indexes: A dictionary mapping tuples of edge attributes
        to indices, where each index maps the corresponding edge
        attribute values to lists of edges.
    """
    def __init__(self, token, **propnames):
        """
        Construct a new empty chart.

        @type token: L{Token}
        @ivar token: The sentence that this chart will be used to
            parse.
        @param propnames: A dictionary that can be used to override
            the default property names used by the chart.  Each entry
            maps from a default property name to a new property name.
        """
        assert chktype(1, token, Token)
        subtokens_prop = propnames.get('subtokens', 'subtokens')

        # Record the sentence token and the sentence length.
        self._token = token
        self._num_leaves = len(token[subtokens_prop])

        # Property names, used to access self._token.
        self._propnames = propnames
        
        # A list of edges contained in this chart.
        self._edges = []
        
        # The set of child pointer lists associated with each edge.
        self._edge_to_cpls = {}

        # Indexes mapping attribute values to lists of edges (used by
        # select()).
        self._indexes = {}

    #////////////////////////////////////////////////////////////
    # Sentence Access
    #////////////////////////////////////////////////////////////

    def num_leaves(self):
        """
        @return: The number of words in this chart's sentence.
        @rtype: C{int}
        """
        return self._num_leaves

    def leaf(self, index):
        """
        @return: The leaf value of the word at the given index.
        @rtype: C{string}
        """
        subtokens_prop = self._propnames.get('subtokens', 'subtokens')
        leaf_prop = self._propnames.get('leaf', 'leaf')
        return self._token[subtokens_prop][index][leaf_prop]

    #////////////////////////////////////////////////////////////
    # Edge access
    #////////////////////////////////////////////////////////////

    def edges(self):
        """
        @return: A list of all edges in this chart.  New edges
            that are added to the chart after the call to edges()
            will I{not} be contained in this list.
        @rtype: C{list} of L{EdgeI}
        @see: L{iteredges}, L{select}
        """
        return self._edges[:]

    def iteredges(self):
        """
        @return: An iterator over the edges in this chart.  Any
            new edges that are added to the chart before the iterator
            is exahusted will also be generated.
        @rtype: C{iter} of L{EdgeI}
        @see: L{edges}, L{select}
        """
        return iter(self._edges)

    # Iterating over the chart yields its edges.
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
            is exahusted will also be generated.  C{restrictions}
            can be used to restrict the set of edges that will be
            generated.
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
        """
        A helper function for L{select}, which creates a new index for
        a given set of attributes (aka restriction keys).
        """
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
        @type child_pointer_list: C{tuple} of L{Edge}
        @param child_pointer_list: A list of the edges that were used to
            form this edge.  This list is used to reconstruct the trees
            (or partial trees) that are associated with C{edge}.
        @rtype: C{bool}
        @return: True if this operation modified the chart.  In
            particular, return true iff the chart did not already
            contain C{edge}, or if it did not already associate
            C{child_pointer_list} with C{edge}.
        """
        # Is it a new edge?
        if not self._edge_to_cpls.has_key(edge):
            # Add it to the list of edges.
            self._edges.append(edge)

            # Register with indexes
            for (restr_keys, index) in self._indexes.items():
                vals = [getattr(edge, k)() for k in restr_keys]
                index = self._indexes[restr_keys]
                index.setdefault(tuple(vals),[]).append(edge)

        # Get the set of child pointer lists for this edge.
        cpls = self._edge_to_cpls.setdefault(edge,{})
        child_pointer_list = tuple(child_pointer_list)

        if cpls.has_key(child_pointer_list):
            # We've already got this CPL; return false.
            return False
        else:
            # It's a new CPL; register it, and return true.
            cpls[child_pointer_list] = True
            return True

    #////////////////////////////////////////////////////////////
    # Tree extraction & child pointer lists
    #////////////////////////////////////////////////////////////

    def parses(self, root):
        """
        @return: A list of the complete tree structures that span
        the entire chart, and whose root node is C{root}.
        """
        trees = []
        for edge in self.select(span=(0,self._num_leaves), lhs=root):
            trees += self.trees(edge)
        return trees

    def trees(self, edge):
        """
        @return: A list of the tree structures that are associated
        with C{edge}.

        If C{edge} is incomplete, then the unexpanded children will be
        encoded as childless subtrees, whose node value is the
        corresponding terminal or nonterminal.
            
        @rtype: C{list} of L{TreeToken}
        @note: If two trees share a common subtree, then the same
            C{TreeToken} may be used to encode that subtree in
            both trees.  If you need to eliminate this subtree
            sharing, then create a deep copy of each tree.
        """
        return self._trees(edge, memo={})

    def _trees(self, edge, memo):
        """
        A helper function for L{edge_to_trees}.
        @param memo: A dictionary used to record the trees that we've
            generated for each edge, so that when we see an edge more
            than once, we can reuse the same trees.
        """
        # If we've seen this edge before, then reuse our old answer.
        if memo.has_key(edge): return memo[edge]

        subtokens_prop = self._propnames.get('subtokens', 'subtokens')
        node_prop = self._propnames.get('node', 'node')
        trees = []

        # Until we're done computing the trees for edge, set
        # memo[edge] to be empty.  This has the effect of filtering
        # out any cyclic trees (i.e., trees that contain themselves as
        # descendants), because if we reach this edge via a cycle,
        # then it will appear that the edge doesn't generate any
        # trees.
        memo[edge] = []
        
        # Leaf edges.
        if isinstance(edge, LeafEdge):
            leaf = self._token[subtokens_prop][edge.start()]
            memo[edge] = leaf
            return [leaf]
        
        # Each child pointer list can be used to form trees.
        for cpl in self.child_pointer_lists(edge):
            # Get the set of child choices for each child pointer.
            # child_choices[i] is the set of choices for the tree's
            # ith child.
            child_choices = [self._trees(cp, memo) for cp in cpl]

            # For each combination of children, add a tree.
            for children in self._choose_children(child_choices):
                lhs = edge.lhs().symbol()
                trees.append(TreeToken(**{node_prop:lhs,
                                          'children':children}))

        # If the edge is incomplete, then extend it with "partial
        # trees":
        if edge.is_incomplete():
            unexpanded = [TreeToken(**{node_prop:elt, 'children':()})
                          for elt in edge.rhs()[edge.dot():]]
            for tree in trees:
                tree['children'].extend(unexpanded)

        # Update the memoization dictionary.
        memo[edge] = trees

        # Return the list of trees.
        return trees

    def _choose_children(self, child_choices):
        """
        A helper function for L{_trees} that finds the possible sets
        of subtrees for a new tree.
        
        @param child_choices: A list that specifies the options for
        each child.  In particular, C{child_choices[i]} is a list of
        tokens and subtrees that can be used as the C{i}th child.
        """
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
    def pp_edge(self, edge, width=5):
        """
        @return: A pretty-printed string representation of a given edge
            in this chart.
        @rtype: C{string}
        @param width: The number of characters allotted to each
            index in the sentence.
        """
        (start, end) = (edge.start(), edge.end())

        str = '|' + ('.'+' '*(width-1))*start

        # Zero-width edges are "#" if complete, ">" if incomplete
        if start == end:
            if edge.is_complete(): str += '#'
            else: str += '>'

        # Spanning complete edges are "[===]"; Other edges are
        # "[---]" if complete, "[--->" if incomplete
        elif edge.is_complete() and edge.span() == (0,self._num_leaves):
            str += '['+('='*width)*(end-start-1) + '='*(width-1)+']'
        elif edge.is_complete():
            str += '['+('-'*width)*(end-start-1) + '-'*(width-1)+']'
        else:
            str += '['+('-'*width)*(end-start-1) + '-'*(width-1)+'>'
        
        str += (' '*(width-1)+'.')*(self._num_leaves-end)
        return str + '| %s ' % edge

    def pp(self, width=5):
        """
        @return: A pretty-printed string representation of this chart.
        @rtype: C{string}
        @param width: The number of characters allotted to each
            index in the sentence.
        """
        subtokens_prop = self._propnames.get('subtokens', 'subtokens')
        leaf_prop = self._propnames.get('leaf', 'leaf')
        
        # Draw a header.
        if self._token and width>1:
            header = '|.'
            for tok in self._token[subtokens_prop]:
                header += tok[leaf_prop][:width-1].center(width-1)+'.'
            header += '|\n'
            header += '|'+'-'*(self._num_leaves*width+1)+'|\n'
        else:
            header = ''
        
        # sort edges: primary key=length, secondary key=start index.
        # (and filter out the token edges)
        edges = [(e.length(), e.start(), e) for e in self]
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
    of existing edges.  Each chart rule expects a fixed number of
    edges, as indicated by the class variable L{NUM_EDGES}.  In
    particular:
    
      - A chart rule with C{NUM_EDGES=0} specifies what new edges are
        licensed, regardless of existing edges.

      - A chart rule with C{NUM_EDGES=1} specifies what new edges are
        licensed by a single existing edge.

      - A chart rule with C{NUM_EDGES=2} specifies what new edges are
        licensed by a pair of existing edges.
      
    @type NUM_EDGES: C{int}
    @cvar NUM_EDGES: The number of existing edges that this rule uses
        to license new edges.  Typically, this number ranges from zero
        to two.
    """
    def apply(self, chart, grammar, *edges):
        """
        Add the edges licensed by this rule and the given edges to the
        chart.

        @type edges: C{list} of L{EdgeI}
        @param edges: A set of existing edges.  The number of edges
            that should be passed to C{apply} is specified by the
            L{NUM_EDGES} class variable.
        @rtype: C{list} of L{EdgeI}
        @return: A list of the edges that were added.
        """
        raise AssertionError, 'ChartRuleI is an abstract interface'

    def apply_iter(self, chart, grammar, *edges):
        """
        @return: A generator that will add edges licensed by this rule
            and the given edges to the chart, one at a time.  Each
            time the generator is resumed, it will either add a new
            edge and yield that edge; or return.
        @rtype: C{iter} of L{EdgeI}
        
        @type edges: C{list} of L{EdgeI}
        @param edges: A set of existing edges.  The number of edges
            that should be passed to C{apply} is specified by the
            L{NUM_EDGES} class variable.
        """
        raise AssertionError, 'ChartRuleI is an abstract interface'

    def apply_everywhere(self, chart, grammar):
        """
        Add all the edges licensed by this rule and the edges in the
        chart to the chart.
        
        @rtype: C{list} of L{EdgeI}
        @return: A list of the edges that were added.
        """
        raise AssertionError, 'ChartRuleI is an abstract interface'

    def apply_everywhere_iter(self, chart, grammar):
        """
        @return: A generator that will add all edges licensed by
            this rule, given the edges that are currently in the
            chart, one at a time.  Each time the generator is resumed,
            it will either add a new edge and yield that edge; or
            return.
        @rtype: C{iter} of L{EdgeI}
        """
        raise AssertionError, 'ChartRuleI is an abstract interface'
        
class AbstractChartRule:
    """
    An abstract base class for chart rules.  C{AbstractChartRule}
    provides:
      - A default implementation for C{apply}, based on C{apply_iter}.
      - A default implementation for C{apply_everywhere_iter},
        based on C{apply_iter}.
      - A default implementation for C{apply_everywhere}, based on
        C{apply_everywhere_iter}.  Currently, this implementation
        assumes that C{NUM_EDGES}<=3.
      - A default implementation for C{__str__}, which returns a
        name basd on the rule's class name.
    """
    def __init__(self):
        # This is a sanity check, to make sure that NUM_EDGES is
        # consistant with apply() and  apply_iter():
        for method in self.apply, self.apply_iter:
            num_args = method.im_func.func_code.co_argcount
            has_vararg = method.im_func.func_code.co_flags & 4
            if num_args != self.NUM_EDGES+3 and not has_vararg:
                raise AssertionError('NUM_EDGES is incorrect in for %s.%s' %
                                     (self.__class__, func.__name__))

    # Subclasses must define apply_iter.
    def apply_iter(self, chart, grammar, *edges):
        raise AssertionError, 'AbstractChartRule is an abstract class'

    # Default: loop through the given number of edges, and call
    # self.apply() for each set of edges.
    def apply_everywhere_iter(self, chart, grammar):
        if self.NUM_EDGES == 0:
            for new_edge in self.apply(chart, grammar):
                yield new_edge

        elif self.NUM_EDGES == 1:
            for e1 in chart:
                for new_edge in self.apply(chart, grammar, e1):
                    yield new_edge

        elif self.NUM_EDGES == 2:
            for e1 in chart:
                for e2 in chart:
                    for new_edge in self.apply(chart, grammar, e1, e2):
                        yield new_edge

        elif self.NUM_EDGES == 3:
            for e1 in chart:
                for e2 in chart:
                    for e3 in chart:
                        for new_edge in self.apply(chart,grammar,e1,e2,e3):
                            yield new_edge

        else:
            raise AssertionError, 'NUM_EDGES>3 is not currently supported'

    # Default: delegate to apply_iter.
    def apply(self, chart, grammar, *edges):
        return list(self.apply_iter(chart, grammar, *edges))

    # Default: delegate to apply_everywhere_iter.
    def apply_everywhere(self, chart, grammar):
        return list(self.apply_everywhere_iter(chart, grammar))

    # Default: return a name based on the class name.
    def __str__(self):
        # Add spaces between InitialCapsWords.
        return re.sub('([a-z])([A-Z])', r'\1 \2', self.__class__.__name__)

#////////////////////////////////////////////////////////////
# Fundamental Rule
#////////////////////////////////////////////////////////////
class FundamentalRule(AbstractChartRule):
    """
    A rule that joins two adjacent edges to form a single combined
    edge.  In particular, this rule specifies that any pair of edges:
    
        - C{[A->E{alpha}*BE{beta}]@[i:j]
        - C{[B->E{gamma}*]@[j:k]
    licenses the edge:
        - C{[A->E{alpha}B*E{beta}]@[i:j]
    """
    NUM_EDGES=2
    def apply_iter(self, chart, grammar, left_edge, right_edge):
        # Make sure the rule is applicable.
        if not (left_edge.end() == right_edge.start() and
                left_edge.next() == right_edge.lhs() and
                left_edge.is_incomplete() and right_edge.is_complete()):
            return

        # Construct the new edge.
        new_edge = TreeEdge(span=(left_edge.start(), right_edge.end()),
                            lhs=left_edge.lhs(), rhs=left_edge.rhs(),
                            dot=left_edge.dot()+1)

        # Add it to the chart, with appropraite child pointers.
        changed_chart = False
        for cpl1 in chart.child_pointer_lists(left_edge):
            if chart.insert(new_edge, cpl1+(right_edge,)):
                changed_chart = True

        # If we changed the chart, then generate the edge.
        if changed_chart: yield new_edge

class SingleEdgeFundamentalRule(AbstractChartRule):
    """
    A rule that joins a given edge with adjacent edges in the chart,
    to form combined edges.  In particular, this rule specifies that
    either of the edges:
        - C{[A->E{alpha}*BE{beta}]@[i:j]
        - C{[B->E{gamma}*]@[j:k]
    licenses the edge:
        - C{[A->E{alpha}B*E{beta}]@[i:j]
    if the other edge is already in the chart.
    @note: This is basically L{FundamentalRule}, with one edge is left
        unspecified.
    """
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
    
#////////////////////////////////////////////////////////////
# Top-Down Parsing
#////////////////////////////////////////////////////////////
class TopDownInitRule(AbstractChartRule):
    """
    A rule licensing edges corresponding to the grammar productions for
    the grammar's start symbol.  In particular, this rule specifies that:
        - C{[S->*E{alpha}]@[0:i]}
    is licensed for each grammar production C{S->E{alpha}}, where
    C{S} is the grammar's start symbol.
    """
    NUM_EDGES=0
    def apply_iter(self, chart, grammar):
        for prod in grammar.productions():
            if prod.lhs() == grammar.start():
                new_edge = TreeEdge.from_production(prod, 0)
                if chart.insert(new_edge, ()):
                    yield new_edge

class TopDownExpandRule(AbstractChartRule):
    """
    A rule licensing edges corresponding to the grammar productions
    for the nonterminal following an incomplete edge's dot.  In
    particular, this rule specifies that:
        - C{[A->E{alpha}*BE{beta}]@[i:j]}
    licenses the edge:
        - C{[B->*E{gamma}]@[j:j]}
    for each grammar production C{B->E{gamma}}.
    """
    NUM_EDGES=1
    def apply_iter(self, chart, grammar, edge):
        if edge.is_complete(): return
        for prod in grammar.productions():
            if edge.next() == prod.lhs():
                new_edge = TreeEdge.from_production(prod, edge.end())
                if chart.insert(new_edge, ()):
                    yield new_edge

class TopDownMatchRule(AbstractChartRule):
    """
    A rule licensing an edge corresponding to a terminal following an
    incomplete edge's dot.  In particular, this rule specifies that:
        - C{[A->E{alpha}*w{beta}]@[i:j]
    licenses the leaf edge:
        - C{[w->*]@[j:j+1]}
    if the C{j}th word in the text is C{w}.
    """
    NUM_EDGES = 1
    def apply_iter(self, chart, grammar, edge):
        if edge.is_complete() or edge.end() >= chart.num_leaves(): return
        index = edge.end()
        leaf = chart.leaf(index)
        if edge.next() == leaf:
            new_edge = LeafEdge(leaf, index)
            if chart.insert(new_edge, ()):
                yield new_edge

# Add a cache, to prevent recalculating.
class CachedTopDownInitRule(TopDownInitRule):
    """
    A cached version of L{TopDownInitRule}.  After the first time this
    rule is applied, it will not generate any more edges.

    If C{chart} or C{grammar} are changed, then the cache is flushed.
    """
    def __init__(self):
        AbstractChartRule.__init__(self)
        self._done = (None, None)

    def apply_iter(self, chart, grammar):
        # If we've already applied this rule, and the chart & grammar
        # have not changed, then just return (no new edges to add).
        if self._done[0] is chart and self._done[1] is grammar: return

        # Add all the edges indicated by the top down init rule.
        for e in TopDownInitRule.apply_iter(self, chart, grammar):
            yield e

        # Record the fact that we've applied this rule.
        self._done = (chart, grammar)

    def __str__(self): return 'Top Down Init Rule'
    
class CachedTopDownExpandRule(TopDownExpandRule):
    """
    A cached version of L{TopDownExpandRule}.  After the first time
    this rule is applied to an edge with a given C{end} and C{next},
    it will not generate any more edges for edges with that C{end} and
    C{next}.
    
    If C{chart} or C{grammar} are changed, then the cache is flushed.
    """
    def __init__(self):
        AbstractChartRule.__init__(self)
        self._done = {}
        
    def apply_iter(self, chart, grammar, edge):
        # If we've already applied this rule to an edge with the same
        # next & end, and the chart & grammar have not changed, then
        # just return (no new edges to add).
        done = self._done.get((edge.next(), edge.end()), (None,None))
        if done[0] is chart and done[1] is grammar: return

        # Add all the edges indicated by the top down expand rule.
        for e in TopDownExpandRule.apply_iter(self, chart, grammar, edge):
            yield e
            
        # Record the fact that we've applied this rule.
        self._done[edge.next(), edge.end()] = (chart, grammar)
    
    def __str__(self): return 'Top Down Expand Rule'

#////////////////////////////////////////////////////////////
# Bottom-Up Parsing
#////////////////////////////////////////////////////////////

class BottomUpInitRule(AbstractChartRule):
    """
    A rule licensing any edges corresponding to terminals in the
    text.  In particular, this rule licenses the leaf edge:
        - C{[w->*]@[i:i+1]}
    for C{w} is a word in the text, where C{i} is C{w}'s index.
    """
    NUM_EDGES=0
    def apply_iter(self, chart, grammar):
        for index in range(chart.num_leaves()):
            new_edge = LeafEdge(chart.leaf(index), index)
            if chart.insert(new_edge, ()):
                yield new_edge

class BottomUpRule(AbstractChartRule):
    """
    A rule licensing any edge corresponding to a production whose
    right-hand side begins with a complete edge's left-hand side.  In
    particular, this rule specifies that:
        - C{A->E{alpha}*}
    licenses the edge:
        - C{B->*AE{beta}}
    for each grammar production C{B->AE{beta}}
    """
    NUM_EDGES=1
    def apply_iter(self, chart, grammar, edge):
        if edge.is_incomplete(): return
        for prod in grammar.productions():
            if edge.lhs() == prod.rhs()[0]:
                new_edge = TreeEdge.from_production(prod, edge.start())
                if chart.insert(new_edge, ()):
                    yield new_edge

#////////////////////////////////////////////////////////////
# Earley Parsing
#////////////////////////////////////////////////////////////

class CompleterRule(AbstractChartRule):
    """
    A rule that joins a given complete edge with adjacent incomplete
    edges in the chart, to form combined edges.  In particular, this
    rule specifies that:
        - C{[B->E{gamma}*]@[j:k]
    licenses the edge:
        - C{[A->E{alpha}B*E{beta}]@[i:j]
    given that the chart contains:
        - C{[A->E{alpha}*BE{beta}]@[i:j]
    @note: This is basically L{FundamentalRule}, with the left edge
        left unspecified.
    """
    NUM_EDGES=1
    
    _fundamental_rule = FundamentalRule()
    
    def apply_iter(self, chart, grammar, right_edge):
        if right_edge.is_incomplete(): return
        fr = self._fundamental_rule
        for left_edge in chart.select(end=right_edge.start(),
                                     is_complete=False,
                                     next=right_edge.lhs()):
            for e in fr.apply_iter(chart, grammar, left_edge, right_edge):
                yield e

    def __str__(self): return 'Completer Rule (aka Fundamental Rule)'
    
class ScannerRule(AbstractChartRule):
    """
    A rule licensing a leaf edge corresponding to a part-of-speech
    terminal following an incomplete edge's dot.  In particular, this
    rule specifies that:
        - C{[A->E{alpha}*P{beta}]@[i:j]
    licenses the edges:
        - C{[P->w*]@[j:j+1]}
        - C{[w->*]@[j:j+1]}
    if the C{j}th word in the text is C{w}; and C{P} is a valid part
    of speech for C{w}.
    """
    NUM_EDGES=1
    def __init__(self, word_to_pos_lexicon):
        self._word_to_pos = word_to_pos_lexicon

    def apply_iter(self, chart, gramar, edge):
        if edge.is_complete() or edge.end()>=chart.num_leaves(): return
        index = edge.end()
        leaf = chart.leaf(index)
        if edge.next() in self._word_to_pos[leaf]:
            new_leaf_edge = LeafEdge(leaf, index)
            if chart.insert(new_leaf_edge, ()):
                yield new_leaf_edge
            new_pos_edge = TreeEdge((index,index+1), edge.next(),
                                    [leaf], 1)
            if chart.insert(new_pos_edge, (new_leaf_edge,)):
                yield new_pos_edge

# This is just another name for TopDownExpandRule:
class PredictorRule(TopDownExpandRule): pass

########################################################################
##  Simple Earley Chart Parser
########################################################################

class EarleyChartParser(ParserI):
    def __init__(self, grammar, root_node, lexicon, **propnames):
        self._grammar = grammar
        self._root_node = root_node
        self._lexicon = lexicon
        self._propnames = propnames

    def parse(self, token):
        chart = Chart(token, **self._propnames)
        self._parse(chart, self._grammar)
        for tree in chart.parses(self._root_node):
            print tree
#        print '='*60
#        for tree in chart.trees(TreeEdge((1,10), Nonterminal('VP'),
#                                     (Nonterminal('VP'), Nonterminal('PP')),
#                                     1)):
#            print tree
    tok = Token(text='John saw the dog with a cookie with a dog')    
    def _parse(self, chart, grammar):
        root = Nonterminal('-ROOT-')
        edge = TreeEdge((0,0), root, (self._root_node,))
        chart.insert(edge, ())

        predictor = PredictorRule()
        completer = CompleterRule()
        scanner = ScannerRule(self._lexicon)
        
        for end in range(chart.num_leaves()+1):
            # Deep trickiness going on here:
            for edge in chart.select(end=end):
                if edge.is_incomplete():
                    for e in predictor.apply_iter(chart, grammar, edge):
                        print 'P', chart.pp_edge(e)
                    for e in scanner.apply_iter(chart, grammar, edge):
                        print 'S', chart.pp_edge(e)
                elif edge.is_complete():
                    for e in completer.apply_iter(chart, grammar, edge):
                        print 'C', chart.pp_edge(e)

########################################################################
##  Generic Chart Parser
########################################################################
# Apply rules until nothing else gets added.

TD_STRATEGY = [CachedTopDownInitRule(), CachedTopDownExpandRule(), 
               TopDownMatchRule(), CompleterRule()]
BU_STRATEGY = [BottomUpInitRule(), BottomUpRule(), CompleterRule()]

class ChartParser(ParserI):
    def __init__(self, grammar, root_node, strategy, **propnames):
        self._grammar = grammar
        self._root_node = root_node
        self._strategy = strategy
        self._propnames = propnames

    def parse(self, token):
        chart = Chart(token, **self._propnames)
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
                rulename = ''.join([w[0] for w in str(rule).split()])
                #rule.apply_everywhere(chart, grammar)
                for e in rule.apply_everywhere_iter(chart, grammar):
                    print '%-5s%s' % (rulename, chart.pp_edge(e))

########################################################################
##  Demo Code
########################################################################

def demo():
    # Define some nonterminals
    S, VP, NP, PP = nonterminals('S, VP, NP, PP')
    V, N, P, Name, Det = nonterminals('V, N, P, Name, Det')

    # Define a gramar.
    lex_productions = [
        CFGProduction(NP, 'John'), CFGProduction(NP, 'I'), 
        CFGProduction(Det, 'the'), CFGProduction(Det, 'my'),
        CFGProduction(Det, 'a'),
        CFGProduction(N, 'dog'),   CFGProduction(N, 'cookie'),
        CFGProduction(V, 'ate'),  CFGProduction(V, 'saw'),
        CFGProduction(P, 'with'), CFGProduction(P, 'under'),]

    gram_productions = [
        CFGProduction(S, NP, VP),  CFGProduction(PP, P, NP),
        CFGProduction(NP, Det, N), CFGProduction(NP, NP, PP),
        CFGProduction(VP, VP, PP), CFGProduction(VP, V, NP),
        CFGProduction(VP, V),# CFGProduction(NP, NP),
        ]
    grammar1 = CFG(S, gram_productions)
    grammar2 = CFG(S, gram_productions+lex_productions)

    lexicon = {'John': [NP], 'I': [NP],
               'the': [Det], 'my': [Det], 'a': [Det],
               'dog': [N], 'cookie': [N],
               'ate': [V], 'saw': [V],
               'with': [P], 'under': [P]}

    class PretendLexicon:
        def __getitem__(self, item):
            return [item]

    from nltk.tokenizer import WSTokenizer
    tok = Token(text='John saw the dog with a cookie with a dog')
    #tok = Token(text='John saw')
    WSTokenizer().tokenize(tok)
    parser = EarleyChartParser(grammar1, S, lexicon, leaf='text')
    parser.parse(tok)
    #parser = ChartParser(grammar2, S, BU_STRATEGY, leaf='text')
    #parser.parse(tok)
    #parser = ChartParser(grammar2, S, TD_STRATEGY, leaf='text')
    #parser.parse(tok)

import profile
#profile.run('demo()')
demo()
