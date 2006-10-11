# Ewan Klein

"""
Some prototype code to input sentences and output semantic values.
"""

from nltk_lite.contrib.grammarfile import GrammarFile
import nltk_lite.contrib.models 
from nltk_lite import tokenize
from nltk_lite.parse.category import GrammarCategory
from nltk_lite.parse.tree import Tree
import sys

mygramdir = '/Users/ewan/svn/nltk/doc/en'
sys.path.append(mygramdir)

trace = 1
beta = True

def gtest(input, filename):
    grammar = GrammarFile.read_file(filename)
    parses = []
    for sent in input:
        tokens = list(tokenize.whitespace(sent))
        parser = grammar.earley_parser(trace=trace)
        tree = parser.parse(tokens)
        parses.append((sent, tree))
    return parses

def get_root_node(tree):
    # check that we have a tree
    assert isinstance(tree, Tree)
    # in Speer's chart parser, the root node is '[INIT]'
    # so go down to the first child if necessary
    if tree.node.head() == 'S':
        return tree.node
    elif tree[0].node.head() == 'S':
        return tree[0].node
    else:
        raise ValueError("Tree not rooted in 'S' node")


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
    sents3 = ['a boy loves all girls']
    parses = gtest(input=sents3, filename='semtest.cfg')
    for (sent, tree) in parses:
        print sent
        if tree:
            node = get_root_node(tree)
            val = get_sem_val(node, beta_reduce=beta)
            print str(val)
        else:
            print "[No semantics available]"


demo()



    
