# Natural Language Toolkit: Dependency Grammars
#
# Copyright (C) 2001-2008 NLTK Project
# Author: Ewan Klein <ewan@inf.ed.ac.uk>
#
# URL: <http://nltk.org>
# For license information, see LICENSE.TXT
#

"""
Tools for reading and writing dependency trees.
The input is assumed to be in U{Malt-TAB<http://w3.msi.vxu.se/~nivre/research/MaltXML.html>} format.

Currently only reads the first tree in a file.
"""

from nltk.parse import Tree
from pprint import pformat
import re

#################################################################
# DepGraph Class
#################################################################

class DepGraph(object):
	"""
	A container for the nodes and labelled edges of a dependency structure.
	"""
	def __init__(self):
		"""
		We place a dummy 'top' node in the first position 
		in the nodelist, since the root node is often assigned '0'
		as its head. This also means that the indexing of the nodelist
		corresponds directly to the Malt-TAB format, which starts at 1.
		"""
		top = {'word':None, 'deps':[], 'rel': 'TOP', 'tag': 'TOP', 'address': 0}
		self.nodelist = [top]
		self.root = None
		self.stream = None

	def remove_by_address(self, address):
		node_index = len(self.nodelist) - 1
		while(node_index >= 0):
			node = self.nodelist[node_index]
			if(node['address'] == address):
				self.nodelist.pop(node_index)
			node_index -= 1

# originals is a list
	def redirect_arcs(self, originals, redirect):
		for node in self.nodelist:
			new_deps = []
			for dep in node['deps']:
				if dep in originals:
					new_deps.append(redirect)
				else:
					new_deps.append(dep)
			node['deps'] = new_deps

	def add_arc(self, head_address, mod_address):
		for node in self.nodelist:
			if(node['address'] == head_address and (not (mod_address in node['deps']))):
				node['deps'].append(mod_address)

	def connect_graph(self):
		for node1 in self.nodelist:
			for node2 in self.nodelist:
				if(node1['address'] != node2['address'] and node2['rel'] != 'TOP'):
					node1['deps'].append(node2['address'])

	def get_by_address(self, node_address):
		for node in self.nodelist:
			if(node['address'] == node_address):
				return node
		print 'THROW ERROR: address not found in -get_by_address-'

	def contains_address(self, node_address):
		for node in self.nodelist:
			if(node['address'] == node_address):
				return True
		return False
					
	def __str__(self):
		return pformat(self.nodelist)

	def load(self, file):
		"""
		@param file: a file in Malt-TAB format
		"""
		input = open(file).read()
		return self.read(input)

	def _normalize(self, line):
		"""
		Deal with lines in which spaces are used rather than tabs.
		"""
		SPC = re.compile(' +')
		return re.sub(SPC, '\t', line)

	def left_children(self, node_index):
		count = 0
		for child in self.nodelist[node_index]['deps']:
			if (child < int(self.nodelist[node_index]['address'])):
				count += 1
		return count

	def right_children(self, node_index):
		count = 0
		for child in self.nodelist[node_index]['deps']:
			if (child > int(self.nodelist[node_index]['address'])):
				count += 1
		return count
	
	def add_node(self, node):
		if(not self.contains_address(node['address'])):
			self.nodelist.append(node)

	def read(self, input):
		lines = input.split('\n')
		count = 1
		temp = []
		for line in lines:
			line = self._normalize(line).strip(' \t') # for safety, line assumed to be tab delimited
#			print line
			if line != '':
				node = {}
				try:
					nrCells = len(line.split('\t'))
					head = 1
					if(nrCells == 4):
						(word, tag, head, rel) = line.split('\t')
						head = int(head)
						#not required, but useful for inspection
						node['address'] = count        
						node['word'] = word
						node['tag'] = tag
						node['head'] = head
						node['rel']= rel
						node['deps'] = []
						self.nodelist.append(node)
					elif(nrCells == 10):
						(id, form, lemma, cpostag, postag, feats, head, deprel, phead, pdeprel) = line.split("\t")
						head = int(head)
						#not required, but useful for inspection - tag and word necessary for parsing
						node['address'] = count #id
						node['word'] = form
						node['tag'] = postag
						node['head'] = head
						node['rel'] = deprel
						node['deps'] = []
						self.nodelist.append(node)
					else:
						# replace with formal error throw
						print 'Number of tab-delimited fields (%d) not supported by CoNLL(10) or Malt-Tab(4) format' % (nrCells)
					for(dep, hd) in temp:
						if hd == count: #count:
							node['deps'].append(dep)
					try:
						self.nodelist[head]['deps'].append(count)
					except IndexError:
						temp.append((count, head))
						
					count += 1
					
				except ValueError:
					break

		root_address = self.nodelist[0]['deps'][0]
		self.root = self.nodelist[root_address]
		return self

	def _word(self, node, filter=True):
		w = node['word']
		if filter:
			if w != ',': return w
		return w

	def _deptree(self, i):
		"""
		Recursive function for turning dependency graphs into
		NLTK trees.
		@type i: C{int}	
		@param i: index of a node in C{nodelist}
		@return: either a word (if the indexed node 
		is a leaf) or a L{Tree}.
		"""

		node = self.nodelist[i]
		word = node['word']
		deps = node['deps']

		if len(deps) == 0:
			return word
		else:
			return Tree(word, [self._deptree(j) for j in deps])


	def deptree(self):
		"""
		Starting with the C{root} node, build a dependency tree using the NLTK 
		L{Tree} constructor. Dependency labels are omitted.
		"""
		node = self.root
		word = node['word']
		deps = node['deps']
		return Tree(word, [self._deptree(i) for i in deps])

	def _hd(self, i):
		try:
			return self.nodelist[i]['head']
		except IndexError:
			return None

	def _rel(self, i):
		try:
			return self.nodelist[i]['rel']
		except IndexError:
			return None

	# def contains_cycle(self):
	# 	return self.check_cycle(self.root, [])
	# 
	# def check_cycle(self, curr_node, visited_nodes):
	# 	if(curr_node['address'] in visited_nodes):
	# 		return True
	# 	visited_nodes.append(curr_node['address'])
	# 	for dep in curr_node['deps']:
	# 	 	if self.check_cycle(self.nodelist[dep], visited_nodes):
	# 			return True
	# 	return False
	# 		

	def contains_cycle(self):
		distances = {}
		for node in self.nodelist:
			for dep in node['deps']:
				key = tuple([node['address'], dep]) #'%d -> %d' % (node['address'], dep)
				distances[key] = 1
#		print distances
		window = 0
		for n in range(len(self.nodelist)):
			new_entries = {}
			for pair1 in distances:
				for pair2 in distances:
#					print pair1, pair2
					if(pair1[1] == pair2[0]):
						key = tuple([pair1[0], pair2[1]])
						new_entries[key] = distances[pair1] + distances[pair2]
			for pair in new_entries:
				distances[pair] = new_entries[pair]
				if(pair[0] == pair[1]):
					print pair[0]
					path = self.get_cycle_path(self.get_by_address(pair[0]), pair[0]) #self.nodelist[pair[0]], pair[0])
#					print distances
					return path
		#distances.extend(new_entries)
#		print distances
		return False
		

	def get_cycle_path(self, curr_node, goal_node_index):
#		print 'new call:', curr_node['address']
		for dep in curr_node['deps']:
#			print dep
			if(dep == goal_node_index):
				return [curr_node['address']]
#		if(len(curr_node['deps']) == 0):
#			return []
#		else:
		for dep in curr_node['deps']:
#			print 'dep:', dep
			path = self.get_cycle_path(self.get_by_address(dep), goal_node_index)#self.nodelist[dep], goal_node_index)
#			print 'path', path
			if(len(path) > 0):
				path.insert(0, curr_node['address'])
				return path
		return [] 
				

def nx_graph(self):
	"""
	Convert the data in a C{nodelist} into a networkx 
	labeled directed graph.
	@rtype: C{XDigraph}
	"""
	nx_nodelist = range(1, len(self.nodelist))
	nx_edgelist = [(n, self._hd(n), self._rel(n)) 
						for n in nx_nodelist if self._hd(n)]
	self.nx_labels = {}
	for n in nx_nodelist:
		self.nx_labels[n] = self.nodelist[n]['word']

	g = NX.XDiGraph()
	g.add_nodes_from(nx_nodelist)
	g.add_edges_from(nx_edgelist)

	return g

def demo():
#	malt_demo()
#	conll_demo()
#	conll_file_demo()
	cycle_finding_demo()
	demo_remove()

def malt_demo(nx=False):
    """
    A demonstration of the result of reading a dependency
    version of the first sentence of the Penn Treebank.
    """
    dg = DepGraph().read("""Pierre  NNP     2       NMOD
Vinken  NNP     8       SUB
,       ,       2       P
61      CD      5       NMOD
years   NNS     6       AMOD
old     JJ      2       NMOD
,       ,       2       P
will    MD      0       ROOT
join    VB      8       VC
the     DT      11      NMOD
board   NN      9       OBJ
as      IN      9       VMOD
a       DT      15      NMOD
nonexecutive    JJ      15      NMOD
director        NN      12      PMOD
Nov.    NNP     9       VMOD
29      CD      16      NMOD
.       .       9       VMOD
""")
    tree = dg.deptree()
    print tree.pprint()
    if nx:
        #currently doesn't work
        try:
            import networkx as NX
            import pylab as P
        except ImportError:
            raise
            g = dg.nx_graph()
        g.info()
        pos = NX.spring_layout(g, dim=1)
        NX.draw_networkx_nodes(g, pos, node_size=50)
        #NX.draw_networkx_edges(g, pos, edge_color='k', width=8)
        NX.draw_networkx_labels(g, pos, dg.nx_labels)
        P.xticks([])
        P.yticks([])
        P.savefig('deptree.png')
        P.show()


def conll_demo():
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
	print dg
#	print dg.left_children(13)
#	print dg.right_children(13)
# 	for node_index in range(1,len(dg.nodelist)):
# 		productions = []
# 		tags = {}
# 		print
# #		print
# #		print
# 		children = dg.nodelist[node_index]['deps']
# 		nr_left_children = dg.left_children(node_index)
# 		nr_right_children = dg.right_children(node_index)
# 		nr_children = nr_left_children + nr_right_children
# #		print children
# 		print '%s %s %s' % (children, nr_left_children, nr_right_children)
# 		for child_index in range(0 - (nr_left_children + 1), nr_right_children + 2):
# #			print
# #			print 'right_children:%s' % (nr_right_children)
# #			print 'child_index:%s' % (child_index)
# 			head_word = dg.nodelist[node_index]['word']
# 			head_tag = dg.nodelist[node_index]['tag']
# #			print 'head: (%s, %s)' % (head_word, head_tag)
# 			# if(array_index >= 0 and array_index < nr_children):
# 			# 	child = dg.nodelist[children[array_index]]['word']
# 			# 	child_tag = dg.nodelist[children[array_index]]['tag']
# 			if(child_index < 0):
# 				array_index = child_index + nr_left_children
# #				print 'array_index:%s' % (array_index)
# 				child = 'STOP'
# 				child_tag = 'STOP'
# 				prev_word = 'START'
# 				prev_tag = 'START'
# 				if(array_index >= 0):
# #					print 'first'
# 					child = dg.nodelist[children[array_index]]['word']
# 					child_tag = dg.nodelist[children[array_index]]['tag']
# 					if(child != 'STOP'):
# 						productions.append(DependencyProduction.new(head_word, [child]))
# #				print 'curr_left: (%s, %s)' % (child, child_tag)
# 				if(child_index != -1):
# #					print array_index
# 					prev_word = dg.nodelist[children[array_index + 1]]['word']
# 					prev_tag =  dg.nodelist[children[array_index + 1]]['tag']
# #				print 'prev_left: (%s, %s)' % (prev_word, prev_tag)
# 				print '%d left Pr(%s, %s) | tag(%s), head_w(%s), h_tag(%s)' % (child_index, child, child_tag, prev_tag, head_word, head_tag)
# 			elif(child_index > 0):
# 				array_index = child_index + nr_left_children - 1
# #				print 'array_index:%s' % (array_index)
# #				print '_child_index:%s' % (child_index)
# 				child = 'STOP'
# 				child_tag = 'STOP'
# 				prev_word = 'START'
# 				prev_tag = 'START'
# 				if(array_index < nr_children):
# #					print 'first'
# 					child = dg.nodelist[children[array_index]]['word']
# 					child_tag = dg.nodelist[children[array_index]]['tag']
# #				print 'curr_right: (%s, %s)' % (child, child_tag)
# 				if(child_index != 1):
# #					print 'last'
# #					print array_index
# #					print children
# 				#					print array_index
# 					prev_word = dg.nodelist[children[array_index - 1]]['word']
# 					prev_tag =  dg.nodelist[children[array_index - 1]]['tag']
# #				print 'prev_right: (%s, %s)' % (prev_word, prev_tag)
# 				print '%d right Pr(%s, %s) | tag(%s), head_w(%s), h_tag(%s)' % (child_index, child, child_tag, prev_tag, head_word, head_tag)
# 
				
				# 
				# if(array_index < nr_children):
				# 	print array_index
				# 	child = dg.nodelist[children[array_index]]['word']
				# 	child_tag = dg.nodelist[children[array_index]]['tag']
				# 	print 'curr_right: (%s, %s)' % (child, child_tag)
				# 	prev_word = dg.nodelist[children[array_index + 1]]['word']
				# 	prev_tag =  dg.nodelist[children[array_index + 1]]['tag']
				# 	print 'prev_right: (%s, %s)' % (prev_word, prev_tag)
				
#				child_index - 1
				# print
				# print child_index
				# child = 'STOP'
				# child_tag = 'STOP'
				# array_index = child_index + nr_left_children
				# print array_index
				# print children
				# if(array_index >= 0 and array_index < nr_children):
				# 	child = dg.nodelist[children[array_index]]['word']
				# 	child_tag = dg.nodelist[children[array_index]]['tag']
				# print 'tag(%s, %s)' % (child, child_tag)
				# print 'pair(%s, %s)' % (dg.nodelist[node_index]['word'], dg.nodelist[node_index]['tag'])

#			print dg.left_children(node_index)
#			print dg.right_children(node_index)


def conll_file_demo():
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
	for graph in graphs:
		tree = graph.deptree()
		print '\n' + tree.pprint()

def cycle_finding_demo():
	dg = DepGraph().read("""Pierre  NNP     2       NMOD
	Vinken  NNP     8       SUB
	,       ,       2       P
	61      CD      5       NMOD
	years   NNS     6       AMOD
	old     JJ      2       NMOD
	,       ,       2       P
	will    MD      0       ROOT
	join    VB      8       VC
	the     DT      11      NMOD
	board   NN      9       OBJ
	as      IN      9       VMOD
	a       DT      15      NMOD
	nonexecutive    JJ      15      NMOD
	director        NN      12      PMOD
	Nov.    NNP     9       VMOD
	29      CD      16      NMOD
	.       .       9       VMOD
	""")
	print dg.contains_cycle()
	cyclic_dg = DepGraph()
	top =    {'word':None, 'deps':[1],    'rel': 'TOP', 'address': 0}	
	child1 = {'word':None, 'deps':[2],   'rel': 'NTOP', 'address': 1}
	child2 = {'word':None, 'deps':[4], 'rel': 'NTOP', 'address': 2}
	child3 = {'word':None, 'deps':[1],   'rel': 'NTOP', 'address': 3}
	child4 = {'word':None, 'deps':[3],   'rel': 'NTOP', 'address': 4}
	cyclic_dg.nodelist = [top, child1, child2, child3, child4]
	cyclic_dg.root = top
#	print cyclic_dg.nodelist
	print cyclic_dg.contains_cycle()

def demo_remove():
	# Temp demo for testing methods in dev.
	cyclic_dg = DepGraph()
	top =    {'word':None, 'deps':[1],    'rel': 'TOP', 'address': 0}	
	child1 = {'word':None, 'deps':[2],   'rel': 'NTOP', 'address': 1}
	child2 = {'word':None, 'deps':[4], 'rel': 'NTOP', 'address': 2}
	child3 = {'word':None, 'deps':[1],   'rel': 'NTOP', 'address': 3}
	child4 = {'word':None, 'deps':[3],   'rel': 'NTOP', 'address': 4}
	cyclic_dg.nodelist = [top, child1, child2, child3, child4]
	print 'orignial:'
	print cyclic_dg
	cyclic_dg.remove_by_address(2)
	print
	print 'removed:'
	print cyclic_dg
	cyclic_dg.redirect_pointers([1], 5)
	print
	print 'redirected'
	print cyclic_dg
	cyclic_dg.add_arc(1,3)
	print
	print 'arc added 1->3'
	print cyclic_dg

if __name__ == '__main__':
	demo()
