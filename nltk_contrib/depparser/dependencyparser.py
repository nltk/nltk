# Natural Language Toolkit: Dependency Grammars
#
# Copyright (C) 2001-2008 NLTK Project
# Author: Jason Narad <jason.narad@gmail.com>
#
# URL: <http://nltk.org>
# For license information, see LICENSE.TXT
#


from dependencygrammar import *
from dependencygraph import *
from pprint import pformat
from sets import Set

# classify imports
#from nltk.classify.maxent import *

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
	def __init__(self, start_index, end_index, head_index, arcs, tags):
		self._start_index = start_index
		self._end_index = end_index
		self._head_index = head_index
		self._arcs = arcs
		self._hash = hash((start_index, end_index, head_index, tuple(arcs)))
		self._tags = tags

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
			str += '\n%d <- %d, %s' % (i, self._arcs[i], self._tags[i])
		return str

# **** Change comments for following methods!

	def __eq__(self, other):
		"""
		@return: true if this C{DependencyProduction} is equal to C{other}.
		@rtype: C{boolean}.
		"""
		return (isinstance(other, self.__class__) and
				self._start_index == other._start_index and
				self._end_index == other._end_index and
				self._head_index == other._head_index and
				self._arcs == other._arcs)

	def __ne__(self, other):
		return not (self == other)

	def __cmp__(self, other):
		if not isinstance(other, self.__class__): return -1
		return cmp((self._start_index, self._start_index, self._head_index), (other._end_index, other._end_index, other._head_index))

	def __hash__(self):
		return self._hash

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
		self._entries = Set([])
		
	def add(self, span):
		"""
		Appends the given span to the list of spans
		representing the chart cell's entries.
		
		@param span: The span to add.
		@type span: C{DependencySpan}.
		"""
		self._entries.add(span);

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
# Parsing  with Dependency Grammars
#################################################################


class ProjectiveDependencyParser(object):

	def __init__(self, dependency_grammar):
		self._grammar = dependency_grammar

	def parse(self, tokens):
		self._tokens = list(tokens)
		chart = []
		for i in range(0, len(self._tokens) + 1):
			chart.append([])
			for j in range(0, len(self._tokens) + 1):
				chart[i].append(ChartCell(i,j))
				if(i==j+1):
					chart[i][j].add(DependencySpan(i-1,i,i-1,[-1], ['null']))
#				print chart[i][j]
		for i in range(1,len(self._tokens)+1):
			for j in range(i-2,-1,-1):
				for k in range(i-1,j,-1):
					for span1 in chart[k][j]._entries:
							for span2 in chart[i][k]._entries:
								for newspan in self.concatenate(span1, span2):
									chart[i][j].add(newspan)
#		print 'Parses:'
		graphs = []
		trees = []
		for parse in chart[len(self._tokens)][0]._entries:
			conll_format = ""
			malt_format = ""
			for i in range(len(tokens)):
				malt_format += '%s\t%s\t%d\t%s\n' % (tokens[i], 'null', parse._arcs[i] + 1, 'null')
				conll_format += '\t%d\t%s\t%s\t%s\t%s\t%s\t%d\t%s\t%s\t%s\n' % (i+1, tokens[i], tokens[i], 'null', 'null', 'null', parse._arcs[i] + 1, 'null', '-', '-')
			dg = DepGraph().read(conll_format)
#			if(self.meets_arity(dg)):
			graphs.append(dg)
			trees.append(dg.deptree())
#		fgraphs = self.filter_parses(graphs)
		return trees
		
	# def meets_arity(self, parse):
	# 	found = True
	# 	for i in range(len(parse.nodelist)):
	# 		node = parse.nodelist[i]
	# 	#		print '%d %s %s' % (i,node['word'],node['deps'])
	# 		modlist = []
	# 		for mod in node['deps']:
	# 			modlist.append(parse.nodelist[mod]['word'])
	# 		if(modlist != [] and node['word']):
	# 			if(not self._grammar.contains_exactly(node['word'], modlist)):
	# 				found = False
	# 	return found
			

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
		new_tags = span1._tags + span2._tags
		if(self._grammar.contains(self._tokens[span1._head_index], self._tokens[span2._head_index])):
#			print 'Performing rightward cover %d to %d' % (span1._head_index, span2._head_index)
#			print 'newspan size %d' % len(new_arcs)
			new_arcs[span2._head_index - span1._start_index] = span1._head_index
			spans.append(DependencySpan(span1._start_index, span2._end_index, span1._head_index, new_arcs, new_tags))
		# adjacent leftward covered concatenation
		new_arcs = span1._arcs + span2._arcs
		if(self._grammar.contains(self._tokens[span2._head_index], self._tokens[span1._head_index])):
#			print 'performing leftward cover %d to %d' % (span2._head_index, span1._head_index)
			new_arcs[span1._head_index - span1._start_index] = span2._head_index
			spans.append(DependencySpan(span1._start_index, span2._end_index, span2._head_index, new_arcs, new_tags))
		# no concatenation
		return spans





#################################################################
# Parsing  with Probabilistic Dependency Grammars
#################################################################

class ProbabilisticProjectiveDependencyParser(object):

	def __init__(self):
		print 'new parser...'

	def parse(self, tokens):
		self._tokens = list(tokens)
		chart = []
		for i in range(0, len(self._tokens) + 1):
			chart.append([])
			for j in range(0, len(self._tokens) + 1):
				chart[i].append(ChartCell(i,j))
				if(i==j+1):
					if(self._grammar._tags.has_key(tokens[i-1])):
						for tag in self._grammar._tags[tokens[i-1]]:
							print tag
							chart[i][j].add(DependencySpan(i-1,i,i-1,[-1], [tag]))
					else:
						print 'No tag found for input token \'%s\', parse is impossible.' % tokens[i-1]
				print chart[i][j]
		for i in range(1,len(self._tokens)+1):
			for j in range(i-2,-1,-1):
				for k in range(i-1,j,-1):
					for span1 in chart[k][j]._entries:
							for span2 in chart[i][k]._entries:
								for newspan in self.concatenate(span1, span2):
									chart[i][j].add(newspan)
#		print 'Parses:'
		graphs = []
		trees = []
		for parse in chart[len(self._tokens)][0]._entries:
			conll_format = ""
			malt_format = ""
			for i in range(len(tokens)):
				malt_format += '%s\t%s\t%d\t%s\n' % (tokens[i], 'null', parse._arcs[i] + 1, 'null')
				conll_format += '\t%d\t%s\t%s\t%s\t%s\t%s\t%d\t%s\t%s\t%s\n' % (i+1, tokens[i], tokens[i], parse._tags[i], parse._tags[i], 'null', parse._arcs[i] + 1, 'null', '-', '-')
			dg = DepGraph().read(conll_format)
#			if(self.meets_arity(dg)):
			graphs.append(dg)
			print self.get_prob(dg)
			trees.append(dg.deptree())
#		fgraphs = self.filter_parses(graphs)
		return trees


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
		new_tags = span1._tags + span2._tags
		if(self._grammar.contains(self._tokens[span1._head_index], self._tokens[span2._head_index])):
#			print 'Performing rightward cover %d to %d' % (span1._head_index, span2._head_index)
#			print 'newspan size %d' % len(new_arcs)
			new_arcs[span2._head_index - span1._start_index] = span1._head_index
			spans.append(DependencySpan(span1._start_index, span2._end_index, span1._head_index, new_arcs, new_tags))
		# adjacent leftward covered concatenation
		new_arcs = span1._arcs + span2._arcs
		new_tags = span1._tags + span2._tags
		if(self._grammar.contains(self._tokens[span2._head_index], self._tokens[span1._head_index])):
#			print 'performing leftward cover %d to %d' % (span2._head_index, span1._head_index)
			new_arcs[span1._head_index - span1._start_index] = span2._head_index
			spans.append(DependencySpan(span1._start_index, span2._end_index, span2._head_index, new_arcs, new_tags))
		# no concatenation
		return spans





	def train(self, graphs):
	#	print dg.left_children(13)
#	print dg.right_children(13)
		productions = []
		events = {}
		tags = {}
		for dg in graphs:
			for node_index in range(1,len(dg.nodelist)):
				print
#		print
#		print
				children = dg.nodelist[node_index]['deps']
				nr_left_children = dg.left_children(node_index)
				nr_right_children = dg.right_children(node_index)
				nr_children = nr_left_children + nr_right_children
#		print children
				print '%s %s %s' % (children, nr_left_children, nr_right_children)
				for child_index in range(0 - (nr_left_children + 1), nr_right_children + 2):
#			print
#			print 'right_children:%s' % (nr_right_children)
#			print 'child_index:%s' % (child_index)
					head_word = dg.nodelist[node_index]['word']
					head_tag = dg.nodelist[node_index]['tag']
					if(tags.has_key(head_word)):
						tags[head_word].add(head_tag)
					else:
						tags[head_word] = Set([head_tag])
#			print 'head: (%s, %s)' % (head_word, head_tag)
			# if(array_index >= 0 and array_index < nr_children):
			# 	child = dg.nodelist[children[array_index]]['word']
			# 	child_tag = dg.nodelist[children[array_index]]['tag']
					child = 'STOP'
					child_tag = 'STOP'
					prev_word = 'START'
					prev_tag = 'START'
					if(child_index < 0):
						array_index = child_index + nr_left_children
#				print 'array_index:%s' % (array_index)
						if(array_index >= 0):
#					print 'first'
							child = dg.nodelist[children[array_index]]['word']
							child_tag = dg.nodelist[children[array_index]]['tag']
#					if(child != 'STOP'):
#				print 'curr_left: (%s, %s)' % (child, child_tag)
						if(child_index != -1):
#					print array_index
							prev_word = dg.nodelist[children[array_index + 1]]['word']
							prev_tag =  dg.nodelist[children[array_index + 1]]['tag']
#				print 'prev_left: (%s, %s)' % (prev_word, prev_tag)
						print '%d left Pr(%s, %s) | tag(%s), head_w(%s), h_tag(%s)' % (child_index, child, child_tag, prev_tag, head_word, head_tag)
						if(child != 'STOP'):
							productions.append(DependencyProduction(head_word, [child]))
						head_event = '(head (%s %s) (mods (%s, %s, %s) left))' % (child, child_tag, prev_tag, head_word, head_tag)
						mod_event = '(mods (%s, %s, %s) left))' % (prev_tag, head_word, head_tag)
						if(events.has_key(head_event)):
							events[head_event] += 1
						else:
							events[head_event] = 1
						if(events.has_key(mod_event)):
							events[mod_event] += 1
						else:
							events[mod_event] = 1
					elif(child_index > 0):
						array_index = child_index + nr_left_children - 1
#				print 'array_index:%s' % (array_index)
#				print '_child_index:%s' % (child_index)
						if(array_index < nr_children):
#					print 'first'
							child = dg.nodelist[children[array_index]]['word']
							child_tag = dg.nodelist[children[array_index]]['tag']
#				print 'curr_right: (%s, %s)' % (child, child_tag)
						if(child_index != 1):
#					print 'last'
#					print array_index
#					print children
				#					print array_index
							prev_word = dg.nodelist[children[array_index - 1]]['word']
							prev_tag =  dg.nodelist[children[array_index - 1]]['tag']
#				print 'prev_right: (%s, %s)' % (prev_word, prev_tag)
						if(child != 'STOP'):
							productions.append(DependencyProduction(head_word, [child]))
						head_event = '(head (%s %s) (mods (%s, %s, %s) right))' % (child, child_tag, prev_tag, head_word, head_tag)
						mod_event = '(mods (%s, %s, %s) right))' % (prev_tag, head_word, head_tag)
						if(events.has_key(head_event)):
							events[head_event] += 1
						else:
							events[head_event] = 1
						if(events.has_key(mod_event)):
							events[mod_event] += 1
						else:
							events[mod_event] = 1
		#		print '%d right Pr(%s, %s) | tag(%s), head_w(%s), h_tag(%s)' % (child_index, child, child_tag, prev_tag, head_word, head_tag)
		print productions
		print tags
		self._grammar = StatisticalDependencyGrammar(productions, events, tags)
		print self._grammar
		






	def get_prob(self, dg):
		prob = 1.0
		for node_index in range(1,len(dg.nodelist)):
			print
			children = dg.nodelist[node_index]['deps']
			nr_left_children = dg.left_children(node_index)
			nr_right_children = dg.right_children(node_index)
			nr_children = nr_left_children + nr_right_children
			print '%s %s %s' % (children, nr_left_children, nr_right_children)
			for child_index in range(0 - (nr_left_children + 1), nr_right_children + 2):
				head_word = dg.nodelist[node_index]['word']
				head_tag = dg.nodelist[node_index]['tag']
#			print 'head: (%s, %s)' % (head_word, head_tag)
			# if(array_index >= 0 and array_index < nr_children):
			# 	child = dg.nodelist[children[array_index]]['word']
			# 	child_tag = dg.nodelist[children[array_index]]['tag']
				child = 'STOP'
				child_tag = 'STOP'
				prev_word = 'START'
				prev_tag = 'START'
				if(child_index < 0):
					array_index = child_index + nr_left_children
					if(array_index >= 0):
						child = dg.nodelist[children[array_index]]['word']
						child_tag = dg.nodelist[children[array_index]]['tag']
#					if(child != 'STOP'):
#				print 'curr_left: (%s, %s)' % (child, child_tag)
					if(child_index != -1):
#					print array_index
						prev_word = dg.nodelist[children[array_index + 1]]['word']
						prev_tag =  dg.nodelist[children[array_index + 1]]['tag']
#				print 'prev_left: (%s, %s)' % (prev_word, prev_tag)
					print '%d left Pr(%s, %s) | tag(%s), head_w(%s), h_tag(%s)' % (child_index, child, child_tag, prev_tag, head_word, head_tag)
					head_event = '(head (%s %s) (mods (%s, %s, %s) left))' % (child, child_tag, prev_tag, head_word, head_tag)
					mod_event = '(mods (%s, %s, %s) left))' % (prev_tag, head_word, head_tag)
					h_count = self._grammar._events[head_event]
					m_count = self._grammar._events[mod_event]
					print 'hl count: %d' % h_count
					print 'ml count: %d' % m_count
					prob *= (h_count / m_count)
				elif(child_index > 0):
					array_index = child_index + nr_left_children - 1
					if(array_index < nr_children):
						child = dg.nodelist[children[array_index]]['word']
						child_tag = dg.nodelist[children[array_index]]['tag']
					if(child_index != 1):
						prev_word = dg.nodelist[children[array_index - 1]]['word']
						prev_tag =  dg.nodelist[children[array_index - 1]]['tag']
#				print 'prev_right: (%s, %s)' % (prev_word, prev_tag)
					head_event = '(head (%s %s) (mods (%s, %s, %s) right))' % (child, child_tag, prev_tag, head_word, head_tag)
					mod_event = '(mods (%s, %s, %s) right))' % (prev_tag, head_word, head_tag)
					h_count = self._grammar._events[head_event]
					m_count = self._grammar._events[mod_event]
					print 'hr count: %d' % h_count
					print 'mr count: %d' % m_count
					prob *= (h_count / m_count)
		return prob
					#		print '%d right Pr(%s, %s) | tag(%s), head_w(%s), h_tag(%s)' % (child_index, child, child_tag, prev_tag, head_word, head_tag)
		

#################################################################
# Non-Projective Parsing
#################################################################

class ProbabilisticNonprojectiveParser(object):
	
	def __init__(self):
		print 'initializing prob. nonprojective...'

	def train(self, graphs):
		print 'training...'
#		pcorpus = dict(a=1, b=1, c=1)
		corpus = [(dict(a=1,b=1,c=1), 'y'), 
				  (dict(a=1,b=1,c=1), 'x'), 
				  (dict(a=1,b=1,c=0), 'y'), 
				  (dict(a=0,b=1,c=1), 'x')]
		import nltk
		nltk.usage(nltk.ClassifierI)
		nltk.classify.NaiveBayesClassifier.train(corpus)
		# self.scores = [[[-100], [5], [1], [1], [-5, -10], [-3, -7, -4]], 
		# 			  [[-100], [-100], [11], [4], [-100], [-100]], 
		# 	  		  [[-100], [10], [-100], [5], [-100], [-100]], 
		# 			  [[-100], [9], [8], [-100], [-3], [-100]],
		# 			  [[-100], [-100], [-100], [5, -2], [-100], [-100]],
		# 			  [[-100], [-100], [-100], [-100], [-100], [-100]]]
		self.scores = [[[-100], [5], [1], [1]],
					   [[-100], [-100], [11], [4]],
					   [[-100], [10], [-100], [5]],
					   [[-100], [8], [8], [-100]]]

	def parse(self, tokens):
		# print scores[2][1]
		# print scores[2][3]
		# print scores[3][1]
		print 'parsing...\'%s\'' % (' '.join(tokens))
#		malt_string = ""g_graph
#		dg = DepGraph()
#		count = 0
#		deps = []
#		for n in range(len(tokens)):
#			deps.append(n)
#		print deps.remove(1)

		# Initialize g_graph
		g_graph = DepGraph()
		count = 0
		for token in tokens:
			count += 1
			g_graph.nodelist.append({'word':token, 'deps':[], 'rel': 'NTOP', 'address': count})
		# Fully connect non-root nodes in g_graph
		g_graph.connect_graph()
		print 'Initial G_graph:\n', g_graph
		print

		# Initialize B_Graph
		b_graph = DepGraph()
		b_graph.nodelist = []  # Remove default 'TOP' node
		print 'Initial B_Graph:\n', b_graph
		print
		
		# Initialize C_Graph
		c_graph = DepGraph()
		c_graph.nodelist = []  # Remove default 'TOP' node
		count = 0
		for token in tokens:
			count += 1
			c_graph.nodelist.append({'word':token, 'deps':[], 'rel': 'NTOP', 'address': count})
		print 'Initial C_Graph:\n', c_graph
		
		nr_vertices = len(tokens)
		unvisited_vertices = []
		for vertex in c_graph.nodelist:
			unvisited_vertices.append(vertex['address'])
		while(len(unvisited_vertices) > 0):
			# Mark v_i as unvisited
			current_vertex = unvisited_vertices.pop(0)
			print 'current_vertex:', current_vertex
			# Get corresponding node n_i to vertex v_i
			current_node = g_graph.get_by_address(current_vertex)
			print 'current_node:', current_node
			# Get highest-scoring incoming arc to node n_i
			best_in_arc = self.best_incoming_arc(current_vertex)
			print 'best_in_arc', best_in_arc

			# Update B = B U b
			for new_vertex in [current_vertex, best_in_arc]:
				if(not b_graph.contains_address(new_vertex)):
					word_label = new_vertex - 1
					if(new_vertex - 1 > len(tokens) ):
						word_label = 'TEMP'
					b_graph.nodelist.append({'word':word_label, 'deps':[], 'rel': 'NTOP', 'address': new_vertex})
			b_graph.add_arc(best_in_arc, current_vertex)

			# Check for cycles in B_Graph
			print
			print 'Checking B_graph for cycles..\n', b_graph
			cycle = b_graph.contains_cycle()
			if(cycle):
				print 'Cycle found:', cycle
				
				# New node v_n+1
				new_cnode = {'word': 'NONE', 'deps':[], 'rel': 'NTOP', 'address': nr_vertices + 1}
				# All Children of cycle are children of new_node in C_Graph
				cycle.sort()
				new_cnode['deps'] = cycle
				c_graph.nodelist.append(new_cnode)
				
				# Update scoring to reflect collapsed cycle in G_Graph
#				subtract_from = []  # to store the list of global updates to be made
				print self.scores
				for cycle_node_index in cycle:
					best_arc = self.best_incoming_arc(cycle_node_index)
					subtract_score = max(self.scores[best_arc][cycle_node_index])
					for g_node in g_graph.nodelist:
						if(cycle_node_index in g_node['deps']):
							print 'Should update: ', g_node['address'], '-->', cycle_node_index, ' - ', subtract_score
							e_scores = self.scores[g_node['address']][cycle_node_index]
							for i in range(len(e_scores)):
								e_scores[i] -= subtract_score
							self.scores[g_node['address']][cycle_node_index] = e_scores
				print 'Updated scores\n',self.scores

				# Collapse all cycle nodes into v_n+1 in G_Graph
				new_gnode = {'word': 'NONE', 'deps':[], 'rel': 'NTOP', 'address': nr_vertices + 1}
				for cycle_node_index in cycle:
					g_graph.remove_by_address(cycle_node_index)
				g_graph.nodelist.append(new_gnode)
				g_graph.redirect_arcs(cycle, nr_vertices + 1)
				
				# Redirect the score arcs
				# initialize to scores[i] size
				new_out_scores = []
				for i in range(len(self.scores[0])):
					new_out_scores.append([])
				for i in range(len(self.scores)):
					# Empty out the arcs between the collapsed nodes
					if(i in cycle):
						for cycle_node_index in cycle:
							self.scores[i][cycle_node_index] = []
						for j in range(len(self.scores[i])):
							new_out_scores[j] += self.scores[i][j]
					# Add pointers from old non-cyclic nodes to the new node
					new_in_scores = []
					for cycle_node_index in cycle:
						new_in_scores += self.scores[i][cycle_node_index]
					self.scores[i].append(new_in_scores)
				# Add pointers out from the new node to old nodes
				new_out_scores.append([])
				# Clean out all cyclic node out scores
				for i in range(len(self.scores)):
					if(i in cycle):
						for j in range(len(self.scores[i])):
							self.scores[i][j] = []
				print 'new out scores:', new_out_scores
				self.scores.append(new_out_scores)
				print 'Redirected scores\n', self.scores
				
				# for cycle_node_index in cycle:
				# 	for i in g_graph.nodelist
				# 	self.[index][nr_vertices +1] = self.scores[index][cycle_node_index]
				# 	self.[index][cycle_node_index] = -100
				

				# Add v_n+1 to unvisited vertices list
				unvisited_vertices.append(nr_vertices + 1)

				# Update nr_vertices
				nr_vertices += 1
				
				# B_Graph = B_Graph - C_Graph
				for c_node in c_graph.nodelist:
					b_graph.remove_by_address(c_node['address'])

			print
			print 'Iteration complete.'
			print 'G = \n', g_graph
			print 'B = \n', b_graph
			print 'C = \n', c_graph
			print			


	def best_incoming_arc(self, node_index):
		print 'Finding best incoming arc to node ' , node_index

		max_index = -1
		max_score = -101
		for index in range(len(self.scores)):
			for j in range(len(self.scores[index][node_index])):
#				print index, j
				score = self.scores[index][node_index][j]
				if(score > max_score):
					max_score = score
					max_index = index
		return max_index

#################################################################
# Demos
#################################################################

def demo():
#	projective_rule_parse_demo()
#	arity_parse_demo()
#	projective_prob_parse_demo()
    nonprojective_prob_parse_demo()

def nonprojective_prob_parse_demo():
	# infile = open('conll_sample.txt',"r")
	graphs = []
	# entry = ""
	# for line in infile.readlines():
	# 	if(line == '\n' and entry != ""):
	# 		graphs.append(DepGraph().read('\n' + entry))
	# 		entry = ''
	# 	else:
	# 		entry += '\t' + line
	npp = ProbabilisticNonprojectiveParser()
	npp.train(graphs)
	npp.parse(['v1', 'v2', 'v3'])

def projective_rule_parse_demo():
	"""
	A demonstration showing the creation and use of a 
	C{DependencyGrammar} to perform a projective dependency 
	parse.
	"""
	grammar = parse_dependency_grammar("""
	'scratch' -> 'cats' | 'walls'
	'walls' -> 'the'
	'cats' -> 'the'
	""")
	print grammar
	pdp = ProjectiveDependencyParser(grammar)
	trees = pdp.parse(['the', 'cats', 'scratch', 'the', 'walls'])
	for tree in trees:
		print tree
	
def arity_parse_demo():
	"""
	A demonstration showing the creation of a C{DependencyGrammar} 
	in which a specific number of modifiers is listed for a given 
	head.  This can further constrain the number of possible parses
	created by a C{ProjectiveDependencyParser}.
	"""
	print
	print 'A grammar with no arity constraints. Each DependencProduction'
	print 'specifies a relationship between one head word and only one'
	print 'modifier word.:'
	grammar = parse_dependency_grammar("""
	'fell' -> 'price' | 'stock'
	'price' -> 'of' | 'the'
	'of' -> 'stock'
	'stock' -> 'the'
	""")
	print grammar
	
	print
	print 'For the sentence \'The price of the stock fell\', this grammar'
	print 'will produce the following three parses:'	
	pdp = ProjectiveDependencyParser(grammar)
	trees = pdp.parse(['the', 'price', 'of', 'the', 'stock', 'fell'])	
	for tree in trees:
		print tree

	print
	print 'Comparatively, the following grammar contains a '
	print 'C{DependencyProduction} that specifies a relationship'
	print 'between the one head word, \'price\', and two modifier'
	print 'words, \'of\' and \'the\'.'
	grammar = parse_dependency_grammar("""
	'fell' -> 'price' | 'stock'
	'price' -> 'of' 'the'
	'of' -> 'stock'
	'stock' -> 'the'
	""")
	print grammar
	
	print
	print 'This constrains the number of possible parses to just one:' # unimplemented, soon to replace
	pdp = ProjectiveDependencyParser(grammar)
	trees = pdp.parse(['the', 'price', 'of', 'the', 'stock', 'fell'])
	for tree in trees:
		print tree

def projective_prob_parse_demo():
	print
	print 'new demo...'
	print 'Mass conll_read demo...'
	infile = open('conll_sample.txt',"r")
	graphs = []
	entry = ""
	for line in infile.readlines():
		if(line == '\n' and entry != ""):
			graphs.append(DepGraph().read('\n' + entry))
			entry = ''
		else:
			entry += '\t' + line
	ppdp = ProbabilisticProjectiveDependencyParser()
	ppdp.train(graphs)
	trees = ppdp.parse(['Cathy', 'zie', 'hen', 'wild', 'zwaai', '.'])
	print 'Parses:'
	for tree in trees:
		print tree
# def grab_events(tree, head):
# 	if isinstance(tree, str):
# 		print '(%s %s)' % (head, tree)
# 	else:
# 		print '(%s %s)' % (head, tree.node)
# 		for child in tree:
# 			grab_events(child, tree.node)


demo()
