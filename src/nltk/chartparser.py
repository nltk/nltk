# Natural Language Toolkit: A Chart Parser
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Steven Bird <sb@ldc.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""
The chartparser module defines the C{ChartParser} class, and two supporting
classes, C{Edge} and C{Chart}.
"""

from nltk.parser import *
from nltk.token import *
from nltk.rule import *
from nltk.tree import *
from nltk.set import *

def edgecmp(e1,e2):
    return cmp((e1.loc().length(), e1.loc(), e1.drule()),
               (e2.loc().length(), e2.loc(), e2.drule()))

##//////////////////////////////////////////////////////
##  Edge
##//////////////////////////////////////////////////////

class Edge:
    """
    An edge of a chart.    An edges is a span of tokens (i.e. a C{Location})
    with an associated C{DottedRule} and a C{Tree}.  The Edge class provides
    basic functions plus a some common chart-parser functions on edges.

    @type _drule: C{DottedRule}
    @ivar _drule: The dotted rule of the edge.
    @type _tree: C{TreeToken}
    @ivar _tree: The current parse tree of the edge.
    @type _loc: C{Location}
    @ivar _loc: The span of tokens covered by the edge.
    """
    
    def __init__(self, drule, tree, loc):
        """
        Construct a new C{Edge}.

        @param drule: The dotted rule associated with the edge.
        @type drule: C{DottedRule}
        @param tree: The (partial) parse tree so far constructed for the edge.
        @type tree: C{TreeToken}
        @param loc: The location spanned by the edge.
        @type loc: C{Location}
        """
        self._drule = drule
        self._tree = tree
        self._loc = loc

    def drule(self):
        """
        @return: the dotted rule of the edge.
        @rtype: C{DottedRule}
        """
        return self._drule

    def tree(self):
        """
        @return: the parse tree of the edge.
        @rtype: C{TreeToken}
        """
        return self._tree
    
    # a complete edge is one whose dotted rule is complete
    def complete(self):
        """
        @return: true if the C{DottedRule} of this edge is complete
        @rtype: C{boolean}
        """
        return self._drule.complete()

    def loc(self):
        """
        @return: the location spanned by this edge
        @rtype: C{Location}
        """
        return self._loc

    # the start/end of an edge is the start/end of the edge's location
    def start(self):
        """
        @return: the start index of the edge's location
        @rtype: C{Location}
        """
        return self._loc.start()

    def end(self):
        """
        @return: the end index of the edge's location
        @rtype: C{Location}
        """
        return self._loc.end()

    def __repr__(self):
        """
        @return: A concise string representation of the C{Edge}
        @rtype: C{string}
        """
        return repr(self._drule) + repr(self._tree) + repr(self._loc)

    def __eq__(self, other):
        """
        @return: true if this C{Edge} is equal to C{other}.
        @rtype: C{boolean}
        """
        return (self._drule == other._drule and
                self._tree == other._tree and
                self._loc == other._loc)

    def __hash__(self):
        """
        @return: A hash value for the C{Edge}.
        @rtype: C{int}
        """
        return hash((self._drule, self._tree, self._loc))

    def self_loop_start(self, rule):
        """
        @param rule: A grammar rule
        @type rule: C{Rule}
        @return: a zero-width self-loop edge at the start of this edge,
            with a dotted rule initialized from this rule
        @rtype: C{Edge}
        """
        loc = self.loc().start_loc()
        dr = rule.drule()
        return Edge(dr, TreeToken(dr.lhs()), loc)

    def self_loop_end(self, rule):
        """
        @param rule: A grammar rule
        @type rule: C{Rule}
        @return: a zero-width self-loop edge at the end of this edge,
            with a dotted rule initialized from this rule
        @rtype: C{Edge}
        """
        loc = self._loc.end_loc()
        dr = rule.drule()
        return Edge(dr, TreeToken(dr.lhs()), loc)

    def FR(self, edge):
        """
        @param edge: a completed edge immediately to the right
        @type edge: C{Edge}
        @return: a new edge resulting from the application of the fundamental rule of chart parsing
        @rtype: C{Edge}
        """
        loc = self._loc.union(edge.loc())
        dr = self._drule.shift()
        tree = TreeToken(self._tree.node(),
                         *(self._tree.children() + (edge.tree(),)))
        return Edge(dr, tree, loc)

##//////////////////////////////////////////////////////
##  Chart
##//////////////////////////////////////////////////////

class Chart:
    """
    A chart: a blackboard for hypotheses about syntactic constituents.

    @type _chart: C{Set} of C{Edge}s
    @ivar _chart: The set of C{Edge}s, keys of the hash array
    @type _loc: C{Location}
    @ivar _loc: The span of the chart, the C{Location} of a complete edge
    """
    def __init__(self, loc):
        """
        Construct a new Chart.
        
        @param loc: The span of text that it covered by this chart.  All
            edge indices in the chart will fall within this location.
        @type loc: C{Location}
        """
        self._edgeset = Set()
        self._loc = loc
        
    def loc(self):
        """
        @return: A location specifying the span of text covered by
            this chart.
        @rtype: C{Location}
        """
        return self._loc
    
    def edgeset(self):
        """
        @return: The set of edges contained in this chart.
        @rtype: C{Set} of C{Edge}
        """
        return self._edgeset
    
    def edges(self):
        """
        @return: A list of the edges contained in this chart.
        @rtype: C{sequence} of C{Edge}
        """
        return self._edgeset.elements()
    
    def __len__(self):
        """
        @return: The number of edges contained in this chart.
        @rtype: C{int}
        """
        return len(self._edgeset)

    def complete_edges(self):
        """
        @return: A list of all complete edges contained in this chart.
            A complete edge is an edge whose dotted rule has its dot
            in the final position.
        @rtype: C{sequence} of C{Edge}
        """
        return [e for e in self.edges() if e.complete()]
    
    def incomplete_edges(self):
        """
        @return: A list of all incomplete edges contained in this chart.
            An incomplete edge is an edge whose dotted rule has its dot
            in a nonfinal position.
        @rtype: C{sequence} of C{Edge}
        """
        return [e for e in self.edges() if not e.complete()]

    # [edloper 9/27/01] There is a copy module, which provides both
    # shallow & deep copying..  But I'm not sure that we need this
    # copy method anyway.  It wreaks havoc with my ChartView class,
    # cuz it doesn't like having to switch to a new chart. :)
    def copy(self):
        """
        @return: A deep copy of this chart.
        @rtype: C{Chart}
        """
        chart = Chart(self.loc())
        chart._edgeset = self._edgeset.copy()
        return chart
    
    def insert(self, edge):
        """
        Attempt to insert a new edge into this chart.  If the edge is
        already present, return []; otherwise, return a list
        containing the inserted edge.
        """
        if self._edgeset.insert(edge):
            return [edge]
        else:
            return []
        
    def parses(self, node):
        """
        Return the set of complete parses encoded by this chart, whose
        root node value is C{node}.  Use self._loc to test if the edge
        spans the entire chart.
        """
        return [edge.tree() for edge in self.edges() if
                edge.loc() == self._loc and edge.drule().lhs() == node]

    def contains(self, edge):
        """
        @return: true iff this C{Chart} contains the specified edge.
        @rtype: C{boolean}
        """
        return edge in self._edgeset
        
    def __contains__(self, edge):
        """
        @return: true iff this C{Chart} contains the specified edge.
        @rtype: C{boolean}
        """
        return edge in self._edgeset
            
    #draw (NB, there is also a tkinter version nltk.draw.chart)
    def draw(self, width=7):
        print "="*75
        edges = self.edges()
        edges.sort(edgecmp)
        for edge in edges:
            start = edge.start()
            end = edge.end()
            indent = " " * width * start
            print indent, edge.drule()
            print indent + "|" + "-"*(width*(end-start)-1) + "|"

# this code should be replaced with a more transparent version
def _seq_loc(tok_sent):
    """
    Return the location that spans a given sequence of tokens.
    """
    return TreeToken('', *tok_sent).loc()

##//////////////////////////////////////////////////////
##  ChartParserStrategy
##//////////////////////////////////////////////////////

class ChartParserStrategy:
    # A couple of paragraphs here are identical to paragraphs from the
    # ChartParser docs.  I think that's ok.
    """
    The C{ChartParserStrategy} class encodes the list of X{chart
    rules} used by a C{ChartParser} to specify the conditions under
    which new edges should be added to the chart.  There are two kinds
    of chart rules:

        - X{Static Rules} search the chart for specific contexts
          where edges should be added.  The C{parse} method will
          repeatedly invoke each static rule, until it produces no
          new edges.
        - X{Edge Triggerd Rules} add new edges to the chart whenever
          certain kinds of edges are added by any chart rule.

    A C{ChartParserStrategy} consists of a list of static rules and
    a list of edge triggered rules.
          
    Chart rules are defined using functions, which return a list of
    new edges to add to a chart.  These functions should I{not}
    directly modify the chart (e.g., do not add the edges to the chart
    yourself; C{ChartParser} will add them for you).  Static rules
    are defined with functions of the form::

        def static_rule(chart, grammar, basecat):
            ...   # Decide which edges to add (if any)
            return edges

    Where C{chart} is the chart that the static rule should act
    upon; C{grammar} is the grammar used by the chart parser; and
    C{basecat} is the top-level category of the grammar (e.g. 'S').
    The function should return a C{list} of C{Edge}s.  These edges
    will be added to the chart by the chart parser.
            
    Edge triggered rules are defined with functions of the form::

        def edge_triggered_rule(chart, grammar, basecat, edge):
            ...   # Decide which edges to add (if any)
            return edges

    Where C{chart} is the chart that the static rule should act
    upon; C{grammar} is the grammar used by the chart parser;
    C{basecat} is the top-level category of the grammar (e.g. 'S');
    and C{edge} is the edge that triggered this rule.  The function
    should return a C{list} of C{Edge}s.  These edges will be added to
    the chart by the chart parser.
    """
    def __init__(self, static, edgetriggered):
        """
        Construct a new C{ChartParserStrategy} containing the given
        lists of static rules and edge triggered rules.  See the
        reference documentation for the C{ChartParserStrategy} class
        for more information on what values should be used for
        static chart rules and edge triggered chart rules.
        
        @type static: C{list} of C{function}s
        @param static: The ordered list of static rules that
            should be used by a C{ChartParser}.
        @type edgetriggered: C{list} of C{function}s
        @param edgetriggered: The ordered list of edge triggered rules
            that should be used by a C{ChartParser}.
        """
        self._static = static
        self._edgetriggered = edgetriggered

    def static(self):
        """
        @return: the ordered list of static rules that
            should be used by a C{ChartParser}.
        @rtype: C{list} of C{function}s
        """
        return self._static
        
    def edgetriggered(self):
        """
        @return: the ordered list of edge triggered rules that
            should be used by a C{ChartParser}.
        @rtype: C{list} of C{function}s
        """
        return self._edgetriggered

##//////////////////////////////////////////////////////
##  ChartParser
##//////////////////////////////////////////////////////

class ChartParser(ParserI):
    # [edloper 9/27/01]: "Standard rules" *really* needs a different
    #     name.  -- changed to "Static" for now, still not happy
    #     with that name..
    # [edloper 9/27/01]: We are using "rule" with two different
    #     meanings: a CFG rule (as in the Rule class); and a
    #     chart-parsing rule (as in top-down rule, fundamental rule).
    #     This is almost guaranteed to cause confusion.  Can we play
    #     any games with our terminology to clean this up?  For now
    #     I'm using the terms "chart rule" and "production rule"...
    """
    A generic chart parser.  C{ChartParser} derives parse trees for a
    text by iteratively adding "edges" to a "chart."  Each X{edge}
    represents a hypothesis about the tree structure representing a
    subsequence of the text.  The X{chart} is a "blackboard" for
    composing and combining these hypotheses.

    When the chart parser begins parsing a text, it creates a new
    (empty) chart, spanning the text.  It then incrementally adds new
    edges to the chart.  A set of X{chart rules} specifies the
    conditions under which new edges should be added to the chart.
    There are two kinds of chart rules:

        - X{Static Rules} search the chart for specific contexts where
          edges should be added.  The C{parse} method will repeatedly
          invoke each static rule, until it produces no new edges.
        - X{Edge Triggerd Rules} add new edges to the chart whenever
          certain kinds of edges are added by any chart rule.

    Once the chart reaches a stage where none of the static rules
    adds any new edges, parsing is complete.
          
    The set of chart rules used by a chart parser is known as its
    X{strategy}.  Several standard strategies, such as X{top-down
    parsing} and X{bottom-up parsing}, are already defined by the
    C{nltk.chartparser} module; however, you can easily create your
    own rules and strategies, as well.

    The Lexicon and Grammar
    =======================
    
    When a new C{ChartParser} is constructed, it must be given a
    lexicon and a grammar.  The X{lexicon} specifies the lexical
    category for each lexical item.  For example, when parsing
    sentences, it would specify lexical categories such as "N" and "V"
    for words types such as "dog" and "run."  The X{grammar} specifies
    the set of valid X{production rules} that can be used to construct
    a parse tree.  For example, it might include the production rule
    "NP->Det N," specifying that a noun phrase may be composed of a
    determiner followed by a noun.

    Both the lexicon and the grammar are specified using lists of
    C{Rule}s.  Typical lexicon and grammar rules are::

        lexicon_rule = Rule('N', ('dog',))
        grammar_rule = Rule('NP', ('Det', 'N'))
        
    You should be careful not to confuse I{production rules} (which
    are represented as C{Rule} objects) with I{chart rules} (which are
    represented with functions).  See the reference documentation for
    C{nltk.rule.Rule} for more information about production rules.
    
    Parsing
    =======
    
    Before a chart parser can be used, its strategy must be defined.
    You can set a chart parser's strategy with the C{set_strategy}
    method, or by calling C{parse} with a C{strategy} keyword
    argument.  Once you have defined the C{ChartParser}'s strategy,
    you can parse a sentence using the C{parse} method.

    @type _grammar: C{sequence} of C{Rule}s
    @ivar _grammar: The C{Rule}s of the grammar
    @type _basecat: C{string}
    @ivar _basecat: The top-level category of the grammar (e.g. 'S')
    @type _lexicon: C{sequence} of C{Rule}s
    @ivar _lexicon: The C{Rule}s of the lexicon;
        lexical rules are assumed to have only one rhs element
    @type _strategy: C{ChartParserStrategy}
    @ivar _strategy: The strategy used by this ChartParser.
    """
    ##############################################
    # Initialization
    ##############################################
    def __init__(self, grammar, lexicon, basecat, **kwargs):
        """
        Construct a new generic chart parser.  Before the chart parser
        can be used to parse a sentence, its strategy must be set,
        with the C{set_strategy} method.  Alternatively, you can give
        C{parse} a C{strategy} keyword argument.

        Valid keyword arguments are C{trace}, which causes the
        C{ChartParser} to print out information about what edges it
        adds to the chart whenever it parses a sentence;
        C{callback}, which specifies a callback function to be invoked
        every time a new edge is added to the chart; and C{strategy},
        which defines the C{ChartParser}'s strategy.

        @type grammar: C{list} of C{Rule}
        @param grammar: The list of production rules in the grammar.
        @type lexicon: C{list} of C{Rule}
        @param lexicon: The list of production rules in the lexicon.
        @type basecat: C{string}
        @param basecat: The top-level category of the grammar
            (e.g. 'S').
        """
        self._grammar = grammar
        self._lexicon = lexicon
        self._basecat = basecat
        self._callback = self._trace = None
        self._strategy = None
        if kwargs.has_key('callback'):
            self._callback = kwargs['callback']
        if kwargs.has_key('trace'):
            self._trace = kwargs['trace']
        if kwargs.has_key('strategy'):
            self.set_strategy(kwargs['strategy'])
        self._chart = None

    def set_strategy(self, strategy):
        """
        Define which strategy this C{ChartParser} should use.  The
        strategy determines the conditions under which the
        C{ChartParser} will add edges to its chart.

        @param strategy: The new strategy
        @type strategy: C{ChartParserStrategy}
        """
        self._strategy = strategy

    ##############################################
    # Accessor functions.
    ##############################################
    def grammar(self):
        """
        @return: The list of production rules in the
            C{ChartParser}'s grammar.
        @rtype: C{list} of C{Rule}
        """
        return self._grammar
    
    def lexicon(self):
        """
        @return: The list of production rules in the
            C{ChartParser}'s lexicon.
        @rtype: C{list} of C{Rule}
        """
        return self._lexicon
    
    def basecat(self):
        """
        @return: The top-level category of the grammar (e.g. 'S')
        @rtype: C{string}
        """
        return self._basecat
    
    def chart(self):
        """
        @return: The chart used by this C{ChartParser}.  This chart
          should not be modified; doing so will have undefined effects
          on the behavior of the ChartParser.
        @rtype: C{Chart}
        """
        return self._chart

    def parses(self):
        """
        @return: A list of the complete parses that are currently
            present on this C{ChartParser}'s chart.
        @rtype: C{list} of C{TreeToken}
        """
        return self._chart.parses(self._basecat)

    ##############################################
    # Parsing
    ##############################################
    
    def _initialize_chart(self, tok_sent):
        """
        Initialize the chart with a given tokenized sentence.  This
        constructs a new chart; and populates it with "lexical edges,"
        i.e., edges spanning each of the lexical items.  Note that
        this will *not* cause any edge triggered rules to fire.

        @param tok_sent: A tokenized list of the tokens which should
            be parsed.
        """
        # Construct a new (empty) chart that spans the given
        # sentence.
        loc = _seq_loc(tok_sent)
        self._chart = Chart(loc)

        # Add an edge for each lexical item.
        added = []
        for word in tok_sent:
            # Find a lexical rule for this word.
            for rule in self._lexicon:
                if word.type() == rule[0]:
                    # We found an edge for this word.
                    drule = DottedRule(rule.lhs(), rule.rhs(), 1)
                    tree = TreeToken(rule.lhs(), word)
                    edge = Edge(drule, tree, word.loc())
                    added += self._chart.insert(edge)

        # If we're tracing the output, print the newly initialized chart.
        if self._trace:
            self._chart.draw()

        # Return the list of edges that we added to the chart.
        return added

    def _insert(self, edge):
        """
        Insert a given edge into the chart.  Call all edge triggered
        rules with this new edge, and insert their results into the
        chart (with a recursive call to C{_insert}).
        
        @param edge: The new edge to insert
        @type edge: C{Edge}
        """
        # Insert the edge.  If it's already present, return, because
        # there's nothing else to do.
        added = self._chart.insert(edge)
        if not added: return []

        # Handle trace and callback.
        if self._trace: print edge
        if self._callback: self._callback(self._chart, edge)

        # Try each of the edge triggered rules, and add their results
        # to the chart (with a recursive call to _insert).
        for func in self._strategy.edgetriggered():
            for new_edge in func(self._chart, self._grammar,
                                 self._basecat, edge):
                added += self._insert(new_edge)

        # Return the list of all new edges that we added.
        return added

    def parse(self, tok_sent, n=None, **kwargs):
        # Inherit documentation from ParserI
        # This means that we don't document the strategy keyword
        # argument -- but that's ok for now.  We could always
        # copy/paste, I guess.

        # Make sure we have a valid strategy.
        if kwargs.has_key('strategy'):
            self._strategy = kwargs['strategy']
        if not self._strategy:
            raise ValueError('You must define a strategy before '+
                             'you can parse')

        # Initialize the chart with the new sentence.
        self._initialize_chart(tok_sent)

        # Run the static rules.  Run each rule until it generates no
        # new edges.  Use the variable "added" to keep track
        # of what edges we've added (so we'll know whether to keep
        # running the rule or not).
        chart = self._chart
        grammar = self._grammar
        basecat = self._basecat

        for func in self._strategy.static():
            while 1:
                added = []
                new_edges = func(chart, grammar, basecat)
                for edge in new_edges:
                    added += self._insert(edge)

                # If there were no new edges, we're done with this rule.
                if not added: break

        # Return the n best parses.
        if n == None:
            return self.parses()
        else:
            return self.parses()[:n]

##//////////////////////////////////////////////////////
##  Chart Rules
##//////////////////////////////////////////////////////
#
# See the docstring for ChartParser for a discussion of the
# different types of chart rules.

def TD_init(chart, grammar, basecat):
    "Top-down init (static rule)"
    added = []

    loc = chart.loc().start_loc()
    for rule in grammar:
        if rule.lhs() == basecat:
            drule = rule.drule()
            new_edge = Edge(drule, TreeToken(drule.lhs()), loc)
            added += [new_edge]
    return added

def TD_edge(chart, grammar, basecat, edge):
    "Top-down init (edge triggered rule)"
    added = []
    for rule in grammar:
        if not edge.complete() and rule.lhs() == edge.drule().next():
            new_edge = edge.self_loop_end(rule)
            added += [new_edge]
    return added

def BU_init_edge(chart, grammar, basecat, edge):
    "Bottom-up init (static rule helper) (NOT A RULE)"
    added = []
    for rule in grammar:
        if edge.drule().lhs() == rule[0]:
            new_edge = edge.self_loop_start(rule)
            added += [new_edge]
    return added

def BU_init(chart, grammar, basecat):
    "Bottom-up init (static rule)"
    added = []
    for edge in chart.edges():
        added += BU_init_edge(chart, grammar, basecat, edge)
    return added

# Fundamental rule edge
def FR_edge(chart, grammar, basecat, edge):
    "Fundamental rule (static rule helper) (NOT A RULE)"
    added = []
    if not edge.complete():
        for edge2 in chart.complete_edges():
            if (edge.drule().next() == edge2.drule().lhs() and
                edge.end() == edge2.start()):
                new_edge = edge.FR(edge2)
                added += [new_edge]
    return added

# fundamental rule
def FR(chart, grammar, basecat):
    "Fundamental rule (static rule)"
    added = []
    for edge in chart.edges():
        added += FR_edge(chart, grammar, basecat, edge)
    return added

##//////////////////////////////////////////////////////
##  Strategies
##//////////////////////////////////////////////////////

# Define some useful rule invocation strategies.
TD_STRATEGY = ChartParserStrategy([TD_init, FR], [TD_edge])
BUINIT_STRATEGY = ChartParserStrategy([BU_init], [])
BU_STRATEGY = ChartParserStrategy([BU_init, FR], [])
TDINIT_STRATEGY = ChartParserStrategy([TD_init], [])
FR_STRATEGY = ChartParserStrategy([FR], [])
def bu_edge_strategy(edge):
    def BU_edge_rule(chart, grammar, basecat, edge=edge):
        return BU_init_edge(chart, grammar, basecat, edge)
    return ChartParserStrategy([BU_edge_rule], [])
def fr_edge_strategy(edge):
    def FR_edge_rule(chart, grammar, basecat, edge=edge):
        return FR_edge(chart, grammar, basecat, edge)
    return ChartParserStrategy([FR_edge_rule], [])
def td_edge_strategy(edge):
    def TD_edge_rule(chart, grammar, basecat, edge=edge):
        return TD_edge(chart, grammar, basecat, edge)
    return ChartParserStrategy([TD_edge_rule], [])


##//////////////////////////////////////////////////////
##  SteppingChartParser
##//////////////////////////////////////////////////////

class SteppingChartParser(ChartParser):
    """
    A C{ChartParser} that allows you to step through the parsing
    process, adding a single edge at a time.  It also allows you to
    change the strategy you are using.
    
    It defines one new method: C{step}

    @ivar _queue: A list of I{(edge, rule)} pairs, where I{edge} was 
        generated by I{rule}.
    """
    # To implement the stepping chart parser, we need to override the
    # _insert method, to only add one edge at a time.
    #

    def __init__(self, grammar, lexicon, basecat, **kwargs):
        # Inherit docs from ChartParser.
        ChartParser.__init__(self, grammar, lexicon,
                             basecat, **kwargs)
        self._queue = []
        self._initialized = 0
        self._function_index = 0
        self._current_strategy = None

    def initialize(self, tok_sent, **kwargs):
        # Make sure we have a valid strategy.
        if kwargs.has_key('strategy'):
            self._strategy = kwargs['strategy']
        if not self._strategy.static():
            raise ValueError('You must define a strategy before '+
                             'you can parse')

        # Initialize the chart with the new sentence.
        self._initialize_chart(tok_sent)

        # We need to keep track of which static function we're
        # currently working on.
        self._function_index = 0

        # Remember what strategy we started out using.
        self._current_strategy = self._strategy
        
        # We have successfully initialized.
        self._initialized = 1

        # Did we just change strategies?  This is useful to know,
        # because if we did, we need to check to make sure we don't
        # skip any edge-triggered rules.
        self._just_changed_strategy = 0

    ##############################################
    # Queueing
    ##############################################
    
    def _insert(self, edge, rule):
        # Add an edge to the end of the queue
        if edge in self._chart:
            # We need to make sure that we get the right edge-triggered
            # edges.  If we just switched strategies, we should
            # re-check our edge-triggered rules.  Once we find at
            # least once edge-triggered rule that we hadn't found
            # before, we're in the clear.
            if (self._strategy.edgetriggered() and
                self._just_changed_strategy):
                self._queue = [(edge, rule)] + self._queue
                self._dequeue()
                if self._queue:
                    self._just_changed_strategy = 0
        else:
            self._queue.append( (edge, rule) )
        return []
        
    def _dequeue(self, **kwargs):
        """
        Add the first Edge from the queue to the chart, and return
        it.  At this time, we also run the edge_trigger functions on
        that edge, and queue their results.

        If we wanted to mimic the behavior of the non-stepped version
        more closely, then we should enqueue those at the beginning of
        the queue.
        
        This function assumes that self._queue is non-empty; it will
        raise an exception otherwise.
        """
        (edge, rule) = self._queue[0]
        self._chart.insert(edge)
        del self._queue[0]
        
        # Queue up any edges generated by the edge triggers.
        for func in self._strategy.edgetriggered():
            edges = func(self._chart, self._grammar,
                             self._basecat, edge)
            new_edges = [(e, func) for e in edges if (e not in self._chart)]
            self._queue = new_edges + self._queue

        if kwargs.has_key('getrule') and kwargs['getrule']:
            return (edge, rule)
        else:
            return edge
        
    def step(self, **kwargs):
        """
        Remove one item from the queue.
        """
        if not self._initialized:
            raise ValueError('You must initialize before you can step')

        if kwargs.has_key('strategy'):
            self._strategy = kwargs['strategy']

        # If the strategy changes, then we need to throw away
        # everything in the queue.
        if self._strategy != self._current_strategy:
            self._queue = []
            self._current_strategy = self._strategy
            self._just_changed_strategy = 1
            self._function_index = 0
        
        if self._queue:
            return self._dequeue(**kwargs)
        else:
            chart = self._chart
            grammar = self._grammar
            basecat = self._basecat
            while self._function_index < len(self._strategy.static()):
                # Run this static function, and add any new edges to
                # the queue.
                func = self._strategy.static()[self._function_index]
                new_edges = func(chart, grammar, basecat)
                for edge in new_edges:
                    self._insert(edge, func)

                # If we found any new edges, then add the first one.
                # Otherwise, we're done with this static function,
                # so move on to the next one.
                if self._queue:
                    return self._dequeue(**kwargs)
                else:
                    self._function_index += 1

        # Nothing left to do.
        return None

    def parse(self, tok_sent, n=None, **kwargs):
        # Initialize the token list/strategy.
        self.initialize(tok_sent, **kwargs)

        # Keep stepping, as long as there's anything to do.
        while self.step(): pass

        # Return the n best parses.
        if n == None:
            return self.parses()
        else:
            return self.parses()[:n]

edgenum = 0
def xyzzy(chart, edge):
    global edgenum
    edgenum += 1
    print edgenum, edge
    return 0

##//////////////////////////////////////////////////////
##  Demonstration Code
##//////////////////////////////////////////////////////

def demo():
    grammar = (
        Rule('S',('NP','VP')),
        Rule('NP',('Det','N')),
        Rule('NP',('Det','N', 'PP')),
        Rule('VP',('V','NP')),
        Rule('VP',('V','PP')),
        Rule('VP',('V','NP', 'PP')),
        Rule('VP',('V','NP', 'PP', 'PP')),
        Rule('PP',('P','NP'))
    )

    lexicon = (
        Rule('NP',('I',)),
        Rule('Det',('the',)),
        Rule('Det',('a',)),
        Rule('N',('man',)),
        Rule('V',('saw',)),
        Rule('P',('in',)),
        Rule('P',('with',)),
        Rule('N',('park',)),
        Rule('N',('telescope',))
    )

    sent = 'I saw a man in the park with a telescope'
    print "Sentence:\n", sent

    # tokenize the sentence
    tok_sent = WSTokenizer().tokenize(sent)

    # initialize the chartparser
    # cp = ChartParser(grammar, lexicon, 'S', strategy = TD_STRATEGY)
    cp = ChartParser(grammar, lexicon, 'S', strategy = BU_STRATEGY)
    cp.parse(tok_sent)

    # play with the stepping chart parser
    # cp = SteppingChartParser(grammar, lexicon, 'S')
    # cp.initialize(tok_sent, strategy = BUINIT_STRATEGY)
    # while cp.step(): pass
    # while cp.step(strategy = FR_STRATEGY): pass
    # cp.chart().draw()

    print "Parse(s):"
    for parse in cp.parses():
        print parse.pp()

    print "Chart Size:", len(cp.chart())
    # cp.chart().draw()

if __name__ == '__main__': demo()
