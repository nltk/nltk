from nltk.featurestruct import *
from nltk.cfg import Nonterminal, CFGProduction
import string

class Category(FeatureStruct, Nonterminal):
	"""
	A C{Category} is a specialized feature structure, intended for use in
	parsing.  It can act as a C{Nonterminal}.

	A C{Category} differs from a C{FeatureStructure} in these ways:
		- Categories may not be re-entrant.
		
		- Categories use value-based equality, while FeatureStructures use
		  identity-based equality.

		- Strings in Categories are compared case-insensitively.
		  
		- Categories have one feature marked as the 'head', which prints
		  differently than other features if it has a value. For example,
		  in the repr() representation of a Category, the head goes to the
		  left, on the outside of the brackets. Subclasses of Category
		  may change the feature name that is designated as the head, which is
		  _head by default.

		- Subclasses of Category may contain a list of I{required features},
		  which are names of features whose value is None if unspecified. A
		  Category lacking a feature that is required in it will not unify with
		  any Category that has that feature. If a required feature's value is
		  None, it is considered to be not present.
		  
		- True and False are allowed as values. A feature named 'foo' with a
		  value of True is simply expressed as C{+foo}. Similarly, if it is
		  False, it is expressed as C{-foo}.
	"""
	
	headname = '_head'
	requiredFeatures = []
	
	def __init__(self, **features):
		self._features = features
		self._required = self.__class__.requiredFeatures
		for name in self._required:
			if not self._features.has_key(name):
				self._features[name] = None
		items = self._features.items()
		items.sort()
		self._hash = None
		self._frozen = False
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
		return self.__class__(**dict)

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
		if not other.__class__ == self.__class__: return False
		if hash(self) != hash(other): return False
		return (self.equal_values(other) == True)

	def __ne__(self, other):
		return not (self == other)

	def __hash__(self):
		if self._hash is not None: return self._hash
		items = self._features.items()
		items.sort()
		return hash(tuple(items))
	
	def freeze(self):
		self._hash = hash(self)
	
	def __setitem__(self, name, value):
		if self._frozen: raise "Cannot modify a frozen Category"
		self._features[name] = value
	
	def symbol(self):
		return repr(self)

	def head(self):
		return self._features.get(self.__class__.headname)
	
	def deepcopy(self, memo=None):
		newcopy = self.__class__()
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
	
	# All this is unlikely to be necessary. All I've changed is to make
	# strings case-insensitive.
	def _destructively_unify(self, other, bindings, trace=False, depth=0):
		"""
		Attempt to unify C{self} and C{other} by modifying them
		in-place.  If the unification succeeds, then C{self} will
		contain the unified value, and the value of C{other} is
		undefined.	If the unification fails, then a
		_UnificationFailureError is raised, and the values of C{self}
		and C{other} are undefined.
		"""
		if trace:
			# apply_forwards to get reentrancy links right:
			self._apply_forwards({})
			other._apply_forwards({})
			print '  '+'|   '*depth+' /'+`self`
			print '  '+'|   '*depth+'|\\'+ `other`
		
		# Look up the "cannonical" copy of other.
		while hasattr(other, '_forward'): other = other._forward

		# If self is already identical to other, we're done.
		# Note: this, together with the forward pointers, ensures
		# that unification will terminate even for cyclic structures.
		# [XX] Verify/prove this?
		if self is other:
			if trace:
				print '  '+'|   '*depth+'|'
				print '  '+'|   '*depth+'| (identical objects)'
				print '  '+'|   '*depth+'|'
				print '  '+'|   '*depth+'+-->'+`self`
			return

		# Set other's forward pointer to point to self; this makes us
		# into the cannonical copy of other.
		other._forward = self

		for (fname, otherval) in other._features.items():
			if trace:
				trace_otherval = otherval
				trace_selfval_defined = self._features.has_key(fname)
				trace_selfval = self._features.get(fname)
			if self._features.has_key(fname):
				selfval = self._features[fname]
				# If selfval or otherval is a bound variable, then
				# replace it by the variable's bound value.
				if isinstance(selfval, FeatureVariable):
					selfval = bindings.lookup(selfval)
				if isinstance(otherval, FeatureVariable):
					otherval = bindings.lookup(otherval)
				
				if trace:
					print '  '+'|   '*(depth+1)
					print '  '+'%s| Unify %s feature:'%('|   '*(depth),fname)
					
				# Case 1: unify 2 feature structures (recursive case)
				if (isinstance(selfval, FeatureStruct) and
					isinstance(otherval, FeatureStruct)):
					selfval._destructively_unify(otherval, bindings,
												 trace, depth+1)

				# Case 2: unify 2 variables
				elif (isinstance(selfval, FeatureVariable) and
					  isinstance(otherval, FeatureVariable)):
					self._features[fname] = selfval.alias(otherval)
				
				# Case 3: unify a variable with a value
				elif isinstance(selfval, FeatureVariable):
					bindings.bind(selfval, otherval)
				elif isinstance(otherval, FeatureVariable):
					bindings.bind(otherval, selfval)

				# Case 4A: unify two strings.
				elif isinstance(selfval, str) and isinstance(otherval, str)\
				and selfval.upper() == otherval.upper(): pass
					
				# Case 4: unify 2 non-equal values (failure case)
				elif selfval != otherval:
					if trace: print '  '+'|   '*depth + 'X <-- FAIL'
					raise FeatureStruct._UnificationFailureError()

				# Case 5: unify 2 equal values
				else: pass

				if trace and not isinstance(selfval, FeatureStruct):
					# apply_forwards to get reentrancy links right:
					if isinstance(trace_selfval, FeatureStruct):
						trace_selfval._apply_forwards({})
					if isinstance(trace_otherval, FeatureStruct):
						trace_otherval._apply_forwards({})
					print '  '+'%s|    /%r' % ('|   '*(depth), trace_selfval)
					print '  '+'%s|   |\\%r' % ('|   '*(depth), trace_otherval)
					print '  '+'%s|   +-->%r' % ('|   '*(depth),
											self._features[fname])
					
			# Case 5: copy from other
			else:
				self._features[fname] = otherval

		if trace:
			# apply_forwards to get reentrancy links right:
			self._apply_forwards({})
			print '  '+'|   '*depth+'|'
			print '  '+'|   '*depth+'+-->'+`self`
			if len(bindings.bound_variables()) > 0:
				print '  '+'|   '*depth+'    '+`bindings`
 
	
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
			if fname == self.__class__.headname: continue
			fval = self[fname]
			if isinstance(fval, bool):
				if fval: segments.append('+%s' % fname)
				else: segments.append('-%s' % fname)
			elif not isinstance(fval, Category):
				segments.append('%s=%r' % (fname, fval))
			else:
				fval_repr = fval._repr(reentrances, reentrance_ids)
				segments.append('%s=%s' % (fname, fval_repr))

		head = self._features.get(self.__class__.headname)
		if head is None: head = ''
		if head and not len(segments): return head
		return '%s[%s]' % (head, ', '.join(segments))

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
		if self.feature_names() == [self.__class__.headname]:
			return ['%s[]' % self[self.__class__.headname]]
		
		
		# What's the longest feature name?	Use this to align names.
		maxfnamelen = max([len(k) for k in self.feature_names()])

		lines = []
		items = self.feature_names()
		items.sort() # sorting note: keys are unique strings, so we'll
					 # never fall through to comparing values.
		if self.__class__.headname in items:
			items.remove(self.__class__.headname)
			# items.insert(0, self.__class__.headname)
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
		headline = (len(lines) - 1)/2
		if self.has_feature(self.__class__.headname):
			head = self[self.__class__.headname]
		else: head = ''
		maxlen = max([len(line) for line in lines])
		for l in range(len(lines)):
			line = lines[l]
			if l == headline:
				lines[l] = ('%s[ %s%s ]' % (head, line, ' '*(maxlen-len(line))))
			else:
				lines[l] = ('%s[ %s%s ]' % (' '*len(head), line, ' '*(maxlen-len(line))))

		return lines

	# Regular expressions for parsing.
	_PARSE_RE = {'name': re.compile(r'\s*([^\s\(\)"\'\-=,\[\]]+)\s*'),
				 'categorystart': re.compile(r'\s*([^\s\(\)"\'\-=,\[\]]*)\s*\['),
				 'bool': re.compile(r'\s*([-\+])'),
				 'ident': re.compile(r'\s*\((\d+)\)\s*'),
				 'arrow': re.compile(r'\s*->\s*'),
				 'assign': re.compile(r'\s*=\s*'),
				 'bracket': re.compile(r'\s*]\s*'),
				 'comma': re.compile(r'\s*,\s*'),
				 'none': re.compile(r'None(?=\s|\]|,)'),
				 'int': re.compile(r'-?\d+(?=\s|\]|,)'),
				 'var': re.compile(r'\?[a-zA-Z_][a-zA-Z0-9_]*'+'|'+
								   r'\?<[a-zA-Z_][a-zA-Z0-9_]*'+
								   r'(=[a-zA-Z_][a-zA-Z0-9_]*)*>'),
				 'symbol': re.compile(r'\w+'),
				 'disjunct': re.compile(r'\s*\|\s*'),
				 'whitespace': re.compile(r'\s*'),
				 'stringmarker': re.compile("['\"\\\\]")}
	
	def parse(cls, s):
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
			value, position = cls._parse(s, 0, {})
		except ValueError, e:
			estr = ('Error parsing field structure\n\n\t' +
					s + '\n\t' + ' '*e.args[1] + '^ ' +
					'Expected %s\n' % e.args[0])
			raise ValueError, estr
		if position != len(s): raise ValueError()
		return value
	
	def _parse(cls, s, position=0, reentrances=None):
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
		_PARSE_RE = cls._PARSE_RE

		# Find the head, if there is one.
		match = _PARSE_RE['name'].match(s, position)
		if match is not None:
			head = match.group(1)
			position = match.end()
		else: head = None
		
		# Check that the name is followed by an open bracket.
		if position >= len(s) or s[position] != '[':
			return cls(**{cls.headname: head}), position
		position += 1

		# If it's immediately followed by a close bracket, then just
		# return an empty feature structure.
		match = _PARSE_RE['bracket'].match(s, position)
		if match is not None:
			if head is None: return cls(), match.end()
			else: return cls(**{cls.headname: head}), match.end()

		# Build a list of the features defined by the structure.
		# Each feature has one of the three following forms:
		#	  name = value
		#	  +name
		#	  -name
		features = {}
		if head is not None: features[cls.headname] = head
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

				val, position = cls._parseval(s, position, reentrances)
			features[name] = val
					
			# Check for a close bracket
			match = _PARSE_RE['bracket'].match(s, position)
			if match is not None:
				return cls(**features), match.end()
				
			# Otherwise, there should be a comma
			match = _PARSE_RE['comma'].match(s, position)
			if match is None: raise ValueError('comma', position)
			position = match.end()
			
		# We never saw a close bracket.
		raise ValueError('close bracket', position)

	def _parseval(cls, s, position, reentrances):
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
		_PARSE_RE = cls._PARSE_RE
		
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
			return cls._parse(s, position, reentrances)

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
			return cls(**{cls.headname: match.group()}), match.end()

		# We don't know how to parse this value.
		raise ValueError('value', position)
	
	def parse_rule(cls, s):
		_PARSE_RE = cls._PARSE_RE
		position = 0
		lhs, position = cls._parse(s, position)
		match = _PARSE_RE['arrow'].match(s, position)
		if match is None: raise ValueError('arrow', position)
		else: position = match.end()
		rhs = []
		while position < len(s):
			val, position = cls._parseval(s, position)
			position = _PARSE_RE['whitespace'].match(s, position).end()
			rhs.append(val)
		return CFGProduction(lhs, *rhs)

	def parse_rules(cls, s):
		_PARSE_RE = cls._PARSE_RE
		position = 0
		lhs, position = cls._parse(s, position)
		match = _PARSE_RE['arrow'].match(s, position)
		if match is None: raise ValueError('arrow', position)
		else: position = match.end()
		rules = []
		while position < len(s):
			rhs = []
			while position < len(s) and _PARSE_RE['disjunct'].match(s,
			position) is None:
				val, position = cls._parseval(s, position, {})
				rhs.append(val)
				position = _PARSE_RE['whitespace'].match(s, position).end()
			rules.append(CFGProduction(lhs, *rhs))
			
			if position < len(s):
				match = _PARSE_RE['disjunct'].match(s, position)
				position = match.end()
		return rules

	_parseval=classmethod(_parseval)
	_parse=classmethod(_parse)
	parse=classmethod(parse)
	parse_rule=classmethod(parse_rule)
	parse_rules=classmethod(parse_rules)

class SyntaxCategory(Category):
	headname = 'pos'
	requiredFeatures = ['/']
	
	# This class also changes the parsing so that slash features display
	# in a special way (more consistent with teaching materials).
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
			if fname == self.__class__.headname or fname == '/': continue
			fval = self[fname]
			if isinstance(fval, bool):
				if fval: segments.append('+%s' % fname)
				else: segments.append('-%s' % fname)
			elif not isinstance(fval, Category):
				segments.append('%s=%r' % (fname, fval))
			else:
				fval_repr = fval._repr(reentrances, reentrance_ids)
				segments.append('%s=%s' % (fname, fval_repr))
		
		head = self._features.get(self.__class__.headname)
		if head is None: head = ''
		if not len(segments): features = ''
		else: features = "[%s]" % ', '.join(segments)
		slash = self._features.get('/')
		if slash is None: slash = ''
		else: slash = '/%r' % slash
		
		return '%s%s%s' % (head, features, slash)

	_PARSE_RE = {'name': re.compile(r'\s*([^\s\(\)"\'\-=,\[\]/]+)\s*'),
				 'categorystart': re.compile(r'\s*([^\s\(\)"\'\-=,\[\]/]*)\s*(\[|/)'),
				 'bool': re.compile(r'\s*([-\+])'),
				 'ident': re.compile(r'\s*\((\d+)\)\s*'),
				 'arrow': re.compile(r'\s*->\s*'),
				 'assign': re.compile(r'\s*=\s*'),
				 'bracket': re.compile(r'\s*]\s*'),
				 'comma': re.compile(r'\s*,\s*'),
				 'none': re.compile(r'None(?=\s|\]|,)'),
				 'int': re.compile(r'-?\d+(?=\s|\]|,)'),
				 'var': re.compile(r'\?[a-zA-Z_][a-zA-Z0-9_]*'+'|'+
								   r'\?<[a-zA-Z_][a-zA-Z0-9_]*'+
								   r'(=[a-zA-Z_][a-zA-Z0-9_]*)*>'),
				 'symbol': re.compile(r'\w+'),
				 'disjunct': re.compile(r'\s*\|\s*'),
				 'slash': re.compile(r'\s*/\s*'),
				 'whitespace': re.compile(r'\s*'),
				 'stringmarker': re.compile("['\"\\\\]")}
	
	def _parse(cls, s, position=0, reentrances=None):
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
		_PARSE_RE = cls._PARSE_RE

		features = {}
		
		# Find the head, if there is one.
		match = _PARSE_RE['name'].match(s, position)
		if match is not None:
			features[cls.headname] = match.group(1)
			position = match.end()
		
		# If the name is followed by an open bracket, start looking for
		# features.
		if position < len(s) and s[position] == '[':
			position += 1
	
			# Build a list of the features defined by the structure.
			# Each feature has one of the three following forms:
			#	  name = value
			#	  +name
			#	  -name
			while True:
				if not position < len(s):
					raise ValueError('close bracket', position)
			
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
	
					val, position = cls._parseval(s, position, reentrances)
				features[name] = val
						
				# Check for a close bracket
				match = _PARSE_RE['bracket'].match(s, position)
				if match is not None:
					position = match.end()
					# Get out and check for a slash value.
					break	
					
				# Otherwise, there should be a comma
				match = _PARSE_RE['comma'].match(s, position)
				if match is None: raise ValueError('comma', position)
				position = match.end()
			
		# Check for a slash value
		match = _PARSE_RE['slash'].match(s, position)
		if match is not None:
			position = match.end()
			slash, position = cls._parseval(s, position, 0)
			features['/'] = slash
		
		return cls(**features), position
		
	_parse = classmethod(_parse)

