# Natural Language Toolkit: Feature Structures
#
# Copyright (C) 2003 University of Pennsylvania
# Author: Edward Loper <edloper@ldc.upenn.edu>,
#         Rob Speer (original code)
# URL: <http://nltk.sourceforge.net>
# For license information, see LICENSE.TXT
#
# $Id$


"""
Basic data classes for representing feature structures.  A X{feature
structure} is a mapping from feature names to feature values, where:

  - Each X{feature name} is a case sensitive string.
  - Each X{feature value} can be a base value (such as a string), a
    variable, or a nested feature structure.

Feature structures are typically used to represent partial information
about objects.  A feature name that is not mapped to a value stands
for a feature whose value is unknown (I{not} a feature without a
value).  Two feature structures that represent (potentially
overlapping) information about the same object can be combined by
X{unification}.  When two inconsistant feature structures are unified,
the unification fails and returns C{None}.

Features are usually specified using X{feature paths}, or tuples of
feature names that specify path through the nested feature structures
to a value.

Feature structures may contain reentrant feature values.  A
X{reentrant feature value} is a single feature value that can be
accessed via multiple feature paths.  Unification preserves the
reentrance relations imposed by both of the unified feature
structures.  After unification, any extensions to a reentrant feature
value will be visible using any of its feature paths.

Feature structure variables are encoded using the
L{FeatureStructureVariable} class.  Feature structure variables are
essentially just names; they do not directly contain values.  Instead,
the mapping from variables to values is encoded externally to the
variable, as a set of X{bindings}.  These bindings are stored using
the L{FeatureStructureVariableBinding} class, which maintains two
types of information about variables:

  - For X{bound variables}, or variables that have been assigned
    values, it records their values.
    
  - For X{unbound variables}, or variables that have not been assigned
    values, it records which variables have been set equal to each
    other, or X{merged}.  When an unbound variable is bound to a new
    value, any variables that it has been merged with will be bound to
    the same value.
"""

# Open question: should there be a "feature" object?
#
# The current implementation doesn't actually include an object to
# encode a "feature" (i.e., a name/value pair).  This makes the code
# simpler -- one less class to deal with, and you can directly query
# for feature values, rather than going through a feature object.  But
# there might be use cases for adding a Feature object.  E.g., if we
# wanted to assign properties (like is_required) to features.  But I'd
# like to see some compelling use cases before we add it.

import re, copy
from nltk.chktype import chktype as _chktype

#//////////////////////////////////////////////////////////////////////
# Variables and variable bindings
#//////////////////////////////////////////////////////////////////////

class FeatureStructureVariable:
    """
    A variable that can stand for a single feature value in a feature
    structure.  Each variable is uniquely identified by a case
    sensitive identifier.  Any two C{FeatureStructureVariable} objects
    with the same identifier are treated as the same variable.

    Variables do not directly contain values; instead, the mapping
    from variables to values is encoded externally as a set of
    bindings, using L{FeatureStructureVariableBinding}.

    @see: L{FeatureStructure}
    """
    def __init__(self, identifier):
        """
        Construct a new feature structure variable.
        @type identifier: C{string}
        @param identifier: A unique identifier for this variable.
            Any two C{FeatureStructureVariable} objects with the
            same identifier are treated as the same variable.
        """
        assert _chktype(1, identifier, str)
        self._identifier = identifier

    def identifier(self):
        """
        @return: This variable's unique identifier.
        @rtype: C{string}
        """
        return self._identifier

    def __repr__(self):
        """
        @return: A string representation of this feature structure
           variable.  A feature structure variable with identifier
           C{I{x}} is represented as C{'?I{x}'}.
        """
        return '?%s' % self._identifier

    def __cmp__(self, other):
        if not isinstance(other, FeatureStructureVariable): return -1
        return cmp(self._identifier, other._identifier)

    def __hash__(self):
        return self._identifier.__hash__()

class FeatureStructureVariableBinding:
    """
    A set of bindings for feature structure variables.  Each variable
    is either X{bound} (i.e., assigned a value), or X{unbound} (i.e.,
    left unspecified).  Two or more unbound variables can be set equal
    by X{merging} them together.  When an unbound variable is assigned
    a value, any variables that have been merged with it will also be
    assigned that value.

    Feature structure variable bindings are monotonic: once a value is
    bound, it cannot be unbound or rebound.

    @note: There is one exception to the rule that bindings are
    monotonic: when unifying a bound variable with another value, the
    variable's value might be replaced by an equal value, to preserve
    reentrancy.

    @group Variable Binding: bind, bound_variables, lookup, is_bound
    @group Variable Merging: merge, merged_variables, synonyms
    @param _bindings: A dictionary mapping from bound variables
        to their values.
    @param _synonyms: A dictionary mapping from unbound variables
        to other variables that they have been merged with.
    """
    def __init__(self, **initial_bindings):
        """
        Construct a new set of bindings for feature structure
        variables.
        @param initial_bindings: The initial set of bindings and
            merged variables.  This dictionary should map
            variables to either values or other variables.  If a
            variable maps to a value, it will be bound to that
            value.  If a variable maps to another variable, then
            the two variables will be merged.
        """
        self._bindings = {}
        self._synonyms = {}

        # Look for variables to merge.
        for (src, dst) in initial_bindings.items():
            if isinstance(dst, FeatureStructureVariable):
                self.merge(src, dst)

        # Look for variables to bind.  (n.b.: this is intentionally
        # done *after* looking for variables to merge.)
        for (src, dst) in initial_bindings.items():
            if not isinstance(dst, FeatureStructureVariable):
                self.bind(src, dst)

    def variables(self):
        """
        @return: A list of all variables that have been bound
            to other values or merged with other variables.
        @rtype: C{list} of L{FeatureStructureVariable}
        """
        return self._bindings.keys() + self._synonyms.keys()

    def bound_variables(self):
        """
        @return: A list of all variables that have been bound to
            values.
        @rtype: C{list} of L{FeatureStructureVariable}
        """
        return self._bindings.keys()

    def merged_variables(self):
        """
        @return: A list of all variables that have been merged
            with other variables.
        @rtype: C{list} of L{FeatureStructureVariable}
        """
        return self._synonyms.keys()

    def synonyms(self, variable):
        """
        @return: A list of the variables that C{variable} has been
        merged with.
        """
        assert _chktype(1, variable, FeatureStructureVariable)
        if self._bindings.has_key(variable):
            raise ValueError('Only unbound variables can have synonyms')
        return self._synonyms.get(variable, {variable:1}).keys()

    def is_bound(self, variable):
        """
        @return: true if the given variable is bound to a value.
        @rtype: C{bool}
        """
        assert _chktype(1, variable, FeatureStructureVariable)
        return self._bindings.has_key(variable)

    def lookup(self, variable):
        """
        @return: The value that the given variable is bound to; or
            the variable itself, if it's not bound.
        """
        assert _chktype(1, variable, FeatureStructureVariable)
        return self._bindings.get(variable, variable)
    
    def merge(self, var1, var2):
        """
        Merge two unbound variables together.
        @raise ValueError: if C{var1} or C{var2} is already bound.
        """
        assert _chktype(1, var1, FeatureStructureVariable)
        assert _chktype(1, var2, FeatureStructureVariable)
        if self._bindings.has_key(var1) or self._bindings.has_key(var2):
            raise ValueError('Only unbound variables may be merged')
        # If var1 isn't listed in self._synonyms, add it:
        self._synonyms.setdefault(var1, {var1:1})
        # Combine the merge lists for var1 and var2 into var1.
        self._synonyms[var1].update(self._synonyms.get(var2, {var2:1}))
        # Copy the new merge list into var2.
        self._synonyms[var2] = self._synonyms[var1]

    def bind(self, variable, value):
        """
        Bind an unbound variable to a value.
        @raise ValueError: If C{variable} is already bound.
        @raise ValueError: If C{value} is a variable.  (Variables
            cannot be bound to other variables; use L{merge()}
            instead.)
        """
        assert _chktype(1, variable, FeatureStructureVariable)
        if isinstance(value, FeatureStructureVariable):
            raise ValueError('Variables cannot be bound to other '+
                             'variables; use merge() instead.')
        if self._bindings.has_key(variable):
            raise ValueError('Bound variables may not be rebound')
        for variable in self._synonyms.get(variable,{variable:1}).keys():
            self._bindings[variable] = value

    def _rebind(self, variable, new_value):
        """
        Replace the value that a variable is bound to with an equal
        value.  This is used by L{FeatureStructure.
        _cleanup_binding_forwards} to preserve reentrance when
        unifying feature structures.
        @precondition: The old binding for C{variable} is equal to
            C{new_value}.
        @precondition: C{variable} is bound.
        """
        self._bindings[variable] = new_value

    def __repr__(self):
        vars = self.variables()
        if self._bindings:
            return '<Bindings: %s>' % repr(self._bindings)[1:-1]
        else:
            return '<Bindings (empty)>'

    def __cmp__(self, other):
        if not isinstance(other, FeatureStructureVariable): return -1
        return cmp((self._bindings, self._synonyms),
                   (other._bindings, other._synonyms))
        
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

    def __cmp__(self, other):
        if self==other: return 0
        else: return -1

    #################################################################
    ## Unification
    #################################################################

    # Unification is done in two steps:
    #   1. Make copies of self and other, and destructively unify
    #      them.
    #   2. Make a pass through the unified structure to make sure
    #      that we preserved reentrancy.
    def unify(self, other, bindings=None):
        """
        @param bindings: Modified during unification.
        """
        # If no bindings initial were specified, then everything
        # starts out unbound.
        apply_bindings = (bindings is None)
        if bindings is None:
            bindings = FeatureStructureVariableBinding()

        # Make copies of self & other (since the unification algorithm
        # is destructive).
        selfcopy = copy.deepcopy(self)
        othercopy = copy.deepcopy(other)
        
        # Do the unification.
        try: selfcopy._destructively_unify(othercopy, bindings)
        except FeatureStructure._UnificationFailureError: return None

        # Clean up any forwards.
        selfcopy._cleanup_forwards({})
        selfcopy._cleanup_binding_forwards(bindings)
        
        # Apply the variable bindings.
        if apply_bindings:
            selfcopy._apply_and_normalize_bindings(bindings, {})
        
        # Return the result.
        return selfcopy

    def _apply_and_normalize_bindings(self, bindings, visited):
        # Only visit each node once:
        if visited.has_key(id(self)): return
        visited[id(self)] = 1
    
        for (fname, fval) in self._features.items():
            if isinstance(fval, FeatureStructureVariable):
                if bindings.is_bound(fval):
                    self._features[fname] = bindings.lookup(fval)
                else:
                    pass
                    #self._features[fname] = bindings.normalize(fval)
            elif isinstance(fval, FeatureStructure):
                fval._apply_and_normalize_bindings(bindings, visited)

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
                if isinstance(selfval, FeatureStructureVariable):
                    selfval = bindings.lookup(selfval)
                if isinstance(otherval, FeatureStructureVariable):
                    otherval = bindings.lookup(otherval)
                
                # Case 1: unify 2 feature structures (recursive case)
                if (isinstance(selfval, FeatureStructure) and
                    isinstance(otherval, FeatureStructure)):
                    selfval._destructively_unify(otherval, bindings)
                    
                # Case 2: unify 2 variables
                elif (isinstance(selfval, FeatureStructureVariable) and
                    isinstance(otherval, FeatureStructureVariable)):
                    bindings.merge(selfval, otherval)
                
                # Case 3: unify a variable with a value
                elif isinstance(selfval, FeatureStructureVariable):
                    bindings.bind(selfval, otherval)
                elif isinstance(otherval, FeatureStructureVariable):
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
    
    def _cleanup_binding_forwards(self, bindings):
        for var in bindings._bindings.keys():
            value = bindings.lookup(var)
            if (isinstance(value, FeatureStructure) and
                value._forward is not None):
                while value._forward is not None:
                    value = value._forward
                bindings._rebind(var, value)

    #################################################################
    ## String Represenations
    #################################################################

    def __repr__(self):
        """
        Display a single-line representation of this feature structure,
        suitable for embedding in other representations.
        """
        return self._repr(self._find_reentrances({}), {})

    def __str__(self):
        """
        Display a multi-line representation of this feature structure
        as an FVM (feature value matrix).
        """
        return '\n'.join(self._str(self._find_reentrances({}), {}))

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

        # If this is the first time we've seen a reentrant structure,
        # then assign it a unique identifier.
        if reentrances[id(self)]:
            assert not reentrance_ids.has_key(id(self))
            reentrance_ids[id(self)] = `len(reentrance_ids)+1`

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
                fval_repr = fval._repr(reentrances, reentrance_ids)
                segments.append('%s = %s' % (fname, fval_repr))

        # If it's reentrant, then add on an identifier tag.
        if reentrances[id(self)]:
            return '(%s) [%s]' % (reentrance_ids[id(self)],
                                ', '.join(segments))
        else:
            return '[%s]' % (', '.join(segments))

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
        # If this is the first time we've seen a reentrant structure,
        # then tack on an id string.
        if reentrances[id(self)]:
            assert not reentrance_ids.has_key(id(self))
            reentrance_ids[id(self)] = `len(reentrance_ids)+1`

        # Special case:
        if len(self._features) == 0:
            if reentrances[id(self)]:
                return ['(%s) []' % reentrance_ids[id(self)]]
            else:
                return ['[]']
        
        # What's the longest feature name?  Use this to align names.
        maxfnamelen = max([len(k) for k in self._features.keys()])

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
                            
                # Separate FeatureStructures by a blank line.
                lines.append('')

        # Get rid of any excess blank lines.
        if lines[-1] == '': lines = lines[:-1]
        
        # Add brackets around everything.
        maxlen = max([len(line) for line in lines])
        lines = ['[ %s%s ]' % (line, ' '*(maxlen-len(line))) for line in lines]

        # If it's reentrant, then add on an identifier tag.
        if reentrances[id(self)]:
            idstr = '(%s) ' % reentrance_ids[id(self)]
            lines = [(' '*len(idstr))+l for l in lines]
            idline = (len(lines)-1)/2
            lines[idline] = idstr + lines[idline][len(idstr):]

        return lines

    # Walk through the feature tree.  The first time we see a feature
    # value, map it to False (not reentrant).  If we see a feature
    # value more than once, then map it to C{True} (reentrant).
    def _find_reentrances(self, reentrances):
        """
        Find all of the feature values contained by self that are
        reentrant (i.e., that can be reached by multiple paths through
        feature structure's features).  Return a dictionary
        C{reentrances} that maps from the C{id} of each feature value
        to a boolean value, indicating whether it is reentrant or not.
        """
        if reentrances.has_key(id(self)):
            # We've seen it more than once.
            reentrances[id(self)] = True
        else:
            # This is the first time we've seen it.
            reentrances[id(self)] = False
        
            # Recurse to contained feature structures.
            for fval in self._features.values():
                if isinstance(fval, FeatureStructure):
                    fval._find_reentrances(reentrances)

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

        # Add calls to the FeatureStructureVariable constructor.
        str = re.sub(r'"\?(\w+)"', r'FeatureStructureVariable("\1")', str)
        
        # Strip whitespace and get rid of the comma after the last ')' 
        str = str.strip()
        
        # Use "eval" to convert the string
        try:
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
        cvar = FeatureStructureVariable('cvar')
        dvar = FeatureStructureVariable('dvar')
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
        x = FeatureStructureVariable('x')
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

