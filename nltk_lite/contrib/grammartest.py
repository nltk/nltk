# Ewan Klein

"""
A set of methods to help combine syntactic parse output with semantic
representation and model-checking.

"""

from nltk_lite.parse.grammarfile import GrammarFile
import nltk_lite.semantics.evaluate as evaluate
from nltk_lite import tokenize
from nltk_lite.parse.category import GrammarCategory
from nltk_lite.parse.tree import Tree

mygramdir = '/Users/ewan/svn/nltk/examples/parse/'


trace = 0


def text_parse(inputs, grammar):
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

def root_semrep(syntree, beta_reduce=True):
    """
    Find the semantic representation at the root of a tree.
    """
    node = root_node(syntree)
    return semrep(node, beta_reduce=beta_reduce)

def text_interpret(inputs, grammar):
    """
    Add the semantic representation to each syntactic parse tree
    of each input sentence.
    """
    parses = text_parse(inputs, grammar)
    semreps = {}
    for sent in inputs:
        syntrees = parses[sent]
        syn_sem = [(syn, root_semrep(syn)) for syn in syntrees]
        semreps[sent] = syn_sem
    return semreps

def text_evaluate(inputs, grammar, model, assignment):
    """
    Add the truth-in-a-model value to each semantic representation
    for each syntactic parse of each input sentences.
    """
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
    val = evaluate.Valuation()
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
    val.read(v)
    dom = val.domain
    m = evaluate.Model(dom, val)
    g = evaluate.Assignment(dom)


sents = ['Fido sees a boy with Mary',
         'John sees Mary',
         'every girl chases a dog',
         'every boy chases a girl',
         'John walks with a girl in Noosa'
         ]

sents0 = ['a dog barks']

def demo(evaluate=0):
    model_init()
    SPACER = '-' * 30
    filename = mygramdir + 'sem1.cfg'
    model = m
    assignment = g
    grammar = GrammarFile.read_file(filename)
    inputs = sents0
    
    for sent in inputs:
        n = 1
        print '\nSentence: %s' % sent
        print SPACER
        if evaluate:
            evaluations = text_evaluate(inputs, grammar, model, assignment)
            for (syntree, semrep, value) in evaluations[sent]:
                print '%d:  %s' % (n, semrep.infixify())
                print '%9s in Model m' % value
            n += 1
        else:
            semreps = text_interpret(inputs, grammar)
            for (syntree, semrep) in semreps[sent]:
                print '%d:  %s' % (n, semrep.infixify())
            n += 1
                
if __name__ == "__main__":
    demo()


demo(evaluate=True)
