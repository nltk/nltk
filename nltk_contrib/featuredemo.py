from nltk.parse import GrammarFile
from nltk.parse.featurechart import *

"""
An interactive interface to the feature-based parser. Run "featuredemo.py -h" for
command-line options.

This interface will read a grammar from a *.cfg file, in the format of
test.cfg. It will prompt for a filename for the grammar (unless one is given on
the command line) and for a sentence to parse, then display the edges being
generated and any resulting parse trees.
"""

def text_parse(grammar, sent, trace=2, drawtrees=False, latex=False):
    parser = grammar.earley_parser(trace=trace)
    print parser._grammar
    tokens = sent.split()
    trees = parser.get_parse_list(tokens)
    if drawtrees:
        from treeview import TreeView
        TreeView(trees)
    else:
        for tree in trees:
            if latex: print tree.latex_qtree()
            else: print tree

def main():
    import sys
    from optparse import OptionParser, OptionGroup
    usage = """%%prog [options] [grammar_file]

by Rob Speer
Distributed under the GPL. See LICENSE.TXT for information.""" % globals()

    opts = OptionParser(usage=usage)
    opts.add_option("-b", "--batch",
    metavar="FILE", dest="batchfile", default=None,
    help="Batch test: parse all the lines in a file")

    opts.add_option("-v", "--verbose",
    action="count", dest="verbosity", default=0,
    help="show more information during parse")
    opts.add_option("-q", "--quiet",
    action="count", dest="quietness", default=0,
    help="show only the generated parses (default in batch mode)")
    opts.add_option("-l", "--latex",
    action="store_true", dest="latex",
    help="output parses as LaTeX trees (using qtree.sty)")
    opts.add_option("-d", "--drawtrees",
    action="store_true", dest="drawtrees",
    help="show parse trees in a GUI window")

    (options, args) = opts.parse_args()
    trace = 0
    batch = False
    
    if options.batchfile is not None:
        trace = 0
        batch = True
        if options.drawtrees:
            sys.stderr.write("Cannot use --drawtrees and --batch simultaneously.")
            sys.exit(1)
    if options.quietness > 0: trace = 0
    trace += options.verbosity

    if len(args): filename = args[0]
    else: filename = None

    if filename is None:
        sys.stderr.write("Load rules from file: ")
        filename = sys.stdin.readline()[:-1]
        if filename == '': return
    
    grammar = GrammarFile(filename)

    if not batch:
        sys.stderr.write("Sentence: ")
        sentence = sys.stdin.readline()[:-1]
        if sentence == '': return
        text_parse(grammar, sentence, trace, options.drawtrees, options.latex)
    else:
        for line in open(options.batchfile):
            sentence = line.strip()
            if sentence == '': continue
            if sentence[0] == '#': continue
            print "Sentence: %s" % sentence
            text_parse(grammar, sentence, trace, False, options.latex)

if __name__ == '__main__':
    main()

