# Natural Language Toolkit: Semantic Interpretation
#
# Author: Ewan Klein <ewan@inf.ed.ac.uk>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""
Utility functions for batch-processing sentences: parsing and
extraction of the semantic representation of the root node of the the
syntax tree, followed by evaluation of the semantic representation in
a first-order model.
"""

import evaluate
import re
import nltk
from logic import LogicParser, Error


##############################################################
## Utility functions for connecting parse output to semantics
##############################################################

def text_parse(inputs, grammar, trace=0):
    """
    Convert input sentences into syntactic trees.
    
    @parameter inputs: sentences to be parsed
    @type inputs: C{list} of C{str}
    @parameter grammar: feature-based grammar to use in parsing
    @rtype: C{dict}
    @return: a mapping from input sentences to a list of L{Tree}s
    """
    parses = {}
    cp = nltk.parse.FeatureEarleyChartParser(grammar, trace=trace)
    for sent in inputs:
        tokens = sent.split()
        syntrees = cp.nbest_parse(tokens)
        parses[sent] = syntrees
    return parses

def _semrep(node, beta_reduce=True):
    """
    Find the semantic representation at a given tree node.
    
    @parameter node: node of a parse L{Tree}
    @rtype: L{logic.Expression}
    """
    assert isinstance(node, nltk.cfg.FeatStructNonterminal)
    try:
        semrep = node['sem']
        if beta_reduce:
            semrep = semrep.simplify()
        return semrep
    except KeyError:
        print "Node has no 'sem' feature specification"
    raise

def root_semrep(syntree, beta_reduce=True, start='S'):
    """
    Find the semantic representation at the root of a tree.
    
    @parameter syntree: a parse L{Tree}
    @parameter beta_reduce: if C{True}, carry out beta reduction on the logical forms that are returned
    @return: the semantic representation at the root of a L{Tree}
    @rtype: L{logic.Expression}
    """
    return _semrep(syntree.node, beta_reduce=beta_reduce)

def text_interpret(inputs, grammar, beta_reduce=True, start='S', syntrace=0):
    """
    Add the semantic representation to each syntactic parse tree
    of each input sentence.
    
    @parameter inputs: a list of sentences
    @parameter grammar: a feature-based grammar
    @return: a mapping from sentences to lists of pairs (parse-tree, semantic-representations)
    @rtype: C{dict}
    """
    parses = text_parse(inputs, grammar, trace=syntrace)
    semreps = {}
    for sent in inputs:
        syntrees = parses[sent]
        syn_sem = \
           [(syn, root_semrep(syn, beta_reduce=beta_reduce, start=start))
            for syn in syntrees]
        semreps[sent] = syn_sem
    return semreps

def text_evaluate(inputs, grammar, model, assignment, semtrace=0):
    """
    Add the truth-in-a-model value to each semantic representation
    for each syntactic parse of each input sentences.
    
    @return: a mapping from sentences to lists of triples (parse-tree, semantic-representations, evaluation-in-model)
    @rtype: C{dict}
    """
    g = assignment
    m = model
    semreps = text_interpret(inputs, grammar)
    evaluations = {}
    for sent in inputs:
        syn_sem_val = \
          [(syn, sem, m.evaluate(str(sem), g, trace=semtrace)) for (syn, sem) in semreps[sent]]
        evaluations[sent] = syn_sem_val
    return evaluations

##########################################
# REs used by the parse_valuation function
##########################################
_VAL_SPLIT_RE = re.compile(r'\s*=+>\s*')
_ELEMENT_SPLIT_RE = re.compile(r'\s*,\s*')
_TUPLES_RE = re.compile(r"""\s*         
                                (\([^)]+\))  # tuple-expression
                                \s*""", re.VERBOSE)

def parse_valuation_line(s):
    """
    Parse a line in a valuation file.
    
    Lines are expected to be of the form::
    
      noosa => n
      girl => {g1, g2}
      chase => {(b1, g1), (b2, g1), (g1, d1), (g2, d2)}
    
    @parameter s: input line
    @type s: C{str}
    @return: a pair (symbol, value)
    @rtype: C{tuple}
    """
    pieces = _VAL_SPLIT_RE.split(s)
    symbol = pieces[0]
    value = pieces[1]
    # check whether the value is meant to be a set
    if value.startswith('{'):
        value = value[1:-1]
        tuple_strings = _TUPLES_RE.findall(value)
        # are the set elements tuples?
        if tuple_strings:
            set_elements = []
            for ts in tuple_strings:
                ts = ts[1:-1]
                element = tuple(_ELEMENT_SPLIT_RE.split(ts))
                set_elements.append(element)
        else:
            set_elements = _ELEMENT_SPLIT_RE.split(value)
        value = set(set_elements)
    return symbol, value
    
def parse_valuation(s):
    """
    Convert a valuation file into a valuation.
    
    @parameter s: the contents of a valuation file
    @type s: C{str}
    @return: a L{nltk.sem} valuation
    @rtype: L{Valuation}
    """
    statements = []
    for linenum, line in enumerate(s.splitlines()):
        line = line.strip()
        if line.startswith('#') or line=='': continue
        try: statements.append(parse_valuation_line(line))
        except ValueError:
            raise ValueError, 'Unable to parse line %s: %s' % (linenum, line)
    val = evaluate.Valuation()
    val.read(statements)
    return val

def parse_fol(s):
    """
    Convert a  file of First Order Formulas into a list of {Expression}s.
    
    @parameter s: the contents of the file
    @type s: C{str}
    @return: a list of parsed formulas.
    @rtype: C{list} of L{Expression}
    """
    statements = []
    lp = LogicParser()
    for linenum, line in enumerate(s.splitlines()):
        line = line.strip()
        if line.startswith('#') or line=='': continue
        try:
            statements.append(lp.parse(line))
        except Error:
            raise ValueError, 'Unable to parse line %s: %s' % (linenum, line)
    return statements
        
def demo_model0():
    global m0, g0
    val = evaluate.Valuation()
    #Initialize a valuation of non-logical constants."""
    v = [('john', 'b1'),
        ('mary', 'g1'),
        ('suzie', 'g2'),
        ('fido', 'd1'),
        ('tess', 'd2'),
        ('noosa', 'n'),
        ('girl', set(['g1', 'g2'])),
        ('boy', set(['b1', 'b2'])),
        ('dog', set(['d1', 'd2'])),
        ('bark', set(['d1', 'd2'])),
        ('walk', set(['b1', 'g2', 'd1'])),
        ('chase', set([('b1', 'g1'), ('b2', 'g1'), ('g1', 'd1'), ('g2', 'd2')])),
        ('see', set([('b1', 'g1'), ('b2', 'd2'), ('g1', 'b1'),('d2', 'b1'), ('g2', 'n')])),
        ('in', set([('b1', 'n'), ('b2', 'n'), ('d2', 'n')])),
        ('with', set([('b1', 'g1'), ('g1', 'b1'), ('d1', 'b1'), ('b1', 'd1')]))
     ]
    #Read in the data from C{v}
    val.read(v)
    #Bind C{dom} to the C{domain} property of C{val}
    dom = val.domain
    #Initialize a model with parameters C{dom} and C{val}.
    m0 = evaluate.Model(dom, val)
    #Initialize a variable assignment with parameter C{dom}
    g0 = evaluate.Assignment(dom)


def read_sents(file):
    sents = [l.rstrip() for l in open(file)]
    # get rid of blank lines
    sents = [l for l in sents if len(l) > 0]
    sents = [l for l in sents if not l[0] == '#']
    return sents

def demo():
    import sys
    from optparse import OptionParser
    description = \
    """
    Parse and evaluate some sentences.
    """

    opts = OptionParser(description=description)
    
    opts.set_defaults(evaluate=True, beta=True, syntrace=0,
                      semtrace=0, demo='default', grammar='', sentences='')

    opts.add_option("-d", "--demo", dest="demo",
                    help="choose demo D; omit this for the default demo, or specify 'chat80'", metavar="D")
    opts.add_option("-g", "--gram", dest="grammar",
                    help="read in grammar G", metavar="G")
    opts.add_option("-m", "--model", dest="model",
                        help="import model M (omit '.py' suffix)", metavar="M")
    opts.add_option("-s", "--sentences", dest="sentences",
                        help="read in a file of test sentences S", metavar="S")
    opts.add_option("-e", "--no-eval", action="store_false", dest="evaluate",
                    help="just do a syntactic analysis")
    opts.add_option("-b", "--no-beta-reduction", action="store_false",
                    dest="beta", help="don't carry out beta-reduction")
    opts.add_option("-t", "--syntrace", action="count", dest="syntrace",
                    help="set syntactic tracing on; requires '-e' option")
    opts.add_option("-T", "--semtrace", action="count", dest="semtrace",
                    help="set semantic tracing on")

    (options, args) = opts.parse_args()
    
    SPACER = '-' * 30

    demo_model0()

    sents = [
    'Fido sees a boy with Mary',
    'John sees Mary',
    'every girl chases a dog',
    'every boy chases a girl',
    'John walks with a girl in Noosa',
    'who walks']
    
    gramfile = 'grammars/sem2.fcfg'
        
    if options.sentences:
        sentsfile = options.sentences
    if options.grammar:
        gramfile = options.grammar
    if options.model:
        exec "import %s as model" % options.model
    
    if sents is None:
        sents = read_sents(sentsfile)

    gram = nltk.data.load(gramfile)
    
    # Set model and assignment
    model = m0
    g = g0

    if options.evaluate: 
        evaluations = \
            text_evaluate(sents, gram, model, g, semtrace=options.semtrace)
    else:
        semreps = \
            text_interpret(sents, gram, beta_reduce=options.beta, syntrace=options.syntrace)
        
    for sent in sents:
        n = 1
        print '\nSentence: %s' % sent
        print SPACER
        if options.evaluate: 
            
            for (syntree, semrep, value) in evaluations[sent]:
                if isinstance(value, dict):
                    value = set(value.keys())
                print '%d:  %s' % (n, semrep.infixify())
                print value
                n += 1
        else:
           
            for (syntree, semrep) in semreps[sent]:
#                print '%d:  %s' % (n, semrep.infixify())
                print '%d:  %s' % (n, semrep)
                n += 1
                
if __name__ == "__main__":
    demo()
