# Natural Language Toolkit: Viterbi Probabilistic Parser
#
# Copyright (C) 2001-2005 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
#         Steven Bird <sb@csse.unimelb.edu.au>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

from nltk_lite.parse import ParseI, AbstractParse
from nltk_lite.parse import cfg, pcfg
from nltk_lite.parse.tree import Tree, ProbabilisticTree
from nltk_lite.parse.chart import Chart, LeafEdge, TreeEdge, AbstractChartRule
import types

##//////////////////////////////////////////////////////
##  Viterbi PCFG Parser
##//////////////////////////////////////////////////////

class ViterbiParse(AbstractParse):
    """
    A bottom-up C{PCFG} parser that uses dynamic programming to find
    the single most likely parse for a text.  The C{ViterbiParse} parser
    parses texts by filling in a X{most likely constituent table}.
    This table records the most probable tree representation for any
    given span and node value.  In particular, it has an entry for
    every start index, end index, and node value, recording the most
    likely subtree that spans from the start index to the end index,
    and has the given node value.

    The C{ViterbiParse} parser fills in this table incrementally.  It starts
    by filling in all entries for constituents that span one element
    of text (i.e., entries where the end index is one greater than the
    start index).  After it has filled in all table entries for
    constituents that span one element of text, it fills in the
    entries for constitutants that span two elements of text.  It
    continues filling in the entries for constituents spanning larger
    and larger portions of the text, until the entire table has been
    filled.  Finally, it returns the table entry for a constituent
    spanning the entire text, whose node value is the grammar's start
    symbol.

    In order to find the most likely constituent with a given span and
    node value, the C{ViterbiParse} parser considers all productions that
    could produce that node value.  For each production, it finds all
    children that collectively cover the span and have the node values
    specified by the production's right hand side.  If the probability
    of the tree formed by applying the production to the children is
    greater than the probability of the current entry in the table,
    then the table is updated with this new tree.

    A pseudo-code description of the algorithm used by
    C{ViterbiParse} is:

      - Create an empty most likely constituent table, M{MLC}.
      - For M{width} in 1...len(M{text}):
        - For M{start} in 1...len(M{text})-M{width}:
          - For M{prod} in grammar.productions:
            - For each sequence of subtrees [M{t[1]}, M{t[2]}, ..., 
              M{t[n]}] in M{MLC}, where M{t[i]}.node==M{prod}.rhs[i],
              and the sequence covers [M{start}:M{start}+M{width}]:
                - M{old_p} = M{MLC}[M{start}, M{start+width}, M{prod}.lhs]
                - M{new_p} = P(M{t[1]})*P(M{t[1]})*...*P(M{t[n]})*P(M{prod})
                - if M{new_p} > M{old_p}:
                  - M{new_tree} = Tree(M{prod}.lhs, M{t[1]}, M{t[2]},
                    ..., M{t[n]})
                  - M{MLC}[M{start}, M{start+width}, M{prod}.lhs]
                    = M{new_tree}
      - Return M{MLC}[0, len(M{text}), M{start_symbol}]
                
    @type _grammar: C{pcfg.Grammar}
    @ivar _grammar: The grammar used to parse sentences.
    @type _trace: C{int}
    @ivar _trace: The level of tracing output that should be generated
        when parsing a text.
    """
    def __init__(self, grammar, trace=0):
        """
        Create a new C{ViterbiParse} parser, that uses {grammar} to
        parse texts.

        @type grammar: C{pcfg.Grammar}
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
        # Inherit docs from ParseI

        # The most likely constituent table.  This table specifies the
        # most likely constituent for a given span and type.
        # Constituents can be either Trees or Tokens.  For
        # Trees, the "type" is the Nonterminal for the tree's
        # root node value.  For Tokens, the "type" is the token's
        # type.  The table is stored as a dictionary, since it is
        # sparse.
        constituents = {}
        
        # Initialize the constituents dictionary with the words from
        # the text.
        if self._trace: print ('Inserting tokens into the most likely'+
                               ' constituents table...')
        for index in range(len(tokens)):
            token = tokens[index]
            constituents[index,index+1,token] = token
            if self._trace > 1:
                self._trace_lexical_insertion(token, index, len(tokens))

        # Consider each span of length 1, 2, ..., n; and add any trees
        # that might cover that span to the constituents dictionary.
        for length in range(1, len(tokens)+1):
            if self._trace:
                if self._trace > 1: print
                print ('Finding the most likely constituents'+
                       ' spanning %d text elements...' % length)
            #print constituents
            for start in range(len(tokens)-length+1):
                span = (start, start+length)
                self._add_constituents_spanning(span, constituents,
                                                tokens)

        # Find all trees that span the entire text & have the right cat
        trees = [constituents.get((0, len(tokens),
                                   self._grammar.start()), [])]

        # Sort the trees, and return the requested number of them.
        trees.sort(lambda t1,t2: cmp(t2.prob(), t1.prob()))
        return trees

    def _add_constituents_spanning(self, span, constituents, tokens):
        """
        Find any constituents that might cover C{span}, and add them
        to the most likely constituents table.

        @rtype: C{None}
        @type span: C{(int, int)}
        @param span: The section of the text for which we are
            trying to find possible constituents.  The span is
            specified as a pair of integers, where the first integer
            is the index of the first token that should be included in
            the constituent; and the second integer is the index of
            the first token that should not be included in the
            constituent.  I.e., the constituent should cover
            C{M{text}[span[0]:span[1]]}, where C{M{text}} is the text
            that we are parsing.

        @type constituents: C{dictionary} from
            C{(int,int,Nonterminal)} to (C{ProbabilisticToken} or
            C{ProbabilisticTree}).
        @param constituents: The most likely constituents table.  This
            table records the most probable tree representation for
            any given span and node value.  In particular,
            C{constituents(M{s},M{e},M{nv})} is the most likely
            C{ProbabilisticTree} that covers C{M{text}[M{s}:M{e}]}
            and has a node value C{M{nv}.symbol()}, where C{M{text}}
            is the text that we are parsing.  When
            C{_add_constituents_spanning} is called, C{constituents}
            should contain all possible constituents that are shorter
            than C{span}.
            
        @type tokens: C{list} of tokens
        @param tokens: The text we are parsing.  This is only used for
            trace output.  
        """
        # Since some of the grammar productions may be unary, we need to
        # repeatedly try all of the productions until none of them add any
        # new constituents.
        changed = 1
        while changed:
            changed = 0
            
            # Find all ways instantiations of the grammar productions that
            # cover the span.
            instantiations = self._find_instantiations(span, constituents)

            # For each production instantiation, add a new
            # ProbabilisticTree whose probability is the product
            # of the childrens' probabilities and the production's
            # probability.
            for (production, children) in instantiations:
                subtrees = [c for c in children if isinstance(c, Tree)]
                p = reduce(lambda pr,t:pr*t.prob(),
                           subtrees, production.prob())
                node = production.lhs().symbol()
                tree = ProbabilisticTree(node, children, prob=p)

                # If it's new a constituent, then add it to the
                # constituents dictionary.
                c = constituents.get((span[0], span[1], production.lhs()),
                                     None)
                if self._trace > 1:
                    if c is None or c != tree:
                        if c is None or c.prob() < tree.prob():
                            print '   Insert:',
                        else:
                            print '  Discard:',
                        self._trace_production(production, p, span, len(tokens))
                if c is None or c.prob() < tree.prob():
                    constituents[span[0], span[1], production.lhs()] = tree
                    changed = 1

    def _find_instantiations(self, span, constituents):
        """
        @return: a list of the production instantiations that cover a
            given span of the text.  A X{production instantiation} is
            a tuple containing a production and a list of children,
            where the production's right hand side matches the list of
            children; and the children cover C{span}.  @rtype: C{list}
            of C{pair} of C{Production}, (C{list} of
            (C{ProbabilisticTree} or token.

        @type span: C{(int, int)}
        @param span: The section of the text for which we are
            trying to find production instantiations.  The span is
            specified as a pair of integers, where the first integer
            is the index of the first token that should be covered by
            the production instantiation; and the second integer is
            the index of the first token that should not be covered by
            the production instantiation.
        @type constituents: C{dictionary} from
            C{(int,int,Nonterminal)} to (C{ProbabilisticToken} or
            C{ProbabilisticTree}).
        @param constituents: The most likely constituents table.  This
            table records the most probable tree representation for
            any given span and node value.  See the module
            documentation for more information.
        """
        rv = []
        for production in self._grammar.productions():
            childlists = self._match_rhs(production.rhs(), span, constituents)
                                        
            for childlist in childlists:
                rv.append( (production, childlist) )
        return rv

    def _match_rhs(self, rhs, span, constituents):
        """
        @return: a set of all the lists of children that cover C{span}
            and that match C{rhs}.
        @rtype: C{list} of (C{list} of C{ProbabilisticTree} or
            C{Token}) 

        @type rhs: C{list} of C{Nonterminal} or (any)
        @param rhs: The list specifying what kinds of children need to
            cover C{span}.  Each nonterminal in C{rhs} specifies
            that the corresponding child should be a tree whose node
            value is that nonterminal's symbol.  Each terminal in C{rhs}
            specifies that the corresponding child should be a token
            whose type is that terminal.
        @type span: C{(int, int)}
        @param span: The section of the text for which we are
            trying to find child lists.  The span is specified as a
            pair of integers, where the first integer is the index of
            the first token that should be covered by the child list;
            and the second integer is the index of the first token
            that should not be covered by the child list.
        @type constituents: C{dictionary} from
            C{(int,int,Nonterminal)} to (C{ProbabilisticToken} or
            C{ProbabilisticTree}).
        @param constituents: The most likely constituents table.  This
            table records the most probable tree representation for
            any given span and node value.  See the module
            documentation for more information.
        """
        (start, end) = span
        
        # Base case
        if start >= end and rhs == (): return [[]]
        if start >= end or rhs == (): return []

        # Find everything that matches the 1st symbol of the RHS
        childlists = []
        for split in range(start, end+1):
            l=constituents.get((start,split,rhs[0]))
            if l is not None:
                rights = self._match_rhs(rhs[1:], (split,end), constituents)
                childlists += [[l]+r for r in rights]

        return childlists

    def _trace_production(self, production, p, span, width):
        """
        Print trace output indicating that a given production has been
        applied at a given location.

        @param production: The production that has been applied
        @type production: C{Production}
        @param p: The probability of the tree produced by the production.  
        @type p: C{float}
        @param span: The span of the production
        @type span: C{tuple}
        @rtype: C{None}
        """
        
        str = '|' + '.' * span[0]
        str += '=' * (span[1] - span[0])
        str += '.' * (width - span[1]) + '| '
        str += '%s' % production
        if self._trace > 2: str = '%-40s %12.10f ' % (str, p)

        print str

    def _trace_lexical_insertion(self, token, index, width):
        str = '   Insert: |' + '.' * index + '=' + '.' * (width-index-1) + '| '
        str += '%s' % (token,)
        print str

    def __repr__(self):
        return '<ViterbiParser for %r>' % self._grammar


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
    from nltk_lite.parse import cfg, pcfg, ViterbiParse

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

    parser = ViterbiParse(grammar)
    all_parses = {}

    print '\nsent: %s\nparser: %s\ngrammar: %s' % (sent,parser,grammar)
    parser.trace(3)
    t = time.time()
    parses = parser.get_parse_list(tokens)
    time = time.time()-t
    if parses:
        average = reduce(lambda a,b:a+b.prob(), parses, 0)/len(parses)
    else:
        average = 0
    num_parses = len(parses)
    for p in parses:
        all_parses[p.freeze()] = 1

    # Print some summary statistics
    print
    print 'Time (secs)   # Parses   Average P(parse)'
    print '-----------------------------------------'
    print '%11.4f%11d%19.14f' % (time, num_parses, average)
    parses = all_parses.keys()
    if parses:
        p = reduce(lambda a,b:a+b.prob(), parses, 0)/len(parses)
    else: p = 0
    print '------------------------------------------'
    print '%11s%11d%19.14f' % ('n/a', len(parses), p)

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
