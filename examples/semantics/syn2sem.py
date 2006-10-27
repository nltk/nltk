# Natural Language Toolkit: Parsers
#
# Author: Ewan Klein <ewan@inf.ed.ac.uk>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#

"""
Demo of how to combine the output of parsing with evaluation in a model.
Requires two inputs:

 - C{sem2.cfg}: a toy grammar with some syntactic and semantic rules.
 - C{model0.py}: a small first-order model to interpret outputs of the grammar.



"""

from nltk_lite.semantics import *
from model0 import *


sents = ['Fido sees a boy with Mary',
         'John sees Mary',
         'every girl chases a dog',
         'every boy chases a girl',
         'John walks with a girl in Noosa'
         ]

sents0 = ['a dog barks']

def main(evaluate=0):
    SPACER = '-' * 30
    filename = 'sem1.cfg'
    model = m
    assignment = g
    # GrammarFile is imported indirectly via nltk_lite.semantics
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
    main(evaluate=1)



