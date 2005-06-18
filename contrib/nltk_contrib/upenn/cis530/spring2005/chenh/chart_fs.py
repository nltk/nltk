# CIS530 final project
#
# Topic: A Chart Parser with Feature Structures
#
# Author: Huang-Wen Chen <chenh@seas.upenn.edu>
#
"""
This module includes the following:
1. An interface 'FeatureStructureI', and an implementaion utilizing
   existing nltk.featurestructure
2. An extended context free grammer 'CFG_fs' that can store a list
   of FeatureStructureI
3. An extended TreeEdge and LeafEdge that can store FeatureStructureI
4. An extended Chart that allows edges with same grammar rules
   but different feature structures. It also checks for subsumation
   of  feature structures of edges. It rejects the insertion of
   new edge if its feature sturcture is subsumed by edges already
   in the chart.
5. Three modified rules: PredictorRule, ScannerRule, and CompleterRule
6. The modified EarleyChartParser
7. demo code

Developing Environment:
  python 2.3.5
  Numeric 23.8
  nltk 1.4.3 win32

Filename & path:
  nltk\parser\chart_fs.py

Some examples of output:
  |. these .  dogs .  eat  .  the  . cookie.|
Predictor |>       .       .       .       .       .| S  -> * NP VP//[NP=[AGR=?x1], VP=[AGR=?x1]] 
Predictor |>       .       .       .       .       .| NP -> * Det N//[Det=[AGR=?x3], N=[AGR=?<x2=x3>], NP=[AGR=?x2]] 
Predictor |>       .       .       .       .       .| NP -> * NP PP//[] 
Scanner   |[-------]       .       .       .       .| 'these'.//[Det=[AGR=[Num='pl', Person='3rd']]] 
Scanner   |[-------]       .       .       .       .| Det -> 'these' *//[Det=[AGR=[Num='pl', Person='3rd']]] 
Completer |[------->       .       .       .       .| NP -> Det * N//[Det=[AGR=(1)[Num='pl', Person='3rd']], N=[AGR->(1)], NP=[AGR->(1)]] 
Scanner   |.       [-------]       .       .       .| 'dogs'.//[N=[AGR=[Num='pl', Person='3rd']]] 
***Summary***
  "this dog eats the cookie": Parsing Succeed.  0.875sec
 "this dogs eats the cookie":    Parsing Fail.  0.157sec
 "these dog eats the cookie":    Parsing Fail.  0.156sec
 "these dogs eat the cookie": Parsing Succeed.  1.047sec
"these dogs eats the cookie":    Parsing Fail.  0.657sec
          "I eat the cookie": Parsing Succeed.  1.000sec
         "I eats the cookie":    Parsing Fail.  0.578sec

Some Comments:
  This project consumes much more time than I've planed for the following reasons:
  1. I have to thoroughly study both feature structure and earley parser algorithms.
     Especially for feature structure, since the slides are not enough, I have to
     search and read more literatures about this topic.
  2. I have to read existing code for both feature structure and earley parser.
     Especially for EarleyChartParser, since it uses lots of advanced python techniques,
     such as inherence, generator, regular expression and customizations.
  3. I need to design a good interface for feature structure and a concise class hierarchy
     for modified EarleyChartParser
  4. The core idea about how to enhance Earley parser to support feature structures takes time
     (The only thing I've planed in advance)
  5. Distinguishing 'I eat the cookie' and 'these dogs eat the cookie' is quite complicated.
     The current NLTK code should be examine and modified.

"""

import re
from nltk.chktype import chktype
from nltk.token import Token
from nltk.parser import AbstractParser
from nltk.cfg import CFG, CFGProduction, Nonterminal, nonterminals

from nltk import cfg
from nltk import featurestructure
from nltk.parser import chart
from nltk.parser.chart import AbstractChartRule

#################################################################
# FeatureStructureI and FeatureStructure
#################################################################
class FeatureStructureI:
    """
    This interface support the following operations:
    1. FeatureStructureI() : Construct an empty feature sturcture '[]'
    2. FeatureStructureI(['<VP AGR>=<V=AGR>']) : Construct a feature
       structure with a set of "unification constraints".
       The unification constraints is defined as:

       B0 -> B1 ... Bn

       {set of constraints}
       
       <Bi feature path>=atomic value
       <Bi feature path>=<Bk feature path>
    3. unify() : Unification of two feature structures
    4. issubsumed() : Is feature sturcture A subsumed (included)
       by feature structure B ?
    """

    def __init__(self, consts=None, fs=None, bindings=None):
        if self.__class__ == FeatureStructureI: 
            raise TypeError('FeatureStructureI is an abstract interface')

    def unify(self, fs2):
        raise AssertionError('FeatureStructureI is an abstract interface')

    def issubsumed(self, fs2):
        raise AssertionError('FeatureStructureI is an abstract interface')

class FeatureStructure(FeatureStructureI):
    """
    The implementation of FeatureStructureI utilizing nltk.featurestructure.
    It is quite simple, except for the parsing of unification constraints.
    """

    _next_numbered_id = 1;
    
    def __init__(self, consts=None, fs=None, bindings=None):
        if fs == None:
            self._fs = featurestructure.FeatureStructure()
        if bindings == None:
            self._bindings = featurestructure.FeatureBindings()

        # empty feature stcutres : '[]'
        if consts == None:
            return

        # Convert unification constraints into string representation
        # , then pass the string to FeatureStructure.parse()
        for s in consts:
            #e.g. <a b c>=<d e f>
            r = re.compile('<(.+)>\s*=\s*<(.+)>')
            m = r.match(s)
            if (m != None):
                myvar = '?x' + '%d' % FeatureStructure._next_numbered_id
                FeatureStructure._next_numbered_id += 1

                str = FeatureStructure._featurepath2str(self, m.group(1), myvar)
                fs2 = featurestructure.FeatureStructure.parse(str)
                self._fs = self._fs.unify(fs2)

                str = FeatureStructure._featurepath2str(self, m.group(2), myvar)
                fs2 = featurestructure.FeatureStructure.parse(str)
                self._fs = self._fs.unify(fs2, self._bindings)
            else:
                #e.g. <a b c>=some_value
                r = re.compile('<(.+)>\s*=\s*(.+)') 
                m = r.match(s)
                if(m != None):
                    str = FeatureStructure._featurepath2str(self, m.group(1), m.group(2))
                    fs2 = featurestructure.FeatureStructure.parse(str)
                    self._fs = self._fs.unify(fs2, self._bindings)
                else:
                    raise AssertionError("Bad Format:"+s)

    def _featurepath2str(self, path, val):
        """
        Generate '[path1=[path2=val]]'
        """
        path = path.strip().split()
        str = '[' + path.pop() + '=' + val + ']'
        
        while len(path) != 0:
            str = '[' + path.pop() + '=' + str + ']'

        return str;

    def unify(self, fs2):
        """
        unify two FeatureSturctureI and generate a new one
        """
        bindings = self._bindings.copy()
        fs3 = self._fs.unify(fs2._fs, bindings)
        if fs3 == None:
            return None

        #==A strange bug, I can't use the following line:
        #return FeatureStructure(fs=fs3, bindings=bindings)
        #==Instead, the following lines work
        fs = FeatureStructure(fs=fs3, bindings=self._bindings)
        fs._fs = fs3
        fs._bindings = bindings
        return fs

    def issubsumed(self, fs2):
        """
        Is fs1 subsumed (included) by fs2 ?
        """
        if repr(fs2._fs) == '[]':
            return False
        
        fs3 = self._fs.unify(fs2._fs, self._bindings)
        if repr(fs3) ==  repr(self._fs):
            return True
        else:
            return False

    def __repr__(self):
        return repr(self._fs)

#################################################################
# CFG_fs
#################################################################
class CFG_fs(CFG):
    """
    A CFG with feature sturcture.
    This class inherents existing nltk.cfg.CFG.
    """
    def __init__(self, start, productions, fs):
        """
        Store the list of feature structures
        """
        assert chktype(3, fs, list)
        self._fs = fs;
        CFG.__init__(self, start, productions)

    def fs(self):
        """
        Retrieve the list of feature structures
        """
        return self._fs

########################################################################
##  Edges (TreeEdge & LeafEdge)
########################################################################
class TreeEdge(chart.TreeEdge):
    """
    A TreeEdge with feature structures.
    This class inherents nltk.parser.chart.TreeEdge.
    """
    def __init__(self, span, lhs, rhs, fs=FeatureStructure(), dot=0):
        """
        Store the of feature structure
        """
        assert chktype(4, fs, FeatureStructure)
        self._fs = fs
        chart.TreeEdge.__init__(self, span, lhs, rhs, dot)

    # Accessors
    def fs(self): return self._fs

    # Comparisons & hashing
    def __cmp__(self, other):
        """
        Two edges are consided identical if they have the same feature structure
        """
        if not isinstance(other, TreeEdge): return -1
        return cmp((self._span, self._lhs, self._rhs, self._dot, self._fs),
                   (other._span, other._lhs, other._rhs, other._dot, other._fs))
    def __hash__(self):
        """
        Two edges are consided identical if they have the same feature structure
        """
        return hash((self._lhs, self._rhs, self._span, self._dot, self._fs))

    # [staticmethod]
    def from_production(production, index, fs=FeatureStructure()):
        """
        Store the of feature structure if given
        """
        return TreeEdge(span=(index, index), lhs=production.lhs(),
                        rhs=production.rhs(), fs=fs, dot=0)
    from_production = staticmethod(from_production)

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

        #Append feature structure, Modified by howard
        str += '//' + repr(self._fs)
        return str
        
class LeafEdge(chart.LeafEdge):
    """
    A LeafEdge with feature structures.
    This class inherents nltk.parser.chart.LeafEdge.
    """
    def __init__(self, leaf, index, fs=FeatureStructure()):
        """
        Store the of feature structure
        """
        assert chktype(3, fs, FeatureStructure)
        self._fs = fs
        chart.LeafEdge.__init__(self, leaf, index)

    # Accessors
    def fs(self): return self._fs

    # Comparisons & hasing
    def __cmp__(self, other):
        if not isinstance(other, LeafEdge): return -1
        return cmp((self._index, self._leaf, self._fs), (other._index, other._leaf, other._fs))
    def __hash__(self):
        return hash((self._index, self._leaf, self._fs))

    # String representations
    def __str__(self): return '%r.//' % self._leaf + repr(self._fs)         #Append feature structure, Modified by howard

########################################################################
##  Chart
########################################################################

class Chart(chart.Chart):
    """
    A Chart which checks for subsumation when an edge is inserted
    This class inherents nltk.parser.chart.Chart.
    """
    #////////////////////////////////////////////////////////////
    # Edge Insertion
    #////////////////////////////////////////////////////////////

    def insert(self, edge, child_pointer_list):
        """
        Reject insertion of the new edge if it is subsumed by edges
        already in chart
        """
        # Is it a new edge?
        if not self._edge_to_cpls.has_key(edge):
            # Is this edge subsumed by edges in chart. Modified by howard
            issubsumed = False
            for e in self._edges:
                if (edge == e) and (edge.fs().issubsumed(e.fs())):
                    issubsumed = True
                    break

            #DEBUG
            if issubsumed:
                print '****issubsumed %s' % issubsumed + str(edge) +'/' + str(e)

            if not issubsumed:
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
# Earley Parsing Rules
#////////////////////////////////////////////////////////////

class FundamentalRule(AbstractChartRule):
    """
    The FundamentalRule (used by CompleterRule) is modified for:
    1. Check for compatibility of two edges (unification)
    2. Supply the new edge with the feature structure unified from
       two joining edges
    """
    NUM_EDGES=2
    def apply_iter(self, chart, grammar, left_edge, right_edge):
        # Make sure the rule is applicable.
        if not (left_edge.end() == right_edge.start() and
                left_edge.next() == right_edge.lhs() and
                left_edge.is_incomplete() and right_edge.is_complete()):
            return

        # Make sure feature structures are compatiable, Modified by howard
        fs = left_edge.fs().unify(right_edge.fs())
        if (fs == None):
            return

        # Construct the new edge.
        new_edge = TreeEdge(span=(left_edge.start(), right_edge.end()),
                            lhs=left_edge.lhs(), rhs=left_edge.rhs(),
                            fs = fs, #Modified by howard
                            dot=left_edge.dot()+1)

        # Add it to the chart, with appropraite child pointers.
        changed_chart = False
        for cpl1 in chart.child_pointer_lists(left_edge):
            if chart.insert(new_edge, cpl1+(right_edge,)):
                changed_chart = True

        # If we changed the chart, then generate the edge.
        if changed_chart: yield new_edge

class CompleterRule(chart.CompleterRule):
    """
    This CompleterRule extends nltk.parser.chart.CompleterRule.
    The only modification is setting the member variable
    '_fundamental_rule' to FundeamentalRule() in this module.
    See FundamentalRule for the details.
    """
    NUM_EDGES=1
    
    _fundamental_rule = FundamentalRule()
    
class ScannerRule(AbstractChartRule):
    """
    This ScannerRule is modified for:
    1. Supply the newly generated LeafEdge with feature structure
    2. If there are lexcion rules that having the same rule but
       different feature structures, insert all of them into chart
    """
    NUM_EDGES=1
    def __init__(self, word_to_pos_lexicon, lexicon_fs):
        self._word_to_pos = word_to_pos_lexicon
        self._lexicon_fs = lexicon_fs  #Modified by howard

    def apply_iter(self, chart, gramar, edge):
        if edge.is_complete() or edge.end()>=chart.num_leaves(): return
        index = edge.end()
        leaf = chart.leaf(index)

        #Generate all LeafEdges with same leaf (string) but different
        #feature structures, Modified by howard
        for i in range(len(self._word_to_pos.get(leaf, []))):
            #a leaf points to a list of fs and rules
            literal = self._word_to_pos.get(leaf, [])[i]
            fs = self._lexicon_fs.get(leaf, [FeatureStructure()])[i]
            if edge.next() == literal:
                new_leaf_edge = LeafEdge(leaf, index, fs) #Modified by howard
                if chart.insert(new_leaf_edge, ()):
                    yield new_leaf_edge
                new_pos_edge = TreeEdge((index,index+1), edge.next(),
                                        [leaf], fs, 1)  #Modified by howard
                if chart.insert(new_pos_edge, (new_leaf_edge,)):
                    yield new_pos_edge

class PredictorRule(TopDownExpandRule):
    """
    This PredictorRule is modified for:
    1. Supply the newly generated TreeEdge with feature structure
    2. If there are grammatical rules that having the same rule but
       different feature structures, insert all of them into chart
    """
    NUM_EDGES=1
    def apply_iter(self, chart, grammar, edge):
        if edge.is_complete(): return

        #Retrieve both productions and fs, modified by howard
        for i in range(len(grammar.productions())):
            prod = grammar.productions()[i]
            fs = grammar.fs()[i]
            if edge.next() == prod.lhs():
                new_edge = TreeEdge.from_production(prod, edge.end(), fs)
                if chart.insert(new_edge, ()):
                    yield new_edge
########################################################################
##  Simple Earley Chart Parser
########################################################################

class EarleyChartParser(AbstractParser):
    """
    This EarleyChartParser is modified for:
    1. Store the feature structure of lexicon
    2. Use PredictorRule, CompleterRule, ScannerRule in this module

    My suggestion to nltk.chart.EarleyChartParser:
       Rule variables can be promoted as member variables (in 'self'),
       so that I can set these variables in a child class.
       
       for example:
       predictor -> self._predictor
       completer -> self._completer
       scanner -> self._scanner

       By doing this, the new EarleyChartParser can simply extend
       chart.EarleyChartParser and override only __init__ to set
       these variables. This can reduce the trouble of overriding
       get_parser_list().
    """
    def __init__(self, grammar, lexicon, lexicon_fs, trace=0, **property_names):  #Modified by howard
        """
        Store the feature structure of lexicon 
        """
        self._grammar = grammar
        self._lexicon = lexicon
        self._lexicon_fs = lexicon_fs  #Modified by howard
        self._trace = trace
        AbstractParser.__init__(self, **property_names)

    def get_parse_list(self, token):
        chart = Chart(token, **self.property_names())
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
        scanner = ScannerRule(self._lexicon, self._lexicon_fs)  #Modified by howard

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
        return chart.parses(grammar.start())
            
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
        CFGProduction(S, [NP, VP]),  #1
        CFGProduction(PP, [P, NP]),  #2
        CFGProduction(NP, [Det, N]), #3
        CFGProduction(NP, [NP, PP]), #4 
        CFGProduction(VP, [VP, PP]), #5
        CFGProduction(VP, [V, NP]),  #6
        CFGProduction(VP, [V])       #7
        ]      

    # Define feature structures for productions
    grammatical_fs = [
        FeatureStructure(['<NP AGR>=<VP AGR>']),   #1
        FeatureStructure(),                        #2
        FeatureStructure(['<NP AGR>=<N AGR>',
                          '<Det AGR>=<N AGR>']),   #3
        FeatureStructure(),                        #4
        FeatureStructure(),                        #5
        FeatureStructure(['<VP AGR>=<V AGR>']),    #6
        FeatureStructure(['<VP AGR>=<V AGR>'])     #7
        ]

    # Define some lexical productions.
    lexical_productions = [
        CFGProduction(Det, ['this']),  #1
        CFGProduction(Det, ['these']), #2
        CFGProduction(N, ['dog']),     #3
        CFGProduction(N, ['dogs']),    #4
        CFGProduction(NP, ['I']),      #5
        CFGProduction(V, ['eat']),     #6
        CFGProduction(V, ['eat']),     #7
        CFGProduction(V, ['eats']),    #8
        CFGProduction(Det, ['the']),   #9
        CFGProduction(N, ['cookie']),  #10
        ]

    lexical_fs = [
        FeatureStructure(['<Det AGR Num>=sg', '<Det AGR Person>=3rd']),  #1
        FeatureStructure(['<Det AGR Num>=pl', '<Det AGR Person>=3rd']),  #2
        FeatureStructure(['<N AGR Num>=sg', '<N AGR Person>=3rd']),      #3
        FeatureStructure(['<N AGR Num>=pl', '<N AGR Person>=3rd']),      #4
        FeatureStructure(['<NP AGR Num>=sg', '<NP AGR Person>=1st']),    #5
        FeatureStructure(['<V AGR Num>=sg', '<V AGR Person>=1st']),      #6
        FeatureStructure(['<V AGR Num>=pl', '<V AGR Person>=3rd']),      #7
        FeatureStructure(['<V AGR Num>=sg', '<V AGR Person>=3rd']),      #8
        FeatureStructure(),                                              #9
        FeatureStructure(),                                              #10
        ]

    # Convert the grammar productions to an earley-style lexicon.
    earley_lexicon = {}
    earley_lexicon_fs = {}
    for i in range(len(lexical_productions)):
        prod = lexical_productions[i]
        fs = lexical_fs[i]
        earley_lexicon.setdefault(prod.rhs()[0], []).append(prod.lhs())
        earley_lexicon_fs.setdefault(prod.rhs()[0], []).append(fs)

    # The grammar for EarleyChartParser:
    earley_grammar = CFG_fs(S, grammatical_productions, grammatical_fs)

    # Tokenize a sample sentence.
    test_strings = [
        #Det<->Noun Agreement
        'this dog eats the cookie',
        'this dogs eats the cookie',
        'these dog eats the cookie',

        #Subject<->Verb Agreement
        'these dogs eat the cookie',
        'these dogs eats the cookie',

        #Subject<->Verb Agreement, eat could be either [1st, sg] or [3rd, pl]
        'I eat the cookie',
        'I eats the cookie',
        ]
    
    times = {}
    result = {}

    for txt in test_strings:

        sent = Token(TEXT=txt)
        print "Sentence:\n", sent
        from nltk.tokenizer import WhitespaceTokenizer
        WhitespaceTokenizer(SUBTOKENS='WORDS').tokenize(sent)

        # Keep track of how long each parser takes.

        cp = EarleyChartParser(earley_grammar, earley_lexicon, earley_lexicon_fs,
                               LEAF='TEXT', SUBTOKENS='WORDS', trace=1)
        t = time.time()
        parses = cp.get_parse_list(sent)
        times[txt] = time.time()-t
        result[txt] = len(parses)
        print '----------------------------------------------------------------------------------'

    # Print the times of all parsers:
    maxlen = max([len(key) for key in times.keys()])
    format = '%' + `maxlen+2` + 's: %15s. %6.3fsec'
    print "***Summary***"
    for txt in test_strings:
        if(result[txt]>0):
            print format % ('"'+txt+'"', 'Parsing Succeed', times[txt])
        else:
            print format % ('"'+txt+'"', 'Parsing Fail', times[txt])
            
            
if __name__ == '__main__': demo()
