"""
A preliminary feature structure module.

Based loosely on C{feature.py} by Rob Speer.

Should there be a feature object?
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
The current implementation doesn't actually include an object to
encode a "feature" (i.e., a name/value pair).  This makes the code
simpler -- one less class to deal with, and you can directly query for
feature values, rather than going through a feature structure.  But
there might be use cases for adding a Feature object.  E.g., if we
wanted to assign properties (like is_required) to features.  But I'd
like to see some compelling use cases before we add it.

NullCategory and StarCategory
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Rob's code included 2 special feature values: star and null.  Star
unifies with everything, and null unifies with (almost) nothing.  In
Rob's code, null does unify with star and with itself; although I'm
not sure what the justification for that is.

This version doesn't include anything like the star & null values; and
I'm not convinced that we need them.  In particular, a feature with a
value of star acts just like an unspecified feature.  And I'm not sure
what the use cases for the Null value are.  It's possible that the
star value would be more meaningful if we also implemented
feature.is_required.  But for both values, I'd like to see some use
cases before we decide whether and how to add them.
"""

import re, copy

# This class doesn't actually do anything; all the work is done
# by FeatureVariableBinding, and during unification.  All that
# matters is that 2 FeatureVariables with the same identifier
# should compare equal.
class FeatureVariable:
    """
    A variable that can stand for a single feature value in a feature
    structure.  A feature value can either be a base value (immutable
    and hashable) or a C{FeatureStructure}.
    """
    _next_autoid = 0

    def __init__(self, identifier=None):
        # Generate an automatic identifier, if none was specified.
        if identifier==None:
            id = str(FeatureVariable._next_autoid)
            FeatureVariable._next_autoid += 1
        self._identifier = identifier

    def __repr__(self):
        return '?%s' % self._identifier

    def __cmp__(self, other):
        if not isinstance(other, FeatureVariable): return -1
        return cmp(self._identifier, other._identifier)

    def __hash__(self):
        return self._identifier.__hash__()

# This is used to keep track of a set of bound variables.  We can't
# get away with just using a dictionary, because we might want to
# "merge" unbound variables together (see docstring), and that's not
# convenient to represent in a dictionary.
class FeatureVariableBinding:
    """
    A set of bindings for feature variables.  Each variable is either
    bound to a value, or unbound.  Two or more unbound variables can
    be set equal by X{merging} them together.  When an unbound
    variable is bound to a value, any variables that have been merged
    with it will also be bound to that value.

    Feature variable bindings are monotonic: once a value is bound, it
    cannot be unbound or rebound.
    """
    def __init__(self, **initial_bindings):
        # [XX] check for variables that are bound together and
        # merge them instead of putting them in bindings??
        self._bindings = initial_bindings
        self._merged_vars = {}

    def bound_variables(self):
        return self._bindings.keys()

    def is_bound(self, variable):
        return self._bindings.has_key(variable)

    def lookup(self, variable):
        """
        return the value it's bound to; or the variable itself if it's
        not bound.
        """
        return self._bindings.get(variable, variable)
    
    def merge(self, var1, var2):
        if self._bindings.has_key(var1) or self._bindings.has_key(var2):
            raise ValueError('Only unbound variables may be merged')
        varlist = (self._merged_vars.get(var1,[var1]) +
                   self._merged_vars.get(var2,[var2]))
        self._merged_vars[var1] = varlist
        self._merged_vars[var2] = varlist

    def bind(self, var, value):
        if self._bindings.has_key(var):
            raise ValueError('Bound variables may not be rebound')
        for var in self._merged_vars.get(var,[var]):
            self._bindings[var] = value

    def __repr__(self):
        return '<Bindings: %s; Merged=%s>' % (self._bindings,
                                              self._merged_vars)

# This corresponds to "Category" in Rob Speer's code.
class FeatureStructure:
    """
    A structured set of features.  These features are represented as a
    mapping from feature names to feature values, where each feature
    value is either a basic value (such as a string or an integer), or
    a nested feature structure.

    A feature structure's feature values can be accessed via indexing:

      >>> fstruct1 = FeatureStructure(number='singular', person='3rd')
      >>> print fstruct1['number']
      'singular'

      >>> fstruct2 = FeatureStructure(subject=fstruct1)
      >>> print fstruct2['subject']['person']
      '3rd'

    A nested feature value can be also accessed via a X{feature
    paths}, or a tuple of feature names that specifies the paths to
    the nested feature:

      >>> fpath = ('subject','number')
      >>> print fstruct2[fpath]
      'singular'

    Feature structures may contain reentrant feature values.  A
    X{reentrant feature value} is a single feature value that can be
    accessed via multiple feature paths.

    @note: Should I present them as DAGs instead?  That would make it
        easier to explain reentrancy.
    @ivar _features: A dictionary mapping from feature names to values.

    @ivar _forward: A pointer to another feature structure that
        replaced this feature structure.  This is used during the
        unification process to preserve reentrance.  In particular, if
        we're unifying feature structures A and B, where:

          - x and y are feature paths.
          - A contains a feature structure A[x]
          - B contains a reentrant feature structure B[x]=B[y]

        Then we need to ensure that in the unified structure C,
        C[x]=C[y].  (Here the equals sign is used to denote the object
        identity relation, i.e., C{is}.)
    """
    def __init__(self, **features):
        self._features = features
        self._forward = None

    def __getitem__(self, index):
        if type(index) == str:
            return self._features[index]
        elif len(index) == 0:
            return self
        elif len(index) == 1:
            return self._features[index[0]]
        elif isinstance(self._features[index[0]], FeatureStructure):
            return self._features[index[0]][index[1:]]
        else:
            raise IndexError('Bad feature path')

    def feature_names(self):
        return self._features.keys()

    #################################################################
    ## Unification
    #################################################################

    # Unification is done in two steps:
    #   1. Make copies of self and other, and destructively unify
    #      them.
    #   2. Make a pass through the unified structure to make sure
    #      that we preserved reentrancy.
    def unify(self, other):
        try:
            # Make copies of self & other (since unification is
            # destructive). 
            selfcopy = copy.deepcopy(self)
            othercopy = copy.deepcopy(other)
            
            # Create an empty set of variable bindings.
            bindings = FeatureVariableBinding()

            # Do the unification.
            selfcopy._destructively_unify(othercopy, bindings)
            selfcopy._cleanup_forwards({})

            # Clean up any forwards in the bindings.
            selfcopy._cleanup_binding_forwards(bindings)

            # Apply the variable bindings.
            selfcopy._apply_bindings(bindings, {})

            # Return the result.
            return selfcopy
        except FeatureStructure._UnificationFailureError: return None

    # [XX] This cheats (breaks abstraction barrier)
    def _cleanup_binding_forwards(self, bindings):
        for var in bindings._bindings.keys():
            if isinstance(bindings._bindings[var], FeatureStructure):
                while bindings._bindings[var]._forward is not None:
                    bindings._bindings[var] = bindings._bindings[var]._forward

    def unify_with_bindings(self, other, initial_bindings=None):
        """
        Unify self with other, and return both the unified structure
        and the variable bindings necessary for unification.

        @rtype: C{(L{FeatureStructure}, L{FeatureVariableBinding})}
        """
        if initial_bindings is None:
            initial_bindings = FeatureVariableBinding()

        try:
            # Make copies of self & other (since unification is
            # destructive).
            selfcopy = copy.deepcopy(self)
            othercopy = copy.deepcopy(other)

            # Do the unification.
            selfcopy._destructively_unify(othercopy, bindings)
            selfcopy._cleanup_forwards({})

            # Clean up any forwards in the bindings.
            selfcopy._cleanup_binding_forwards(bindings)

            # Return the unified value and the bindings
            return selfcopy, bindings
        except FeatureStructure._UnificationFailureError: return None
            

    def _apply_bindings(self, bindings, visited):
        # Only visit each node once:
        if visited.has_key(id(self)): return
        visited[id(self)] = 1
    
        for (fname, fval) in self._features.items():
            if (isinstance(fval, FeatureVariable) and
                bindings.is_bound(fval)):
                self._features[fname] = bindings.lookup(fval)
            if isinstance(fval, FeatureStructure):
                fval._apply_bindings(bindings, visited)

    class _UnificationFailureError(Exception):
        """
        An exception that is used by C{_destructively_unify} to abort
        unification when a failure is encountered.
        """

    def _destructively_unify(self, other, bindings):
        """
        Attempt to unify C{self} and C{other} by modifying them
        in-place.  If the unification succeeds, then C{self} will
        contain the unified value, and the value of C{other} is
        undefined.  If the unification fails, then a
        _UnificationFailureError is raised, and the values of C{self}
        and C{other} are undefined.
        """
        # Look up the "cannonical" copy of other.
        while other._forward is not None: other = other._forward

        # Set other's forward pointer to point to self; this makes us
        # into the cannonical copy of other.
        other._forward = self
        
        for (fname, otherval) in other._features.items():
            if self._features.has_key(fname):
                selfval = self._features[fname]

                # If selfval or otherval is a bound variable, then
                # replace it by the variable's bound value.
                if isinstance(selfval, FeatureVariable):
                    selfval = bindings.lookup(selfval)
                if isinstance(otherval, FeatureVariable):
                    otherval = bindings.lookup(otherval)
                
                # Case 1: unify 2 feature structures (recursive case)
                if (isinstance(selfval, FeatureStructure) and
                    isinstance(otherval, FeatureStructure)):
                    selfval._destructively_unify(otherval, bindings)
                    
                # Case 2: unify 2 variables
                elif (isinstance(selfval, FeatureVariable) and
                    isinstance(otherval, FeatureVariable)):
                    bindings.merge(selfval, otherval)
                
                # Case 3: unify a variable with a value
                elif isinstance(selfval, FeatureVariable):
                    bindings.bind(selfval, otherval)
                elif isinstance(otherval, FeatureVariable):
                    bindings.bind(otherval, selfval)
                    
                # Case 4: unify 2 non-equal values (failure case)
                elif selfval != otherval:
                    raise FeatureStructure._UnificationFailureError()
                
            # Case 5: copy from other
            else:
                self._features[fname] = otherval

    def _cleanup_forwards(self, visited):
        """
        Use the C{_forward} links on a feature structure generated
        by L{_destructively_unify} to ensure that reentrancy is
        preserved.
        """
        # Only visit each node once:
        if visited.has_key(id(self)): return
        visited[id(self)] = 1
        
        for fname, fval in self._features.items():
            if isinstance(fval, FeatureStructure):
                if fval._forward is not None:
                    self._features[fname] = fval._forward
                fval._cleanup_forwards(visited)
    
    #################################################################
    ## String Represenations
    #################################################################

    def __repr__(self):
        """
        Display a single-line representation of this feature structure,
        suitable for embedding in other representations.
        """
        return self._repr(self._find_reentrances(), {})

    def __str__(self):
        """
        Display a multi-line representation of this feature structure
        as an FVM (feature value matrix).
        """
        return '\n'.join(self._str(self._find_reentrances(), {}))

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
        items = self._features.items()
        items.sort() # sorting note: keys are unique strings, so we'll
                     # never fall through to comparing values.
        for (fname, fval) in items:
            if not isinstance(fval, FeatureStructure):
                segments.append('%s = %s' % (fname, fval))
            elif reentrance_ids.has_key(id(fval)):
                segments.append('%s -> (%s)' % (fname,
                                                reentrance_ids[id(fval)]))
            else:
                is_reentrant = reentrances[id(fval)]
                if is_reentrant:
                    # Pick a new id.
                    reentrance_ids[id(fval)] = len(reentrance_ids)+1
                    
                fval_repr = fval._repr(reentrances, reentrance_ids)
                if is_reentrant:
                    segments.append('%s = (%d) %s' % 
                                    (fname, reentrance_ids[id(fval)],
                                     fval_repr))
                else:
                    segments.append('%s = %s' % (fname, fval_repr))
        return '[' + ', '.join(segments) + ']'

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
        if len(self._features) == 0:
            return ['[]']
        
        # What's the longest feature name?  Use this to align names.
        maxfnamelen = max([len(fname) for fname in self._features.keys()])

        lines = []
        items = self._features.items()
        items.sort() # sorting note: keys are unique strings, so we'll
                     # never fall through to comparing values.
        for (fname, fval) in items:
            if not isinstance(fval, FeatureStructure):
                # It's not a nested feature structure -- just print it.
                lines.append('%s = %s' % (fname.ljust(maxfnamelen), fval))

            elif reentrance_ids.has_key(id(fval)):
                # It's a feature structure we've seen before -- print
                # the reentrance id.
                lines.append('%s -> (%s)' % (fname.ljust(maxfnamelen),
                                               reentrance_ids[id(fval)]))

            else:
                # It's a new feature structure.  Separate it from
                # other values by a blank line.
                if lines and lines[-1] != '': lines.append('')

                # Is it reentrant?  If so, assign it an id number.
                is_reentrant = reentrances[id(fval)]
                if is_reentrant:
                    # Pick a new id.
                    reentrance_ids[id(fval)] = len(reentrance_ids)+1
                    
                # Recursively print the feature's value (fval).
                fval_lines = fval._str(reentrances, reentrance_ids)
                
                # Indent each line to make room for fname.
                fval_lines = [(' '*(maxfnamelen+3))+l for l in fval_lines]

                # Pick which line we'll display fname on.
                nameline = (len(fval_lines)-1)/2
                
                # Is it reentrant?  If it is, display its id
                # (along with fname) on the name line.
                if is_reentrant:
                    # Indent each line to make room for the id.
                    fid = ' (%s)' % reentrance_ids[id(fval)]
                    fval_lines = [(' '*len(fid))+l for l in fval_lines]
                    # Display the id and the name.
                    fval_lines[nameline] = (
                        fname.ljust(maxfnamelen)+' ='+str(fid)+
                        fval_lines[nameline][maxfnamelen+len(fid)+2:])

                # If it's not reentrant, then just display fname
                # on the name line.
                else:
                    fval_lines[nameline] = (
                        fname.ljust(maxfnamelen)+' ='+
                        fval_lines[nameline][maxfnamelen+2:])

                # Add the feature structure to the output.
                lines += fval_lines
                            
                # Separate FeatureStructures by a blank line.
                lines.append('')

        # Get rid of any excess blank lines.
        if lines[-1] == '': lines = lines[:-1]
        
        # Add brackets around everything.
        maxlen = max([len(line) for line in lines])
        lines = ['[ %s%s ]' % (line, ' '*(maxlen-len(line))) for line in lines]

        return lines

    def _find_reentrances(self, reentrances=None, visited=None):
        """
        Find all of the feature values contained by self that are
        reentrant (i.e., that can be reached by multiple paths through
        feature structure's features).  Return a dictionary
        C{reentrances} that maps from the C{id} of each feature value
        to a boolean value, indicating whether it is reentrant or not.
        """
        if reentrances is None: reentrances={}

        # Visit each node only once.
        if visited is None: visited={}
        if visited.has_key(id(self)): return
        visited[id(self)] = 1

        # Walk through the feature tree.  The first time we see a
        # feature value, map it to False (not reentrant).  If we see a
        # feature value more than once, then map it to C{True}
        # (reentrant).
        for fval in self._features.values():
            # False the first time we see it; True if we see it more
            # than once.
            reentrances[id(fval)] = reentrances.has_key(id(fval))
            # Recurse to contained feature structures.
            if isinstance(fval, FeatureStructure):
                fval._find_reentrances(reentrances, visited)

        return reentrances

    #################################################################
    ## Parsing
    #################################################################

    # [XX] This won't read in reentrant structures.
    # [XX] Audit this code to make sure the call to eval is secure.
    def parse(str):
        # Get rid of any newlines, etc.
        str = ' '.join(str.split())

        # Backslash any quote marks or backslashes in the string.
        str = re.sub(r'([\\"\'])', r'\\\1', str)
        
        # Add quote marks and commas around words.
        str = re.sub('([^\[\] ,=]+)', r'"\1"', str)

        # Replace '=' with ':'
        str = str.replace('=', ':')

        # Change close brackets.
        str = str.replace(r']', '})')
        
        # Add calls to the FeatureStructure constructor.
        str = str.replace(r'[', 'FeatureStructure(**{')

        # Add calls to the FeatureVariable constructor.
        str = re.sub(r'"\?(\w+)"', r'FeatureVariable("\1")', str)
        
        # Strip whitespace and get rid of the comma after the last ')' 
        str = str.strip()
        
        # Use "eval" to convert the string
        try:
            print str
            result = eval(str)
            return result
        except:
            raise ValueError('Bad FeatureStructure string')

    parse=staticmethod(parse)


#//////////////////////////////////////////////////////////////////////
# TESTING...
#//////////////////////////////////////////////////////////////////////

import unittest

# Note: since FeatureStructure.__repr__() sorts by keys before
# displaying, there is a single unique string repr for each
# FeatureStructure.
class FeatureStructureTestCase(unittest.TestCase):
    'Unit testing for FeatureStructure'

    def failUnlessEqualSorted(self, list1, list2):
        list1.sort()
        list2.sort()
        self.failUnlessEqual(list1, list2)

    def testUnification(self):
        'Test basic unification'

        # Copying from self to other.
        fs1 = FeatureStructure(number='singular')
        fs2 = fs1.unify(FeatureStructure())
        self.failUnlessEqual(repr(fs2), '[number = singular]')

        # Copying from other to self
        fs1 = FeatureStructure()
        fs2 = fs1.unify(FeatureStructure(number='singular'))
        self.failUnlessEqual(repr(fs2), '[number = singular]')

        # Cross copying
        fs1 = FeatureStructure(number='singular')
        fs2 = fs1.unify(FeatureStructure(person='3rd'))
        self.failUnlessEqual(repr(fs2), '[number = singular, person = 3rd]')

        # Merging a nested structure
        fs1 = FeatureStructure(A=FeatureStructure(B='b'))
        fs2 = FeatureStructure(A=FeatureStructure(C='c'))
        fs3 = fs1.unify(fs2)
        self.failUnlessEqual(repr(fs3), '[A = [B = b, C = c]]')

    def testReentrantUnification(self):
        'Test unification of reentrant objects'
        fs1 = FeatureStructure(B='b')
        fs2 = FeatureStructure(A=fs1, E=FeatureStructure(F=fs1))
        fs3 = FeatureStructure(A=FeatureStructure(C='c'),
                               E=FeatureStructure(F=FeatureStructure(D='d')))
        
        fs4 = fs2.unify(fs3)
        fs4repr = '[A = (1) [B = b, C = c, D = d], E = [F -> (1)]]'
        self.failUnlessEqual(repr(fs4), fs4repr)

        fs5 = fs3.unify(fs2)
        fs5repr = '[A = (1) [B = b, C = c, D = d], E = [F -> (1)]]'
        self.failUnlessEqual(repr(fs5), fs5repr)

    def testVariableForwarding(self):
        'Test that bound variable values get forwarded appropriately'
        cvar = FeatureVariable('cvar')
        dvar = FeatureVariable('dvar')
        fs1x = FeatureStructure(X='x')
        fs1 = FeatureStructure(A=fs1x, B=fs1x, C=cvar, D=dvar)

        fs2y = FeatureStructure(Y='y')
        fs2z = FeatureStructure(Z='z')
        fs2 = FeatureStructure(A=fs2y, B=fs2z, C=fs2y, D=fs2z)

        fs3 = fs1.unify(fs2)
        fs3repr = ('[A = (1) [X = x, Y = y, Z = z], '+
                   'B -> (1), C -> (1), D -> (1)]')
        self.failUnlessEqual(repr(fs3), fs3repr)

    def testCyclicUnification(self):
        'Create a cyclic structure via unification'
        # Create the following cyclic feature structure:
        #     [G = (1) [H -> (1)], F = (1)]
        # Where fs['G'] == fs['G', 'H'] == fs['G', 'H', 'H'] == ...
        fs1 = FeatureStructure()
        fs2 = FeatureStructure()
        fs3 = FeatureStructure(F=fs1, G=fs1)
        fs4 = FeatureStructure(F=FeatureStructure(H=fs2), G=fs2)
        fs5 = fs3.unify(fs4)

        # Check that we got the value right.
        self.failUnlessEqual(repr(fs5), '[F = (1) [H -> (1)], G -> (1)]')

        # Check that we got the cyclicity right.
        self.failUnless(fs5['F'] is fs5['G'])
        self.failUnless(fs5['F'] is fs5['G', 'H'])
        self.failUnless(fs5['F'] is fs5['G', 'H', 'H'])
        self.failUnless(fs5['F'] is fs5[('G',)+(('H',)*10)])

    def testCyclicUnificationFromBinding(self):
        'create a cyclic structure via variables'
        x = FeatureVariable('x')
        fs1 = FeatureStructure(F=FeatureStructure(H=x))
        fs2 = FeatureStructure(F=x)
        fs3 = fs1.unify(fs2)

        # Check that we got the value right.
        self.failUnlessEqual(repr(fs3), '[F = (1) [H -> (1)]]')

        # Check that we got the cyclicity right.
        self.failUnless(fs3['F'] is fs3['F','H'])
        self.failUnless(fs3['F'] is fs3['F','H','H'])
        self.failUnless(fs3['F'] is fs3[('F',)+(('H',)*10)])

def testsuite():
    t1 = unittest.makeSuite(FeatureStructureTestCase)
    return unittest.TestSuite( (t1,) )

def test():
    runner = unittest.TextTestRunner()
    runner.run(testsuite())

if __name__ == '__main__':
    test()

    
        
    
