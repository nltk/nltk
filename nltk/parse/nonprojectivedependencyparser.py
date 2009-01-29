# Natural Language Toolkit: Dependency Grammars
#
# Copyright (C) 2001-2009 NLTK Project
# Author: Jason Narad <jason.narad@gmail.com>
#
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT
#

import math

from nltk import parse_dependency_grammar

from dependencygraph import *

#################################################################
# DependencyScorerI - Interface for Graph-Edge Weight Calculation
#################################################################

class DependencyScorerI(object):
    """
    A scorer for calculated the weights on the edges of a weighted 
    dependency graph.  This is used by a 
    C{ProbabilisticNonprojectiveParser} to initialize the edge  
    weights of a C{DependencyGraph}.  While typically this would be done 
    by training a binary classifier, any class that can return a 
    multidimensional list representation of the edge weights can 
    implement this interface.  As such, it has no necessary
    fields.
    """

    def __init__(self):
        if self.__class__ == DependencyScorerI:
            raise TypeError('DependencyScorerI is an abstract interface')

    def train(self, graphs):
        """
        @type graphs: A list of C{DependencyGraph}
        @param graphs: A list of dependency graphs to train the scorer.
        Typically the edges present in the graphs can be used as
        positive training examples, and the edges not present as negative 
        examples.
        """
        raise AssertionError('DependencyScorerI is an abstract interface')

    def score(self, graph):
        """
        @type graph: A C{DependencyGraph}
        @param graph: A dependency graph whose set of edges need to be 
        scored.  
        @rtype: A three-dimensional list of numbers.
        @return: The score is returned in a multidimensional(3) list, such
        that the outer-dimension refers to the head, and the
        inner-dimension refers to the dependencies.  For instance,  
        scores[0][1] would reference the list of scores corresponding to 
        arcs from node 0 to node 1.  The node's 'address' field can be used 
        to determine its number identification.
        
        For further illustration, a score list corresponding to Fig.2 of 
        Keith Hall's 'K-best Spanning Tree Parsing' paper:
              scores = [[[], [5],  [1],  [1]],
                       [[], [],   [11], [4]],
                       [[], [10], [],   [5]],
                       [[], [8],  [8],  []]]
        When used in conjunction with a MaxEntClassifier, each score would 
        correspond to the confidence of a particular edge being classified 
        with the positive training examples.
        """
        raise AssertionError('DependencyScorerI is an abstract interface')

    #////////////////////////////////////////////////////////////
    # Comparisons
    #////////////////////////////////////////////////////////////
    def __cmp__(self, other):
        raise AssertionError('DependencyScorerI is an abstract interface')

    def __hash__(self, other):
        raise AssertionError('DependencyScorerI is an abstract interface')



#################################################################
# NaiveBayesDependencyScorer
#################################################################

class NaiveBayesDependencyScorer(DependencyScorerI):
    """
    A dependency scorer built around a MaxEnt classifier.  In this
    particular class that classifier is a C{NaiveBayesClassifier}.
    It uses head-word, head-tag, child-word, and child-tag features
    for classification.
    """

    def __init__(self):
        print # Do nothing without throwing error?

    def train(self, graphs):
        """
        Trains a C{NaiveBayesClassifier} using the edges present in 
        graphs list as positive examples, the edges not present as
        negative examples.  Uses a feature vector of head-word,
        head-tag, child-word, and child-tag.
        
        @type graphs: A list of C{DependencyGraph}
        @param graphs: A list of dependency graphs to train the scorer.     
        """

        # Create training labeled training examples
        labeled_examples = []
        for graph in graphs:
            for head_node in graph.nodelist:
                for child_index in range(len(graph.nodelist)):
                    child_node = graph.get_by_address(child_index)
                    if child_index in head_node['deps']:
                        label = "T"
                    else:
                        label = "F"
                    features = [head_node['word'], head_node['tag'], child_node['word'], child_node['tag']]
                    labeled_examples.append((dict(a=head_node['word'],b=head_node['tag'],c=child_node['word'],d=child_node['tag']), label))
        # Train the classifier
        import nltk
        nltk.usage(nltk.ClassifierI)
        self.classifier = nltk.classify.NaiveBayesClassifier.train(labeled_examples)

    def score(self, graph):
        """
        Converts the graph into a feature-based representation of 
        each edge, and then assigns a score to each based on the 
        confidence of the classifier in assigning it to the 
        positive label.  Scores are returned in a multidimensional list.
        
        @type graph: C{DependencyGraph}
        @param graph: A dependency graph to score.
        @rtype: 3 dimensional list
        @return: Edge scores for the graph parameter.
        """
        # Convert graph to feature representation
        edges = []
        for i in range(len(graph.nodelist)):
            for j in range(len(graph.nodelist)):
                head_node = graph.get_by_address(i)
                child_node = graph.get_by_address(j)
                print head_node
                print child_node
                edges.append((dict(a=head_node['word'],b=head_node['tag'],c=child_node['word'],d=child_node['tag'])))
        # Score edges
        edge_scores = []
        row = []
        count = 0
        for pdist in self.classifier.batch_prob_classify(edges):
            print '%.4f %.4f' % (pdist.prob('T'), pdist.prob('F'))
            row.append([math.log(pdist.prob("T"))])
            count += 1
            if count == len(graph.nodelist):
                edge_scores.append(row)
                row = []
                count = 0
        return edge_scores              


#################################################################
# A Scorer for Demo Purposes
#################################################################
# A short class necessary to show parsing example from paper
class DemoScorer:

    def train(self, graphs):
        print 'Training...'

    def score(self, graph):
        # scores for Keith Hall 'K-best Spanning Tree Parsing' paper
        return [[[], [5],  [1],  [1]],
                [[], [],   [11], [4]],
                [[], [10], [],   [5]],
                [[], [8],  [8],  []]]

#################################################################
# Non-Projective Probabilistic Parsing
#################################################################

class ProbabilisticNonprojectiveParser(object):
    """
    A probabilistic non-projective dependency parser.  Nonprojective 
    dependencies allows for "crossing branches" in the parse tree 
    which is necessary for representing particular linguistic 
    phenomena, or even typical parses in some languages.  This parser 
    follows the MST parsing algorithm, outlined in McDonald(2005), 
    which likens the search for the best non-projective parse to 
    finding the maximum spanning tree in a weighted directed graph.
    """
    def __init__(self):
        """
        Creates a new non-projective parser.
        """
        print 'initializing prob. nonprojective...'

    def train(self, graphs, dependency_scorer):
        """
        Trains a C{DependencyScorerI} from a set of C{DependencyGraph} objects,
        and establishes this as the parser's scorer.  This is used to 
        initialize the scores on a C{DependencyGraph} during the parsing 
        procedure.
        
        @type graphs: A list of C{DependencyGraph}
        @param graphs: A list of dependency graphs to train the scorer.
        @type dependency_scorer: C{DependencyScorerI}
        @param dependency_scorer: A scorer which implements the
        C{DependencyScorerI} interface.
        """
        self._scorer = dependency_scorer
        self._scorer.train(graphs)

    def initialize_edge_scores(self, graph):
        """
        Assigns a score to every edge in the C{DependencyGraph} graph.
        These scores are generated via the parser's scorer which 
        was assigned during the training process.
        
        @type graph: C{DependencyGraph}
        @param graph: A dependency graph to assign scores to.
        """
        self.scores = self._scorer.score(graph)

    def collapse_nodes(self, new_node, cycle_path, g_graph, b_graph, c_graph):
        """
        Takes a list of nodes that have been identified to belong to a cycle,
        and collapses them into on larger node.  The arcs of all nodes in 
        the graph must be updated to account for this.
        
        @type new_node: Node.
        @param new_node: A Node (Dictionary) to collapse the cycle nodes into.
        @type cycle_path: A list of integers.
        @param cycle_path: A list of node addresses, each of which is in the cycle.
        @type g_graph, b_graph, c_graph: C{DependencyGraph}
        @param g_graph, b_graph, c_graph: Graphs which need to be updated.
        """
        print 'Collapsing nodes...'
        # Collapse all cycle nodes into v_n+1 in G_Graph
        for cycle_node_index in cycle_path:
            g_graph.remove_by_address(cycle_node_index)
        g_graph.nodelist.append(new_node)
        g_graph.redirect_arcs(cycle_path, new_node['address'])

    def update_edge_scores(self, new_node, cycle_path):
        """
        Updates the edge scores to reflect a collapse operation into
        new_node.
        
        @type new_node: A Node.
        @param new_node: The node which cycle nodes are collapsed into.
        @type cycle_path: A list of integers.
        @param cycle_path: A list of node addresses that belong to the cycle.
        """
        print 'cycle', cycle_path
        cycle_path = self.compute_original_indexes(cycle_path)
        print 'old cycle ', cycle_path
        print 'Prior to update:\n', self.scores
        for i, row in enumerate(self.scores):
            for j, column in enumerate(self.scores[i]):
                print self.scores[i][j]
                if j in cycle_path and not i in cycle_path and len(self.scores[i][j]) > 0:
                    new_vals = []
                    subtract_val = self.compute_max_subtract_score(j, cycle_path)
                    print self.scores[i][j], ' - ', subtract_val
                    for cur_val in self.scores[i][j]:
                        new_vals.append(cur_val - subtract_val)
                    self.scores[i][j] = new_vals
        for i, row in enumerate(self.scores):
            for j, cell in enumerate(self.scores[i]):
                if i in cycle_path and j in cycle_path:
                    self.scores[i][j] = []
        print 'After update:\n', self.scores

    def compute_original_indexes(self, new_indexes):
        """
        As nodes are collapsed into others, they are replaced 
        by the new node in the graph, but it's still necessary
        to keep track of what these original nodes were.  This
        takes a list of node addresses and replaces any collapsed
        node addresses with their original addresses.
        
        @type new_address: A list of integers.
        @param new_addresses: A list of node addresses to check for
        subsumed nodes.
        """
        swapped = True
        while(swapped):
            originals = []
            swapped = False
            for new_index in new_indexes:
                if self.inner_nodes.has_key(new_index):
                    for old_val in self.inner_nodes[new_index]:
                        if not old_val in originals:
                            originals.append(old_val)
                            swapped = True
                else:
                    originals.append(new_index)
            new_indexes = originals
        return new_indexes
        
    def compute_max_subtract_score(self, column_index, cycle_indexes):
        """
        When updating scores the score of the highest-weighted incoming
        arc is subtracted upon collapse.  This returns the correct 
        amount to subtract from that edge.
        
        @type column_index: integer.
        @param column_index: A index representing the column of incoming arcs
        to a particular node being updated
        @type cycle_indexes: A list of integers.
        @param cycle_indexes: Only arcs from cycle nodes are considered.  This 
        is a list of such nodes addresses.
        """
        max_score = -100000
        for row_index in cycle_indexes:
            for subtract_val in self.scores[row_index][column_index]:
                if subtract_val > max_score:
                    max_score = subtract_val
        return max_score


    def best_incoming_arc(self, node_index):
        """
        Returns the source of the best incoming arc to the 
        node with address: node_index
        
        @type node_index: integer.
        @param node_index: The address of the 'destination' node,
        the node that is arced to.
        """
        originals = self.compute_original_indexes([node_index])
        print 'originals:', originals
        max_arc = None
        max_score = None
        for row_index in range(len(self.scores)):
            for col_index in range(len(self.scores[row_index])):
#               print self.scores[row_index][col_index]
                if col_index in originals and self.scores[row_index][col_index] > max_score:
                    max_score = self.scores[row_index][col_index]
                    max_arc = row_index
                    print row_index, ',', col_index
        print max_score
        for key in self.inner_nodes:
            replaced_nodes = self.inner_nodes[key]
            if max_arc in replaced_nodes:
                return key
        return max_arc
        
    def original_best_arc(self, node_index):
        """
        ???
        """
        originals = self.compute_original_indexes([node_index])
        max_arc = None
        max_score = None
        max_orig = None
        for row_index in range(len(self.scores)):
            for col_index in range(len(self.scores[row_index])):
                if col_index in originals and self.scores[row_index][col_index] > max_score:
                    max_score = self.scores[row_index][col_index]
                    max_arc = row_index
                    max_orig = col_index
        return [max_arc, max_orig]

                        
    def parse(self, tokens, tags):
        """
        Parses a list of tokens in accordance to the MST parsing algorithm
        for non-projective dependency parses.  Assumes that the tokens to 
        be parsed have already been tagged and those tags are provided.  Various 
        scoring methods can be used by implementing the C{DependencyScorerI}
        interface and passing it to the training algorithm.
        
        @type tokens: A list of C{String}.
        @param tokens: A list of words or punctuation to be parsed.
        @type tags: A List of C{String}.
        @param tags: A list of tags corresponding by index to the words in the tokens list.
        """
        self.inner_nodes = {}
        # Initialize g_graph
        g_graph = DependencyGraph()
        for index, token in enumerate(tokens):
            g_graph.nodelist.append({'word':token, 'tag':tags[index], 'deps':[], 'rel':'NTOP', 'address':index+1})
        # Fully connect non-root nodes in g_graph
        g_graph.connect_graph() 
        original_graph = DependencyGraph()
        for index, token in enumerate(tokens):
            original_graph.nodelist.append({'word':token, 'tag':tags[index], 'deps':[], 'rel':'NTOP', 'address':index+1})

        # Initialize b_graph
        b_graph = DependencyGraph()
        b_graph.nodelist = []
        # Initialize c_graph
        c_graph = DependencyGraph()
        c_graph.nodelist = [{'word':token, 'tag':tags[index], 'deps':[],
                             'rel':'NTOP', 'address':index+1}
                            for index, token in enumerate(tokens)]
        # Assign initial scores to g_graph edges
        self.initialize_edge_scores(g_graph)
        print self.scores
        # Initialize a list of unvisited vertices (by node address)
        unvisited_vertices = [vertex['address'] for vertex in c_graph.nodelist]
        # Iterate over unvisited vertices
        nr_vertices = len(tokens)
        betas = {}
        while(len(unvisited_vertices) > 0):
            # Mark current node as visited
            current_vertex = unvisited_vertices.pop(0)
            print 'current_vertex:', current_vertex
            # Get corresponding node n_i to vertex v_i
            current_node = g_graph.get_by_address(current_vertex)
            print 'current_node:', current_node
            # Get best in-edge node b for current node
            best_in_edge = self.best_incoming_arc(current_vertex)
            betas[current_vertex] = self.original_best_arc(current_vertex)
            print 'best in arc: ', best_in_edge, ' --> ', current_vertex
            # b_graph = Union(b_graph, b)
            for new_vertex in [current_vertex, best_in_edge]:
                b_graph.add_node({'word':'TEMP', 'deps':[], 'rel': 'NTOP', 'address': new_vertex})
            b_graph.add_arc(best_in_edge, current_vertex)
            # Beta(current node) = b  - stored for parse recovery
            # If b_graph contains a cycle, collapse it
            cycle_path = b_graph.contains_cycle()
            if cycle_path:
            # Create a new node v_n+1 with address = len(nodes) + 1
                new_node = {'word': 'NONE', 'deps':[], 'rel': 'NTOP', 'address': nr_vertices + 1}
            # c_graph = Union(c_graph, v_n+1)
                c_graph.add_node(new_node)
            # Collapse all nodes in cycle C into v_n+1
                self.update_edge_scores(new_node, cycle_path)
                self.collapse_nodes(new_node, cycle_path, g_graph, b_graph, c_graph)
                for cycle_index in cycle_path:
                    c_graph.add_arc(new_node['address'], cycle_index)
#                   self.replaced_by[cycle_index] = new_node['address']

                self.inner_nodes[new_node['address']] = cycle_path

            # Add v_n+1 to list of unvisited vertices
                unvisited_vertices.insert(0, nr_vertices + 1)               
            # increment # of nodes counter
                nr_vertices += 1
            # Remove cycle nodes from b_graph; B = B - cycle c
                for cycle_node_address in cycle_path:
                    b_graph.remove_by_address(cycle_node_address)
            print 'g_graph:\n', g_graph
            print
            print 'b_graph:\n', b_graph
            print
            print 'c_graph:\n', c_graph
            print
            print 'Betas:\n', betas
            print 'replaced nodes', self.inner_nodes
            print
        #Recover parse tree
        print 'Final scores:\n', self.scores
        print 'Recovering parse...'
        for i in range(len(tokens) + 1, nr_vertices + 1):
            betas[betas[i][1]] = betas[i]
        print 'Betas: ', betas
        new_graph = DependencyGraph()
        for node in original_graph.nodelist:
            node['deps'] = []
        for i in range(1, len(tokens) + 1):
#           print i, betas[i]
            original_graph.add_arc(betas[i][0], betas[i][1])
#       print original_graph
        return original_graph
        print 'Done.'

        

#################################################################
# Rule-based Non-Projective Parser
#################################################################

class NonprojectiveDependencyParser(object):
    """
    A non-projective, rule-based, dependency parser.  This parser 
    will return the set of all possible non-projective parses based on 
    the word-to-word relations defined in the parser's dependency 
    grammar, and will allow the branches of the parse tree to cross 
    in order to capture a variety of linguistic phenomena that a 
    projective parser will not.
    """

    def __init__(self, dependency_grammar):
        """
        Creates a new C{NonprojectiveDependencyParser}.

        @param dependency_grammar: a grammar of word-to-word relations.
        @type depenedncy_grammar: C{DependencyGrammar}
	    """
        self._grammar = dependency_grammar

    def parse(self, tokens):
        """
        Parses the input tokens with respect to the parser's grammar.  Parsing 
        is accomplished by representing the search-space of possible parses as 
        a fully-connected directed graph.  Arcs that would lead to ungrammatical 
        parses are removed and a lattice is constructed of length n, where n is 
        the number of input tokens, to represent all possible grammatical 
        traversals.  All possible paths through the lattice are then enumerated
        to produce the set of non-projective parses.

        param tokens: A list of tokens to parse.
        type tokens: A C{list} of L{String}.
        return: A set of non-projective parses.
        rtype: A C{list} of L{DependencyGraph} 
        """
        # Create graph representation of tokens
        self._graph = DependencyGraph()
        self._graph.nodelist = []  # Remove the default root
        for index, token in enumerate(tokens):
            self._graph.nodelist.append({'word':token, 'deps':[], 'rel':'NTOP', 'address':index})
        for head_node in self._graph.nodelist:
            deps = []
            for dep_node in self._graph.nodelist:
                if self._grammar.contains(head_node['word'], dep_node['word']) and not head_node['word'] == dep_node['word']:
                    deps.append(dep_node['address'])
            head_node['deps'] = deps
        # Create lattice of possible heads
        roots = []
        possible_heads = []
        for i, word in enumerate(tokens):
            heads = []
            for j, head in enumerate(tokens):
                if (i != j) and self._grammar.contains(head, word):
                    heads.append(j)
            if len(heads) == 0:
                roots.append(i)
            possible_heads.append(heads)
        # Set roots to attempt
        if len(roots) > 1:
            print "No parses found."
            return False
        elif len(roots) == 0:
            for i in range(len(tokens)):
                roots.append(i)
        # Traverse lattice
        analyses = []
        for root in roots:
            stack = []
            analysis = [[] for i in range(len(possible_heads))]
            i = 0
            forward = True
            while(i >= 0):
                if forward:
                    if len(possible_heads[i]) == 1:
                        analysis[i] = possible_heads[i][0]
                    elif len(possible_heads[i]) == 0:
                        analysis[i] = -1
                    else:
                        head = possible_heads[i].pop()
                        analysis[i] = head
                        stack.append([i, head])
                if not forward:
                    index_on_stack = False
                    for stack_item in stack:
#                       print stack_item
                        if stack_item[0] == i:
                            index_on_stack = True
                    orig_length = len(possible_heads[i])
#                    print len(possible_heads[i])
                    if index_on_stack and orig_length == 0:
                        for j in xrange(len(stack) -1, -1, -1):
                            stack_item = stack[j]
                            if stack_item[0] == i:
                                possible_heads[i].append(stack.pop(j)[1])
#                        print stack
                    elif index_on_stack and orig_length > 0:
                        head = possible_heads[i].pop()
                        analysis[i] = head
                        stack.append([i, head])
                        forward = True

#                   print 'Index on stack:', i, index_on_stack
                if i + 1 == len(possible_heads):
                    analyses.append(analysis[:])
                    forward = False
                if forward:
                    i += 1
                else:
                    i -= 1
        # Filter parses
        graphs = []
        #ensure 1 root, every thing has 1 head
        for analysis in analyses:
            root_count = 0
            root = []
            for i, cell in enumerate(analysis):
                if cell == -1:
                    root_count += 1
                    root = i
            if root_count == 1:
                graph = DependencyGraph()
                graph.nodelist[0]['deps'] = root + 1
                for i in range(len(tokens)):
                    node = {'word':tokens[i], 'address':i+1}
                    node['deps'] = [j+1 for j in range(len(tokens)) if analysis[j] == i] 
                    graph.nodelist.append(node)
#                cycle = graph.contains_cycle()
#                if not cycle:
                graphs.append(graph)
        return graphs


#################################################################
# Demos
#################################################################

def demo():
#   hall_demo()
    nonprojective_conll_parse_demo()
    rule_based_demo()


def hall_demo():
    npp = ProbabilisticNonprojectiveParser()
    npp.train([], DemoScorer())
    parse_graph = npp.parse(['v1', 'v2', 'v3'], [None, None, None])
    print parse_graph

def nonprojective_conll_parse_demo():
    graphs = [DependencyGraph(entry)
              for entry in conll_data2.split('\n\n') if entry]    
    npp = ProbabilisticNonprojectiveParser()
    npp.train(graphs, NaiveBayesDependencyScorer())
    parse_graph = npp.parse(['Cathy', 'zag', 'hen', 'zwaaien', '.'], ['N', 'V', 'Pron', 'Adj', 'N', 'Punc'])
    print parse_graph

def rule_based_demo():
    grammar = parse_dependency_grammar("""
    'taught' -> 'play' | 'man'
    'man' -> 'the' | 'in'
    'in' -> 'corner'
    'corner' -> 'the'
    'play' -> 'golf' | 'dachshund' | 'to'
    'dachshund' -> 'his'
    """)
    print grammar
    ndp = NonprojectiveDependencyParser(grammar)
    graphs = ndp.parse(['the', 'man', 'in', 'the', 'corner', 'taught', 'his', 'dachshund', 'to', 'play', 'golf'])
    print 'Graphs:'
    for graph in graphs:
        print graph

if __name__ == '__main__':
    demo()
