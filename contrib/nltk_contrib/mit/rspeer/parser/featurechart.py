from nltk.parser.chart import *
from nltk_contrib.mit.rspeer.feature import *

def apply(obj, vars):
    """A helper function to determine the value of an object when variables
    are set. It uses apply_bindings if the object is a Category, and simply
    returns the object otherwise."""
    if isinstance(obj, Category): return obj.apply_bindings(vars)
    else: return obj

class FeatureTreeEdge(TreeEdge):
    """
    A modification of L{TreeEdge} to handle nonterminals with features
    (known as L{Categories<Category>}.

    In addition to the span, left-hand side, right-hand side, and dot position
    (described at L{TreeEdge}), a C{FeatureTreeEdge} includes X{vars}, a
    set of L{FeatureBindings} saying which L{FeatureVariable}s are set to which
    values.

    These values are applied when examining the C{lhs} or C{rhs} of a
    C{FeatureTreeEdge}.
    
    For more information about edges, see the L{EdgeI} interface.
    """
    def __init__(self, span, lhs, rhs, dot=0, vars=None):
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
        @type vars: L{FeatureBindings}
        @param vars: The bindings specifying what values certain variables in
            this edge must have.
        """
        TreeEdge.__init__(self, span, lhs, rhs, dot)
        if vars is None: vars = FeatureBindings()
        assert chktype(5, vars, FeatureBindings)
        self._vars = vars
    def from_production(production, index, bindings=None):
        """
        @return: A new C{FeatureTreeEdge} formed from the given production.
            The new edge's left-hand side and right-hand side will
            be taken from C{production}; its span will be C{(index,
            index)}; its dot position will be C{0}, and it may have specified
            variables set.
        @rtype: L{FeatureTreeEdge}
        """
        return FeatureTreeEdge(span=(index, index), lhs=production.lhs(),
                        rhs=production.rhs(), dot=0, vars=bindings)
    from_production = staticmethod(from_production)
    
    def vars(self):
        """
        @return: the L{VariableBindings} mapping L{FeatureVariable}s to values.
        @rtype: L{VariableBindings}
        """
        return self._vars.copy()
    def lhs(self):
        return TreeEdge.lhs(self).apply_bindings(self._vars)
    def orig_lhs(self):
        """
        @return: the value of the left-hand side with no variables set.
        @rtype: C{Category}
        """
        return TreeEdge.lhs(self)
    def rhs(self):
        return tuple([apply(x, self._vars) for x in TreeEdge.rhs(self)])
    def orig_rhs(self):
        """
        @return: the value of the right-hand side with no variables set.
        @rtype: C{Category}
        """
        return TreeEdge.rhs(self)
    def __str__(self):
        str = '%r ->' % self.lhs()

        for i in range(len(self._rhs)):
            if i == self._dot: str += ' *'
            str += ' %r' % (self.rhs()[i],)
        if len(self._rhs) == self._dot: str += ' *'
        return str
    def __cmp__(self, other):
        if not isinstance(other, FeatureTreeEdge): return -1
        return cmp(str(self), str(other))
        # This stopped working for some reason.
        #return cmp((self._span, self.lhs(), self.rhs(), self._dot),
        #          (other._span, other.lhs(), other.rhs(), other._dot))
        
    def __hash__(self):
        return hash((self._span, self.lhs(), self.rhs(), self._dot))

class FeatureFundamentalRule(FundamentalRule):
    NUM_EDGES=2
    def apply_iter(self, chart, grammar, left_edge, right_edge):
        # Make sure the rule is applicable.
        if not (left_edge.end() == right_edge.start() and
                left_edge.is_incomplete() and right_edge.is_complete() and
                isinstance(left_edge, FeatureTreeEdge) and
                isinstance(right_edge, FeatureTreeEdge)
               ):
            return
        bindings = left_edge.vars()
        unify = left_edge.next().unify(right_edge.lhs().remove_unbound_vars(), bindings)
        if unify is None: return

        # Construct the new edge.
        new_edge = FeatureTreeEdge(span=(left_edge.start(), right_edge.end()),
                            lhs=left_edge.lhs(), rhs=left_edge.rhs(),
                            dot=left_edge.dot()+1, vars=bindings)
        
        # Add it to the chart, with appropraite child pointers.
        changed_chart = False
        for cpl1 in chart.child_pointer_lists(left_edge):
            if chart.insert(new_edge, cpl1+(right_edge,)):
                changed_chart = True

        # If we changed the chart, then generate the edge.
        if changed_chart: yield new_edge

class SingleEdgeFeatureFundamentalRule(SingleEdgeFundamentalRule):
    NUM_EDGES=1

    _fundamental_rule = FeatureFundamentalRule()
    
    def apply_iter(self, chart, grammar, edge1):
        fr = self._fundamental_rule
        if edge1.is_incomplete():
            # edge1 = left_edge; edge2 = right_edge
            for edge2 in chart.select(start=edge1.end(), is_complete=True):
                if isinstance(edge2, FeatureTreeEdge):
                    for new_edge in fr.apply_iter(chart, grammar, edge1, edge2):
                        yield new_edge
        else:
            # edge2 = left_edge; edge1 = right_edge
            for edge2 in chart.select(end=edge1.start(), is_complete=False):
                for new_edge in fr.apply_iter(chart, grammar, edge2, edge1):
                    yield new_edge

class FeatureTopDownExpandRule(TopDownExpandRule):
    NUM_EDGES=1
    def apply_iter(self, chart, grammar, edge):
        if edge.is_complete(): return
        for prod in grammar.productions():
            bindings = FeatureBindings()
            unify = edge.next().unify(prod.lhs(), bindings)
            # Bindings are not preserved here. Should they be?
            if unify is not None:
                new_edge = FeatureTreeEdge.from_production(prod, edge.end())
                if chart.insert(new_edge, ()):
                    yield new_edge

class FeatureEarleyChartParser(EarleyChartParser):
    """
    A chart parser implementing the Earley parsing algorithm, allowing
    nonterminals that have features (known as L{Categories<Category>}).

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

    C{FeatureEarleyChartParser} uses a X{lexicon} to decide whether a leaf
    has a given part of speech.  This lexicon is encoded as a
    dictionary that maps each word to a list of parts of speech that
    word can have. Unlike in the L{EarleyChartParser}, this lexicon is
    case-insensitive.
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
        #self._lexicon = lexicon
        
        # Build a case-insensitive lexicon.
        self._lexicon = {}
        for (name, value) in lexicon.items():
            self._lexicon[name.upper()] = value
        self._trace = trace
        AbstractParser.__init__(self, **property_names)

    def parse_n(self, token):
        TREES = self.property('TREES')
        chart = Chart(token, **self.property_names())
        grammar = self._grammar

        # Width, for printing trace edges.
        #w = 40/(chart.num_leaves()+1)
        w = 2
        if self._trace > 0: print ' '*9, chart.pp_leaves(w)

        # Initialize the chart with a special "starter" edge.
        root = GrammarCategory(pos='[INIT]')
        edge = FeatureTreeEdge((0,0), root, (grammar.start(),), 0,
        FeatureBindings())
        chart.insert(edge, ())

        # Create the 3 rules:
        predictor = FeatureTopDownExpandRule()
        completer = SingleEdgeFeatureFundamentalRule()
        #scanner = ScannerRule(self._lexicon)

        for end in range(chart.num_leaves()+1):
            if self._trace > 1: print 'Processing queue %d' % end
            
            # Scanner rule substitute
            if end > 0 and end-1 < chart.num_leaves():
                leaf = chart.leaf(end-1)
                for pos in self._lexicon.get(leaf.upper(), []):
                    newedge = FeatureTreeEdge((end-1, end), pos, [leaf], 1,
                    FeatureBindings())
                    leafedge = LeafEdge(leaf, end-1)
                    chart.insert(leafedge, ())
                    chart.insert(newedge, (leafedge,))
                    if self._trace > 0:
                        print  'Scanner  ', chart.pp_edge(newedge,w)
            
            for edge in chart.select(end=end):
                if edge.is_incomplete():
                    for e in predictor.apply(chart, grammar, edge):
                        if self._trace > 0:
                            print 'Predictor', chart.pp_edge(e,w)
                #if edge.is_incomplete():
                #    for e in scanner.apply(chart, grammar, edge):
                #        if self._trace > 0:
                #            print 'Scanner  ', chart.pp_edge(e,w)
                if edge.is_complete():
                    for e in completer.apply(chart, grammar, edge):
                        if self._trace > 0:
                            print 'Completer', chart.pp_edge(e,w)

        # Output a list of complete parses.
        token[TREES] = chart.parses(root)
        
    def parse(self, token):
        # Delegate to parse_n
        self._parse_from_parse_n(token)

def demo():
    import sys, time

    S = GrammarCategory.parse('S')
    VP = GrammarCategory.parse('VP')
    NP = GrammarCategory.parse('NP')
    PP = GrammarCategory.parse('PP')
    V = GrammarCategory.parse('V')
    N = GrammarCategory.parse('N')
    P = GrammarCategory.parse('P')
    Name = GrammarCategory.parse('Name')
    Det = GrammarCategory.parse('Det')
    DetSg = GrammarCategory.parse('Det[-pl]')
    DetPl = GrammarCategory.parse('Det[+pl]')
    NSg = GrammarCategory.parse('N[-pl]')
    NPl = GrammarCategory.parse('N[+pl]')

    # Define some grammatical productions.
    grammatical_productions = [
        CFGProduction(S, (NP, VP)),  CFGProduction(PP, (P, NP)),
        CFGProduction(NP, (NP, PP)),
        CFGProduction(VP, (VP, PP)), CFGProduction(VP, (V, NP)),
        CFGProduction(VP, (V,)), CFGProduction(NP, (DetPl, NPl)),
        CFGProduction(NP, (DetSg, NSg))]

    # Define some lexical productions.
    lexical_productions = [
        CFGProduction(NP, ('John',)), CFGProduction(NP, ('I',)),
        CFGProduction(Det, ('the',)), CFGProduction(Det, ('my',)),
        CFGProduction(Det, ('a',)),
        CFGProduction(NSg, ('dog',)),   CFGProduction(NSg, ('cookie',)),
        CFGProduction(V, ('ate',)),  CFGProduction(V, ('saw',)),
        CFGProduction(P, ('with',)), CFGProduction(P, ('under',)),
        ]
    
    earley_grammar = CFG(S, grammatical_productions)
    earley_lexicon = {}
    for prod in lexical_productions:
        earley_lexicon.setdefault(prod.rhs()[0].upper(), []).append(prod.lhs())

    sent = Token(TEXT='I saw John with a dog with my cookie')
    print "Sentence:\n", sent
    from nltk.tokenizer import WhitespaceTokenizer
    WhitespaceTokenizer().tokenize(sent)
    t = time.time()
    cp = FeatureEarleyChartParser(earley_grammar, earley_lexicon,
                           LEAF='TEXT', trace=1)
    cp.parse_n(sent)
    print "Time: %s" % (time.time() - t)
    for tree in sent['TREES']: print tree

def run_profile():
    import profile
    profile.run('for i in range(10): demo()', '/tmp/profile.out')
    import pstats
    p = pstats.Stats('/tmp/profile.out')
    p.strip_dirs().sort_stats('time', 'cum').print_stats(60)
    p.strip_dirs().sort_stats('cum', 'time').print_stats(60)

if __name__ == '__main__':
    demo()

