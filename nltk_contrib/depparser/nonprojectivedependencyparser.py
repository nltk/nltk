# Natural Language Toolkit: Dependency Grammars
#
# Copyright (C) 2001-2008 NLTK Project
# Author: Jason Narad <jason.narad@gmail.com>
#
# URL: <http://nltk.org>
# For license information, see LICENSE.TXT
#

import math

from dependencygrammar import *
from dependencygraph import *
from pprint import pformat

# classify imports
#from nltk.classify.maxent import *


#################################################################
# Non-Projective Parsing
#################################################################

class ProbabilisticNonprojectiveParser(object):
	
	def __init__(self):
		print 'initializing prob. nonprojective...'

	def train(self, graphs):
		print 'training...'
		corpus = []
		for graph in graphs:
			for head_node in graph.nodelist:
				for child_index in range(len(graph.nodelist)):
#				for dep_index in head_node['deps']:
					child_node = graph.get_by_address(child_index)
					if(child_index in head_node['deps']):
						label = "T"
					else:
						label = "F"
					features = [head_node['word'], head_node['tag'], child_node['word'], child_node['tag']]
					corpus.append((dict(a=head_node['word'],b=head_node['tag'],c=child_node['word'],d=child_node['tag']), label))
#					print features
#		pcorpus = dict(a=1, b=1, c=1)
#		tcorpus = [(dict(a='zie',b='V',c='Cathy',d='N'), 'T'),
#				   (dict(a='hoor',b='V',c=''))]
		# corpus = [(dict(a=1,b=1,c=1), 'y'), 
		# 		  (dict(a=1,b=1,c=1), 'x'), 
		# 		  (dict(a=1,b=1,c=0), 'y'), 
		# 		  (dict(a=0,b=1,c=1), 'x')]
		test = [(dict(a='zie',b='V',c='Cathy',d='N')),
				(dict(a='Cathy',b='N',c=None,d='TOP'))]
		import nltk
		nltk.usage(nltk.ClassifierI)
#		print corpus
		self.classifier = nltk.classify.NaiveBayesClassifier.train(corpus)
#		print classifier.batch_classify(test)

					
					
	def assign_scores(self, graph):
		print 'Assigning scoring from classifier...'
		edges = []
		print edges
		print len(graph.nodelist)
		print graph
		for i in range(len(graph.nodelist)):
			for j in range(len(graph.nodelist)):
#				print i,j
				head_node = graph.get_by_address(i)
				child_node = graph.get_by_address(j)
				edges.append((dict(a=head_node['word'],b=head_node['tag'],c=child_node['word'],d=child_node['tag'])))
		print edges
		edge_scores = []
		row = []
		count = 0
		for pdist in self.classifier.batch_prob_classify(edges):
			print '%.4f %.4f' % (pdist.prob('T'), pdist.prob('F'))
			row.append(math.log(pdist.prob("T")))
#			row.append(pdist.prob("T"))
			count += 1
			if(count == len(graph.nodelist)):
				edge_scores.append(row)
				row = []
				count = 0
		print edge_scores

	
	# def test_parse(self, tokens, tags):  # tags are just temp. provided
	# 	print 'Parsing...\'%s\'' % (' '.join(tokens))
	# 
	# 	# Initialize test g_graph
	# 	g_graph = DepGraph()
	# 	count = 0
	# 	for i in range(len(tokens)):
	# 		count += 1
	# 		g_graph.nodelist.append({'word':tokens[i], 'tag':tags[i], 'deps':[], 'rel': 'NTOP', 'address': count})
	# 
	# 	# Initialize edge weights - here just explicitly assigned
	# 	self.scores = [[[-100], [5], [1], [1]],
	# 				   [[-100], [-100], [11], [4]],
	# 				   [[-100], [10], [-100], [5]],
	# 				   [[-100], [8], [8], [-100]]]
	# 
	# 
	# 	
	# 	
	
	def initialize_edge_scores(self, graph):
		self.scores = [[[], [5],  [1],  [1]],
					   [[], [],   [11], [4]],
					   [[], [10], [],   [5]],
					   [[], [8],  [8],  []]]
			
	def collapse_nodes(self, new_node, cycle_path, g_graph, b_graph, c_graph):
		print 'Collapsing nodes...'
		# Collapse all cycle nodes into v_n+1 in G_Graph
		for cycle_node_index in cycle_path:
			g_graph.remove_by_address(cycle_node_index)
		g_graph.nodelist.append(new_node)
		g_graph.redirect_arcs(cycle_path, new_node['address'])
		#

	def update_edge_scores(self, new_node, cycle_path):
		print 'cycle', cycle_path
		cycle_path = self.compute_original_indexes(cycle_path)
		print 'old cycle ', cycle_path
		print 'Prior to update:\n', self.scores
		for i, row in enumerate(self.scores):
			for j, column in enumerate(self.scores[i]):
				if(j in cycle_path and not i in cycle_path and len(self.scores[i][j]) > 0):
					new_vals = []
					subtract_val = self.compute_max_subtract_score(j, cycle_path)
					print self.scores[i][j], ' - ', subtract_val
					for cur_val in self.scores[i][j]:
						new_vals.append(cur_val - subtract_val)
					self.scores[i][j] = new_vals
		for i, row in enumerate(self.scores):
			for j, cell in enumerate(self.scores[i]):
				if(i in cycle_path and j in cycle_path):
					self.scores[i][j] = []
		print 'After update:\n', self.scores

	def compute_original_indexes(self, new_indexes):
		swapped = True
		while(swapped):
			originals = []
			swapped = False
			for new_index in new_indexes:
				if(self.inner_nodes.has_key(new_index)):
					for old_val in self.inner_nodes[new_index]:
						if(not old_val in originals):
							originals.append(old_val)
							swapped = True
				else:
					originals.append(new_index)
			new_indexes = originals
		return new_indexes
		
	def compute_max_subtract_score(self, column_index, cycle_indexes):
		max_score = -100000
		for row_index in cycle_indexes:
			for subtract_val in self.scores[row_index][column_index]:
				if(subtract_val > max_score):
					max_score = subtract_val
		return max_score

# 	def update_edge_scores(self, new_node, cycle_path):
# 		print self.scores
# 		print cycle_path.pop() # remove the duplicate value from the closed path
# 		# Updates the scores to reflect the collapse
# 		for i, row in enumerate(self.scores):
# 			for j, column in enumerate(self.scores[i]):
# 				if(j in cycle_path and not i in cycle_path and len(self.scores[i][j]) > 0):
# 					# Subtract cell[k][j] from cell[i][j] where k is in the cycle path
# 					for k in cycle_path:						 
# #					for k, inner_row in enumerate(self.scores):
# 						if(len(self.scores[k][j]) > 0):
# 							new_vals = []
# 							for val in self.scores[i][j]:
# 								print 'Updating: [%d][%d] %s - [%d][%d] %s , %s' % (i, j, val, k, j, self.scores[k][j], sum(self.scores[k][j]))	
# 								new_vals.append(val - sum(self.scores[k][j]))
# 							self.scores[i][j] = new_vals
# 		print self.scores
# 		print
# 		# Remove edges between cycle nodes
# 		for i, row in enumerate(self.scores):
# 			for j, cell in enumerate(self.scores[i]):
# 				if(i in cycle_path and j in cycle_path):
# 					self.scores[i][j] = []
# 		# Add edges to the new node
# 		for i, row in enumerate(self.scores):
# 			new_edges = []
# 			for j, cell in enumerate(self.scores[i]):
# 				if(j in cycle_path):
# 					new_edges += self.scores[i][j]
# 			self.scores[i].append(new_edges)
# 		# Add edges from the new node
# #		new_out_edges = [[], [], [], [], []]  # replace with smart initialize
# 		new_out_edges = []
# 		while(len(new_out_edges) < len(self.scores[0])):
# 			new_out_edges.append([])
# 		for i, row in enumerate(self.scores):
# 			if(i in cycle_path):
# 				for j, cell in enumerate(self.scores[i]):
# #					print j, '-', self.scores[i][j]
# 					new_out_edges[j] += self.scores[i][j]
# 		self.scores.append(new_out_edges)
# 		print self.scores
# 		print
					
				# print j, self.scores[i]
	def best_incoming_arc(self, node_index):
		print self.scores[0]
		originals = self.compute_original_indexes([node_index])
		print 'originals:', originals
		max_arc = None
		max_score = None
		for row_index in range(len(self.scores)):
			for col_index in range(len(self.scores[row_index])):
				if(col_index in originals and self.scores[row_index][col_index] > max_score):
					max_score = self.scores[row_index][col_index]
					max_arc = row_index
					print row_index, ',', col_index
		print max_score
		for key in self.inner_nodes:
			replaced_nodes = self.inner_nodes[key]
			if(max_arc in replaced_nodes):
				return key
		return max_arc
		
	def original_best_arc(self, node_index):
		originals = self.compute_original_indexes([node_index])
		max_arc = None
		max_score = None
		max_orig = None
		for row_index in range(len(self.scores)):
			for col_index in range(len(self.scores[row_index])):
				if(col_index in originals and self.scores[row_index][col_index] > max_score):
					max_score = self.scores[row_index][col_index]
					max_arc = row_index
					max_orig = col_index
		# for key in self.inner_nodes:
		# 		replaced_nodes = self.inner_nodes[key]
		# 		if(max_arc in replaced_nodes):
		# 			return key
		return [max_arc, max_orig]
			
				# 	def best_incoming_arc(self, node_index):
				# 		print 'Finding best incoming arc to node ' , node_index
				# 
				# 		max_index = -1
				# 		max_score = -101
				# 		for index in range(len(self.scores)):
				# 			for j in range(len(self.scores[index][node_index])):
				# #				print index, j
				# 				score = self.scores[index][node_index][j]
				# 				if(score > max_score and not self.replaced_by.has_key(index)):
				# 					max_score = score
				# 					max_index = index
				# 		return max_index
						
						
	def parse(self, tokens, tags):
		self.inner_nodes = {}
		# Initialize g_graph
		g_graph = DepGraph()
		for index, token in enumerate(tokens):
			g_graph.nodelist.append({'word':token, 'deps':[], 'rel':'NTOP', 'address':index+1})
		# Fully connect non-root nodes in g_graph
		g_graph.connect_graph()
		original_graph = DepGraph()
		for index, token in enumerate(tokens):
			original_graph.nodelist.append({'word':token, 'deps':[], 'rel':'NTOP', 'address':index+1})

		# Initialize b_graph
		b_graph = DepGraph()
		b_graph.nodelist = []
		# Initialize c_graph
		c_graph = DepGraph()
		c_graph.nodelist = []
		for index, token in enumerate(tokens):
			c_graph.nodelist.append({'word':token, 'deps':[], 'rel':'NTOP', 'address':index+1})
		# Assign initial scores to g_graph edges
		self.initialize_edge_scores(g_graph)
		# Initialize a list of unvisited vertices (by node address)
		unvisited_vertices = []
		for vertex in c_graph.nodelist:
			unvisited_vertices.append(vertex['address'])
		# Iterate over unvisited vertices
		nr_vertices = len(tokens)
		betas = {}
		while(len(unvisited_vertices) > 0):
			# Mark current node as visited
			current_vertex = unvisited_vertices.pop(0)
#			print 'current_vertex:', current_vertex
			# Get corresponding node n_i to vertex v_i
			current_node = g_graph.get_by_address(current_vertex)
#			print 'current_node:', current_node
			# Get best in-edge node b for current node
			best_in_edge = self.best_incoming_arc(current_vertex)
			betas[current_vertex] = self.original_best_arc(current_vertex)
			print 'best in arc: ', best_in_edge, ' --> ', current_vertex
			# b_graph = Union(b_graph, b)
			for new_vertex in [current_vertex, best_in_edge]:
				b_graph.add_node({'word':'TEMP', 'deps':[], 'rel': 'NTOP', 'address': new_vertex})
			b_graph.add_arc(best_in_edge, current_vertex)
			# Beta(current node) = b  - stored for parse recovery
			# If b_graph contains a cycle, collapse it
			cycle_path = b_graph.contains_cycle()
			if(cycle_path):
			# Create a new node v_n+1 with address = len(nodes) + 1
				new_node = {'word': 'NONE', 'deps':[], 'rel': 'NTOP', 'address': nr_vertices + 1}
			# c_graph = Union(c_graph, v_n+1)
				c_graph.add_node(new_node)
			# Collapse all nodes in cycle C into v_n+1
				self.update_edge_scores(new_node, cycle_path)
				self.collapse_nodes(new_node, cycle_path, g_graph, b_graph, c_graph)
				for cycle_index in cycle_path:
					c_graph.add_arc(new_node['address'], cycle_index)
#					self.replaced_by[cycle_index] = new_node['address']

				self.inner_nodes[new_node['address']] = cycle_path

			# Add v_n+1 to list of unvisited vertices
				unvisited_vertices.insert(0, nr_vertices + 1)				
			# increment # of nodes counter
				nr_vertices += 1
			# Remove cycle nodes from b_graph; B = B - cycle c
				for cycle_node_address in cycle_path:
					b_graph.remove_by_address(cycle_node_address)
			print 'g_graph:\n', g_graph
			print
			print 'b_graph:\n', b_graph
			print
			print 'c_graph:\n', c_graph
			print
			print 'Betas:\n', betas
			print 'replaced nodes', self.inner_nodes
			print
		#Recover parse tree
		print 'Final scores:\n', self.scores
		print 'Recovering parse...'
		for i in range(len(tokens) + 1, nr_vertices + 1):
			betas[betas[i][1]] = betas[i]
		print betas
		new_graph = DepGraph()
		for node in original_graph.nodelist:
			node['deps'] = []
		for i in range(1, len(tokens) + 1):
			print i, betas[i]
			original_graph.add_arc(betas[i][0], betas[i][1])
		print original_graph
		print 'Done.'



	def test(self):
		self.inner_nodes = {}
		self.update_edge_scores({'word': 'NONE', 'deps':[], 'rel': 'NTOP', 'address': 4}, [1,2])
		self.inner_nodes[4] = [1,2]
		self.update_edge_scores({'word': 'NONE', 'deps':[], 'rel': 'NTOP', 'address': 5}, [4,3])
		self.inner_nodes[5] = [1,2,3,4]
		


# 
# 	def test_parse(self, tokens, tags):  # tags are just temp. provided
# 		print 'parsing...\'%s\'' % (' '.join(tokens))		
# 		tokens = ['v1', 'v2', 'v3']  # for testing, to match KH paper
# 		
# 		# Initialize g_graph
# 		g_graph = DepGraph()
# 		for index, token in enumerate(tokens):
# 				g_graph.nodelist.append({'word':token, 'deps':[], 'rel': 'NTOP', 'address': index + 1})
# 		
# 		# Fully connect non-root nodes in g_graph
# 		g_graph.connect_graph()
# 		print 'Initial G_graph:\n', g_graph
# 		print
# 
# 		# Initialize B_Graph
# 		b_graph = DepGraph()
# 		b_graph.nodelist = []  # Remove default 'TOP' node
# 		print 'Initial B_Graph:\n', b_graph
# 		print
# 		
# 		# Initialize C_Graph
# 		c_graph = DepGraph()
# 		c_graph.nodelist = []  # Remove default 'TOP' node
# 		count = 0
# 		for token in tokens:
# 			count += 1
# 			c_graph.nodelist.append({'word':token, 'deps':[], 'rel': 'NTOP', 'address': count})
# 		print 'Initial C_Graph:\n', c_graph
# 		
# 		# Initialize edge weights - here just explicitly assigned
# 		self.scores = [[[-100], [5], [1], [1]],
# 					   [[-100], [-100], [11], [4]],
# 					   [[-100], [10], [-100], [5]],
# 					   [[-100], [8], [8], [-100]]]
# 
# 
# 		nr_vertices = len(tokens)
# 		unvisited_vertices = []
# 		for vertex in c_graph.nodelist:
# 			unvisited_vertices.append(vertex['address'])
# 		while(len(unvisited_vertices) > 0):
# 			# Mark v_i as unvisited
# 			current_vertex = unvisited_vertices.pop(0)
# 			print 'current_vertex:', current_vertex
# 			# Get corresponding node n_i to vertex v_i
# 			current_node = g_graph.get_by_address(current_vertex)
# 			print 'current_node:', current_node
# 			# Get highest-scoring incoming arc to node n_i
# 			best_in_arc = self.best_incoming_arc(current_vertex)
# 			print 'best_in_arc', best_in_arc
# 
# 			# Update B = B U b
# 			for new_vertex in [current_vertex, best_in_arc]:
# 				if(not b_graph.contains_address(new_vertex)):
# 					word_label = new_vertex - 1
# 					if(new_vertex - 1 > len(tokens) ):
# 						word_label = 'TEMP'
# 					b_graph.nodelist.append({'word':word_label, 'deps':[], 'rel': 'NTOP', 'address': new_vertex})
# 			b_graph.add_arc(best_in_arc, current_vertex)
# 
# 			# Check for cycles in B_Graph
# 			print
# 			print 'Checking B_graph for cycles..\n', b_graph
# 			cycle = b_graph.contains_cycle()
# 			if(cycle):
# 				print 'Cycle found:', cycle
# 				
# 				# New node v_n+1
# 				new_cnode = {'word': 'NONE', 'deps':[], 'rel': 'NTOP', 'address': nr_vertices + 1}
# 				# All Children of cycle are children of new_node in C_Graph
# 				cycle.sort()
# 				new_cnode['deps'] = cycle
# 				c_graph.nodelist.append(new_cnode)
# 				
# 				# Update scoring to reflect collapsed cycle in G_Graph
# #				subtract_from = []  # to store the list of global updates to be made
# 				print self.scores
# 				for cycle_node_index in cycle:
# 					best_arc = self.best_incoming_arc(cycle_node_index)
# #					subtract_score = max(self.scores[best_arc][cycle_node_index])
# 					subtract_score = self.best_incoming_score(cycle_node_index)
# 					for g_node in g_graph.nodelist:
# 						if(cycle_node_index in g_node['deps']):
# 							print 'Should update: ', g_node['address'], '-->', cycle_node_index, ' from ', self.scores[g_node['address']][cycle_node_index], ' - ', subtract_score
# 							e_scores = self.scores[g_node['address']][cycle_node_index]
# 							for i in range(len(e_scores)):
# 								e_scores[i] -= subtract_score
# 							self.scores[g_node['address']][cycle_node_index] = e_scores
# 				print 'Updated scores\n',self.scores
# 
# 				# Collapse all cycle nodes into v_n+1 in G_Graph
# 				new_gnode = {'word': 'NONE', 'deps':[], 'rel': 'NTOP', 'address': nr_vertices + 1}
# 				for cycle_node_index in cycle:
# 					g_graph.remove_by_address(cycle_node_index)
# 				g_graph.nodelist.append(new_gnode)
# 				g_graph.redirect_arcs(cycle, nr_vertices + 1)
# 				
# 				# Redirect the score arcs
# 				# initialize to scores[i] size
# 				new_out_scores = []
# 				for i in range(len(self.scores[0])):
# 					new_out_scores.append([])
# 				for i in range(len(self.scores)):
# 					# Empty out the arcs between the collapsed nodes
# 					if(i in cycle):
# 						for cycle_node_index in cycle:
# 							self.scores[i][cycle_node_index] = []
# 						for j in range(len(self.scores[i])):
# 							new_out_scores[j] += self.scores[i][j]
# 					# Add pointers from old non-cyclic nodes to the new node
# 					new_in_scores = []
# 					for cycle_node_index in cycle:
# 						new_in_scores += self.scores[i][cycle_node_index]
# 					self.scores[i].append(new_in_scores)
# 				# Add pointers out from the new node to old nodes
# 				new_out_scores.append([])
# 				# Clean out all cyclic node out scores
# 				for i in range(len(self.scores)):
# 					if(i in cycle):
# 						for j in range(len(self.scores[i])):
# 							self.scores[i][j] = []
# 				
# 				# zero out arcs from non-cyclic to collapsed nodes
# 				for i in range(len(self.scores)):
# 					for cycle_node_index in cycle:
# 						self.scores[i][cycle_node_index] = []
# 									
# 				print 'new out scores:', new_out_scores
# 				self.scores.append(new_out_scores)
# 				print 'Redirected scores\n', self.scores
# 				
# 
# 						
# 				# 	self.[index][nr_vertices +1] = self.scores[index][cycle_node_index]
# 				# 	self.[index][cycle_node_index] = -100
# 				
# 
# 				# Add v_n+1 to unvisited vertices list
# 				unvisited_vertices.insert(0, nr_vertices + 1)
# 
# 				# Update nr_vertices
# 				nr_vertices += 1
# 				
# 				# B_Graph = B_Graph - C_Graph
# 				for c_node in c_graph.nodelist:
# 					b_graph.remove_by_address(c_node['address'])
# 
# 			print
# 			print 'Iteration complete.'
# 			print 'G = \n', g_graph
# 			print 'B = \n', b_graph
# 			print 'C = \n', c_graph
# 			print self.scores
# 			print			


			# 	def parse(self, tokens, tags):  # tags are just temp. provided
			# 		print 'parsing...\'%s\'' % (' '.join(tokens))		
			# 		tokens = ['v1', 'v2', 'v3']  # for testing, to match KH paper
			# 
			# 		# Initialize g_graph
			# 		g_graph = DepGraph()
			# 		count = 0
			# 		for token in tokens:
			# 			count += 1
			# 			g_graph.nodelist.append({'word':token, 'deps':[], 'rel': 'NTOP', 'address': count})
			# 		# Fully connect non-root nodes in g_graph
			# 		g_graph.connect_graph()
			# 		print 'Initial G_graph:\n', g_graph
			# 		print
			# 
			# 		# Initialize B_Graph
			# 		b_graph = DepGraph()
			# 		b_graph.nodelist = []  # Remove default 'TOP' node
			# 		print 'Initial B_Graph:\n', b_graph
			# 		print
			# 
			# 		# Initialize C_Graph
			# 		c_graph = DepGraph()
			# 		c_graph.nodelist = []  # Remove default 'TOP' node
			# 		count = 0
			# 		for token in tokens:
			# 			count += 1
			# 			c_graph.nodelist.append({'word':token, 'deps':[], 'rel': 'NTOP', 'address': count})
			# 		print 'Initial C_Graph:\n', c_graph
			# 
			# 		nr_vertices = len(tokens)
			# 		unvisited_vertices = []
			# 		for vertex in c_graph.nodelist:
			# 			unvisited_vertices.append(vertex['address'])
			# 		while(len(unvisited_vertices) > 0):
			# 			# Mark v_i as unvisited
			# 			current_vertex = unvisited_vertices.pop(0)
			# 			print 'current_vertex:', current_vertex
			# 			# Get corresponding node n_i to vertex v_i
			# 			current_node = g_graph.get_by_address(current_vertex)
			# 			print 'current_node:', current_node
			# 			# Get highest-scoring incoming arc to node n_i
			# 			best_in_arc = self.best_incoming_arc(current_vertex)
			# 			print 'best_in_arc', best_in_arc
			# 
			# 			# Update B = B U b
			# 			for new_vertex in [current_vertex, best_in_arc]:
			# 				if(not b_graph.contains_address(new_vertex)):
			# 					word_label = new_vertex - 1
			# 					if(new_vertex - 1 > len(tokens) ):
			# 						word_label = 'TEMP'
			# 					b_graph.nodelist.append({'word':word_label, 'deps':[], 'rel': 'NTOP', 'address': new_vertex})
			# 			b_graph.add_arc(best_in_arc, current_vertex)
			# 
			# 			# Check for cycles in B_Graph
			# 			print
			# 			print 'Checking B_graph for cycles..\n', b_graph
			# 			cycle = b_graph.contains_cycle()
			# 			if(cycle):
			# 				print 'Cycle found:', cycle
			# 
			# 				# New node v_n+1
			# 				new_cnode = {'word': 'NONE', 'deps':[], 'rel': 'NTOP', 'address': nr_vertices + 1}
			# 				# All Children of cycle are children of new_node in C_Graph
			# 				cycle.sort()
			# 				new_cnode['deps'] = cycle
			# 				c_graph.nodelist.append(new_cnode)
			# 
			# 				# Update scoring to reflect collapsed cycle in G_Graph
			# #				subtract_from = []  # to store the list of global updates to be made
			# 				print self.scores
			# 				for cycle_node_index in cycle:
			# 					best_arc = self.best_incoming_arc(cycle_node_index)
			# #					subtract_score = max(self.scores[best_arc][cycle_node_index])
			# 					subtract_score = self.best_incoming_score(cycle_node_index)
			# 					for g_node in g_graph.nodelist:
			# 						if(cycle_node_index in g_node['deps']):
			# 							print 'Should update: ', g_node['address'], '-->', cycle_node_index, ' from ', self.scores[g_node['address']][cycle_node_index], ' - ', subtract_score
			# 							e_scores = self.scores[g_node['address']][cycle_node_index]
			# 							for i in range(len(e_scores)):
			# 								e_scores[i] -= subtract_score
			# 							self.scores[g_node['address']][cycle_node_index] = e_scores
			# 				print 'Updated scores\n',self.scores
			# 
			# 				# Collapse all cycle nodes into v_n+1 in G_Graph
			# 				new_gnode = {'word': 'NONE', 'deps':[], 'rel': 'NTOP', 'address': nr_vertices + 1}
			# 				for cycle_node_index in cycle:
			# 					g_graph.remove_by_address(cycle_node_index)
			# 				g_graph.nodelist.append(new_gnode)
			# 				g_graph.redirect_arcs(cycle, nr_vertices + 1)
			# 
			# 				# Redirect the score arcs
			# 				# initialize to scores[i] size
			# 				new_out_scores = []
			# 				for i in range(len(self.scores[0])):
			# 					new_out_scores.append([])
			# 				for i in range(len(self.scores)):
			# 					# Empty out the arcs between the collapsed nodes
			# 					if(i in cycle):
			# 						for cycle_node_index in cycle:
			# 							self.scores[i][cycle_node_index] = []
			# 						for j in range(len(self.scores[i])):
			# 							new_out_scores[j] += self.scores[i][j]
			# 					# Add pointers from old non-cyclic nodes to the new node
			# 					new_in_scores = []
			# 					for cycle_node_index in cycle:
			# 						new_in_scores += self.scores[i][cycle_node_index]
			# 					self.scores[i].append(new_in_scores)
			# 				# Add pointers out from the new node to old nodes
			# 				new_out_scores.append([])
			# 				# Clean out all cyclic node out scores
			# 				for i in range(len(self.scores)):
			# 					if(i in cycle):
			# 						for j in range(len(self.scores[i])):
			# 							self.scores[i][j] = []
			# 
			# 				# zero out arcs from non-cyclic to collapsed nodes
			# 				for i in range(len(self.scores)):
			# 					for cycle_node_index in cycle:
			# 						self.scores[i][cycle_node_index] = []
			# 
			# 				print 'new out scores:', new_out_scores
			# 				self.scores.append(new_out_scores)
			# 				print 'Redirected scores\n', self.scores
			# 
			# 
			# 
			# 				# 	self.[index][nr_vertices +1] = self.scores[index][cycle_node_index]
			# 				# 	self.[index][cycle_node_index] = -100
			# 
			# 
			# 				# Add v_n+1 to unvisited vertices list
			# 				unvisited_vertices.insert(0, nr_vertices + 1)
			# 
			# 				# Update nr_vertices
			# 				nr_vertices += 1
			# 
			# 				# B_Graph = B_Graph - C_Graph
			# 				for c_node in c_graph.nodelist:
			# 					b_graph.remove_by_address(c_node['address'])
			# 
			# 			print
			# 			print 'Iteration complete.'
			# 			print 'G = \n', g_graph
			# 			print 'B = \n', b_graph
			# 			print 'C = \n', c_graph
			# 			print self.scores
			# 			print			



# 	def best_incoming_arc(self, node_index):
# 		print 'Finding best incoming arc to node ' , node_index
# 
# 		max_index = -1
# 		max_score = -101
# 		for index in range(len(self.scores)):
# 			for j in range(len(self.scores[index][node_index])):
# #				print index, j
# 				score = self.scores[index][node_index][j]
# 				if(score > max_score and not self.replaced_by.has_key(index)):
# 					max_score = score
# 					max_index = index
# 		return max_index
# 
# # soon to be replaced....
# 	def best_incoming_score(self, node_index):
# 		print 'Finding best incoming score to node ' , node_index
# 
# 		max_index = -1
# 		max_score = -101
# 		for index in range(len(self.scores)):
# 			for j in range(len(self.scores[index][node_index])):
# 	#			print index, j
# 				score = self.scores[index][node_index][j]
# 				if(score > max_score and not self.replaced_by.has_key(index)):
# 					max_score = score
# 					max_index = index
# 		return max_score

#################################################################
# Demos
#################################################################

def demo():
    hall_demo()
#	nonprojective_conll_parse_demo()
#	test_demo()
	
def test_demo():
	npp = ProbabilisticNonprojectiveParser()
	npp.scores = [[[], [5],  [1],  [1]],
				   [[], [],   [11], [4]],
				   [[], [10], [],   [5]],
				   [[], [8],  [8],  []]]
	npp.test()
		
def hall_demo():
	npp = ProbabilisticNonprojectiveParser()
	npp.scores = [[[-100], [5], [1], [1]],
				   [[-100], [-100], [11], [4]],
				   [[-100], [10], [-100], [5]],
				   [[-100], [8], [8], [-100]]]
	npp.parse(['v1', 'v2', 'v3'], [None, None, None])

def nonprojective_conll_parse_demo():
	infile = open('conll_sample.txt',"r")
	graphs = []
	entry = ""
	for line in infile.readlines():
		if(line == '\n' and entry != ""):
			graphs.append(DepGraph().read('\n' + entry))
			entry = ''
		else:
			entry += '\t' + line
	npp = ProbabilisticNonprojectiveParser()
	npp.train(graphs)
	npp.parse(['v1', 'v2', 'v3'], [None, None, None])
#	npp.parse(['Cathy', 'zag', 'hen', 'zwaaien', '.'], ['N', 'V', 'Pron', 'Adj', 'N', 'Punc'])
#	npp.parse(['v1', 'v2', 'v3'])


if __name__ == '__main__':
    demo()
