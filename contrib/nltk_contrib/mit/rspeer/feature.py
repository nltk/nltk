from nltk.featurestruct import *
from nltk.cfg import Nonterminal

class Category(FeatureStruct, Nonterminal):
	"""
	A C{Category} is a specialized feature structure, intended for use in
	parsing.  It can act as a C{Nonterminal}.

	A C{Category} differs from a C{FeatureStructure} in these ways:
		- Categories may not be re-entrant.
		- Categories use value-based equality, while FeatureStructures use
		  identity-based equality.
		- Categories may contain a list of I{required features}, which are
		  names of features whose value is None if unspecified. A Category
		  lacking a feature that is required in it will not unify with any
		  Category that has that feature. If a required feature's value is
		  None, it is considered to be not present.
		- True and False are allowed as values. A feature named 'foo' with a
		  value of True is simply expressed as C{+foo}. Similarly, if it is
		  False, it is expressed as C{-foo}.
	"""
	
	requiredFeatures = ['/']
	
	def requireFeature(name): # static
		"""
		Designates a feature name as a required feature. All Categories
		constructed after this will include that name as a required feature.
		Existing Categories are unaffected.
		"""
		if name not in Category.requiredFeatures:
			Category.requiredFeatures.append(name)
	requireFeature = staticmethod(requireFeature)
	
	def unrequireFeature(name): # static
		"""
		Indicates that a feature name should no longer be required. All
		Categories constructed after this will not include that name as a
		required feature. Existing Categories are unaffected.
		"""
		if name in Category.requiredFeatures:
			Category.requiredFeatures.remove(name)
	unrequireFeature = staticmethod(unrequireFeature)

	def __init__(self, **features):
		self._features = features
		self._required = Category.requiredFeatures
		for name in self._required:
			if not self._features.has_key(name):
				self._features[name] = None
		items = self._features.items()
		items.sort()
		self._hash = hash(tuple(items))
		self._memorepr = None
				
	def required_features(self):
		"A list of the names of all required features."
		return self._required

	def __cmp__(self, other):
		return cmp(repr(self), repr(other))
	
	def __div__(self, other):
		temp = self.deepcopy()
		dict = temp._features
		dict['/'] = other
		return Category(**dict)

	def __eq__(self, other):
		"""
		@return: True if C{self} and C{other} assign the same value to
		to every feature.  In particular, return true if
		C{self[M{p}]==other[M{p}]} for every feature path M{p} such
		that C{self[M{p}]} or C{other[M{p}]} is a base value (i.e.,
		not a nested feature structure).
		"""
		
		# Get the result of equal_values, and make it a real boolean while
		# we're at it.
		if not isinstance(other, Category): return False
		if hash(self) != hash(other): return False
		return (self.equal_values(other) == True)

	def __ne__(self, other):
		return not (self == other)

	def __hash__(self):
		return self._hash

	def symbol(self):
		return self._features.get('symbol')
	
	def deepcopy(self, memo=None):
		newcopy = Category()
		features = newcopy._features

		# Fill out the features.
		for (fname, fval) in self._features.items():
			if isinstance(fval, FeatureStruct):
				features[fname] = fval.deepcopy()
			else:
				features[fname] = fval

		return newcopy
	
	def reentrances(self):
		return []

	def feature_names(self):
		return filter(lambda x: not (x in self._required and self[x] is None),
		self._features.keys())
	
	def get_feature(self, *args):
		try:
			return self.__getitem__(*args)
		except IndexError:
			return StarValue()
	
	def has_feature(self, name):
		return (name in self.feature_names())
	
	def __repr__(self):
		if self._memorepr is None:
			self._memorepr = self._repr({}, {})
		return self._memorepr
	
	def _repr(self, reentrances, reentrance_ids):
		"""
		@return: A string representation of this feature structure.
		@param reentrances: A dictionary that maps from the C{id} of
			each feature value in self, indicating whether that value
			is reentrant or not.
		@param reentrance_ids: A dictionary mapping from the C{id}s
			of feature values to unique identifiers.  This is modified
			by C{repr}: the first time a reentrant feature value is
			displayed, an identifier is added to reentrance_ids for
			it.
		"""
		segments = []

		items = self.feature_names()
		items.sort() # sorting note: keys are unique strings, so we'll
					 # never fall through to comparing values.
		for fname in items:
			if fname == 'symbol': continue
			fval = self[fname]
			if isinstance(fval, bool):
				if fval: segments.append('+%s' % fname)
				else: segments.append('-%s' % fname)
			elif not isinstance(fval, Category):
				segments.append('%s=%r' % (fname, fval))
			else:
				fval_repr = fval._repr(reentrances, reentrance_ids)
				segments.append('%s=%s' % (fname, fval_repr))

		symbol = self._features.get('symbol')
		if symbol is None: symbol = ''
		return '%s[%s]' % (symbol, ', '.join(segments))

	def _str(self, reentrances, reentrance_ids):
		"""
		@return: A list of lines composing a string representation of
			this feature structure.  
		@param reentrances: A dictionary that maps from the C{id} of
			each feature value in self, indicating whether that value
			is reentrant or not.
		@param reentrance_ids: A dictionary mapping from the C{id}s
			of feature values to unique identifiers.  This is modified
			by C{repr}: the first time a reentrant feature value is
			displayed, an identifier is added to reentrance_ids for
			it.
		"""

		# Special case:
		if len(self.feature_names()) == 0:
			return ['[]']
		if self.feature_names() == ['symbol']:
			return ['%s[]' % self['symbol']]
		
		
		# What's the longest feature name?	Use this to align names.
		maxfnamelen = max([len(k) for k in self.feature_names()])

		lines = []
		items = self.feature_names()
		items.sort() # sorting note: keys are unique strings, so we'll
					 # never fall through to comparing values.
		if 'symbol' in items:
			items.remove('symbol')
			items.insert(0, 'symbol')
		for fname in items:
			fval = self[fname]
			if not isinstance(fval, FeatureStruct):
				# It's not a nested feature structure -- just print it.
				lines.append('%s = %r' % (fname.ljust(maxfnamelen), fval))

			else:
				# It's a new feature structure.  Separate it from
				# other values by a blank line.
				if lines and lines[-1] != '': lines.append('')

				# Recursively print the feature's value (fval).
				fval_lines = fval._str(reentrances, reentrance_ids)
				
				# Indent each line to make room for fname.
				fval_lines = [(' '*(maxfnamelen+3))+l for l in fval_lines]

				# Pick which line we'll display fname on.
				nameline = (len(fval_lines)-1)/2
				
				fval_lines[nameline] = (
						fname.ljust(maxfnamelen)+' ='+
						fval_lines[nameline][maxfnamelen+2:])

				# Add the feature structure to the output.
				lines += fval_lines
							
				# Separate FeatureStructs by a blank line.
				lines.append('')

		# Get rid of any excess blank lines.
		if lines[-1] == '': lines = lines[:-1]
		
		# Add brackets around everything.
		maxlen = max([len(line) for line in lines])
		lines = ['[ %s%s ]' % (line, ' '*(maxlen-len(line))) for line in lines]

		return lines

	# Regular expressions for parsing.
	_PARSE_RE = {'name': re.compile(r'\s*([^\s\(\)"\'\-=,\[\]]+)\s*'),
				 'categorystart': re.compile(r'\s*([^\s\(\)"\'\-=,\[\]]*)\s*\['),
				 'bool': re.compile(r'\s*([-\+])'),
				 'ident': re.compile(r'\s*\((\d+)\)\s*'),
				 'reentrance': re.compile(r'\s*->\s*'),
				 'assign': re.compile(r'\s*=\s*'),
				 'bracket': re.compile(r'\s*]\s*'),
				 'comma': re.compile(r'\s*,\s*'),
				 'none': re.compile(r'None(?=\s|\]|,)'),
				 'int': re.compile(r'-?\d+(?=\s|\]|,)'),
				 'var': re.compile(r'\?[a-zA-Z_][a-zA-Z0-9_]*'+'|'+
								   r'\?<[a-zA-Z_][a-zA-Z0-9_]*'+
								   r'(=[a-zA-Z_][a-zA-Z0-9_]*)*>'),
				 'symbol': re.compile(r'\w+'),
				 'stringmarker': re.compile("['\"\\\\]")}
	
	def parse(s):
		"""
		Convert a string representation of a feature structure (as
		displayed by repr) into a C{Category}.	This parse
		imposes the following restrictions on the string
		representation:
		  - Feature names cannot contain any of the following:
			whitespace, parenthases, quote marks, equals signs,
			dashes, and square brackets.
		  - Only the following basic feature value are supported:
			strings, integers, variables, C{None}, and unquoted
			alphanumeric strings.
		"""
		try:
			value, position = Category._parse(s, 0, {})
		except ValueError, e:
			estr = ('Error parsing field structure\n\n\t' +
					s + '\n\t' + ' '*e.args[1] + '^ ' +
					'Expected %s\n' % e.args[0])
			raise ValueError, estr
		if position != len(s): raise ValueError()
		return value
	
	def _parse(s, position=0, reentrances=None):
		"""
		Helper function that parses a Category.
		@param s: The string to parse.
		@param position: The position in the string to start parsing.
		@param reentrances: A dictionary from reentrance ids to values.
		@return: A tuple (val, pos) of the feature structure created
			by parsing and the position where the parsed feature
			structure ends.
		"""
		# A set of useful regular expressions (precompiled)
		_PARSE_RE = Category._PARSE_RE

		# Find the symbol, if there is one.
		match = _PARSE_RE['name'].match(s, position)
		if match is not None:
			symbol = match.group(1)
			position = match.end()
		else: symbol = None
		
		# Check that the name is followed by an open bracket.
		if s[position] != '[': raise ValueError('open bracket', position)
		position += 1

		# If it's immediately followed by a close bracket, then just
		# return an empty feature structure.
		match = _PARSE_RE['bracket'].match(s, position)
		if match is not None:
			if symbol is None: return Category(), match.end()
			else: return Category(symbol=symbol), match.end()

		# Build a list of the features defined by the structure.
		# Each feature has one of the three following forms:
		#	  name = value
		#	  +name
		#	  -name
		features = {}
		if symbol is not None: features['symbol'] = symbol
		while position < len(s):
			# Use these variables to hold info about the feature:
			name = target = val = None
			
			# Is this a shorthand boolean value?
			match = _PARSE_RE['bool'].match(s, position)
			if match is not None:
				if match.group(1) == '+': val = True
				else: val = False
				position = match.end()
			
			# Find the next feature's name.
			match = _PARSE_RE['name'].match(s, position)
			if match is None: raise ValueError('feature name', position)
			name = match.group(1)
			position = match.end()
			
			# If it's not a shorthand boolean, it must be an assignment.
			if val is None:
				match = _PARSE_RE['assign'].match(s, position)
				if match is None: raise ValueError('equals sign', position)
				position = match.end()

				val, position = Category._parseval(s, position, reentrances)
			features[name] = val
					
			# Check for a close bracket
			match = _PARSE_RE['bracket'].match(s, position)
			if match is not None:
				return Category(**features), match.end()
				
			# Otherwise, there should be a comma
			match = _PARSE_RE['comma'].match(s, position)
			if match is None: raise ValueError('comma', position)
			position = match.end()
			
		# We never saw a close bracket.
		raise ValueError('close bracket', position)

	def _parseval(s, position, reentrances):
		"""
		Helper function that parses a feature value.  Currently
		supports: None, integers, variables, strings, nested feature
		structures.
		@param s: The string to parse.
		@param position: The position in the string to start parsing.
		@param reentrances: A dictionary from reentrance ids to values.
		@return: A tuple (val, pos) of the value created by parsing
			and the position where the parsed value ends.
		"""
		# A set of useful regular expressions (precompiled)
		_PARSE_RE = Category._PARSE_RE
		
		# End of string (error)
		if position == len(s): raise ValueError('value', position)
		
		# String value
		if s[position] in "'\"":
			start = position
			quotemark = s[position:position+1]
			position += 1
			while 1: 
				match = _PARSE_RE['stringmarker'].search(s, position)
				if not match: raise ValueError('close quote', position)
				position = match.end()
				if match.group() == '\\': position += 1
				elif match.group() == quotemark:
					return eval(s[start:position]), position

		# Nested category
		if _PARSE_RE['categorystart'].match(s, position) is not None:
			return Category._parse(s, position, reentrances)

		# Variable
		match = _PARSE_RE['var'].match(s, position)
		if match is not None:
			return FeatureVariable.parse(match.group()), match.end()

		# None
		match = _PARSE_RE['none'].match(s, position)
		if match is not None:
			return None, match.end()

		# Integer value
		match = _PARSE_RE['int'].match(s, position)
		if match is not None:
			return int(match.group()), match.end()

		# Alphanumeric symbol (must be checked after integer)
		match = _PARSE_RE['symbol'].match(s, position)
		if match is not None:
			return Category(symbol=match.group()), match.end()

		# We don't know how to parse this value.
		raise ValueError('value', position)

	_parseval=staticmethod(_parseval)
	_parse=staticmethod(_parse)
	parse=staticmethod(parse)


