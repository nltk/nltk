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
@group Data Types: Chart, EdgeI, *Edge
@group Chart Parsers: *Parser
@group Chart Rules: ChartRuleI, *Rule
"""

import re
from nltk.chktype import chktype
from nltk.token import Token
from nltk.parser import ParserI, AbstractParser
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
      - A X{leaf}, specifying the word's LEAF property.

    A leaf edge's left-hand side is its leaf value, and its right hand
    side is C{()}.  Its span is C{[index, index+1]}, and its dot
    position is C{0}.
    """
    def __init__(self, leaf, index):
        """
        Construct a new C{LeafEdge}.

        @param leaf: The new edge's leaf value, specifying the LEAF
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

    @inprop: C{SUBTOKENS}: The list of subtokens to be parsed.
    @inprop: C{LEAF}: The string content of the subtokens.
    @outprop: C{NODE}: The subtrees' constituent label.
    
    @ivar _token: The sentence that the chart covers.
    @ivar _num_leaves: The number of subtokens in L{_token}.
    @ivar _property_names: The property names that should be used to
        access L{_token}.
    @ivar _edges: A list of the edges in the chart
    @ivar _edge_to_cpls: A dictionary mapping each edge to a set
        of child pointer lists that are associated with that edge.
    @ivar _indexes: A dictionary mapping tuples of edge attributes
        to indices, where each index maps the corresponding edge
        attribute values to lists of edges.
    """
    def __init__(self, token, **property_names):
        """
        Construct a new empty chart.

        @type token: L{Token}
        @param token: The sentence that this chart will be used to
            parse.
        @param property_names: A dictionary that can be used to override
            the default property names used by the chart.  Each entry
            maps from a default property name to a new property name.
        """
        assert chktype(1, token, Token)
        SUBTOKENS = property_names.get('SUBTOKENS', 'SUBTOKENS')

        # Record the sentence token and the sentence length.
        self._token = token
        self._num_leaves = len(token[SUBTOKENS])

        # Property names, used to access self._token.
        self._property_names = property_names
        
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
        SUBTOKENS = self._property_names.get('SUBTOKENS', 'SUBTOKENS')
        LEAF = self._property_names.get('LEAF', 'LEAF')
        return self._token[SUBTOKENS][index][LEAF]

    def leaves(self):
        """
        @return: A list of the leaf values of each word in the
            chart's sentence.
        @rtype: C{list} of C{string}
        """
        SUBTOKENS = self._property_names.get('SUBTOKENS', 'SUBTOKENS')
        LEAF = self._property_names.get('LEAF', 'LEAF')
        return [tok[LEAF] for tok in self._token[SUBTOKENS]]

    def token(self):
        """
        @rtype: L{Token}
        @return: The sentence that this chart is used to parse.
        """
        return self._token

    def property_names(self):
        """
        @rtype: C{dict}
        @return: The property names dictionary, as given in the
            constructor.
        """
        return self._property_names

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

        SUBTOKENS = self._property_names.get('SUBTOKENS', 'SUBTOKENS')
        NODE = self._property_names.get('NODE', 'NODE')
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
            leaf = self._token[SUBTOKENS][edge.start()]
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
                trees.append(TreeToken({NODE:lhs,
                                          'CHILDREN':children}))

        # If the edge is incomplete, then extend it with "partial
        # trees":
        if edge.is_incomplete():
            unexpanded = [TreeToken({NODE:elt, 'CHILDREN':()})
                          for elt in edge.rhs()[edge.dot():]]
            for tree in trees:
                tree['CHILDREN'].extend(unexpanded)

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
    def pp_edge(self, edge, width=None):
        """
        @return: A pretty-printed string representation of a given edge
            in this chart.
        @rtype: C{string}
        @param width: The number of characters allotted to each
            index in the sentence.
        """
        if width is None: width = 50/(self.num_leaves()+1)
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

    def pp_leaves(self, width=None):
        """
        @return: A pretty-printed string representation of this
            chart's leaves.  This string can be used as a header
            for calls to L{pp_edge}.
        """
        if width is None: width = 50/(self.num_leaves()+1)
        SUBTOKENS = self._property_names.get('SUBTOKENS', 'SUBTOKENS')
        LEAF = self._property_names.get('LEAF', 'LEAF')
        
        if self._token is not None and width>1:
            header = '|.'
            for tok in self._token[SUBTOKENS]:
                header += tok[LEAF][:width-1].center(width-1)+'.'
            header += '|'
        else:
            header = ''

        return header

    def pp(self, width=None):
        """
        @return: A pretty-printed string representation of this chart.
        @rtype: C{string}
        @param width: The number of characters allotted to each
            index in the sentence.
        """
        if width is None: width = 50/(self.num_leaves()+1)
        # sort edges: primary key=length, secondary key=start index.
        # (and filter out the token edges)
        edges = [(e.length(), e.start(), e) for e in self]
        edges.sort()
        edges = [e for (_,_,e) in edges]
        
        return (self.pp_leaves(width) + '\n' +
                '\n'.join([self.pp_edge(edge, width) for edge in edges]))
                
    #////////////////////////////////////////////////////////////
    # Display: Dot (AT&T Graphviz)
    #////////////////////////////////////////////////////////////

    def dot_digraph(self):
        # Header
        s = 'digraph nltk_chart {\n'
        #s += '  size="5,5";\n'
        s += '  rankdir=LR;\n'
        s += '  node [height=0.1,width=0.1];\n'
        s += '  node [style=filled, color="lightgray"];\n'

        # Set up the nodes
        for y in range(self.num_edges(), -1, -1):
            if y == 0:
                s += '  node [style=filled, color="black"];\n'
            for x in range(self.num_leaves()+1):
                if y == 0 or (x <= self._edges[y-1].start() or
                              x >= self._edges[y-1].end()):
                    s += '  %04d.%04d [label=""];\n' % (x,y)

        # Add a spacer
        s += '  x [style=invis]; x->0000.0000 [style=invis];\n'

        # Declare ranks.
        for x in range(self.num_leaves()+1):
            s += '  {rank=same;'
            for y in range(self.num_edges()+1):
                if y == 0 or (x <= self._edges[y-1].start() or
                              x >= self._edges[y-1].end()):
                    s += ' %04d.%04d' % (x,y)
            s += '}\n'

        # Add the leaves
        s += '  edge [style=invis, weight=100];\n'
        s += '  node [shape=plaintext]\n'
        s += '  0000.0000'
        for x in range(self.num_leaves()):
            s += '->%s->%04d.0000' % (self.leaf(x), x+1)
        s += ';\n\n'

        # Add the edges
        s += '  edge [style=solid, weight=1];\n'
        for y, edge in enumerate(self):
            for x in range(edge.start()):
                s += ('  %04d.%04d -> %04d.%04d [style="invis"];\n' %
                      (x, y+1, x+1, y+1))
            s += ('  %04d.%04d -> %04d.%04d [label="%s"];\n' %
                  (edge.start(), y+1, edge.end(), y+1, edge))
            for x in range(edge.end(), self.num_leaves()):
                s += ('  %04d.%04d -> %04d.%04d [style="invis"];\n' %
                      (x, y+1, x+1, y+1))
        s += '}\n'
        return s

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
            for new_edge in self.apply_iter(chart, grammar):
                yield new_edge

        elif self.NUM_EDGES == 1:
            for e1 in chart:
                for new_edge in self.apply_iter(chart, grammar, e1):
                    yield new_edge

        elif self.NUM_EDGES == 2:
            for e1 in chart:
                for e2 in chart:
                    for new_edge in self.apply_iter(chart, grammar, e1, e2):
                        yield new_edge

        elif self.NUM_EDGES == 3:
            for e1 in chart:
                for e2 in chart:
                    for e3 in chart:
                        for new_edge in self.apply_iter(chart,grammar,e1,e2,e3):
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
    
        - [AS{->}S{alpha}*BS{beta}]@[i:j]
        - [BS{->}S{gamma}*]@[j:k]
    licenses the edge:
        - [AS{->}S{alpha}B*S{beta}]@[i:j]
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
        - [AS{->}S{alpha}*BS{beta}]@[i:j]
        - [BS{->}S{gamma}*]@[j:k]
    licenses the edge:
        - [AS{->}S{alpha}B*S{beta}]@[i:j]
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
        - [SS{->}*S{alpha}]@[0:i]
    is licensed for each grammar production C{SS{->}S{alpha}}, where
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
        - [AS{->}S{alpha}*BS{beta}]@[i:j]
    licenses the edge:
        - [BS{->}*S{gamma}]@[j:j]
    for each grammar production C{BS{->}S{gamma}}.
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
        - [AS{->}S{alpha}*w{beta}]@[i:j]
    licenses the leaf edge:
        - [wS{->}*]@[j:j+1]
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
        - [wS{->}*]@[i:i+1]
    for C{w} is a word in the text, where C{i} is C{w}'s index.
    """
    NUM_EDGES=0
    def apply_iter(self, chart, grammar):
        for index in range(chart.num_leaves()):
            new_edge = LeafEdge(chart.leaf(index), index)
            if chart.insert(new_edge, ()):
                yield new_edge

class BottomUpPredictRule(AbstractChartRule):
    """
    A rule licensing any edge corresponding to a production whose
    right-hand side begins with a complete edge's left-hand side.  In
    particular, this rule specifies that:
        - [AS{->}S{alpha}*]
    licenses the edge:
        - [BS{->}*AS{beta}]
    for each grammar production C{BS{->}AS{beta}}
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
        - [BS{->}S{gamma}*]@[j:k]
    licenses the edge:
        - [AS{->}S{alpha}B*S{beta}]@[i:j]
    given that the chart contains:
        - [AS{->}S{alpha}*BS{beta}]@[i:j]
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

    def __str__(self): return 'Completer Rule'
    
class ScannerRule(AbstractChartRule):
    """
    A rule licensing a leaf edge corresponding to a part-of-speech
    terminal following an incomplete edge's dot.  In particular, this
    rule specifies that:
        - [AS{->}S{alpha}*PS{beta}]@[i:j]
    licenses the edges:
        - [PS{->}w*]@[j:j+1]
        - [wS{->}*]@[j:j+1]
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
        if edge.next() in self._word_to_pos.get(leaf, []):
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

class EarleyChartParser(AbstractParser):
    """
    A chart parser implementing the Earley parsing algorithm:

        - For each index I{end} in [0, 1, ..., N]:
          - For each I{edge} s.t. I{edge}.end = I{end}:
            - If I{edge} is incomplete, and I{edge}.next is not a part
              of speech:
                - Apply PredictorRule to I{edge}
            - If I{edge} is incomplete, and I{edge}.next is a part of
              speech:
                - Apply ScannerRule to I{edge}
            - If I{edge} is complete:
                - Apply CompleterRule to I{edge}
        - Return any complete parses in the chart

    C{EarleyChartParser} uses a X{lexicon} to decide whether a leaf
    has a given part of speech.  This lexicon is encoded as a
    dictionary that maps each word to a list of parts of speech that
    word can have.
    """
    def __init__(self, grammar, lexicon, trace=0, **property_names):
        """
        Create a new Earley chart parser, that uses C{grammar} to
        parse texts.
        
        @type grammar: C{CFG}
        @param grammar: The grammar used to parse texts.
        @type lexicon: C{dict} from C{string} to (C{list} of C{string})
        @param lexicon: A lexicon of words that records the parts of
            speech that each word can have.  Each key is a word, and
            the corresponding value is a list of parts of speech.
        @type trace: C{int}
        @param trace: The level of tracing that should be used when
            parsing a text.  C{0} will generate no tracing output;
            and higher numbers will produce more verbose tracing
            output.
        @type property_names: C{dict}
        @param property_names: A dictionary that can be used to override
            the default property names.  Each entry maps from a
            default property name to a new property name.
        """
        self._grammar = grammar
        self._lexicon = lexicon
        self._trace = trace
        AbstractParser.__init__(self, **property_names)

    def parse_n(self, token):
        TREES = self._property_names.get('TREES', 'TREES')
        chart = Chart(token, **self._property_names)
        grammar = self._grammar

        # Width, for printing trace edges.
        w = 50/(chart.num_leaves()+1)
        if self._trace > 0: print ' ', chart.pp_leaves(w)

        # Initialize the chart with a special "starter" edge.
        root = Nonterminal('[INIT]')
        edge = TreeEdge((0,0), root, (grammar.start(),))
        chart.insert(edge, ())

        # Create the 3 rules:
        predictor = PredictorRule()
        completer = CompleterRule()
        scanner = ScannerRule(self._lexicon)

        for end in range(chart.num_leaves()+1):
            if self._trace > 1: print 'Processing queue %d' % end
            for edge in chart.select(end=end):
                if edge.is_incomplete():
                    for e in predictor.apply(chart, grammar, edge):
                        if self._trace > 0:
                            print 'Predictor', chart.pp_edge(e,w)
                if edge.is_incomplete():
                    for e in scanner.apply(chart, grammar, edge):
                        if self._trace > 0:
                            print 'Scanner  ', chart.pp_edge(e,w)
                if edge.is_complete():
                    for e in completer.apply(chart, grammar, edge):
                        if self._trace > 0:
                            print 'Completer', chart.pp_edge(e,w)

        # Output a list of complete parses.
        token[TREES] = chart.parses(grammar.start())
            
    def parse(self, token):
        # Delegate to parse_n
        self._parse_from_parse_n(token)

########################################################################
##  Generic Chart Parser
########################################################################

TD_STRATEGY = [CachedTopDownInitRule(), CachedTopDownExpandRule(), 
               TopDownMatchRule(), SingleEdgeFundamentalRule()]
BU_STRATEGY = [BottomUpInitRule(), BottomUpPredictRule(),
               SingleEdgeFundamentalRule()]

class ChartParser(AbstractParser):
    """
    A generic chart parser.  A X{strategy}, or list of
    L{ChartRules<ChartRuleI>}, is used to decide what edges to add to
    the chart.  In particular, C{ChartParser} uses the following
    algorithm to parse texts:

        - Until no new edges are added:
          - For each I{rule} in I{strategy}:
            - Apply I{rule} to any applicable edges in the chart.
        - Return any complete parses in the chart
    """
    def __init__(self, grammar, strategy, trace=0, **property_names):
        """
        Create a new chart parser, that uses C{grammar} to parse
        texts.

        @type grammar: L{CFG}
        @param grammar: The grammar used to parse texts.
        @type strategy: C{list} of L{ChartRuleI}
        @param strategy: A list of rules that should be used to decide
            what edges to add to the chart.
        @type trace: C{int}
        @param trace: The level of tracing that should be used when
            parsing a text.  C{0} will generate no tracing output;
            and higher numbers will produce more verbose tracing
            output.
        @type property_names: C{dict}
        @param property_names: A dictionary that can be used to override
            the default property names.  Each entry maps from a
            default property name to a new property name.
        """
        self._grammar = grammar
        self._strategy = strategy
        self._trace = trace
        AbstractParser.__init__(self, **property_names)

    def parse_n(self, token):
        TREES = self._property_names.get('TREES', 'TREES')
        chart = Chart(token, **self._property_names)
        grammar = self._grammar

        # Width, for printing trace edges.
        w = 50/(chart.num_leaves()+1)
        if self._trace > 0: print chart.pp_leaves(w)
        
        edges_added = 1
        while edges_added > 0:
            edges_added = 0
            for rule in self._strategy:
                edges_added_by_rule = 0
                for e in rule.apply_everywhere(chart, grammar):
                    if self._trace > 0 and edges_added_by_rule == 0:
                        print '%s:' % rule
                    edges_added_by_rule += 1
                    if self._trace > 1: print chart.pp_edge(e,w)
                if self._trace == 1 and edges_added_by_rule > 0:
                    print '  - Added %d edges' % edges_added_by_rule
                edges_added += edges_added_by_rule
        
        # Output a list of complete parses.
        token[TREES] = chart.parses(grammar.start())
        
    def parse(self, token):
        # Delegate to parse_n
        self._parse_from_parse_n(token)

########################################################################
##  Stepping Chart Parser
########################################################################

class SteppingChartParser(ChartParser):
    """
    A C{ChartParser} that allows you to step through the parsing
    process, adding a single edge at a time.  It also allows you to
    change the parser's strategy or grammar midway through parsing a
    text.

    The C{initialize} method is used to start parsing a text.  C{step}
    adds a single edge to the chart.  C{set_strategy} changes the
    strategy used by the chart parser.  C{parses} returns the set of
    parses that has been found by the chart parser.

    @ivar _restart: Records whether the parser's strategy, grammar,
        or chart has been changed.  If so, then L{step} must restart
        the parsing algorithm.
    """
    def __init__(self, grammar, strategy=None, trace=0, **property_names):
        self._chart = None
        self._current_chartrule = None
        self._restart = False
        ChartParser.__init__(self, grammar, strategy, trace, **property_names)

    #////////////////////////////////////////////////////////////
    # Initialization
    #////////////////////////////////////////////////////////////

    def initialize(self, token):
        "Begin parsing the given token."
        self._chart = Chart(token, **self._property_names)
        self._restart = True

    #////////////////////////////////////////////////////////////
    # Stepping
    #////////////////////////////////////////////////////////////

    def step(self):
        """
        @return: A generator that adds edges to the chart, one at a
        time.  Each time the generator is resumed, it adds a single
        edge and yields that edge.  If no more edges can be added,
        then it yields C{None}.

        If the parser's strategy, grammar, or chart is changed, then
        the generator will continue adding edges using the new
        strategy, grammar, or chart.

        Note that this generator never terminates, since the grammar
        or strategy might be changed to values that would add new
        edges.  Instead, it yields C{None} when no more edges can be
        added with the current strategy and grammar.
        """
        if self._chart is None:
            raise ValueError, 'Parser must be initialized first'
        while 1:
            self._restart = False
            w = 50/(self._chart.num_leaves()+1)
            
            for e in self._parse():
                if self._trace > 1: print self._current_chartrule
                if self._trace > 0: print self._chart.pp_edge(e,w)
                yield e
                if self._restart: break
            else:
                yield None # No more edges.

    def _parse(self):
        """
        A generator that implements the actual parsing algorithm.
        L{step} iterates through this generator, and restarts it
        whenever the parser's strategy, grammar, or chart is modified.
        """
        chart = self._chart
        grammar = self._grammar
        edges_added = 1
        while edges_added > 0:
            edges_added = 0
            for rule in self._strategy:
                self._current_chartrule = rule
                for e in rule.apply_everywhere_iter(chart, grammar):
                    edges_added += 1
                    yield e

    #////////////////////////////////////////////////////////////
    # Accessors
    #////////////////////////////////////////////////////////////

    def strategy(self):
        "@return: The strategy used by this parser."
        return self._strategy

    def grammar(self):
        "@return: The grammar used by this parser."
        return self._grammar

    def chart(self):
        "@return: The chart that is used by this parser."
        return self._chart

    def current_chartrule(self):
        "@return: The chart rule used to generate the most recent edge."
        return self._current_chartrule

    def parses(self):
        "@return: The parse trees currently contained in the chart."
        return self._chart.parses(self._grammar.start())

    #////////////////////////////////////////////////////////////
    # Parser modification
    #////////////////////////////////////////////////////////////

    def set_strategy(self, strategy):
        """
        Change the startegy that the parser uses to decide which edges
        to add to the chart.
        @type strategy: C{list} of L{ChartRuleI}
        @param strategy: A list of rules that should be used to decide
            what edges to add to the chart.
        """
        if strategy == self._strategy: return
        self._strategy = strategy[:] # Make a copy.
        self._restart = True

    def set_grammar(self, grammar):
        "Change the grammar used by the parser."
        if grammar is self._grammar: return
        self._grammar = grammar
        self._restart = True

    def set_chart(self, chart):
        "Load a given chart into the chart parser."
        if chart is self._chart: return
        self._chart = chart
        self._restart = True

    #////////////////////////////////////////////////////////////
    # Standard parser methods
    #////////////////////////////////////////////////////////////

    def parse_n(self, token):
        TREES = self._property_names.get('TREES', 'TREES')

        # Initialize ourselves.
        self.initialize(token)

        # Step until no more edges are generated.
        for e in self.step():
            if e is None: break
            
        # Output a list of complete parses.
        token[TREES] = self.parses()

########################################################################
##  Demo Code
########################################################################

def demo():
    """
    A demonstration of the chart parsers.
    """
    import sys, time
    
    # Define some nonterminals
    S, VP, NP, PP = nonterminals('S, VP, NP, PP')
    V, N, P, Name, Det = nonterminals('V, N, P, Name, Det')

    # Define some grammatical productions.
    grammatical_productions = [
        CFGProduction(S, NP, VP),  CFGProduction(PP, P, NP),
        CFGProduction(NP, Det, N), CFGProduction(NP, NP, PP),
        CFGProduction(VP, VP, PP), CFGProduction(VP, V, NP),
        CFGProduction(VP, V),]

    # Define some lexical productions.
    lexical_productions = [
        CFGProduction(NP, 'John'), CFGProduction(NP, 'I'), 
        CFGProduction(Det, 'the'), CFGProduction(Det, 'my'),
        CFGProduction(Det, 'a'),
        CFGProduction(N, 'dog'),   CFGProduction(N, 'cookie'),
        CFGProduction(V, 'ate'),  CFGProduction(V, 'saw'),
        CFGProduction(P, 'with'), CFGProduction(P, 'under'),
        ]

    # Convert the grammar productions to an earley-style lexicon.
    earley_lexicon = {}
    for prod in lexical_productions:
        earley_lexicon.setdefault(prod.rhs()[0], []).append(prod.lhs())

    # The grammar for ChartParser and SteppingChartParser:
    grammar = CFG(S, grammatical_productions+lexical_productions)

    # The grammar for EarleyChartParser:
    earley_grammar = CFG(S, grammatical_productions)

    # Tokenize a sample sentence.
    sent = Token(TEXT='I saw John with a dog with my cookie')
    print "Sentence:\n", sent
    from nltk.tokenizer import WSTokenizer
    WSTokenizer().tokenize(sent)

    # Ask the user which parser to test
    print '  1: Top-down chart parser'
    print '  2: Bottom-up chart parser'
    print '  3: Earley parser'
    print '  4: Stepping chart parser (alternating top-down & bottom-up)'
    print '  5: All parsers'
    print '\nWhich parser (1-5)? ',
    choice = sys.stdin.readline().strip()
    print
    if choice not in '12345':
        print 'Bad parser number'
        return

    # Keep track of how long each parser takes.
    times = {}

    # Run the top-down parser, if requested.
    if choice in ('1', '5'):
        cp = ChartParser(grammar, TD_STRATEGY, LEAF='TEXT', trace=2)
        t = time.time()
        cp.parse_n(sent)
        times['top down'] = time.time()-t
        assert len(sent['TREES'])==5, 'Not all parses found'
        for tree in sent['TREES']: print tree

    # Run the bottom-up parser, if requested.
    if choice in ('2', '5'):
        cp = ChartParser(grammar, BU_STRATEGY, LEAF='TEXT', trace=2)
        t = time.time()
        cp.parse_n(sent)
        times['bottom up'] = time.time()-t
        assert len(sent['TREES'])==5, 'Not all parses found'
        for tree in sent['TREES']: print tree

    # Run the earley, if requested.
    if choice in ('3', '5'):
        cp = EarleyChartParser(earley_grammar, earley_lexicon,
                               LEAF='TEXT', trace=1)
        t = time.time()
        cp.parse_n(sent)
        times['Earley parser'] = time.time()-t
        assert len(sent['TREES'])==5, 'Not all parses found'
        for tree in sent['TREES']: print tree

    # Run the stepping parser, if requested.
    if choice in ('4', '5'):
        t = time.time()
        cp = SteppingChartParser(grammar, LEAF='TEXT', trace=1)
        cp.initialize(sent)
        for i in range(4):
            print '*** SWITCH TO TOP DOWN'
            cp.set_strategy(TD_STRATEGY)
            for j, e in enumerate(cp.step()):
                if j>20 or e is None: break
            print '*** SWITCH TO BOTTOM UP'
            cp.set_strategy(BU_STRATEGY)
            for j, e in enumerate(cp.step()):
                if j>20 or e is None: break
        times['stepping'] = time.time()-t
        assert len(cp.parses())==5, 'Not all parses found'
        for parse in cp.parses(): print parse

    # Print the times of all parsers:
    maxlen = max([len(key) for key in times.keys()])
    format = '%' + `maxlen` + 's parser: %6.3fsec'
    times_items = times.items()
    times_items.sort(lambda a,b:cmp(a[1], b[1]))
    for (parser, t) in times_items:
        print format % (parser, t)
            
#if __name__ == '__main__': demo()
