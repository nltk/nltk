# CIS 530 Project: Formal Semantics
# Spring 2005 (20 May)
# Benjamin R. George

from nltk.cfg import CFG, CFGProduction, Nonterminal
from nltk.tree import *

### Abstract Semantics

# A meaningless trivial function for handling the case where
# there is no need for a `commons' object. (explained below)
def NilFunction():
	return []
	
# A class for abritary compositional translation into semantic representations
# Each class instance can convert parse trees within its area of grammatical
# knolwedge into semantic represetations in accordance with the semantic rules
# with which it was initialized.
class SkeletonInterpretationManual:
	# Initializes with a function that looks up semantic rules to go with productions
	# and a function for generating global information structures.
	# Note that global information structures default to triviality, since many
	# semantic systems won't use them, and we want it to be possible to ignore them
	# if one doesn't intend to use such things.
	def __init__(self, rulelookupfunction, commonsgenerator = NilFunction):
		self.FindSemanticRule = rulelookupfunction
		self.DefaultCommons = commonsgenerator
	
	# Given a parse tree, returns the CFG production that was used to expand the root
	# node of that tree.
	def FindNodeProduction(self, tr):
		return CFGProduction(tr.node,map(self.SignatureOf,list(tr)))
	# A helper function for the above
	# returns the signature of a `child' tree that would be visible to a CFG production
	# (i.e. grammatical cateogry, or string value, as appropriate).
	def SignatureOf(self,child):
		if isinstance(child, Tree):
			return child.node
		else:
			return child
 
	# Derives the meaning of the root node of a tree recursively
	# using the operations of semantic composition defined at object creation.
	# It is generally assumed that the caller will not set commons directly
	# but that it will be used in the recursion case.
	def GetTreeMeaning(self, tr, commons = None):
		# If this is a call from the outside, get yourself a `commons':
		if commons == None:
			commons = self.DefaultCommons()
		# Derive a CFG production for the current root node:
		p = self.FindNodeProduction(tr)
		# Get a list of meanings for all children with internal structure:
		l = []
		for child in tr:
			if isinstance(child, Tree):
				l.append(self.GetTreeMeaning(child, commons))
		# Apply the function associated with the production to the 
		# meanings of the constituents:
		try:
			F = self.FindSemanticRule(p)
		except err:
			raise Exception('no semantics given for production: ' + str(p))
		return F(l,commons)

### An Application: A Semantic System Based on Predicate Logic

# An interpretation manual class for lamba / predicate logic expressions
# (somewhat sloppily augmented to handle a little scope ambiguity)
class LambdaInterpretationManual(SkeletonInterpretationManual):
	# Initializes the table of rules for interpreting specific productions
	# (including indiosyncratic words) and for interpreting lexical categories.
	def __init__(self,ruleandlogicalwordtable,lexicalcategorytable):
		self.lext = lexicalcategorytable
		self.rulet = ruleandlogicalwordtable
	# The `commons' for any interpretation attempt is always a
	# LambdaCommons (a simple counter to allocate variable subscripts)
	def DefaultCommons(self):
		return LambdaCommons()
	# To find a rule associated with a particular production...
	def FindSemanticRule(self,p):
		# ...first check to see if it's in the rule table...
		if self.rulet.has_key(p):
			return self.rulet[p].F # note that semantic functions are packaged inside objects
		# ...then see if it's a lexical derivation for a category you know.
		elif len(p.rhs())==1 and isinstance(p.rhs()[0],str) and self.lext.has_key(p.lhs()):
			return self.lext[p.lhs()](p.rhs()[0]).F
		else:
			raise Exception()
	# Functions to check the grammatical coverage of the semantics
	# (can also be used to build a grammar from the semantics,
	# with a little work and a good lexicon).
	def SupportedProductions(self):
		return self.rulet.keys()
	def SupportedLexicalCategories(self):
		return self.lext.keys()
	def SupportsProduction(self,r):
		return self.rulet.has_key(r)
	def SupportsLexicalCategory(self,pos):
		return self.rulet.has_key(pos)

# A base class for building objects to combine semantic meanings
# headpos is taken to be the list position of the `function' constituent
# all other constituents, taken from left to right, are `arguments'
class LambdaCombine:
	def __init__(self, n):
		self.headpos = n
		
# Simple function application with combination of scoped element lists:
class ApplyCombine(LambdaCombine):
	def lapply(self, l, commons):
		f = l[self.headpos].meaning
		s = l[self.headpos].scopedbits
		arglist = l[:self.headpos]+l[self.headpos+1:]
		for argmeaning in arglist:
			f = f(argmeaning.meaning)
			s = s + argmeaning.scopedbits
		return LambdaMeaning(f,s)
	def F(self, l, commons):
		return self.lapply(l, commons)

# Function application for scoped quantifiers
# Does regular function application, then binds to
# A fresh variable, makes the variable the primary meaning
# And adds the determiner to the scoped elements list
# Thus, determiners have three arguments:
# A restriction, a variable, and a sentence they scope over.
# The below can generalize to multi-argument determiner-like constructions such as `More N1 than N2'
class CheatCombine(ApplyCombine):
	def lcheat(self, l, commons):
		v = commons.getnewvar()
		m = self.lapply(l,commons)
		f = v
		s = m.scopedbits + [m.meaning(v)]
		return LambdaMeaning(f,s)
	def F(self, l, commons):
		return self.lcheat(l, commons)

# A class for the basic semantic objects of the system:
# These consist of a function or string, the primary meaning
# and a list of scoped elements the scope order of which has yet to be determined
class LambdaMeaning:
	def __init__(self, logicalformfunction, scopedelementlist):
		self.meaning = logicalformfunction
		self.scopedbits = scopedelementlist
	# Prints all possible readings of a parse tree
	# (i.e., all possible orderings of scoped elements)
	def PrintAllReadings(self):
		# recursively generates all orderings available and prints results
		
		if isinstance(self.meaning,str):
			if self.scopedbits == []:
				print self.meaning
			else:
				for i in range(len(self.scopedbits)):
					LambdaMeaning(self.scopedbits[i](self.meaning),self.scopedbits[:i]+self.scopedbits[i+1:]).PrintAllReadings()
		else:
			print 'Readings Cannot Be Displayed - Some Arguments are Missing'

# A class to issue fresh variable names upon request
class LambdaCommons:
	# At initialization, start counting variables anew:
	def __init__(self):
		self.varsubscript = -1;
	# Marks previous variable as taken, and hands a new one:
	def getnewvar(self):
		self.varsubscript = self.varsubscript+1
		return 'v' + (str(self.varsubscript))
	# Hands out another copy of the last variable handed out:
	def getcurvar(self):
		return 'v' + (str(self.varsubscript))

#Functions for packaging handwritten lambda forms as functions of a constituent list and a commons:

#Takes a curried function of a constituent list and a commons, and makes it a two-argument function
#in a wrapper object:
class UnCurry:
	def __init__(self,o):
		self.soledatum = o
	def F(self,l,commons):
		return self.soledatum(l)(commons)

#Takes an object (in the present context, a meaning object),
#and generates the trivial two-argument function that always returns it:
class TrivialUnCurry:
	def __init__(self,o):
		self.thunk = o
	def F(self,l, commons):
		return self.thunk

#Takes a function of a single variable,
#and makes a two-argument function that ignores constituents
#and fills the need for a variable from the commons.
class BindVar:
	def __init__(self,o):
		self.predicate = o
	def F(self,l,commons):
		return self.predicate(commons.getnewvar())

### An Demonstration of the Application: A Semantics for a Toy English Grammar

def semanticsdemo():

	# nonterminals:
	VP = Nonterminal('VP')
	VPB = Nonterminal('VPB')
	Vi = Nonterminal('Vi')
	Vt = Nonterminal('Vt')
	ViB = Nonterminal('ViB')
	VtB = Nonterminal('VtB')
	Det = Nonterminal('Det')
	NP = Nonterminal('NP')
	N = Nonterminal('N')
	Nbar = Nonterminal('Nbar')
	Adj = Nonterminal('Adj')
	S = Nonterminal('S')
	
	# note that in everything that follows, lambda abstractions inside a construction of a LambdaMeaning object
	# are part of word meaning, ones outside are used to express context-dependence and to describe ad hoc rules.
	
	# default semantics for lexical categories:
	toylext = dict()
	toylext[NP] = lambda word: TrivialUnCurry(LambdaMeaning(word,[]))
	toylext[Vi] = lambda word: TrivialUnCurry(LambdaMeaning((lambda subj: word + "("+subj+")"),[]))
	toylext[Vt] = lambda word: TrivialUnCurry(LambdaMeaning((lambda obj: (lambda subj: word + "("+subj+","+ obj +")")),[]))
	toylext[ViB] = lambda word: TrivialUnCurry(LambdaMeaning((lambda subj: word + "("+subj+")"),[]))
	toylext[VtB] = lambda word: TrivialUnCurry(LambdaMeaning((lambda obj: (lambda subj: word + "("+subj+","+ obj +")")),[]))
	toylext[N] = lambda word: TrivialUnCurry(LambdaMeaning((lambda x: word+ "("+x+")"),[]))
	toylext[Adj] = lambda word: BindVar(lambda v: LambdaMeaning((lambda noun: lambda x: word+ "(LAMBDA "+v+"." + noun(v)+")("+x+")"),[]))
		# note that adjectives are higher-order functions that take properties as arguments, so that they can be non-intersective
		# note also that no default semantics is provided for determiners.
	
	# semantics for grammatical rules and special words:
	toyrulet = dict()
	# simple grammatical combinations:
	toyrulet[CFGProduction(VP,[Vi])] = ApplyCombine(0)
	toyrulet[CFGProduction(VP,[Vt, NP])] = ApplyCombine(0)
	toyrulet[CFGProduction(VPB,[ViB])] = ApplyCombine(0)
	toyrulet[CFGProduction(VPB,[VtB, NP])] = ApplyCombine(0)
	toyrulet[CFGProduction(S,[NP,VP])] = ApplyCombine(1)
	toyrulet[CFGProduction(NP,[Det,Nbar])] = CheatCombine(0)
	toyrulet[CFGProduction(Nbar,[N])] = ApplyCombine(0)
	toyrulet[CFGProduction(Nbar,[Adj,Nbar])] = ApplyCombine(0)
	
	# kludgier rules for constructions with trickier real-world syntax:
	toyrulet[CFGProduction(VP,['did', 'not', VPB])] = UnCurry(lambda l: lambda c: LambdaMeaning(l[0].meaning, l[0].scopedbits + [lambda s: '!'+s]))
	toyrulet[CFGProduction(VP,['was', Vt])] = UnCurry(lambda l: lambda c: LambdaMeaning(lambda obj: '(THEREIS '+c.getnewvar()+')['+ l[0].meaning(c.getcurvar())(obj) + ']', l[0].scopedbits))
	toyrulet[CFGProduction(VP,['was', 'not', Vt])] = UnCurry(lambda l: lambda c: LambdaMeaning(lambda obj: '(THEREIS '+c.getnewvar()+')['+ l[0].meaning(c.getcurvar())(obj) + ']', l[0].scopedbits + [lambda s: '!'+s]))
	toyrulet[CFGProduction(VP,['was', Adj])] = UnCurry(lambda l: lambda c: LambdaMeaning(l[0].meaning(lambda x: 'ENTITY('+x+')'), l[0].scopedbits))
		#The above need `UnCurry' because the action of the rule on the constituents must be specified directly.
	
	# determiners and quantifiers:
	toyrulet[CFGProduction(Det,['every'])] = TrivialUnCurry(LambdaMeaning(lambda res: lambda v: lambda s: '(FORALL '+v+')['+ res(v) +' -> ' + s + ']',[]))
	toyrulet[CFGProduction(Det,['some'])] = TrivialUnCurry(LambdaMeaning(lambda res: lambda v: lambda s: '(THEREIS '+v+')['+ res(v) +' & ' + s + ']',[]))
	toyrulet[CFGProduction(Det,['no'])] = TrivialUnCurry(LambdaMeaning(lambda res: lambda v: lambda s: '!(THEREIS '+v+')['+ res(v) +' & ' + s + ']',[]))
		#Note that determiners don't invoke the commons directly, but are associated with a variable when they combine to form an NP (thanks to CheatApply)
	toyrulet[CFGProduction(NP,['everybody'])] = BindVar(lambda v: LambdaMeaning(v, [lambda s: '(FORALL '+v+')[PERSON('+v+') -> ' + s + ']']))
	toyrulet[CFGProduction(NP,['somebody'])] = BindVar(lambda v: LambdaMeaning(v, [lambda s: '(THEREIS '+v+')[PERSON('+v+') & ' +s +']']))
	toyrulet[CFGProduction(NP,['everything'])] = BindVar(lambda v: LambdaMeaning(v, [lambda s: '(FORALL '+v+')[' + s + ']']))
	toyrulet[CFGProduction(NP,['something'])] = BindVar(lambda v: LambdaMeaning(v, [lambda s: '(THEREIS '+v+')[' +s +']']))

	# generates the manual:
	themanual = LambdaInterpretationManual(toyrulet,toylext)

	# building some sample parse trees:
	# (by inspection, all trees are CFG-generable, assuming a CFG with the rules above plus suitable rules for individual words)	

	# Partial trees:
	tr_weasela = Tree(N, ['weasel'])
	tr_weaselb = Tree(Nbar, [tr_weasela])
	tr_every = Tree(Det, ['every'])
	tr_some = Tree(Det, ['some'])
	tr_no = Tree(Det, ['no'])
	tr_someweasel = Tree(NP, [tr_every, tr_weaselb])
	tr_cynical = Tree(Adj, ['cynical'])
	tr_cynicalweasel = Tree(Nbar, [tr_cynical,tr_weaselb])
	tr_everycynicalweasel = Tree(NP, [tr_every,tr_cynicalweasel])
	tr_anxious = Tree(Adj, ['anxious'])
	tr_wasanxious = Tree(VP, ['was', tr_anxious])
	tr_cassandra = Tree(NP, ['Cassandra'])
	tr_everybody = Tree(NP, ['everybody'])
	tr_somebody = Tree(NP, ['somebody'])
	tr_something = Tree(NP, ['something'])
	tr_topologista = Tree(N, ['topologist'])
	tr_topologistb = Tree(Nbar, [tr_topologista])
	tr_alleged = Tree(Adj, ['alleged'])
	tr_allegedtopologist = Tree(Nbar, [tr_alleged,tr_topologistb])
	tr_someallegedtopologist = Tree(NP, [tr_some,tr_allegedtopologist])
	tr_noallegedtopologist = Tree(NP, [tr_no,tr_allegedtopologist])
	tr_loved = Tree(Vt,['loved'])
	tr_fled = Tree(Vi,['fled'])
	tr_lovedsomething = Tree(VP, [tr_loved,tr_something])
	tr_threaten = Tree(VtB, ['threaten'])
	tr_threatensomeweasel = Tree(VPB, [tr_threaten,tr_someweasel])
	tr_didnotthreatensomeweasel = Tree(VP, ['did', 'not', tr_threatensomeweasel])
	tr_followed = Tree(Vt, ['followed'])
	tr_wasnotfollowed = Tree(VP, ['was', 'not', tr_followed])
	tr_wasfollowed = Tree(VP, ['was', tr_followed])
	tr_noweasel = Tree(NP, [tr_no, tr_weaselb])
	tr_lovednoweasel = Tree(VP, [tr_loved, tr_noweasel])

	# Parse trees for sentences:
	tr_noallegedtopologistwasfollowed = Tree(S, [tr_noallegedtopologist,tr_wasfollowed])
	tr_someallegedtopologistwasnotfollowed = Tree(S, [tr_someallegedtopologist,tr_wasnotfollowed])
	tr_everybodydidnothreatensomweasel = Tree(S, [tr_everybody,tr_didnotthreatensomeweasel])
	tr_somebodywasanxious = Tree(S, [tr_somebody, tr_wasanxious])
	tr_everycynicalweasellovedsomething = Tree(S, [tr_everycynicalweasel,tr_lovedsomething])
	tr_cassandralovednoweasel = Tree(S, [tr_cassandra, tr_lovednoweasel])
	
	# lists the productions the semantics understands
	rulelist = themanual.SupportedProductions()
	catlist = themanual.SupportedLexicalCategories()
	print 'The semantics understands the following nontrivial productions:'
	for p in rulelist:
		print str(p)
	print '\nIt can handle unfamiliar words of the following lexical categories:'
	for pos in catlist:
		print str(pos)
	
	treelist = [tr_noallegedtopologistwasfollowed, tr_someallegedtopologistwasnotfollowed, tr_everybodydidnothreatensomweasel, tr_somebodywasanxious, tr_everycynicalweasellovedsomething, tr_cassandralovednoweasel]
	print '\nSemantic analyses of a few parse trees:'
	# uses a manual to get a suitable assortment of readings for all the trees given above:
	for tr in treelist:
		print '\nA parse tree:\n' + str(tr)
		print 'Its possible readings:'
		themanual.GetTreeMeaning(tr).PrintAllReadings()
	
if __name__ == '__main__':
	semanticsdemo()