from nltk.cfg import *
from nltk.parser import chart
from nltk.chktype import chktype as _chktype
from nltk.tree import TreeToken
from earleychart import EdgeDescription

"""
Classes to implement grammars with feature tags. Using these classes, you can
tag text with a C{Category} that has features that propagate up the tree,
instead of with a string.

This has nothing to do with the nltk.classifier.feature package, which does not
appear to be usable for this purpose.
"""

debug = False

def merge(dict1, dict2):
	"""
	Takes two dictionaries and merges them. The returned dictionary has all
	the key-value mappings of the two original dictionaries. If this is not
	possible (because the two dictionaries map the same key to different
	values), returns None.

	@type dict1: C{dict}
	@type dict2: C{dict}
	@return: A new dictionary that is the result of merging dict1 and dict2,
	or None if merging is not possible.
	@rtype: C{dict} or C{NoneType}
	"""
	if dict1 is None or dict2 is None: return None
	result = dict(dict1)
	for (key, value) in dict2.items():
		if result.has_key(key):
			vars = result[key].match(value)
			if vars is None: return None
			newval = result[key].matchFor(value)
			if newval is None: return None
			result = merge(result, vars)
			if result is None: return None
			result[key] = newval
		else:
			result[key] = value
	return result

def splitWithBrackets(str, chars=" []"):
	"""
	Splits a string at a certain character, much like split(). However,
	if this character is between specified bracketing characters, the string
	is not split there.

	The first character of C{chars} is the character to split at. The second
	and third characters are the opening and closing brackets, respectively. 

	For example, with the default C{chars}, the string C{'foo[bar baz] quux'}
	will split as C{['foo[bar baz]', 'quux']}.

	@param str: The string to be split
	@type str: C{str}
	@param chars: The characters to use to determine where to split the string.
	@type chars: C{str}
	@return: The string split into tokens.
	@rtype: C{list}
	"""
	parts = []
	pos = 0
	brackets = 0
	for c in range(len(str)):
		char = str[c]
		if char == chars[1]: brackets += 1
		elif char == chars[2]: brackets -= 1
		elif char == chars[0] and brackets == 0:
			parts.append(str[pos:c])
			pos = c+1
	parts.append(str[pos:])
	return parts

class Feature:
	"""
	A feature is a name associated with a FeatureValue. For example,
	C{NUMBER PLURAL} is a feature with the name C{'NUMBER'} and value
	C{'PLURAL'}.

	A feature may be 'required', in which case a Category must have a
	feature by this name in order to match a Category with this feature.
	"""
	def __init__(self, name, value, required=False):
		"""
		Create a C{Feature}.

		@param name: The name of the feature.
		@type name: C{str}.
		@param value: The value of the feature.
		@type value: C{FeatureValue}
		@param required: Whether the feature must be present to match.
		@type required: C{bool}
		"""
		if (name[0] == '+'):
			raise "A feature name cannot begin with +. Use parse to create a feature from its string representation."
		self._name = name
		self._value = value
		self._required = required
	def name(self):
		return self._name
	def value(self):
		return self._value
	def defaultValue(self):
		if self._required: return NullCategory()
		else: return StarCategory()
	def isRequired(self):
		return self._required
	def match(self, other):
		"""
		A feature matches another feature if their names are the same, and
		their values match.

		Matching features may require setting some variables. If the
		categories can match, this method returns a dictionary of variables
		that must be assigned. The keys are varable names (strings), and the
		values are the variable values (also strings). If the features cannot
		match, this method returns None.

		@return: a dictionary of variable assignments if the features can
		match, C{None} otherwise
		@rtype: C{dict} or C{NoneType}
		"""
		if (self.name() != other.name()): return None
		return self.value().match(other.value())
	def __str__(self):
		if (self._required and self._name != '/'):
			return "+%s %s" % (self._name, str(self._value))
		else: return "%s %s" % (self._name, str(self._value))
	def __repr__(self):
		return str(self)
	def __eq__(self, other):
		return isinstance(other, Feature) and self.name() == other.name() and self.value() == other.value()
	def __ne__(self, other):
		return not (self == other)
	def parse(str):
		"""
		Creates a C{Feature} from its string representation, which is
		'C{[+]M{name} M{value}}'. If the + is present, then this feature
		is required.
		"""
		str = str.strip()
		parts = splitWithBrackets(str, " []")
		if len(parts) != 2:
			raise ValueError("Feature '%s' has %d components, expected 2" \
			% (str, len(parts)))
		if parts[0][0] == '+':
			return Feature(parts[0][1:], FeatureValue.parse(parts[1]), True)
		else:
			isSlash = parts[0] == '/'
			return Feature(parts[0], FeatureValue.parse(parts[1]), isSlash)
	parse = staticmethod(parse)

class FeatureValue(Nonterminal):
	"""
	The value of a feature. This value is either a C{Category} or a
	C{VariableValue}. This class is abstract.
	"""
	def symbol(self):
		"""
		@return: The value represented by this.
		@rtype: C{string}
		"""
		pass

	def parse(str):
		"""
		Creates a C{FeatureValue} from its string representation.

		@return: A C{FeatureValue} based on string, which is a C{VariableValue}
			if the string begins with C{?}, or a Category otherwise.
		@rtype: C{FixedValue} or C{VariableValue}
		"""
		str = str.strip()
		if str[0] == '?':
			return VariableValue(str[1:])
		else:
			return Category.parse(str)
	parse = staticmethod(parse)

class VariableValue(FeatureValue):
	"""
	A value for a feature that depends on other values.
	"""
	def __init__(self, varname):
		"""
		Creates a new VariableValue.
		
		@param varname: the name of the variable
		@type varname: C{string}
		"""
		self._varname = varname
	def __str__(self):
		return "?"+self._varname
	def __repr__(self):
		return str(self)
	def __eq__(self, other):
		return isinstance(other, VariableValue) and other.varname() == self.varname()
	def varname(self): return self._varname
	def symbol(self): return str(self)
	def match(self, other):
		if isinstance(other, VariableValue):
			return {}
		else:
			return {self.varname(): other}

class Category(FeatureValue):
	"""
	A C{Category} can be used to tag a grammatical structure with features that
	propagate up the parse tree, instead of a symbol that is simply a string. A
	C{Category} contains a symbol, plus a dictionary mapping feature names to
	C{Feature}s. Non-variable values of features are themselves Categories.

	There are three ways to create a category:
		- Build the dictionary yourself, and use the constructor
		- Use the C{Category.make()} static method, which takes a list of
		  features instead of a dictionary
		- Use C{Category.parse()} to construct a category from its string
		  representation.
	"""

	def __init__(self, symbol, dict=None):
		"""
		Creates a new C{Category}.

		@param symbol: A string representing this grammatical structure.
		@type symbol: C{string}
		@param dict: The dictionary mapping feature names to C{Feature}s.
		(The feature name is stored redundantly for efficiency - for example,
		the string C{'plural'} might map to the feature C{'plural +'}.)
		@type dict: C{dict}
		"""
		if dict is None: dict = {}
		self._symbol = symbol
		self._dict = dict
		self._str = self._getStr()
	
	def __div__(self, rhs):
		"""
		Raises a TypeError. The / operation on nonterminals is meaningless
		for Categories.
		"""
		raise TypeError
	def symbol(self):
		return self._symbol
	def matches(self, other):
		return self.match(other) is not None
	def match(self, other):
		"""
		Tests to see if this Category matches another Category. This may cause
		the values of variables to become set.

		Two categories match if:
			- One is a StarCategory (*), or
			- Their C{symbol}s are equal, and each feature in the first matches
			  the second.

		Matching categories may require unifying some variables. If the
		categories can match, this method returns a dictionary of variables
		that must be assigned. The keys are varable names (strings), and the
		values are the variable values (also strings). If the categories cannot
		match, this method returns None.

		@return: a dictionary of variable assignments if the categories can
		match, C{None} otherwise
		@rtype: C{dict} or C{NoneType}
		"""
		if isinstance(other, StarCategory): return {}
		#if isinstance(other, VariableValue): return other.match(self)
		if isinstance(other, VariableValue): return {}
		if isinstance(other, NullCategory): return None
		if type(other) == type(""): return None
		if self.symbol() != other.symbol(): return None
		else:
			result = {}
			for featurename in self._dict.keys() + other._dict.keys():
				if self._dict.has_key(featurename):
					feature = self._dict[featurename]
				else:
					isRequired = other._dict[featurename].isRequired()
					if isRequired: value = NullCategory()
					else: value = StarCategory()
					feature = Feature(featurename, value, isRequired)
				a = other.match_feature(feature)
				result = merge(result, a)
			return result
	
	def match_feature(self, feature):
		"""
		A feature matches a Category if:
			- The Category is *, or
			- The feature is not required, and does not exist in the Category,
			  or
			- A feature with that name exists in the Category, with a value
			  that matches the first feature's value.
		
		@return: a dictionary of variable assignments if the categories can
		match, C{None} otherwise.
		@rtype: C{dict} or C{NoneType}
		"""
		if self._dict.has_key(feature.name()):
			return self._dict[feature.name()].match(feature)
		else:
			return feature.defaultValue().match(feature.value())
	def getFeature(self, name):
		result = self._dict.get(name)
		if result is None: return Feature(name, NullCategory())
		else: return result
	def _getStr(self):
		keys = self._dict.keys()
		keys.sort()
		if len(keys) > 0:
			return "%s%s" % (self._symbol, [self._dict[key] for key in keys])
		else: return self._symbol
	def __str__(self): return self._str
	def __repr__(self):
		return str(self)
	def __eq__(self, other):
		if type(other) == Nonterminal:
			return self.symbol() == other.symbol()
		if hash(self) != hash(other): return False
		return str(self) == str(other)
	def __hash__(self):
		return hash(str(self))
	def __cmp__(self, other):
		return cmp(str(self), str(other))
	def matchFor(self, other):
		vars = self.match(other)
		if vars is None: return None
		return self.usingValues(vars)
	def usingValues(self, vars):
		newdict = {}
		for (name, feature) in self._dict.items():
			value = feature.value()
			if isinstance(value, VariableValue):
				if vars.has_key(value.varname()):
					if vars[value.varname()] != feature.defaultValue():
						newdict[name] = Feature(name, vars[value.varname()],
						feature.isRequired())
				else:
					newdict[name] = Feature(name, value, feature.isRequired())
			else:
				newdict[name] = Feature(name, value.usingValues(vars),
				feature.isRequired())
		return Category(self._symbol, newdict)
	
	# static methods
	def make(symbol, features):
		"""
		Create a C{Category} from a symbol and a list of C{Feature}s.

		@param symbol: the symbol for the category
		@type symbol: C{str}
		@param features: a list of features for the category
		@type features: C{list} of C{Feature}s
		@return: a new Category using the symbol and features
		@rtype: C{Category}
		"""
		dict = {}
		for f in features:
			dict[feature.name()] = feature
		return Category(symbol, dict)
	def parse(str):
		str = str.strip()
		if str == '*': return StarCategory()
		if '[' not in str: return Category(str, {})
		bracketpos = str.find('[')
		symbol = str[:bracketpos]
		features = str[bracketpos+1 : -1]
		features = splitWithBrackets(features, ',[]')
		dict = {}
		if features != ['']:
			for f in features:
				feature = Feature.parse(f)
				dict[feature.name()] = feature
		return Category(symbol, dict)
	parse = staticmethod(parse)

def parse(str):
	"""
	Parse a string as either a C{VariableValue}, C{Category}, a
	rule, or a lexical definition.
	"""
	tokens = splitWithBrackets(str)
	if '->' in tokens: return parseRule(str)
	elif len(tokens) == 1: return FeatureValue.parse(str)
	else: return parseDefinition(str)

def parseRule(str):
	"""
	Parse a string as a rule (a C{CFGProduction} of C{Categories}).
	"""
	tokens = splitWithBrackets(str)
	if not len(tokens) >= 3 and tokens[1] != '->':
		raise "This doesn't look like a rule:\n\t%s" % str
	return CFGProduction(Category.parse(tokens[0]),
						 *tuple(map(lambda x: Category.parse(x), tokens[2:])))

def parseDefinition(str):
	"""
	Parse a string as a lexical definition, and return a list of
	C{CFGProductions} that comprise that definition.
	"""
	tokens = splitWithBrackets(str)
	if not len(tokens) >= 2:
		raise "This doesn't look like a definition:\n\t%s" % str
	word = tokens[0]
	return map(lambda x: CFGProduction(parse(x), word), tokens[1:])

class StarCategory(Category):
	"""
	The special category *, which matches anything.
	"""
	def __init__(self):
		self._dict = {}
	def symbol(self):
		return '*'
	def match(self, other):
		return {}
	def match_feature(self, feature):
		return {}
	def matchFor(self, other):
		return StarCategory()
	def usingValues(self, vars):
		return StarCategory()
	def __eq__(self, other):
		return isinstance(other, StarCategory)
	def __str__(self):
		return '*'
	def __repr__(self):
		return str(self)

class NullCategory(Category):
	def __init__(self):
		self._dict = {}
	def symbol(self):
		return '0'
	def match(self, other):
		if isinstance(other, StarCategory) or isinstance(other, VariableValue):
			return other.match(self)
		elif isinstance(other, NullCategory):
			return {}
		else: return None
	def matchFor(self, other):
		if self.match(other) is not None: return NullCategory()
		else: return None
	def usingValues(self, vars):
		return NullCategory()
	def __eq__(self, other):
		return isinstance(other, NullCategory)
	def __str__(self):
		return '0'
	def __repr__(self):
		return str(self)

class FeatureProductionEdge(chart.ProductionEdge):
	"""
	A ProductionEdge that can keep track of the values of variables, in order
	to match and propagate variable values up the parse tree.
	"""
	def __init__(self, prod, structure, loc, dotpos, vars, children):
		chart.ProductionEdge.__init__(self, prod, structure, loc, dotpos)
		# The 'structure' shows the particular structure that this edge was
		# generated from, but it is not compared for equality, so not all
		# parse trees will be represented in 'structure'. All parse trees
		# can be recovered from 'children', though.
		self._vars = vars
		self._lhs = self._prod.lhs().usingValues(self._vars)
		self._children = children
		self._compare = (self._prod, self._children)
		#items = self._vars.items()
		#items.sort()
		#items = tuple(items)
		#self._hash = hash((self._prod, self._loc, self._dotpos, items))
		self._hash = hash((self._compare, self._loc, self._dotpos, self._lhs))
	def vars(self):
		return self._vars
	def lhs(self):
		return self._lhs
	def children(self):
		return self._children
	def __str__(self):
		str = '%s ->' % (self._lhs, )
		for i in range(len(self._prod.rhs())):
			if i == self._dotpos: str += ' @'
			if isinstance(self._prod.rhs()[i], Nonterminal):
				str += ' %s' % (self._prod.rhs()[i],)
			else:
				str += ' %r' % (self._prod.rhs()[i],)
		return str+" %s" % self._vars
	def __hash__(self):
		return self._hash
	def __cmp__(self, other):
		if hash(self) != hash(other): return cmp(hash(self), hash(other))
		else: return cmp(\
		(self._compare, self._loc, self._dotpos, self._lhs),
		(other._compare, other._loc, other._dotpos, other._lhs))
	def __eq__(self, other):
		return cmp(self, other) == 0

def self_loop_edge(production, loc, vars=None):
	if vars is None: vars={}
	assert _chktype(1, production, CFGProduction)
	assert _chktype(2, loc, Location)
	assert _chktype(3, vars, dict)
	treetok = TreeToken(production.lhs())
	return FeatureProductionEdge(production, treetok, loc, 0, vars, ())

def fr_edge(edge1, edge2, vars=None):
	if vars is None: vars={}
	assert _chktype(1, edge1, chart.EdgeI)
	assert _chktype(2, edge2, chart.EdgeI)
	assert _chktype(3, vars, dict)
	vars1 = {}
	if isinstance(edge1, FeatureProductionEdge): vars1 = edge1.vars()
	loc = edge1.loc().union(edge2.loc())
	treechildren = edge1.structure().children() + (edge2.structure(),)
	treetok = TreeToken(edge1.structure().node(), *treechildren)
	newchildren = edge1.children() + (EdgeDescription.fromEdge(edge2),)
	newvars = merge(vars1, vars)
	if newvars is None: result = None
	else: result = FeatureProductionEdge(edge1.prod(), treetok, loc,
					edge1.dotpos()+1, newvars, newchildren)
	if debug:
		print "Fundamental rule:\n\tedge1 = %s\n\tedge2 = %s\n\tvars=%s\n\tresult = %s" %\
		(edge1, edge2, vars, result)
	return result

# vim:ts=4:sts=4:nowrap
