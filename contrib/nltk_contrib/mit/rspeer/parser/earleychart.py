import nltk.parser.chart as chartmod
from nltk.chktype import chktype as _chktype
from nltk.token import Token, Location


class EarleyChart(chartmod.Chart):
	def __init__(self, text):
		loc = Location(text[0].loc().start(), text[-1].loc().end(),
					   unit=text[0].loc().unit(),
					   source=text[0].loc().source())
		chartmod.Chart.__init__(self, loc)
		self.text = text
	def wordAt(self, i):
		return self.text[i].type()
	def textLength(self):
		return len(self.text)
	def findEdges(self, desc):
		edges = []
		for edge in self.complete_edges():
			if edge.loc() == desc.loc() and edge.lhs() == desc.lhs():
				edges.append(edge)
		return edges

class EdgeDescription:
	"""
	A description of an edge that specifies its left-hand side and its
	location. This is used in parse recovery; an EarleyChart will take this
	description and find all complete edges that fit the description.
	"""
	def __init__(self, lhs, loc):
		self._lhs = lhs
		self._loc = loc
	def lhs(self):
		return self._lhs
	def loc(self):
		return self._loc
	def fromEdge(edge):
		return EdgeDescription(edge.lhs(), edge.loc())
	def __hash__(self):
		return hash((self._lhs, self._loc))
	def __cmp__(self, other):
		return cmp((self._lhs, self._loc), (other._lhs, other._loc))
	fromEdge = staticmethod(fromEdge)

