#!/usr/bin/env python
#
# 6.863 Parser, by Rob Speer
# Adapted from the Earley parser in NLTK.
# Distributed under the GPL (see LICENSE.TXT in the nltk package).

from nltk import cfg
from nltk.cfg import Nonterminal
from nltk.cfg import CFGProduction as Rule
from nltk.parser import chart as chartmod
from nltk.chktype import chktype as _chktype
from nltk.token import Token, Location
from nltk.tree import TreeToken
from nltk.tokenizer import WSTokenizer
from earleychart import *
import types, os, feature

# for the GUI component
from nltk.draw.chart import *
import Tkinter
from ScrolledText import ScrolledText
import tkMessageBox
from nltk.draw import tree as drawTree, CanvasFrame

TITLE = "6.863 Parser"

class EarleyCFG(cfg.CFG):
	def __init__(self, start, grammar, lexicon):
		grammar.extend(lexicon)
		cfg.CFG.__init__(self, start, grammar)

		self.grammar = {}
		self.lexicon = {}
		self.partsOfSpeech = {} #prevents duplicate elements
		for rule in grammar:
			if self.grammar.has_key(rule.lhs()):
				self.grammar[rule.lhs()].append(rule)
			else:
				self.grammar[rule.lhs()] = [rule]
				
			if len(rule.rhs())==1 and type(rule.rhs()[0])==type(""):
				#it's a word definition, not a rule
				if self.lexicon.has_key(rule.rhs()[0]):
					self.lexicon[rule.rhs()[0]].append(rule.lhs())
				else:
					self.lexicon[rule.rhs()[0]] = [rule.lhs()]
				self.partsOfSpeech[rule.lhs().symbol()] = None
			
	def getRules(self, nonterminal):
		if type(nonterminal) == type(""):
			nonterminal = cfg.Nonterminal(nonterminal)
		keys = self.grammar.keys()
		result = []
		for test in keys:
			if test.matches(nonterminal):
				result.extend(self.grammar[test])
		return result

	def getPartsOfSpeech(self, word):
		if self.lexicon.has_key(word):
			return self.lexicon[word]
		else:
			return []

	def isPartOfSpeech(self, nonterminal):
		if type(nonterminal) == type(""):
			nonterminal = feature.Category(nonterminal, {})
		return self.partsOfSpeech.has_key(nonterminal.symbol())
		#return isinstance(nonterminal, feature.Category)

class IncrementalEarleyParser(chartmod.IncrementalChartParser):
	def __init__(self, grammar, strategy, **kwargs):
		chartmod.IncrementalChartParser.__init__(self, grammar, strategy, **kwargs)
		self._output = kwargs.get('output', sys.stdout)
	def _create_chart(self, text):
		"""
		@param text: The text to be parsed
		@rtype: C{Chart}
		"""
		chart = EarleyChart(text)
		

		# Add an edge for each lexical item.
		#if self._trace: print 'Adding lexical edges...'
		#for tok in text:
		#	new_edge = chartmod.TokenEdge(tok)
		#	if chart.insert(new_edge):
		#		if self._trace > 1:
		#			print '%-20s %s' % ('Lexical Insertion',
		#								chart.pp_edge(new_edge))

		# Return the new chart
		return chart

	def _add_edge(self, edge, chart, edge_queue):
		if not chart.insert(edge): return False
		if self._trace > 1: self._output.write(chart.pp_edge(edge)+'\n')
																				
		# Apply all chart rules.
		for chartrule in self._strategy:
			got = chartrule.apply(chart, self._grammar, edge)
			if self._trace > 2: self._output.write("%s:\n\t%s" % (chartrule, "\n\t".join([chart.pp_edge(e) for e in got])) + '\n')
			edge_queue += got
		return True
	
	def initialize(self, text):
		# Create a new chart.
		self.text = text
		self.chart = self._create_chart(text)
		self.edge_queue = self._create_edge_queue(text)
		self.rootDesc = EdgeDescription(self._grammar.start(), self.chart.loc())
		for production in self._grammar.getRules(self._grammar.start()):
			loc = self.chart.loc().start_loc()
			self.edge_queue.append(feature.self_loop_edge(production, loc))
	
	def parse(self, text):
		# Inherit documentation from ParserI
		assert _chktype(1, text, [Token], (Token), types.NoneType)

		self.initialize(text)
 
		# Note that we're adding edges to the end of the queue as we
		# process it.  But we'll eventually get to the end of the
		# queue, since we ignore any edges that are already in the
		# chart (so we can add each edge at most once).
		if self._trace: self._output.write('Processing the edge queue...\n')
		while self.edge_queue:
			self.step()
	def parse_n(self, text, n=None):
		self.parse(text)
		parses = self.recoverParses(self.chart, self.rootDesc, n)
	
		if self._trace:
			self._output.write('Found %d parses with %d edges\n' % (len(parses),
			len(self.chart)))
																				
		# Sort the parses by decreasing likelihood, and return them
		return parses
	def step(self):
		while self.edge_queue:
			edge = self.edge_queue.pop()
			if self._add_edge(edge, self.chart, self.edge_queue):
				return edge
	def recoverParses(self, chart, rootDesc, n):
		parses = []
		forest = ParseForest(chart, rootDesc)
		for tree in forest:
			parses.append(tree)
			if n is not None and len(parses) == n: break
		return parses

def getOneParse(chart, edge):
	if isinstance(edge, feature.FeatureProductionEdge):
		children = edge.children()
	else: children = ()
	try:
		subtrees = [ParseForest(chart, desc).gen().next()\
		for desc in children]
	except StopIteration:
		subtrees = []
	token = TreeToken(edge.lhs(), *subtrees)
	return token

class ParseForest:
	def __init__(self, chart, desc):
		self.chart = chart
		self.desc = desc
	def __iter__(self): return self.gen()
	def gen(self):
		for edge in self.chart.findEdges(self.desc):
			if isinstance(edge, chartmod.TokenEdge) or len(edge.children()) == 0:
				token = Token(edge.lhs(), location=edge.loc())
				yield token
			else: 
				descs = edge.children()
				it = ParseSubForest(self.chart, descs).gen()
				trees = []
				while True: # until StopIteration is raised
					try:
						newTree = TreeToken(edge.lhs(), *it.next())
						if newTree not in trees:
							trees.append(newTree)
							yield newTree
					except StopIteration:
						break

class ParseSubForest:
	def __init__(self, chart, descList):
		self.chart = chart
		self.descList = descList
	def __iter__(self): return self.gen()
	def gen(self):
		if len(self.descList) == 0:
			yield ()
			raise StopIteration
		else:
			it1 = ParseForest(self.chart, self.descList[0]).gen()
			while True: # until StopIteration
				tree = it1.next()
				it2 = ParseSubForest(self.chart, self.descList[1:]).gen()
				while True: # until StopIteration
					try:
						yield (tree,) + it2.next()
					except StopIteration:
						break

class IncrementalEarleyInitRule(chartmod.IncrementalChartRuleI):
	def apply(self, chart, grammar, edge):
		edges = []
		for production in grammar.getRules(grammar.start()):
			loc = chart.loc().start_loc()
			edges.append(feature.self_loop_edge(production, loc))
		return edges
	def __str__(self): return 'Earley Init Rule'

class IncrementalEarleyScanner(chartmod.IncrementalChartRuleI):
	def apply(self, chart, grammar, edge):
		edges = []
		if not edge.complete():
			nextcat = edge.next()
			if grammar.isPartOfSpeech(nextcat):
				if edge.loc().end() >= chart.textLength():
					return []
				word = chart.wordAt(edge.loc().end())
				#if nextcat in grammar.getPartsOfSpeech(word):
				#possibilities = filter(lambda x: x.matches(nextcat),
				#	grammar.getPartsOfSpeech(word))
				pos = grammar.getPartsOfSpeech(word)
				for p in pos:
					vars = p.match(nextcat)
					if vars is not None:
						prod = cfg.CFGProduction(p, word)
						loc = edge.loc().end_loc()
						newedge = feature.self_loop_edge(prod, loc, vars)
						edges.append(newedge)
		return edges
	def __str__(self): return 'Earley Scanner'

class IncrementalEarleyPredictor(chartmod.IncrementalChartRuleI):
	def apply(self, chart, grammar, edge):
		edges = []
		if not edge.complete():
			nextcat = edge.next()
			if not grammar.isPartOfSpeech(nextcat):
				for prod in grammar.getRules(nextcat):
					loc = edge.loc().end_loc()
					edges.append(feature.self_loop_edge(prod, loc))
		return edges
	def __str__(self): return 'Earley Predictor'

class IncrementalEarleyCompleter(chartmod.IncrementalChartRuleI):
	def apply(self, chart, grammar, inedge):
		edges = []
		if inedge.complete():
			more_edges = chart.incomplete_edges()
		else:
			more_edges = chart.complete_edges()
		for otheredge in more_edges:
			edge = None
			edge2 = None
			if inedge.complete():
				edge = otheredge
				edge2 = inedge
			else:
				edge = inedge
				edge2 = otheredge
			if (type(edge2.lhs()) == type("")):
				if (edge2.lhs() == edge.next() and
					edge.end() == edge2.start()):
					newedge = feature.fr_edge(edge, edge2)
					if newedge is not None: edges.append(newedge)
			else:
#					if (edge2.lhs().matches(edge.next()) and
#						edge.end() == edge2.start()):
#						edges.append(chartmod.fr_edge(edge, edge2))
				if edge.end() == edge2.start():
					vars = edge2.lhs().match(edge.next())
					#vars = edge.next().match(edge2.lhs())
					if vars is not None:
						newedge = feature.fr_edge(edge, edge2, vars)
						if newedge is not None: edges.append(newedge)
		return edges
	def __str__(self): return 'Earley Completer'

def parseRule(text):
	tokens = text.split()
	return Rule(cfg.Nonterminal(tokens[0]),
				*map(lambda x: cfg.Nonterminal(x), tokens[2:]))

def parseLexicon(text):
	word, pos = text.split()
	return Rule(cfg.Nonterminal(pos), word)

earleyStrategy = [IncrementalEarleyPredictor(), IncrementalEarleyScanner(), IncrementalEarleyCompleter()]

def parseFile(name):
	f = open(name)
	lines = f.readlines()
	return parseLines(lines)

def parseLines(lines):
	rules = [] # grammar and lexicon
	for line in lines:
		line = line.strip()
		if len(line) == 0: continue
		if line[0] == '#': continue
		if len(line) >= 4 and line[:4] == '----': continue
		newrules = feature.parse(line)
		if isinstance(newrules, Rule): rules.append(newrules)
		elif isinstance(newrules, list): rules += newrules
		else: raise "Cannot add to rules: %s" % newrules
	return EarleyCFG(feature.parse('Start'), rules, [])

def demo():
	sentence = 'Poirot sent the solutions'
	print "Sentence:\n", sentence
	grammar = parseFile("feature.txt")
	print "Grammar:\n", grammar
	
	# tokenize the sentence
	tok_sent = WSTokenizer().tokenize(sentence)

	cp = IncrementalEarleyParser(grammar, earleyStrategy, trace=2)
	
	for parse in cp.parse_n(tok_sent): print parse

class EarleyChartView(ChartView):
	def _draw_tree(self):
		"""Draw the syntax tree for the selected edge"""
		for tag in self._tree_tags:
			self._tree_canvas.delete(tag)
		edge = self._edgeselection
		if not edge: return
		#if edge.structure() is None: return
		#if not isinstance(edge.structure(), TreeToken): return

		treetok = getOneParse(self._chart, edge)
		
		if (isinstance(edge, ProductionEdge) and
			not edge.complete()):
			rhs = edge.prod().rhs()
			dotpos = edge.dotpos()
			
			self._draw_treetok(treetok, edge.loc(), 0, len(rhs)-dotpos)
			
			# Draw dotted lines to unexpanded children.
			c = self._tree_canvas
			x1 = edge.loc().start() * self._unitsize + ChartView._MARGIN
			x2 = ((edge.loc().end()+len(rhs)-dotpos) * self._unitsize +
				  ChartView._MARGIN)
			x = (x1+x2)/2
			childx = ((edge.loc().end()+0.5) * self._unitsize +
					  ChartView._MARGIN)
			
			childy = ChartView._TREE_LEVEL_SIZE + self._text_height
			for node in rhs[dotpos:]:
				tag = c.create_line(x, self._text_height, childx, childy,
							  width=2, fill='#048', dash='2 3')
				self._tree_tags.append(tag)
				# Draw node label.
				tag = c.create_text(childx, childy, anchor='n', fill='#042',
									justify='center', text=str(node), 
									font=('helvetica', self._fontsize, 'bold'))
				self._tree_tags.append(tag)
				childx += self._unitsize
				
			y = ChartView._TREE_LEVEL_SIZE + self._text_height
		else:
			self._draw_treetok(treetok, edge.loc(), 0)
					  
		self._tree_height = ((treetok.height()-1) *
							 (ChartView._TREE_LEVEL_SIZE +
							  self._text_height))
		self._resize()		
	
	def _configure(self, e):
		"""
		The configure callback.  This is called whenever the window is
		resized.  It is also called when the window is first mapped.
		It figures out the unit size, and redraws the contents of each
		canvas.
		"""
		# This breaks things, but I still don't have this quite right:
		if abs(int(self._chart_canvas['width'])-e.width) > 5:
			self._chart_canvas['width'] = e.width
		loc = self._chart.loc()
		unitwidth = loc.end() - loc.start()
		self._unitsize = (e.width - 2*ChartView._MARGIN) / (unitwidth+1)
		self.draw()
	def draw(self):
		"""
		Draw everything (from scratch).
		"""
		if self._tree_canvas:
			self._tree_canvas.delete('all')
			self._draw_tree()

		if self._source_canvas:
			self._source_canvas.delete('all')
			self._draw_source()

		self._chart_canvas.delete('all')
		self._edgetags = {}
		
		# Redraw any edges we erased.
		for lvl in range(len(self._edgelevels)):
			for edge in self._edgelevels[lvl]:
				self._draw_edge(edge, lvl)

		# Add any new edges
		edges = self._chart.edges()
		edges.sort()
		for edge in edges:
			self._add_edge(edge)

		self._draw_loclines()
	def _grow(self):
		"""
		Grow the window, if necessary
		"""
		# Grow, if need-be
		loc = self._chart.loc()
		width = max(int(self._chart_canvas['width']),
					(loc.end() - loc.start())
					* self._unitsize +
					ChartView._MARGIN * 2 )
		width = int(self._chart_canvas['width'])
		#self._chart_canvas['width'] = width # broken??
		unitwidth = loc.end() - loc.start()
		self._unitsize = (width - 2*ChartView._MARGIN) / (unitwidth + 1)
		
		# Reset the height for the source window.
		if self._source_canvas is not None:
			self._source_canvas['height'] = self._source_height
	
	def _draw_edge(self, edge, lvl):
		"""
		Draw a single edge on the ChartView.
		"""
		c = self._chart_canvas
		loc = edge.loc()
		
		# Draw the arrow.
		x1 = (loc.start() * self._unitsize + ChartView._MARGIN)
		x2 = (loc.end() * self._unitsize + ChartView._MARGIN)
		if x2 == x1: x2 += max(4, self._unitsize/5)
		y = (lvl+1) * self._chart_level_size
		linetag = c.create_line(x1, y, x2, y, arrow='last', width=3)

		# Draw a label for the edge.
		if isinstance(edge, ProductionEdge):
			rhs = []
			for elt in edge.prod().rhs():
				if isinstance(elt, Nonterminal):
					rhs.append(str(elt.symbol()))
				else:
					rhs.append(repr(elt))
			pos = edge.dotpos()
		else:
			rhs = []
			pos = 0
			
		rhs1 = ' '.join(rhs[:pos])
		rhs2 = ' '.join(rhs[pos:])
		rhstag1 = c.create_text(x1+3, y+1, text=rhs1,
								font=('helvetica', self._fontsize),
								anchor='nw')
		dotx = c.bbox(rhstag1)[2] + 6
		doty = (c.bbox(rhstag1)[1]+c.bbox(rhstag1)[3])/2
		dottag = c.create_oval(dotx-2, doty-2, dotx+2, doty+2)
		rhstag2 = c.create_text(dotx+6, y+1, text=rhs2,
								font=('helvetica', self._fontsize),
								anchor='nw')
		lhstag = c.create_text(x1+3, y-1, text=str(edge.lhs()),
								anchor='sw',
								font=('helvetica', self._fontsize, 'bold'))

		# Keep track of the edge's tags.
		self._edgetags[edge] = (linetag, rhstag1,
								dottag, rhstag2, lhstag)

		# Register a callback for clicking on the edge.
		def cb(event, self=self, edge=edge): self.select_edge(edge)
		c.tag_bind(rhstag1, '<Button-1>', cb)
		c.tag_bind(rhstag2, '<Button-1>', cb)
		c.tag_bind(linetag, '<Button-1>', cb)
		c.tag_bind(dottag, '<Button-1>', cb)
		c.tag_bind(lhstag, '<Button-1>', cb)

		self._color_edge(edge)
	def _draw_loclines(self):
		"""
		Draw location lines.  These are vertical gridlines used to
		show where each location unit is.
		"""
		c1 = self._tree_canvas
		c2 = self._source_canvas
		c3 = self._chart_canvas
		margin = ChartView._MARGIN
		self._loclines = []
		for i in range(self._chart._loc.start()-1,
					   self._chart._loc.end()+1):
			x = i*self._unitsize + margin

			if c1:
				t1=c1.create_line(x, 0, x, 5000)
				c1.tag_lower(t1)
			if c2:
				t2=c2.create_line(x, 0, x, self._source_height)
				c2.tag_lower(t2)
			t3=c3.create_line(x, 0, x, 5000)
			c3.tag_lower(t3)
			t4=c3.create_text(x+2, 0, text=`i`, anchor='nw',
							  font=('helvetica', self._fontsize))
			c3.tag_lower(t4)
			#if i % 4 == 0:
			#	 if c1: c1.itemconfig(t1, width=2, fill='gray60')
			#	 if c2: c2.itemconfig(t2, width=2, fill='gray60')
			#	 c3.itemconfig(t3, width=2, fill='gray60')
			if i % 2 == 0:
				if c1: c1.itemconfig(t1, fill='gray60')
				if c2: c2.itemconfig(t2, fill='gray60')
				c3.itemconfig(t3, fill='gray60')
			else:
				if c1: c1.itemconfig(t1, fill='gray80')
				if c2: c2.itemconfig(t2, fill='gray80')
				c3.itemconfig(t3, fill='gray80')

class ParserGUI:
	def __init__(self, grammar, sentence, root=None):
		if root is None:
			root = Tkinter.Tk()
		tok_sent = WSTokenizer().tokenize(sentence)
		self._grammar = grammar
		self._tok_sent = tok_sent
		self._ep = IncrementalEarleyParser(grammar, earleyStrategy, trace=0)
		self._ep.initialize(tok_sent)
	
		self._root = Tkinter.Toplevel(root)
		self._root.title(TITLE)
		self._root.geometry("800x600")
		panels = Tkinter.Frame(self._root)
		panels.pack(side='bottom', fill='both')
		metabuttons = Tkinter.Frame(panels)
		metabuttons.pack(side='bottom', fill='both')
		buttons = Tkinter.Frame(metabuttons)
		buttons.pack(side='left', fill='both')
		options = Tkinter.Frame(metabuttons)
		options.pack(side='right', fill='none')
		
		source = self._ep.text
		self._view = EarleyChartView(self._ep.chart, source, panels, draw_tree=True)
		self._view.draw()
		
		Tkinter.Button(buttons, text='Run parser', command=self.run,
		background='#bbffbb').pack(side='left')
		Tkinter.Button(buttons, text='Stop', command=self.stop,
		background='#ffbbbb').pack(side='left')
		Tkinter.Button(buttons, text='Step', command=self.step)\
		.pack(side='left')
		Tkinter.Button(buttons, text='View parse trees',
		command=self.viewTrees).pack(side='left')
		Tkinter.Button(buttons, text='Reset',
		command=self.reset).pack(side='left')
		self._tree = Tkinter.BooleanVar()
		self._tree.set(True)
		Tkinter.Checkbutton(options, text='Show tree while parsing',
		variable=self._tree).pack(side='bottom', anchor='w')
		
		self._running = False
		self._root.mainloop()
	
	def runStep(self):
		oldsize = len(self._ep.chart)
		new_edge = self._ep.step()
		self._view.update()
		if len(self._ep.chart) != oldsize: # the edge is a new one
			self._view.unmark()
			self._view.view_edge(new_edge)
			self._view.mark_edge(new_edge)
			if self._tree.get(): self._view.select_edge(new_edge)
	
	def parse(self):
		if len(self._ep.edge_queue) == 0:
			# Try to find a complete parse, and select it
			self.show_parse()
			self._running = False
			return
		self.runStep()
		if self._running: self._root.after(1, self.parse)
	def show_parse(self):
		desc = EdgeDescription(feature.Category('Start', {}), self._ep.chart.loc())
		edges = self._ep.chart.findEdges(desc)
		if len(edges):
			self._view.view_edge(edges[0])
			if self._view.selected_edge() != edges[0]:
				self._view.select_edge(edges[0])
			self.viewTrees()
		else:
			tkMessageBox.showinfo("Parse failed", "No complete parses found.")
	def run(self):
		if self._running: return
		self._running = True
		self.parse()
	def step(self):
		self._running = False
		self.parse()
	def stop(self):
		self._running = False
	def viewTrees(self):
		edge = self._view.selected_edge()
		if edge is None: return
		TreeView(self, edge)
	def reset(self):
		self._running = False
		self._ep = IncrementalEarleyParser(self._grammar, earleyStrategy, trace=0)
		self._ep.initialize(self._tok_sent)
		self._chart = self._ep.chart
		self._view.update(self._chart)

class TreeView:
	def __init__(self, parent, edge, newwin=True):
		chart = parent._ep.chart
		if newwin: window = Tkinter.Toplevel(parent._root)
		else: window = parent._root
		window.title("Parse Tree")
		window.geometry("600x400")
		self.cf = CanvasFrame(window)
		self.cf.pack(side='top', expand=1, fill='both')
		
		buttons = Tkinter.Frame(window)
		buttons.pack(side='bottom', fill='x')

		self.prev = Tkinter.Button(buttons, text="Prev", command=self.prev)
		self.prev.pack(side='left')
		self.next = Tkinter.Button(buttons, text="Next", command=self.next)
		self.next.pack(side='left')
		self.printps = Tkinter.Button(buttons, text="Print to Postscript", command=self.cf.print_to_file)
		self.printps.pack(side='left')
		self.done = Tkinter.Button(buttons, text="Done", command=window.destroy)
		self.done.pack(side='left')
		self.label = Tkinter.Label(buttons, text="No parse trees")
		self.label.pack(side='right')
		self.prev.configure(state='disabled')
		
		self.gen = ParseForest(chart, EdgeDescription.fromEdge(edge)).gen()
		try:
			self.tree = self.gen.next()
			self.trees = [self.tree]
			self.pos = 0
			self.finished = False
			for i in range(19): self.findNext()
			self.showTree()
		except StopIteration:
			self.next.configure(state='disabled')
	def prev(self):
		self.pos -= 1
		if self.pos == 0:
			self.prev.configure(state='disabled')
		self.next.configure(state='normal')
		self.update()
	def next(self):
		if not self.finished and self.pos == len(self.trees) - 2:
			self.findNext()
		self.pos += 1
		if self.pos == len(self.trees) - 1:
			self.next.configure(state='disabled')
		self.prev.configure(state='normal')
		self.update()
	def findNext(self):
		try:
			self.trees.append(self.gen.next())
		except StopIteration:
			if self.pos == len(self.trees) - 1:
				self.next.configure(state='disabled')
			self.finished = True
	def update(self):
		self.cf.destroy_widget(self.treeWidget)
		self.tree = self.trees[self.pos]
		self.showTree()
	def showTree(self):
		self.treeWidget = drawTree.TreeWidget(self.cf.canvas(), self.tree, draggable=1, shapeable=1)
		self.cf.add_widget(self.treeWidget, 0, 0)
		if len(self.trees) >= 20 and not self.finished:
			total = "lots"
		else: total = len(self.trees)
		labelStr = "Tree %d of %s" % (self.pos + 1, total)
		self.label.configure(text=labelStr)

class InputGUI:
	def __init__(self, filename=None):
		self._root = Tkinter.Tk()
		Tkinter.Label(self._root, text="Enter your grammar here.").pack(side='top')
		self.rules = ScrolledText(self._root, background='white', foreground='black')
		self.rules.pack(side='top')
		bottom = Tkinter.Frame(self._root)
		bottom.pack(side='top', fill='x')
		
		self.sentence = Tkinter.StringVar()
		Tkinter.Label(bottom, text="Sentence:").pack(side='left')
		Tkinter.Entry(bottom, background='white', foreground='black', textvariable=self.sentence).pack(side='left', fill='x', expand=1)
		Tkinter.Button(bottom, text="Parse", command=self.parse).pack(side='left')
		self.init_menubar()
		
		self.filename = filename
		if filename is not None: self.doLoad(filename)
		self.update_title()
		
		self._root.mainloop()
	
	def init_menubar(self):
		menubar = Tkinter.Menu(self._root)
		
		filemenu = Tkinter.Menu(menubar, tearoff=0)
		filemenu.add_command(label='Clear Rules', underline=0,
							 command=self.clear, accelerator='Ctrl+N')
		self._root.bind('<Control-n>', self.clear)
		filemenu.add_command(label='Load Rules', underline=0,
							 command=self.load, accelerator='Ctrl+O')
		self._root.bind('<Control-o>', self.load)
		filemenu.add_command(label='Save Rules', underline=0,
							 command=self.save, accelerator='Ctrl+S')
		self._root.bind('<Control-s>', self.save)
		filemenu.add_command(label='Save Rules As...', underline=0,
							 command=self.saveas)
		filemenu.add_command(label='Exit', underline=1,
							 command=self._root.destroy, accelerator='Ctrl+Q')
		self._root.bind('<Control-q>', self._root.destroy)
		menubar.add_cascade(label='File', underline=0,
							menu=filemenu)
		self._root.config(menu=menubar)
	
	def update_title(self):
		if self.filename is None: name="Untitled"
		else: name = self.filename.split(os.path.sep)[-1]
		self._root.title(TITLE+": "+name)
		
	def load(self):
		from tkFileDialog import askopenfilename
		ftypes = [('Text file', '.txt'),
				  ('All files', '*')]
		filename = askopenfilename(filetypes=ftypes,
								   defaultextension='.txt')
		if filename: self.doLoad(filename)
	
	def doLoad(self, filename):
		f = open(filename, 'r')
		self.clear()
		self.rules.insert(1.0, f.read())
		f.close()
		self.filename = filename
		self.update_title()
	
	def save(self):
		if self.filename is None: self.saveas()
		else: self.doSave(self.filename)
	
	def saveas(self):
		from tkFileDialog import asksaveasfilename
		ftypes = [('Text file', '.txt'),
				  ('All files', '*')]
		filename = asksaveasfilename(filetypes=ftypes,
									 defaultextension='.txt')
		if not filename: return
		self.doSave(filename)

	def doSave(self, filename):
		f = open(filename, 'w')
		f.write(self.rules.get(1.0, Tkinter.END))
		f.close()
		self.filename = filename
		self.update_title()
		
	def clear(self):
		self.rules.delete(1.0, Tkinter.END)
		self.sentence.set('')
		self.filename = None
		self.update_title()

	def parse(self):
		lines = self.rules.get(1.0, Tkinter.END).split("\n")
		grammar = parseLines(lines)
		ParserGUI(grammar, self.sentence.get(), self._root)

	def textParse(self):
		lines = self.rules.get(1.0, Tkinter.END).split("\n")
		grammar = parseLines(lines)
		output = TextWindow(self._root)
		TextParser(grammar, self.sentence.get(), output=output, trace=2)

class TextWindow:
	def __init__(self, root=None):
		if root is None:
			root = Tkinter.Tk()
		self._top = Tkinter.Toplevel(root)
		self._top.title("Parser Output")
		self.output = ScrolledText(self._top, background='white', foreground='black')
		self.output.pack(side='top', expand=1)
		self.queue = []
	def write(self, text):
		self.queue.append(text)
		self._top.after(10, self.addtext)
	def addtext(self):
		self.output.insert(Tkinter.END, self.queue[0])
		del self.queue[0]

class TextParser:
	def __init__(self, grammar, sentence, output=sys.stdout, trace=0, drawtrees=False, latex=False):
		# tokenize the sentence
		tok_sent = WSTokenizer().tokenize(sentence)
		
		self._ep = ep = IncrementalEarleyParser(grammar, earleyStrategy, output=output, trace=trace)
		if not drawtrees:
			for parse in ep.parse_n(tok_sent, None):
				if latex: output.write(parse.latex_qtree() + '\n')
				else: output.write(str(parse) + '\n')
		else:
			ep.parse(tok_sent)
			desc = EdgeDescription(feature.Category('Start', {}), ep.chart.loc())
			edges = ep.chart.findEdges(desc)
			if len(edges):
				self._root = Tkinter.Tk()
				TreeView(self, edges[0], newwin=False)
				self._root.mainloop()
			else:
				sys.stderr.write('No parses.\n')

def main():
	import sys
	from optparse import OptionParser, OptionGroup
	
	usage = "usage: %prog [options] [rule_file]"
	opts = OptionParser(usage=usage)
	opts.add_option("-t", "--text",
	action="store_true", dest="text", default=False,
	help="run in text mode (faster)")

	group=OptionGroup(opts, "Text mode options")
	group.add_option("-v", "--verbose",
	action="store_true", dest="verbose", default=True,
	help="output all edges that are generated [default]")
	group.add_option("-q", "--quiet",
	action="store_false", dest="verbose",
	help="output only the generated parses")
	group.add_option("-l", "--latex",
	action="store_true", dest="latex",
	help="output parses as LaTeX trees (using qtree.sty)")
	group.add_option("-d", "--drawtrees",
	action="store_true", dest="drawtrees",
	help="show parse trees in a GUI window")
	group.add_option("-o", "--outfile",
	metavar="FILE", dest="outfile", default=sys.stdout,
	help="send output to a file")
	opts.add_option_group(group)
	
	(options, args) = opts.parse_args()
	if options.verbose: trace = 2
	else: trace = 0
	
	if len(args): filename = args[0]
	else: filename = None

	if not options.text:
		InputGUI(filename=filename)
	else:
		# text parser
		if filename is None:
			sys.stderr.write("Load rules from file: ")
			filename = sys.stdin.readline()[:-1]
			if filename == '': return
		
		grammar = parseFile(filename)
		sys.stderr.write("Sentence: ")
		sentence = sys.stdin.readline()[:-1]
		if sentence == '': return
		TextParser(grammar, sentence, options.outfile, trace=trace, drawtrees=options.drawtrees, latex=options.latex)

if __name__ == '__main__': main()

