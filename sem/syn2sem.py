# Natural Language Toolkit: Semantic Interpretation
#
# Copyright (C) 2001-2007 University of Pennsylvania
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
from nltk.tree import Tree


##############################################################
## Utility functions for connecting parse output to semantics
##############################################################

def text_parse(inputs, grammar, trace=0):
    """
    Convert input sentences into syntactic trees.
    """
    parses = {}
    cp = grammar.earley_parser(trace=trace)
    for sent in inputs:
        tokens = sent.split()
        syntrees = cp.get_parse_list(tokens)
        parses[sent] = syntrees
    return parses

def root_node(syntree, start='S'):
    """
    Find the root node in a syntactic tree.
    """
    # check that we have a tree
    assert isinstance(syntree, Tree)
    # in the featurechart parser, the root node is '[INIT]'
    # so go down to the first child if necessary
    if syntree.node.head() == start:
        return syntree.node
    elif syntree[0].node.head() == start:
        return syntree[0].node
    else:
        raise ValueError("Tree not rooted in %s node" % start)

def semrep(node, beta_reduce=True):
    """
    Find the semantic representation at a given tree node.
    """
    # check that we have a GrammarCategory
    from nltk.parse import GrammarCategory
    assert isinstance(node, GrammarCategory)
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
    """
    node = root_node(syntree, start=start)
    return semrep(node, beta_reduce=beta_reduce)

def text_interpret(inputs, grammar, beta_reduce=True, start='S', syntrace=0):
    """
    Add the semantic representation to each syntactic parse tree
    of each input sentence.
    """
    parses = text_parse(inputs, grammar, trace=syntrace)
    semreps = {}
    for sent in inputs:
        syntrees = parses[sent]
        syn_sem = \
           [(syn, root_semrep(syn, beta_reduce=beta_reduce, start=start)) for syn in syntrees]
        semreps[sent] = syn_sem
    return semreps

def text_evaluate(inputs, grammar, model, assignment, semtrace=0):
    """
    Add the truth-in-a-model value to each semantic representation
    for each syntactic parse of each input sentences.
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
    
"""
Demo of how to combine the output of parsing with evaluation in a model.
Use 'python syn2sem.py -h' to find out the various options.

Note that this demo currently processes the whole input file
before delivering any results, consequently there may be a significant initial delay.
"""


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
    from nltk.parse.category import GrammarFile
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
    
    gramfile = 'sem2.cfg'
        
    if options.sentences:
        sentsfile = options.sentences
    if options.grammar:
        gramfile = options.grammar
    if options.model:
        exec "import %s as model" % options.model
    
    if sents is None:
        sents = read_sents(sentsfile)

    gram = GrammarFile(gramfile)
    
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
