#!/usr/bin/env python
from nltk_contrib.mit.rspeer.parser.readfile import GrammarFile
from nltk_contrib.mit.rspeer.parser.featurechart import *
from nltk.tokenizer import WhitespaceTokenizer

"""
An interactive interface to the feature-based parser. Run "main.py -h" for
command-line options.

This interface will read a grammar from a *.cfg file, in the format of
test.cfg. It will prompt for a filename for the grammar (unless one is given on
the command line) and for a sentence to parse, then display the edges being
generated and any resulting parse trees.
"""

NAME = '6.863 Earley Parser'
DATE = 'July 13, 2004'
__version__ = '2.0'
__license__ = 'GNU General Public License 2'
NLTK_VERSION = 1.4

def demo():
	gfile = GrammarFile.read_file('test.cfg')
	cp = gfile.earley_parser()
	sent = Token(TEXT='the police read the solutions that Poirot sent')
	WhitespaceTokenizer().tokenize(sent)
	cp.parse_n(sent)
	for tree in sent['TREES']: print tree

def text_parse(grammar, sentence, trace=2, drawtrees=False, latex=False):
	parser = grammar.earley_parser(trace=trace)
	print parser._grammar
	sent = Token(TEXT=sentence)
	WhitespaceTokenizer().tokenize(sent)
	parser.parse_n(sent)
	if drawtrees:
		from treeview import TreeView
		TreeView(sent['TREES'])
	else:
		for tree in sent['TREES']:
			if latex: print tree.latex_qtree()
			else: print tree

def main():
	import sys
	from optparse import OptionParser, OptionGroup
	usage = """%%prog [options] [grammar_file]

%(NAME)s
version %(__version__)s for NLTK %(NLTK_VERSION)s (%(DATE)s)
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
	trace = 2
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
	
	grammar = GrammarFile.read_file(filename)

	if not batch:
		sys.stderr.write("Sentence: ")
		sentence = sys.stdin.readline()[:-1]
		if sentence == '': return
		text_parse(grammar, sentence, trace, options.drawtrees, options.latex)
	else:
		infile = open(options.batchfile)
		for line in infile.readlines():
			sentence = line.strip()
			if sentence == '': continue
			if sentence[0] == '#': continue
			print "Sentence: %s" % sentence
			text_parse(grammar, sentence, trace, False, options.latex)
		infile.close()

if __name__ == '__main__':
	main()

