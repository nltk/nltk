# Contributed by Rob Speer

from nltk_lite.contrib.feature import *
from nltk_lite.contrib.featurechart import *
from nltk_lite.parse import cfg

"""A module to read a grammar from a *.cfg file."""

class GrammarFile(object):
	def __init__(self):
		self.grammatical_productions = []
		self.lexical_productions = []
		self.start = GrammarCategory(pos='Start').freeze()
		
	def grammar(self):
		return cfg.Grammar(self.start, self.grammatical_productions +\
		self.lexical_productions)
		
	def earley_grammar(self):
		return cfg.Grammar(self.start, self.grammatical_productions)
	
	def earley_lexicon(self):
		lexicon = {}
		for prod in self.lexical_productions:
			lexicon.setdefault(prod.rhs()[0], []).append(prod.lhs())
		return lexicon

	def earley_parser(self, trace=1):
		return FeatureEarleyChartParse(self.earley_grammar(),
					       self.earley_lexicon(), trace=trace)

	def apply_lines(self, lines):
		for line in lines:
			line = line.strip()
			if not len(line): continue
			if line[0] == '#': continue
			if line[0] == '%':
				parts = line[1:].split()
				directive = parts[0]
				args = " ".join(parts[1:])
				if directive == 'start':
					self.start = GrammarCategory.parse(args).freeze()
				elif directive == 'include':
					filename = args.strip('"')
					self.apply_file(filename)
			else:
				rules = GrammarCategory.parse_rules(line)
				for rule in rules:
					if len(rule.rhs()) == 1 and isinstance(rule.rhs()[0], str):
						self.lexical_productions.append(rule)
					else:
						self.grammatical_productions.append(rule)

	def apply_file(self, filename):
		f = open(filename)
		lines = f.readlines()
		self.apply_lines(lines)
		f.close()
	
	def read_file(filename):
		result = GrammarFile()
		result.apply_file(filename)
		return result
	read_file = staticmethod(read_file)

def demo():
	g = GrammarFile.read_file("test.cfg")
	print g.grammar()

if __name__ == '__main__':
	demo()

