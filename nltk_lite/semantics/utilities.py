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


from nltk_lite import tokenize
from nltk_lite.parse.category import *
from nltk_lite.parse.grammarfile import *
from nltk_lite.parse.tree import Tree
from evaluate import *
from logic import *

##############################################################
## Utility functions for connecting parse output to semantics
##############################################################

def text_parse(inputs, grammar, trace=0):
    """
    Convert input sentences into syntactic trees.
    """
    parses = {}
    for sent in inputs:
        tokens = list(tokenize.whitespace(sent))
        parser = grammar.earley_parser(trace=trace)
        syntrees = parser.get_parse_list(tokens)
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
    assert isinstance(node, GrammarCategory)
    try:
        semrep = node.get_feature('sem')
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

def text_interpret(inputs, grammar, beta_reduce=True, start='S'):
    """
    Add the semantic representation to each syntactic parse tree
    of each input sentence.
    """
    parses = text_parse(inputs, grammar)
    semreps = {}
    for sent in inputs:
        syntrees = parses[sent]
        syn_sem = \
           [(syn, root_semrep(syn, beta_reduce=beta_reduce, start=start)) for syn in syntrees]
        semreps[sent] = syn_sem
    return semreps

def text_evaluate(inputs, grammar, model, assignment):
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
          [(syn, sem, m.evaluate(str(sem), g)) for (syn, sem) in semreps[sent]]
        evaluations[sent] = syn_sem_val
    return evaluations
    

