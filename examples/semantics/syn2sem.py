# Natural Language Toolkit: Parsers
#
# Author: Ewan Klein <ewan@inf.ed.ac.uk>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

from __future__ import print_statement

"""
Demo of how to combine the output of parsing with evaluation in a model.
Use 'python syn2sem.py -h' to find out the various options.

Note that this demo currently processes the whole input file
before delivering any results, consequently there may be a significant initial delay.
"""

from nltk.semantics import *


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



    if options.demo == 'chat80':
        import model1 as model
        sentsfile = 'chat_sentences'
        gramfile = 'chat80.cfg'
    else:
        import model0 as model
        sentsfile = 'demo_sentences'
        gramfile = 'sem2.cfg'
        
    if options.sentences:
        sentsfile = options.sentences
    if options.grammar:
        gramfile = options.grammar
    if options.model:
        exec "import %s as model" % options.model
    
    sents = read_sents(sentsfile)
    
    # NB. GrammarFile is imported indirectly via nltk.semantics
    gram = GrammarFile.read_file(gramfile)

    m = model.m
    g = model.g

    if options.evaluate: 
        evaluations = \
            text_evaluate(sents, gram, m, g, semtrace=options.semtrace)
    else:
        semreps = \
            text_interpret(sents, gram, beta_reduce=options.beta, syntrace=options.syntrace)
        
    for sent in sents:
        n = 1
        print('\nSentence: %s' % sent)
        print(SPACER)
        if options.evaluate: 
            
            for (syntree, semrep, value) in evaluations[sent]:
                if isinstance(value, dict):
                    value = set(value.keys())
                print('%d:  %s' % (n, semrep.infixify()))
                print(value)
                n += 1
        else:
           
            for (syntree, semrep) in semreps[sent]:
                print('%d:  %s' % (n, semrep.infixify()))
                n += 1
                
if __name__ == "__main__":
    demo()



