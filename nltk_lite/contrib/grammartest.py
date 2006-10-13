# Ewan Klein

"""
Some prototype code to input sentences and output semantic values.
"""

from nltk_lite.contrib.grammarfile import GrammarFile
import nltk_lite.contrib.models 
from nltk_lite import tokenize
from nltk_lite.parse.category import GrammarCategory
from nltk_lite.parse.tree import Tree

mygramdir = '/Users/ewan/svn/nltk/doc/en/'

# specify the level of tracing in chart parser
trace = 0
# specify whether semantic output should undergo beta-reduction
beta = True
# specify the start symbol for the parse tree
start = 'S'

def gtest(input, filename):
    grammar = GrammarFile.read_file(filename)
    parses = []
    for sent in input:
        tokens = list(tokenize.whitespace(sent))
        parser = grammar.earley_parser(trace=trace)
        trees = parser.parse(tokens)
        parses.append((sent, trees))
    return parses

def get_root_node(tree,start='S'):
    # check that we have a tree
    assert isinstance(tree, Tree)
    # in Speer's chart parser, the root node is '[INIT]'
    # so go down to the first child if necessary
    if tree.node.head() == start:
        return tree.node
    elif tree[0].node.head() == start:
        return tree[0].node
    else:
        raise ValueError("Tree not rooted in %s node" % start)


def get_sem_val(node, beta_reduce=True):
    # check that we have a GrammarCategory
    assert isinstance(node, GrammarCategory)
    try:
        sem_val = node.get_feature('sem')
        if beta_reduce:
            sem_val = sem_val.simplify()
        return sem_val
    except KeyError:
        print "Node has no 'sem' feature specification"
    
def demo():
    sents0 = ['who do you like', 'girls you like', 'you do like girls',
         'you claim that you like girls', 'who do you claim that you like']
    sents1 = ['Kim sleeps', 'I like Kim']
    sents2 = ['Fido barks', 'John loves Mary', 'every boy loves Mary']
    sents3 = ['John sees a boy with Fido']
    parses = gtest(input=sents3, filename=mygramdir+'semtest.cfg')
    for (sent, tree) in parses:
        print sent
        if tree:
            node = get_root_node(tree, start)
            val = get_sem_val(node, beta_reduce=beta)
            print str(val)
        else:
            print "[No semantics available]"


#demo()

parses = gtest(input=['John sees a boy with Fido'], filename=mygramdir+'semtest.cfg')

print parses



    
