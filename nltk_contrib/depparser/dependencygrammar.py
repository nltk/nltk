# Natural Language Toolkit: Dependency Grammars
#
# Copyright (C) 2001-2008 NLTK Project
# Author: Jason Narad <jason.narad@gmail.com>
# URL: <http://nltk.org>
# For license information, see LICENSE.TXT
#


from nltk.parse import Tree
from pprint import pformat
from dependencygraph import *
import re

#################################################################
# Dependency Production
#################################################################

class DependencyProduction(object):
	"""
	A dependency grammar production.  Each production maps a single
	head word to an unordered list of one or more modifier words.
	"""
	def __init__(self, lhs, rhs):
		"""
		Construct a new C{DependencyProduction}.
		
		@param lhs: The left-hand side of the new C{DependencyProduction}.
		@type lhs: L{string}
		@param rhs: The right-hand side of the new C{DependencyProduction}.
		@type rhs: sequence of L{string}
		"""
		if isinstance(rhs, (str, unicode)):
			raise TypeError('dependency production right hand side should be a list, '
							'not a string')
		self._lhs = lhs
		self._rhs = tuple(rhs)
		self._hash = hash((self._lhs, self._rhs))

	def lhs(self):
		"""
		@return: the left-hand side of this C{DependencyProduction}.
		@rtype: L{string}
		"""
		return self._lhs

	def rhs(self):
		"""
		@return: the right-hand side of this C{DependencyProduction}.
		@rtype: sequence of L{string}
		"""
		return self._rhs

	def __str__(self):
		"""
		@return: A verbose string representation of the 
			C{DependencyProduction}.
		@rtype: C{string}
		"""
#		return '%s -> %s' % (self._lhs, self._rhs)
		str = '\'%s\' ->' % (self._lhs,)
		for elt in self._rhs:
#			if isinstance(elt, Nonterminal):
				str += ' \'%s\'' % (elt,)
#			else:
#				str += ' %r' % (elt,)
		return str

	def __repr__(self):
		"""
		@return: A concise string reperesentation of the
			C{DependencyProduction}.
		@rtype: C{string}
		"""
		return '%s' % self

	def __eq__(self, other):
		"""
		@return: true if this C{DependencyProduction} is equal to C{other}.
		@rtype: C{boolean}.
		"""
		return (isinstance(other, self.__class__) and
				self._lhs == other._lhs and
				self._rhs == other._rhs)

	def __ne__(self, other):
		return not (self == other)

	def __cmp__(self, other):
		if not isinstance(other, self.__class__): return -1
		return cmp((self._lhs, self._rhs), (other._lhs, other._rhs))

	def __hash__(self):
		return self._hash

#################################################################
# Dependency Grammar
#################################################################

class DependencyGrammar(object):
	"""
	A dependency grammar.  A DependencyGrammar consists of a set of
	productions.  Each production specifies a head/modifier relationship
	between a pair of words.
	"""
	def __init__(self, productions):
		"""
		Create a new dependency grammar, from the set of C{Production}s.
		
		@param productions: The list of productions that defines the grammar
		@type productions: C{list} of L{Production}
		"""
		self._productions = productions

	def contains(self, head, mod):
		"""
		@param head: A head word.
		@type head: C{string}.
		@param mod: A mod word, to test as a modifier of 'head'.
		@type mod: C{string}.

		@return: true if this C{DependencyGrammar} contains a 
			C{DependencyProduction} mapping 'head' to 'mod'.
		@rtype: C{boolean}.
		"""
		for production in self._productions:
			for possibleMod in production._rhs:
				if(production._lhs == head and possibleMod == mod):
					return True
		return False
		

	# 	# should be rewritten, the set comp won't work in all comparisons
	# def contains_exactly(self, head, modlist):
	# 	for production in self._productions:
	# 		if(len(production._rhs) == len(modlist)):
	# 			if(production._lhs == head):
	# 				set1 = Set(production._rhs)
	# 				set2 = Set(modlist)
	# 				if(set1 == set2):
	# 					return True
	# 	return False


	def __str__(self):
		"""
		@return: A verbose string representation of the
			C{DependencyGrammar}
		@rtype: C{string}
		"""
		str = 'Dependency grammar with %d productions' % len(self._productions)
		for production in self._productions:
			str += '\n	%s' % production
		return str
			
	def __repr__(self):
		"""
		@return: A concise string representation of the
			C{DependencyGrammar}
		"""
		return 'Dependency grammar with %d productions' % len(self._productions)
	


#################################################################
# Statistical Dependency Grammar
#################################################################

class StatisticalDependencyGrammar(object):

	def __init__(self, productions, events, tags):
		self._productions = productions
		self._events = events
		self._tags = tags

	def contains(self, head, mod):
		for production in self._productions:
			for possibleMod in production._rhs:
				if(production._lhs == head and possibleMod == mod):
					return True
		return False

	def __str__(self):
		str = 'Statistical dependency grammar with %d productions' % len(self._productions)
		for production in self._productions:
			str += '\n	%s' % production
		str += '\nEvents:'
		for event in self._events:
			str += '\n	%d:%s' % (self._events[event], event)
		str += '\nTags:'
		for tag_word in self._tags:
			str += '\n %s:\t(%s)' % (tag_word, self._tags[tag_word])
		return str

	def __repr__(self):
		"""
		@return: A concise string representation of the
			C{DependencyGrammar}
		"""
		return 'Dependency grammar with %d productions' % len(self._productions)


#################################################################
# Parsing Dependency Grammars
#################################################################

_PARSE_DG_RE = re.compile(r'''^\s*                # leading whitespace
                              ('[^']+')\s*        # single-quoted lhs
                              (?:[-=]+>)\s*        # arrow
                              (?:(                 # rhs:
                                   "[^"]+"         # doubled-quoted terminal
                                 | '[^']+'         # single-quoted terminal
                                 | \|              # disjunction
                                 )
                                 \s*)              # trailing space
                                 *$''',            # zero or more copies
                             re.VERBOSE)
_SPLIT_DG_RE = re.compile(r'''('[^']'|[-=]+>|"[^"]+"|'[^']+'|\|)''')

def parse_dependency_grammar(s):
	productions = []
	for linenum, line in enumerate(s.split('\n')):
		line = line.strip()
		if line.startswith('#') or line=='': continue
		try: productions += parse_dependency_production(line)
		except ValueError:
			raise ValueError, 'Unable to parse line %s: %s' % (linenum, line)
	if len(productions) == 0:
		raise ValueError, 'No productions found!'
	return DependencyGrammar(productions)

def parse_dependency_production(s):
	if not _PARSE_DG_RE.match(s):
		raise ValueError, 'Bad production string'
	pieces = _SPLIT_DG_RE.split(s)
	pieces = [p for i,p in enumerate(pieces) if i%2==1]
	lhside = pieces[0].strip('\'\"')
	rhsides = [[]]
	for piece in pieces[2:]:
		if piece == '|':
			rhsides.append([])
		else:
			rhsides[-1].append(piece.strip('\'\"'))
	return [DependencyProduction(lhside, rhside) for rhside in rhsides]



#################################################################
# Demos
#################################################################

def demo():
	"""
	A demonstration showing the creation and inspection of a 
	C{DependencyGrammar}.
	"""
	grammar = parse_dependency_grammar("""
	'scratch' -> 'cats' | 'walls'
	'walls' -> 'the'
	'cats' -> 'the'
	""")
	print grammar
	
def stat_demo():
	"""
	A demonstration of how to read a string representation of 
	a CoNLL format dependency tree.
	"""
	dg = DepGraph().read("""
	1   Ze                ze                Pron  Pron  per|3|evofmv|nom                 2   su      _  _
	2   had               heb               V     V     trans|ovt|1of2of3|ev             0   ROOT    _  _
	3   met               met               Prep  Prep  voor                             8   mod     _  _
	4   haar              haar              Pron  Pron  bez|3|ev|neut|attr               5   det     _  _
	5   moeder            moeder            N     N     soort|ev|neut                    3   obj1    _  _
	6   kunnen            kan               V     V     hulp|ott|1of2of3|mv              2   vc      _  _
	7   gaan              ga                V     V     hulp|inf                         6   vc      _  _
	8   winkelen          winkel            V     V     intrans|inf                      11  cnj     _  _
	9   ,                 ,                 Punc  Punc  komma                            8   punct   _  _
	10  zwemmen           zwem              V     V     intrans|inf                      11  cnj     _  _
	11  of                of                Conj  Conj  neven                            7   vc      _  _
	12  terrassen         terras            N     N     soort|mv|neut                    11  cnj     _  _
	13  .                 .                 Punc  Punc  punt                             12  punct   _  _
	""")
	tree = dg.deptree()
	print tree.pprint()


if __name__ == '__main__':
	demo()
