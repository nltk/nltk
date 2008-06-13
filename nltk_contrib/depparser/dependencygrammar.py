# Natural Language Toolkit: Dependency Grammars
#
# Copyright (C) 2001-2008 University of Pennsylvania
# Author: Jason Narad <jason.narad@gmail.com>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#

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
		if isinstance(rhs, list):
			raise TypeError('dependency production right hand side should be a string, '
							'not a list')  # will revise with list when arity is added 
		self._lhs = lhs
		self._rhs = rhs
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
		return '%s -> %s' % (self._lhs, self._rhs)

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
			if(production._lhs == head and production._rhs == mod):
#				print '*%s* does head *%s*' % (head, mod)
				return True
#		print '*%s* does NOT head *%s*' % (head, mod)
		return False

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
# Dependency Span
#################################################################

class DependencySpan(object):
	"""
	A contiguous span over some part of the input string representing 
	dependency (head -> modifier) relationships amongst words.  An atomic 
	span corresponds to only one word so it isn't a 'span' in the conventional
	sense, as its _start_index = _end_index = _head_index for concatenation
	purposes.  All other spans are assumed to have arcs between all nodes
	within the start and end indexes of the span, and one head index corresponding
	to the head word for the entire span.  This is the same as the root node if 
	the dependency structure were depicted as a graph.
	"""
	def __init__(self, start_index, end_index, head_index, arcs):
		self._start_index = start_index
		self._end_index = end_index
		self._head_index = head_index
		self._arcs = arcs

	def head_index(self):
		"""
		@return: An value indexing the head of the entire C{DependencySpan}.
		@rtype: C{int}.
		"""
		return self._head_index
	
	def __repr__(self):
		"""
		@return: A concise string representatino of the C{DependencySpan}.
		@rtype: C{string}.
		"""
		return 'Span %d-%d; Head Index: %d' % (self._start_index, self._end_index, self._head_index)
	
	def __str__(self):
		"""
		@return: A verbose string representation of the C{DependencySpan}.
		@rtype: C{string}.
		"""
		str = 'Span %d-%d; Head Index: %d' % (self._start_index, self._end_index, self._head_index)
		for i in range(len(self._arcs)):
			str += '\n%d <- %d' % (i, self._arcs[i])
		return str
			


#################################################################
# Chart Cell
#################################################################

class ChartCell(object):
	"""
	A cell from the parse chart formed when performing the CYK algorithm.
	Each cell keeps track of its x and y coordinates (though this will probably
	be discarded), and a list of spans serving as the cell's entries.
	"""
	def __init__(self, x, y):
		"""
		@param x: This cell's x coordinate.
		@type x: C{int}.
		@param y: This cell's y coordinate.
		@type y: C{int}.
		"""
		self._x = x
		self._y = y
#		self._entriesByHead = {}  # was going to use more efficient
#		self._entriesByMod = {}  # indexing like in Dan Klein's PCFG
		self._entries = []
		
	def add(self, span):
		"""
		Appends the given span to the list of spans
		representing the chart cell's entries.
		
		@param span: The span to add.
		@type span: C{DependencySpan}.
		"""
		self._entries.append(span);

	def __str__(self):
		"""
		@return: A verbose string representation of this C{ChartCell}.
		@rtype: C{string}.
		"""	
		return 'CC[%d,%d]: %s' % (self._x, self._y, self._entries)
		
	def __repr__(self):
		"""
		@return: A concise string representation of this C{ChartCell}.
		@rtype: C{string}.
		"""
		return '%s' % self




#################################################################
# Chart Entry
#################################################################
# 
# class ChartEntry(object):
# 
# 	def __init__(self, span):
# 		self._spans = []
# 		self._spans.append(span);
# 
# 	def addEntry(self, entry):
# 		self.spans.append(entry)
# 
# 	def __repr__(self):
# 		return '%s' % self
# 
# 	def __str__(self):
# 		return 'Entry: %s' % self._spans

#################################################################
# Parsing  with Dependency Grammars
#################################################################

# Fix this to do the arity-based depnedency grammar parsing....
_PARSE_DG_RE = re.compile(r'''^\s*                # leading whitespace
                              (\w+(?:/\w+)?)\s*    # lhs
                              (?:[-=]+>)\s*        # arrow
                              (?:(                 # rhs:
                                   "[^"]+"         # doubled-quoted terminal
                                 | '[^']+'         # single-quoted terminal
                                 | \w+(?:/\w+)?    # non-terminal
                                 | \|              # disjunction
                                 )
                                 \s*)              # trailing space
                                 *$''',            # zero or more copies
                             re.VERBOSE)
_SPLIT_DG_RE = re.compile(r'''(\w+(?:/\w+)?|[-=]+>|"[^"]+"|'[^']+'|\|)''')


class ProjectiveDependencyParser(object):

	def __init__(self, dependency_grammar):
		self._grammar = dependency_grammar

	def parse(self, tokens):
		print '\nParsing...'
		self._tokens = list(tokens)
		chart = []
		for i in range(0, len(self._tokens) + 1):
			chart.append([])
			for j in range(0, len(self._tokens) + 1):
				chart[i].append(ChartCell(i,j))
				if(i==j+1):
					chart[i][j].add(DependencySpan(i-1,i,i-1,[-1]))
				print chart[i][j]
#				print '[%d,%d]' % (i,j)
#		print chart
		for i in range(1,len(self._tokens)+1):
			for j in range(i-2,-1,-1):
				print 'cell: %d %d' % (i,j)
				for k in range(i-1,j,-1):
					for span1 in chart[k][j]._entries:
							for span2 in chart[i][k]._entries:
								for newspan in self.concatenate(span1, span2):
									print 'Adding'
									chart[i][j].add(newspan)
					print '-- comp [%d,%d] and [%d,%d]' % (k,j,i,k)

		print '\n\n\n\n\n'
#		sp1 = chart[3][0]._entries[0]
#		sp2 = chart[4][3]._entries[0]
		print '\n\n\n\n\n'

		for i in range(0, len(self._tokens) + 1):
			chart.append([])
			for j in range(0, len(self._tokens)):
				print chart[i][j]

		print '\n\n\n\n\n'

		# 
		sp1 = DependencySpan(0,0,0,[-1])
		sp2 = DependencySpan(1,1,1,[-1])
		sp3 = DependencySpan(2,2,2,[-1])
		sp4 = DependencySpan(3,3,3,[-1])
		sp5 = DependencySpan(4,4,4,[-1])
		sp1_2 = self.concatenate(sp1, sp2)[0]
		sp1_3 = self.concatenate(sp1_2, sp3)[0]
		print sp1_3
		sp4_5 = self.concatenate(sp4, sp5)[0]
		print sp4_5
		sp1_5 = self.concatenate(sp1_3, sp4_5)[0]
		print sp1_5
		# 
		# # 
		# sp1 = DependencySpan(0,1,1, [1, -1])
		# sp2 = DependencySpan(2,2,2, [-1])
		# print '\nSpans:'
		# spans = self.concatenate(sp1, sp2)
		# leftspan = spans[0]
		# sp3 = DependencySpan(3,4,4, [4,-1])
		# spans2 = self.concatenate(leftspan, sp3)
		# print spans2[0]
		print '\n\n\nParses:'
		for parse in chart[len(self._tokens)][0]._entries:
			print parse
		print 'Done.'
		
	def concatenate(self, span1, span2):
		spans = []
		if(span1._start_index == span2._start_index):
			print 'Error: Mismatched spans - replace this with thrown error'
		if(span1._start_index > span2._start_index):
			temp_span = span1
			span1 = span2
			span2 = temp_span
		# adjacent rightward covered concatenation
		# Case 1: left
		new_arcs = span1._arcs + span2._arcs
		if(self._grammar.contains(self._tokens[span1._head_index], self._tokens[span2._head_index])):
			print 'Performing rightward cover %d to %d' % (span1._head_index, span2._head_index)
			print 'newspan size %d' % len(new_arcs)
			new_arcs[span2._head_index - span1._start_index] = span1._head_index
			spans.append(DependencySpan(span1._start_index, span2._end_index, span1._head_index, new_arcs))
		# adjacent leftward covered concatenation
		new_arcs = span1._arcs + span2._arcs
		if(self._grammar.contains(self._tokens[span2._head_index], self._tokens[span1._head_index])):
			print 'performing leftward cover %d to %d' % (span2._head_index, span1._head_index)
			new_arcs[span1._head_index - span1._start_index] = span2._head_index
			spans.append(DependencySpan(span1._start_index, span2._end_index, span2._head_index, new_arcs))
		# no concatenation
		
		return spans


#################################################################
# Demos
#################################################################

def demo():
	print "Demoing..."
	prod1 = DependencyProduction('scratch', 'cats')
	prod2 = DependencyProduction('scratch', 'walls')
	prod3 = DependencyProduction('walls', 'the')
	prod4 = DependencyProduction('cats', 'the')
#	prod4 = DependencyProduction('walls', ['the'])
	prods = [prod1, prod2, prod3, prod4]
	print prod1 == prod1
	print prod1 == prod2
	dg = DependencyGrammar(prods)
	print dg
	print dg.contains('scratch', 'cats')
	print dg.contains('cats', 'scratch')
	pdp = ProjectiveDependencyParser(dg)
	pdp.parse(['the', 'cats', 'scratch', 'the', 'walls'])
	print "Done."

demo()
