# Natural Language Toolkit: Semantic System
#
# Author: Yurie Hara <yhara@udel.edu>
# $Id$
# 
"""
A class to represent lambda calculus expressions.

It includes interfaces for deriving a semantic meaning from a
sentence's syntax tree and a lexicon. With this interface, the whole
sentence can be denoted by a lambda calculus expression.

Example: The denotation of "John saw Mary" is::

    saw('Mary')('John') == saw(John, Mary) 
"""
__docformat__ = 'plaintext'

from nltk.cfg import CFG, CFGProduction, Nonterminal
from nltk.parser.chart import *
from nltk.tokenizer import WhitespaceTokenizer
from nltk.tree import *

def GetLambda(lex, word):
    """
    Create a lambda expression for a subtree whose child is a lexical item.

    Parameters:
        lex: types of lexical item
        (pn==pronoun,iv==intranstive, tv==transtive
        cn==common noun, adj==adjective, quant==quantifier)
        word: name of the lexical item

    @return: lambda expression of the lexical item
    @rtype: lambda expression
        
    Example:
    the denotation of 'saw'(transtive): lambda x. lambda y. saw(y,x)
    
    """
    if lex=='pn':       #pronoun
        return word
    if lex=='iv':       #intransitive verb
        return lambda subj: word + "("+ subj +")"
    if lex=='tv':       #transitive verb
        return lambda obj: (lambda subj: word + "("+ subj +","+ obj +")")
    if lex=='cn':       #common noun
        return lambda x: word + "(" + x + ")"
    if lex=='adj':       #adjective
        return lambda noun: (lambda y: noun(y) + " and " + word + "(" + y + ")")
    if lex=='quant':    #quantifier
        return lambda res: (lambda matrix: word + "(x)[" + (res("x")) + "][" + (matrix("x")) + "]")

class Semantics:
    """
    A representation for a semantic meaning of a sentence.
    Semantics calculates a semantic meaning using a tree structure and
    denotations of lexical items anchored at the terminals of the tree. 
    """
    def __init__(self, tree, denotations):
         self._tree = tree
         self._denotations = denotations
         self._semantics = self.GetSemantics(self._tree)

    def __str__(self):
        return self._semantics

    def GetSubtreeFrag(self, subtree):
        """
        Creates a local subtree fragment to be assigned to the keys
        in the "denotations" dictionary.
     
         -Iterates through the children of the subtree,
         and gets their nodes or types.

         -The Tree constructor is used to make the new local subtree.
    
        Parameter:
            subtree: tree token

        @return:a subtree fragment
        @rtype: Tree type
    
        Example: if subtree is the tree token:
          ('VP': ('V': 'saw') ('NP': 'John'))@[1w:3w]
        then it returns:
          ('VP': 'V' 'NP')
        """
        type_of_children=[]
        for child in subtree.children():
            if isinstance(child, AbstractTree):
                type_of_children.append(child.node())
            else:    
                type_of_children.append(child.type())
        return Tree(subtree.node(), *type_of_children)
            
    def GetSemantics(self, tree):
        """
        Takes a tree structure and derive a semantic meaning

            -Iterates through the tree recursively
            until it reaches a node that immediately dominates a string

            -Using GetSubtreeFrag, gets the denotation of the terminals and
            the combiners defined in denotations

            -Applys lambda conversion using combiners
            
        Parameter:
            tree: tree token constructed by parser

        @return:  semantic meaning of a sentence
        @rtype: string

        Example: if tree is:
            ('S': ('NP': 'John') ('VP': ('V': 'likes') ('NP': 'Mary')))@[0w:3w]
        then it returns:
            likes(John,Mary)
        """
       
        if not isinstance(tree, AbstractTree):
            return 
        else:
            meaning_of_children=[]
            for child in tree.children():                    
                meaning_of_children.append(self.GetSemantics(child))
        #find a combiner or a denotation from the denotation dictionary
            find_denot = self._denotations[self.GetSubtreeFrag(tree)]
        #Apply a combiner to the meaning of children
        #when tree is not a terminal
            if not meaning_of_children[0] is None:
                return find_denot(*meaning_of_children) #lambda conversion
            else:
                return find_denot     #lexical denotation       

#################################################################
# Test code
#################################################################


def demo():
    # Define the productions
    nonterminals = 'S VP NP QP Q N A V'
    (S, VP, NP, QP, Q, N, A, V) = [Nonterminal(s)
                                           for s in nonterminals.split()]

    productions = [
    # Lexical productions
        CFGProduction(N, 'John'),     CFGProduction(N, 'Mary'),
        CFGProduction(V, 'like'),      CFGProduction(V, 'sleeps'),
        CFGProduction(V, 'likes'),
        CFGProduction(Q, 'every'),      CFGProduction(N, 'girl'),
        CFGProduction(A, 'pretty'),     CFGProduction(N, 'man'),
        CFGProduction(Q, 'some'),
        CFGProduction(Q, 'no'),

    # Syntactic productions
        CFGProduction(S, NP, VP),
        CFGProduction(QP, Q, NP),
        CFGProduction(NP, N),
        CFGProduction(VP, V),
        CFGProduction(VP, V, NP),
        CFGProduction(S, QP, VP),
        CFGProduction(NP, A, N), 
        ]

    #Assign a denotation to trees whose direct children are terminals
    default_denotations = {
    #lexical denotations
        Tree('V','likes'):GetLambda('tv', 'likes'),
        Tree('V','sleeps'):GetLambda('iv', 'sleeps'),
        Tree('N','John'):GetLambda('pn', 'John'),
        Tree('N','Mary'):GetLambda('pn', 'Mary'),
        Tree('Q','every'):GetLambda('quant','every'),
        Tree('Q','some'):GetLambda('quant','some'),
        Tree('Q','no'):GetLambda('quant','no'),
        Tree('N','girl'):GetLambda('cn','girl'),
        Tree('N','man'):GetLambda('cn','man'),
        Tree('A','pretty'):GetLambda('adj','pretty'),
    
    #combiners that determine which child is an argument
    #and which child is a predicate.
        Tree('VP', 'V', 'NP'): lambda v,n:v(n),
        Tree('S', 'NP', 'VP'): lambda n,vp:vp(n),
        Tree('S', 'QP', 'VP'): lambda qp,vp:qp(vp),
        Tree('QP', 'Q', 'NP'): lambda q,np:q(np),
        Tree('NP', 'N'): lambda n:n,
        Tree('VP', 'V'): lambda v:v,
        Tree('NP', 'A', 'N'): lambda a,n:a(n),
        }

   # Define test sentences.
    test_sentences = [
        'Mary sleeps',
        'John likes Mary',
        'every girl likes Mary',
        'some pretty girl likes Mary',
        'no man sleeps',
        ]

    # Create grammar
    grammar = CFG(S, productions)

    # Create a parser.
    parser = IncrementalChartParser(grammar, INCREMENTAL_TD_STRATEGY)

    # Create a tokenizer
    tokenizer = WhitespaceTokenizer()

    # Parse the sentences
    parses = []
    for s in test_sentences:
        parses.append(parser.parse(tokenizer.tokenize(s)))
        
        print s         #print the sentence
        print parses[-1]    #draw the tree
        #print the semantic meaning
        print Semantics(parses[-1], default_denotations)   

if __name__ == '__main__': demo()

