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
    return cmp((e1.loc().length(), e1.loc(), e1.dotted_rule()),
               (e2.loc().length(), e2.loc(), e2.dotted_rule()))

class Edge:
    # [edloper n.b.: I want to change the internal rep of edges.. sometime.]
    """
    An edge of a chart.    Edges are represented using C{Token}s, since
    an edge is just a piece of linguistic information at a
    C{Location}.    Edges also contain a C{DottedRule} and a
    possibly-empty tuple of children (C{Tree}s).    This class mainly
    provides a convenient wrapper around C{Token} with a suitable
    initializer and accessor functions.    Additionally, it provides
    functions to perform common chart-parser functions on edges.

    @type _edge: C{Token}
    @ivar _edge: The edge data structure, a C{Token} with a complex type
    """
    
    def __init__(self, dotted_rule, children, loc):
        self._edge = Token((dotted_rule, children), loc)
    def dotted_rule(self):
        return self._edge.type()[0]
    def children(self):
        return self._edge.type()[1]
    def lhs(self):
        return self.dotted_rule().lhs()
    def next(self):
        return self.dotted_rule().next()
    def complete(self):
        return self.dotted_rule().complete()
    def loc(self):
        return self._edge.loc()
    def start(self):
        return self.loc().start()
    def end(self):
        return self.loc().end()
    def __repr__(self):
        return repr(self.dotted_rule())\
               + repr(self.children()) + repr(self.loc())
    def __eq__(self, other):
        return (self._edge == other._edge)
    def __hash__(self):
        return hash((self.dotted_rule(), self.children(), self.loc()))

    def self_loop_start(self, rule):
        loc = self.loc().start_loc()
        dotted_rule = rule.dotted()
        return Edge(dotted_rule, (), loc)

    def self_loop_end(self, rule):
        loc = self.loc().end_loc()
        dotted_rule = rule.dotted()
        return Edge(dotted_rule, (), loc)

    def FR(self, edge):
        loc = self.loc().union(edge.loc())
        dotted_rule = self.dotted_rule().shift()
        children = self.children() + edge.children()
        if dotted_rule.complete():
            children = (TreeToken(dotted_rule.lhs(), *children),)
        return Edge(dotted_rule,children,loc)

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
        
        @loc: The span of text that it covered by this chart.  All
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
    
    def size(self):
        """
        @return: The number of edges contained in this chart.
        @rtype: int
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
    
    def insert(self,edge):
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
        root node value is C{node}.
        """
        return [edge.children()[0] for edge in self.edges() if
                edge.loc() == self._loc and edge.lhs() == node]

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
            
    #draw (replace with tkinter version)
    def draw(self, width=7):
        print "="*75
        edges = self.edges()
        edges.sort(edgecmp)
        for edge in edges:
            start = edge.start()
            end = edge.end()
            indent = " " * width * start
            print indent, edge.dotted_rule()
            print indent + "|" + "-"*(width*(end-start)-1) + "|"

def _seq_loc(tok_sent):
    """
    Return the location that spans a given sequence of tokens.
    """
    return TreeToken('', *tok_sent).loc()

class ChartParserStrategy:
    # A couple of paragraphs here are identical to paragraphs from the
    # ChartParser docs.  I think that's ok.
    """
    The C{ChartParserStrategy} class encodes the list of X{chart
    rules} used by a C{ChartParser} to specify the conditions under
    which new edges should be added to the chart.  There are two kinds
    of chart rules:

        - X{Explicit Rules} search the chart for specific contexts
          where edges should be added.  The C{parse} method will
          repeatedly invoke each explicit rule, until it produces no
          new edges.
        - X{Edge Triggerd Rules} add new edges to the chart whenever
          certain kinds of edges are added by any chart rule.

    A C{ChartParserStrategy} consists of a list of explicit rules and
    a list of edge triggered rules.
          
    Chart rules are defined using functions, which return a list of
    new edges to add to a chart.  These functions should I{not}
    directly modify the chart (e.g., do not add the edges to the chart
    yourself; C{ChartParser} will add them for you).  Explicit rules
    are defined with functions of the form::

        def explicit_rule(chart, grammar, basecat):
            ...   # Decide which edges to add (if any)
            return edges

    Where C{chart} is the chart that the explicit rule should act
    upon; C{grammar} is the grammar used by the chart parser; and
    C{basecat} is the top-level category of the grammar (e.g. 'S').
    The function should return a C{list} of C{Edge}s.  These edges
    will be added to the chart by the chart parser.
            
    Edge triggered rules are defined with functions of the form::

        def edge_triggered_rule(chart, grammar, basecat, edge):
            ...   # Decide which edges to add (if any)
            return edges

    Where C{chart} is the chart that the explicit rule should act
    upon; C{grammar} is the grammar used by the chart parser;
    C{basecat} is the top-level category of the grammar (e.g. 'S');
    and C{edge} is the edge that triggered this rule.  The function
    should return a C{list} of C{Edge}s.  These edges will be added to
    the chart by the chart parser.
    """
    def __init__(self, explicit, edgetriggered):
        """
        Construct a new C{ChartParserStrategy} containing the given
        lists of explicit rules and edge triggered rules.  See the
        reference documentation for the C{ChartParserStrategy} class
        for more information on what values should be used for
        explicit chart rules and edge triggered chart rules.
        
        @type explicit: C{list} of C{function}s
        @param explicit: The ordered list of explicit rules that
            should be used by a C{ChartParser}.
        @type edgetriggered: C{list} of C{function}s
        @param edgetriggered: The ordered list of edge triggered rules
            that should be used by a C{ChartParser}.
        """
        self._explicit = explicit
        self._edgetriggered = edgetriggered

    def explicit(self):
        """
        @return: the ordered list of explicit rules that
            should be used by a C{ChartParser}.
        @rtype: C{list} of C{function}s
        """
        return self._explicit
        
    def edgetriggered(self):
        """
        @return: the ordered list of edge triggered rules that
            should be used by a C{ChartParser}.
        @rtype: C{list} of C{function}s
        """
        return self._edgetriggered

class ChartParser(ParserI):
    # [edloper 9/27/01]: "Standard rules" *really* needs a different
    #     name.  -- changed to "Explicit" for now, still not happy
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

        - X{Explicit Rules} search the chart for specific contexts where
          edges should be added.  The C{parse} method will repeatedly
          invoke each explicit rule, until it produces no new edges.
        - X{Edge Triggerd Rules} add new edges to the chart whenever
          certain kinds of edges are added by any chart rule.

    Once the chart reaches a stage where none of the explicit rules
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
                    dotted_rule = DottedRule(rule.lhs(), rule.rhs(), 1)
                    tree = TreeToken(rule.lhs(), word)
                    edge = Edge(dotted_rule, (tree,), word.loc())
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

        # Run the explicit rules.  Run each rule until it generates no
        # new edges.  Use the variable "added" to keep track
        # of what edges we've added (so we'll know whether to keep
        # running the rule or not).
        chart = self._chart
        grammar = self._grammar
        basecat = self._basecat

        for func in self._strategy.explicit():
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

############################################
## CHART RULES
#
# See the docstring for ChartParser for a discussion of # the
# different types of chart rules.

# [edloper 9/27/01] These are external.  If we make them member
# functions, then it is not at all obvious how you should write new
# chart rules.  

def TD_init(chart, grammar, basecat):
    "Top-down init (explicit rule)"
    added = []

    loc = chart.loc().start_loc()
    for rule in grammar:
        if rule.lhs() == basecat:
            dotted_rule = rule.dotted()
            new_edge = Edge(dotted_rule, (), loc)
            added += [new_edge]
    return added

def TD_edge(chart, grammar, basecat, edge):
    "Top-down init (edge triggered rule)"
    added = []
    for rule in grammar:
        if not edge.complete() and rule.lhs() == edge.next():
            new_edge = edge.self_loop_end(rule)
            added += [new_edge]
    return added

def BU_init_edge(chart, grammar, basecat, edge):
    "Bottom-up init (explicit rule helper) (NOT A RULE)"
    added = []
    for rule in grammar:
        if edge.lhs() == rule[0]:
            new_edge = edge.self_loop_start(rule)
            added += [new_edge]
    return added

def BU_init(chart, grammar, basecat):
    "Bottom-up init (explicit rule)"
    added = []
    for edge in chart.edges():
        added += BU_init_edge(chart, grammar, basecat, edge)
    return added

# Fundamental rule edge
def FR_edge(chart, grammar, basecat, edge):
    "Fundamental rule (explicit rule helper) (NOT A RULE)"
    added = []
    if not edge.complete():
        for edge2 in chart.complete_edges():
            if edge.next() == edge2.lhs() and edge.end() == edge2.start():
                new_edge = edge.FR(edge2)
                added += [new_edge]
    return added

# fundamental rule
def FR(chart, grammar, basecat):
    "Fundamental rule (explicit rule)"
    added = []
    for edge in chart.edges():
        added += FR_edge(chart, grammar, basecat, edge)
    return added

############################################
## STRATEGIES

# Define some useful rule invocation strategies.
TD_STRATEGY = ChartParserStrategy([TD_init, FR], [TD_edge,])
BU_STRATEGY = ChartParserStrategy([BU_init], [])
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


############################################
## Stepping Chart Parser

class SteppingChartParser(ChartParser):
    """
    A C{ChartParser} that allows you to step through the parsing
    process, adding a single edge at a time.  It also allows you to
    change the strategy you are 
    
    A chart parser for doing chart parsing one step at a time.
    
        - allows you to add edges one at a time
        - allows you to change the strategy at any time

    It defines one new method: C{step}

    Internally, keep track of two queues:
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
        if not self._strategy.explicit():
            raise ValueError('You must define a strategy before '+
                             'you can parse')

        # Initialize the chart with the new sentence.
        self._initialize_chart(tok_sent)

        # We need to keep track of which explicit function we're
        # currently working on.
        self._function_index = 0

        # Remeber what strategy we started out using.
        self._current_strategy = self._strategy
        
        # We have successfully initialized.
        self._initialized = 1

        # Did we just change strategies?  This is useful to know,
        # because if we did, we need to check to make sure we dont' #
        # skip any edge-triggered rules.
        self._just_changed_strategy = 0

    ##############################################
    # Queuing
    ##############################################
    
    def _insert(self, edge):
        # Add an edge to the end of the queue
        if edge in self._chart:
            # We need to make sure that we get the right edge-triggered
            # edges.  If we just switched strategies, we should
            # re-check our edge-triggered rules.  Once we find at
            # least once edge-triggered rule that we hadn't found
            # before, we're in the clear.
            if (self._strategy.edgetriggered() and
                self._just_changed_strategy):
                self._queue = [edge] + self._queue
                self._dequeue()
                if self._queue:
                    self._just_changed_strategy = 0
        else:
            self._queue.append(edge)
        return []
        
    def _dequeue(self):
        """
        Add the first Edge from the queue to the chart, and return
        it.  At this time, we also run the edge_trigger functions on
        that edge, and queue their results.

        If we wanted to mimic the behavior of the non-stepped version
        more closely, then we should enqueue those at the beginning of
        the queue.
        
        This funciton assumes that self._queue is non-empty; it will
        raise an exception otherwise.
        """
        edge = self._queue[0]
        self._chart.insert(edge)
        del self._queue[0]
        
        # Queue up any edges generated by the edge triggers.
        for func in self._strategy.edgetriggered():
            edges = func(self._chart, self._grammar,
                             self._basecat, edge)
            new_edges = [e for e in edges if (e not in self._chart)]
            self._queue = new_edges + self._queue

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
        
        #print 'STEP', self._function_index, [e.loc() for e in self._queue]
        
        if self._queue:
            return self._dequeue()
        else:
            chart = self._chart
            grammar = self._grammar
            basecat = self._basecat
            while self._function_index < len(self._strategy.explicit()):
                # Run this explicit function, and add any new edges to
                # the queue.
                func = self._strategy.explicit()[self._function_index]
                new_edges = func(chart, grammar, basecat)
                for edge in new_edges:
                    self._insert(edge)

                # If we found any new edges, then add the first one.
                # Otherwise, we're done with this explicit function,
                # so move on to the next one.
                if self._queue:
                    return self._dequeue()
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



############################################
## Stepping Chart Parser

class SteppingChartParser2(ChartParser):
    """
    A chart parser for doing chart parsing one step at a time.
    
        - allows you to add edges one at a time
        - allows you to change the strategy at any time

    This chart parser repeatedly changes its underlying chart, making
    it difficult to use with ChartView.  
    """
    def __init__(self, grammar, lexicon, basecat, **kwargs):
        ChartParser.__init__(self, grammar, lexicon, basecat, **kwargs)
        self._queue = []
        self._action = ()

    def clear(self):
        self._queue = []
    def empty(self):
        return self._queue == []
    def dequeue(self):
        if self._queue == []:
            return None
        front = self._queue[0]
        self._queue = self._queue[1:]
        return front
    def next(self):
        added = []
        while added == [] and not self.empty():
            next_edge = self.dequeue()
            added = self._chart.insert(next_edge)
        if added == []:
            return None
        else:
            return added[0]

    def _step(self, edge, function, action):
        if self._action != action or self.empty():
            tmp_chart = self._chart.copy()
            if edge:
                self._queue = function(edge)
            else:
                self._queue = function()
            self._chart = tmp_chart
        self._action = action
        return self.next()

    def FR_step(self, edge):
        return self._step(edge, self.FR_edge, (edge, self.FR_edge))

    def TD_step(self, edge):
        return self._step(edge, self.TD_edge, (edge, self.TD_edge))

    def BU_init_edge_step(self, edge):
        return self._step(edge, self.BU_init_edge, (edge, self.BU_init_edge))

    def BU_init_step(self):
        return self._step(None, self.BU_init, self.BU_init)

    def TD_init_step(self):
        return self._step(None, self.TD_init, self.TD_init)

edgenum = 0
def xyzzy(chart, edge):
    global edgenum
    edgenum += 1
    print edgenum, edge
    return 0

# DEMONSTRATION CODE

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

def demo2():
    global grammar, lexicon
    
    sent = 'I saw a man in the park with a telescope'
    print "Sentence:\n", sent

    # tokenize the sentence
    tok_sent = WSTokenizer().tokenize(sent)

    # initialize the chartparser
    cp = SteppingChartParser(grammar, lexicon, 'S', callback=xyzzy, trace=0)
    cp.set_strategy(td_strategy())

    # run the parser
    parses = cp.parse(tok_sent)

    print "Parse(s):"
    for parse in parses:
        print parse.pp()

def demo():
    global grammar, lexicon
    
    sent = 'I saw a man in the park with a telescope'
    print "Sentence:\n", sent

    # tokenize the sentence
    tok_sent = WSTokenizer().tokenize(sent)

    # initialize the chartparser
    cp = SteppingChartParser(grammar, lexicon, 'S')
    cp.set_strategy(bu_strategy())

    print "THE INITIAL CHART:"
    cp.chart().draw() # NB cp.chart() is ahead of us

    for x in range(2):
        next = cp.TD_init_step()
        print "TD_INIT:", next

    for e in range(3,8):
        edge = cp.chart().edges()[e]
        print "USER PICKED EDGE:", edge
        for x in range(1):
            next = cp.BU_init_edge_step(edge)
            print "BU_INIT:", next

    edge = cp.chart().edges()[2]
    print "USER PICKED EDGE:", edge
    next = cp.FR_step(edge)
    print "FUNDAMENTAL:", next
    if next:
        next = cp.FR_step(next)
        print "FUNDAMENTAL:", next

    edge = cp.chart().edges()[11]
    print "USER PICKED EDGE:", edge
    next = cp.FR_step(edge)
    print "FUNDAMENTAL:", next
    if next:
        next = cp.FR_step(next)
        print "FUNDAMENTAL:", next

    edge = cp.chart().edges()[10]
    print "USER PICKED EDGE:", edge

    for x in range(4):
        next = cp.TD_step(edge)
        print "TD_STEP:", next

    edge = cp.chart().edges()[3]
    print "USER PICKED EDGE:", edge

    for x in range(4):
        next = cp.BU_init_edge_step(edge)
        print "BU_INIT:", next

    cp.chart().draw()

    print "ALRIGHT, LET'S APPLY THE BU_INIT RULE MAXIMALLY"

    edges = cp.BU_init()

    print "ADDED:"
    print edges

    cp.chart().draw()

    edge = cp.chart().edges()[12]
    print "USER PICKED EDGE:", edge
    next = cp.FR_step(edge)
    print "FUNDAMENTAL:", next
    if next:
        next = cp.FR_step(next)
        print "FUNDAMENTAL:", next

    print "NOW LET'S APPLY THE FR MAXIMALLY"
    edges = cp.FR()

    print "ADDED:"
    print edges

    cp.chart().draw()

    print "Parse(s):"
    for parse in cp.parses():
        print parse.pp()
