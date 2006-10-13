# Ewan Klein

"""
Some prototype code to input sentences and output semantic values.
"""

from nltk_lite.contrib.grammarfile import GrammarFile
import nltk_lite.contrib.models as models
from nltk_lite import tokenize
from nltk_lite.parse.category import GrammarCategory
from nltk_lite.parse.tree import Tree
import sys

mygramdir = '/Users/ewan/svn/nltk/doc/en'
sys.path.append(mygramdir)

trace = 0
beta = True


def text_parse(inputs, grammar):
    
    parses = {}
    for sent in inputs:
        tokens = list(tokenize.whitespace(sent))
        parser = grammar.earley_parser(trace=trace)
        syntrees = parser.get_parse_list(tokens)
        parses[sent] = syntrees
    return parses

def get_root_node(syntree, start='S'):
    # check that we have a tree
    assert isinstance(syntree, Tree)
    # in Speer's chart parser, the root node is '[INIT]'
    # so go down to the first child if necessary
    if syntree.node.head() == start:
        return syntree.node
    elif syntree[0].node.head() == start:
        return syntree[0].node
    else:
        raise ValueError("Tree not rooted in %s node" % start)


def get_semrep(node, beta_reduce=True):
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

def get_root_semrep(syntree, beta_reduce=True):
    node = get_root_node(syntree)
    return get_semrep(node, beta_reduce=beta_reduce)

def text_interpret(inputs, grammar):
    parses = text_parse(inputs, grammar)
    semreps = {}
    for sent in inputs:
        syntrees = parses[sent]
        syn_sem = [(syn, get_root_semrep(syn)) for syn in syntrees]
        semreps[sent] = syn_sem
    return semreps
        
def text_evaluate(inputs, grammar, model, assignment):
    semreps = text_interpret(inputs, grammar)
    evaluations = {}
    for sent in inputs:
        syn_sem_val = [(syn, sem, model.evaluate(str(sem), g)) for (syn, sem) in semreps[sent]]
        evaluations[sent] = syn_sem_val
    return evaluations


def model_init():
    """
    Sample model to accompany semtest.cfg grammar
    """
    global m, g 
    val = models.Valuation()
    v = [('john', 'b1'),
         ('mary', 'g1'),
         ('fido', 'd1'),
         ('noosa', 'n'),
         ('girl', set(['g1', 'g2'])),
         ('boy', set(['b1', 'b2'])),
         ('dog', set(['d1'])),
         ('bark', set(['d1'])),
         ('walk', set(['b1', 'g2', 'd1'])),
         ('love', set([('b1', 'g1'), ('b2', 'g2'), ('g1', 'b1'), ('g2', 'b1')])),
         ('see', set([('b1', 'g1'), ('b2', 'd2'), ('g1', 'b1'), ('d2', 'b1'), ('g2', 'n')])),
         ('in', set([('b1', 'n'), ('b2', 'n'), ('d2', 'n')])),
         ('with', set([('b1', 'g1'), ('g1', 'b1'), ('d1', 'b1'), ('b1', 'd1')]))]
    val.parse(v)
    dom = val.domain
    m = models.Model(dom, val)
    g = models.Assignment(dom)


sents = ['Fido sees a boy with Mary',
         'John sees Mary',
         'John walks with a girl in Noosa'
         ]

def demo():
    model_init()
    SPACER = '-' * 30
    filename = 'semtest.cfg'
    model = m
    assignment = g
    grammar = GrammarFile.read_file(filename)
    inputs = sents
    evaluations = text_evaluate(inputs, grammar, model, assignment)

    for sent in evaluations:
        n = 1
        print
        print 'Sentence: %s' % sent
        print SPACER
        for (syntree, semrep, value) in evaluations[sent]:
            print '%d:  %s' % (n, semrep)
            print '%9s in Model m' % value
            n += 1
    
if __name__ == "__main__":
    demo()



    
