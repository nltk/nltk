# Natural Language Toolkit: Feature Structures
#
# Copyright (C) 2001-2007 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>,
#         Rob Speer,
#         Steven Bird <sb@csse.unimelb.edu.au>
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
X{unification}.  When two inconsistent feature structures are unified,
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

Feature structure variables are encoded using the L{FeatureVariable}
class.  Feature structure variables are essentially just names; they
do not directly contain values.  Instead, the mapping from variables
to values is encoded externally to the variable, as a set of
X{bindings}.  These bindings are stored using a dictionary.  If one
var is bound to another, then they are aliased.  the dict maps from
variables (not var names) to values.

@todo: more test cases
@sort: FeatStruct, FeatureVariable, AliasedFeatureVariable,
       FeatureBindings
@group Feature Structures: FeatStruct
@group Variables: FeatureVariable, AliasedFeatureVariable,
                  FeatureBindings
@group Unit Tests: FeatStructTestCase
"""

import re
from types import NoneType

from nltk.sem.logic import Variable, unique_variable

# [xx] deal with this later:
class SubstituteBindingsI:
    """
    An interface for classes that can perform substitutions for feature
    variables.
    """
    def substitute_bindings(self, bindings):
        """
        @return: The object that is obtained by replacing
        each variable bound by C{bindings} with its values.
        @rtype: (any)
        """
        raise NotImplementedError

class SubstituteBindingsMixin(object):
    pass

def unify(*args, **kw):
    raise ValueError('xx')
def substitute_bindings(*args, **kw):
    raise ValueError('xx')
class UnificationFailure(Exception):
    'ack'

######################################################################
# Feature Structure
######################################################################

class FeatStruct(object):
    """
    A structured set of features.  These features are represented as a
    mapping from feature names to feature values, where each feature
    value is either a basic value (such as a string or an integer), or
    a nested feature structure.

    A feature structure's feature values can be accessed via indexing:

      >>> fstruct1 = FeatStruct(number='singular', person='3rd')
      >>> print fstruct1['number']
      'singular'

      >>> fstruct2 = FeatStruct(subject=fstruct1)
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

    @ivar _features: A dictionary mapping from feature names to values.

    @ivar _forward: A pointer to another feature structure that
        replaced this feature structure.  This is used during the
        unification process to preserve reentrance.  In particular, if
        we're unifying feature structures A and B, where:

          - x and y are feature paths.
          - A contains a feature structure A[x]
          - B contains a reentrant feature structure B[x] is B[y]

        Then we need to ensure that in the unified structure C,
        C[x] is C[y].  All forward pointers will be cleaned up
        before unification is done -- hmm.. use a fwd mapping
        instead?  that seems nicer!
    """
    def __init__(self, **features):
        self._features = features

    ##////////////////////////////////////////////////////////////
    ## Mapping Methods (i.e, dict-like methods)
    ##////////////////////////////////////////////////////////////
    
    def __getitem__(self, index):
        try:
            if isinstance(index, basestring):
                return self._features[index]
            elif not isinstance(index, tuple):
                raise TypeError('Expected str or tuple of str.  Got %r.' %
                                index)
            elif len(index) == 0:
                return self
            elif len(index) == 1:
                return self._features[index[0]]
            elif isinstance(self._features[index[0]], FeatStruct):
                return self._features[index[0]][index[1:]]
            else:
                raise KeyError(index)
        except KeyError:
            raise KeyError(index)

    def get(self, index, default=None):
        try:
            return self[index]
        except KeyError:
            return default

    def has_key(self, index):
        return index in self

    def __iter__(self):
        return iter(self._features)

    def __len__(self):
        return len(self._features)

    def __contains__(self, index):
        # (feature paths are ok here)
        try:
            self[index]
            return True
        except KeyError:
            return False

    def keys(self):
        return self._features.keys()
    def values(self):
        return self._features.values()
    def items(self):
        return self._features.items()

    def iterkeys(self):
        return self._features.iterkeys()
    def itervalues(self):
        return self._features.itervalues()
    def iteritems(self):
        return self._features.iteritems()

    ##////////////////////////////////////////////////////////////
    ## Equality
    ##////////////////////////////////////////////////////////////
    
    def equal_values(self, other, check_reentrance=False):
        """
        @return: True if C{self} and C{other} assign the same value to
        to every feature.  In particular, return true if
        C{self[M{p}]==other[M{p}]} for every feature path M{p} such
        that C{self[M{p}]} or C{other[M{p}]} is a base value (i.e.,
        not a nested feature structure).

        @param check_reentrance: If true, then any difference in the
            reentrance relations between C{self} and C{other} will
            cause C{equal_values} to return false.
        """
        if not isinstance(other, FeatStruct): return 0
        if check_reentrance: return `self` == `other`
        if len(self._features) != len(other._features): return 0
        for (fname, selfval) in self._features.items():
            otherval = other._features[fname]
            if isinstance(selfval, FeatStruct):
                if not selfval.equal_values(otherval): return 0
            else:
                if selfval != otherval: return 0
        return 1

    def __eq__(self, other):
        return self.equal_values(other)
    def __ne__(self, other):
        return not (self==other)
    def __hash__(self):
        raise TypeError('FeatStruct must be frozen to be hashed.')

    ##////////////////////////////////////////////////////////////
    ## Copying
    ##////////////////////////////////////////////////////////////

    def copy(self, deep=False):
        if deep:
            return self._deepcopy({})
        else:
            return FeatStruct(**self._features)
    
    def _deepcopy(self, memo):
        # Check the memoization dictionary.
        memo_copy = memo.get(id(self))
        if memo_copy is not None: return memo_copy

        # Create a new copy.  Do this *before* we fill out its
        # features, in case of cycles.
        newcopy = FeatStruct()
        memo[id(self)] = newcopy
        features = newcopy._features

        # Fill out the features.
        for (fname, fval) in self._features.items():
            if isinstance(fval, FeatStruct):
                features[fname] = fval._deepcopy(memo)
            else:
                features[fname] = fval

        return newcopy

    ##////////////////////////////////////////////////////////////
    ## Unsorted
    ##////////////////////////////////////////////////////////////

    def reentrances(self):
        """
        @return: A list of all feature structures that can be reached
            from C{self} by multiple feature paths.
        @rtype: C{list} of L{FeatStruct}
        """
        reentrance_dict = self._find_reentrances({})
        return [struct for (struct, reentrant) in reentrance_dict.items()
                if reentrant]

    def subsumes(self, other):
        """
        Check if this feature structure subsumes another feature structure.
        """
        return other.equal_values(self.unify(other))

    ##////////////////////////////////////////////////////////////
    ## Variables
    ##////////////////////////////////////////////////////////////

    def apply_bindings(self, bindings):
        """
        @return: The feature structure that is obtained by replacing
        each variable bound by C{bindings} with its values.

        This also has the effect of normalizing aliased variables.
        
        @rtype: L{FeatStruct}
        """
        selfcopy = self.copy(deep=True)
        selfcopy._apply_bindings(bindings, set())
        return selfcopy

    def _apply_bindings(self, bindings, visited):
        # Visit each node only once:
        if id(self) in visited: return
        visited.add(id(self))
        
        for (fname, fval) in self._features.items():
            # If it's a bound variable, then replace it with its
            # binding.  (If it's aliased, follow the alias chain.)
            if isinstance(fval, Variable) and fval in bindings:
                while isinstance(fval, Variable) and fval in bindings:
                    fval = bindings[fval]
                self._features[fname] = fval
            # If it's a feature structure, recurse.
            if isinstance(fval, FeatStruct):
                fval._apply_bindings(bindings, visited)

    def variables(self):
        """
        @return: The set of variables used by this feature structure.
        @rtype: C{set} of L{Variable}
        """
        return self._variables(set(), set())

    def _variables(self, vars, visited):
        # Visit each node only once:
        if id(self) in visited: return
        visited.add(id(self))
        for (fname, fval) in self._features.items():
            if isinstance(fval, Variable):
                vars.add(fval)
            elif isinstance(fval, FeatStruct):
                fval._variables(vars, visited)
        return vars

    def rename_variables(self, new_vars=None, used_vars=None):
        """
        @return: The feature structure that is obtained by replacing
        all variables in this feature structure that is listed in
        C{used_vars} with a new variable not listed in C{used_vars}.

        @type used_vars: C{set}
        @param used_vars: The set of variables that should be renamed.
        If not specified, C{self.variables()} is used; i.e., all
        variables will be given new names.

        @type new_vars: C{dict} from L{Variable} to L{Variable}
        @param new_vars: A dictionary that is used to hold the mapping
        from old variables to new variables.  For each variable M{v}
        in this feature structure:

          - If C{new_vars} maps M{v} to M{v'}, then M{v} will be
            replaced by M{v'}.
          - If C{new_vars} does not contain M{v}, then a new entry
            will be added to C{new_vars}, mapping M{v} to the new
            variable that is used to replace it.

        To consistantly rename the variables in a set of feature
        structures, simply apply rename_variables to each one, using
        the same dictionary:

            >>> new_vars = {}  # Maps old vars to alpha-renamed vars
            >>> new_fstruct1 = fstruct1.rename_variables(new_vars)
            >>> new_fstruct2 = fstruct2.rename_variables(new_vars)
            >>> new_fstruct3 = fstruct3.rename_variables(new_vars)

        If new_vars is not specified, then an empty dictionary is used.
        """
        if newv_vars is None: new_vars = {}
        if used_vars is None: new_vars = {}
        selfcopy = self.copy(deep=True)
        selfcopy._rename_variables(new_vars, used_vars, set())
        return selfcopy
        
    def _rename_variables(self, new_vars, used_vars, visited):
        if id(self) in visited: return
        visited.add(id(self))
        for (fname, fval) in self._features.items():
            if isinstance(fval, Variable):
                # If it's in new_vars, then rebind it.
                if fval in new_vars:
                    self._features[fname] = new_vars[fval]
                # If it's in used_vars, pick a new name for it.
                elif fval in used_vars:
                    new_vars[fval] = self._rename_variable(fval, used_vars)
                    self._features[fname] = new_vars[fval]
                    used_vars.add(new_vars[fval])
            elif isinstance(fval, FeatStruct):
                fval._rename_variables(new_vars, used_vars, visited)
        return new_vars

    def _rename_variable(self, var, used_vars):
        name, n = re.sub('\d+$', '', var.name), 2
        while '%s%s' % (name, n) in used_vars: n += 1
        return Variable('%s%s' % (name, n))

    ##////////////////////////////////////////////////////////////
    ## Unification
    ##////////////////////////////////////////////////////////////

    # The basic unification algorithm:
    #   1. Make copies of self and other (preserving reentrance)
    #   2. Destructively unify self and other
    #   3. Apply forward pointers, to preserve reentrance.
    #   4. Replace bound variables with their values.
    def unify(self, other, bindings=None, trace=False,
              rename_conflicting_vars=True):
        """
        Unify C{self} with C{other}, and return the resulting feature
        structure.  This unified feature structure is the minimal
        feature structure that:
          - contains all feature value assignments from both C{self}
            and C{other}.
          - preserves all reentrance properties of C{self} and
            C{other}.

        If no such feature structure exists (because C{self} and
        C{other} specify incompatible values for some feature), then
        unification fails, and C{unify} returns C{None}.

        @param bindings: A set of variable bindings to be used and
            updated during unification.  Bound variables are
            treated as if they were replaced by their values.  Unbound
            variables are bound if they are unified with values; or
            aliased if they are unified with other unbound variables.
            If C{bindings} is unspecified, then all variables are
            assumed to be unbound.
        """
        if trace: print '\nUnification trace:'
        
        # If bindings are unspecified, use an empty set of bindings.
        if bindings is None: bindings = {}

        # Make copies of self & other (since the unification algorithm
        # is destructive).  Use the same memo, to preserve reentrance
        # links between self and other.
        memo = {}
        selfcopy = self._deepcopy(memo)
        othercopy = other._deepcopy(memo)

        if rename_conflicting_vars:
            othercopy._rename_variables({}, selfcopy.variables(), set())

        # Preserve reentrance links from bound variables into either
        # self or other.
        for var, val in bindings.items():
            if (not isinstance(val, Variable) and
                id(val) in memo):
                bindings[var] = memo[id(val)]

        # Do the actual unification.  If it fails, return None.
        forward = {}
        try: selfcopy._destructively_unify(othercopy, bindings,
                                           forward, trace)
        except FeatStruct._UnificationFailureError: return None

        # Replace any feature structure that has a forward pointer
        # with the target of its forward pointer.
        selfcopy._apply_forwards_to_bindings(forward, bindings)
        selfcopy = selfcopy._apply_forwards(forward, visited=set())

        # Replace bound vars with values.
        selfcopy._apply_bindings(bindings, visited=set())
        
        # Return the result.
        return selfcopy

    class _UnificationFailureError(Exception):
        """ An exception that is used by C{_destructively_unify} to
        abort unification when a failure is encountered."""

    def _destructively_unify(self, other, bindings, forward,
                             trace=False, path=()):
        """
        Attempt to unify C{self} and C{other} by modifying them
        in-place.  If the unification succeeds, then C{self} will
        contain the unified value, the value of C{other} is undefined,
        and forward[id(other)] is set to self.  If the unification
        fails, then a _UnificationFailureError is raised, and the
        values of C{self} and C{other} are undefined.
        """
        # Look up the "canonical" copy of self and other.
        while id(self) in forward: self = forward[id(self)]
        while id(other) in forward: other = forward[id(other)]

        if trace: self._trace_unify_start(path, other)

        # If self is already identical to other, we're done.
        # Note: this, together with the forward pointers, ensures
        # that unification will terminate even for cyclic structures.
        if self is other:
            if trace: self._trace_unify_identity(path)
            return

        # Set other's forward pointer to point to self; this makes us
        # into the cannonical copy of other.  N.b. we need to do this
        # before we recurse into any child structures, in case they're
        # cyclic.
        forward[id(other)] = self

        # Note: sorting other's features isn't actually necessary; but
        # we do it to give deterministic behavior, e.g. for tracing.
        for (fname, otherval) in sorted(other._features.items()):
            if self._features.has_key(fname):
                if trace: self._trace_unify_feature(path, fname)
                
                selfval = self._features[fname]

                # If selfval or otherval is a bound variable, then
                # replace it by the variable's bound value.  This
                # includes aliased variables, which are encoded as
                # variables bound to other variables.
                while isinstance(selfval, Variable) and selfval in bindings:
                    selfval = bindings[selfval]
                while isinstance(otherval, Variable) and otherval in bindings:
                    otherval = bindings[otherval]
                    
                # Case 1: unify 2 feature structures (recursive case)
                if (isinstance(selfval, FeatStruct) and
                    isinstance(otherval, FeatStruct)):
                    selfval._destructively_unify(otherval, bindings, forward,
                                                 trace, path+(fname,))

                # Case 2: unify 2 unbound variables (create alias)
                elif (isinstance(selfval, Variable) and
                      isinstance(otherval, Variable)):
                    bindings[otherval] = selfval
                
                # Case 3: unify a variable with a value
                elif isinstance(selfval, Variable):
                    self._features[fname] = bindings[selfval] = otherval
                elif isinstance(otherval, Variable):
                    bindings[otherval] = selfval

#                 # Case 4A: unify two strings, case-insensitively.
#                 elif ci_str_cmp and \
#                     isinstance(selfval, str) and isinstance(otherval, str)\
#                     and selfval.upper() == otherval.upper():
#                     pass
                    
                # Case 4: unify 2 non-equal values (failure case)
                elif selfval != otherval:
                    if trace: self._trace_unify_fail(path)
                    raise FeatStruct._UnificationFailureError()

                # Case 5: unify 2 equal values
                else: pass

                if trace and not isinstance(selfval, FeatStruct):
                    self._trace_unify_fval(path, selfval, otherval,
                                           self._features[fname], forward)
                    
            # Case 6: copy from other
            else:
                self._features[fname] = otherval

        if trace: self._trace_unify_succeed(path, bindings, forward)
        
    def _apply_forwards_to_bindings(self, forward, bindings):
        """
        Replace any feature structure that has a forward pointer with
        the target of its forward pointer (to preserve reentrancy).
        """
        for (var, value) in bindings.items():
            if isinstance(value, FeatStruct):
                while id(value) in forward:
                    value = forward[id(value)]
                bindings[var] = value

    def _apply_forwards(self, forward, visited):
        """
        Replace any feature structure that has a forward pointer with
        the target of its forward pointer (to preserve reentrancy).
        """
        # Follow our own forwards pointers (if any)
        while id(self) in forward: self = forward[id(self)]
            
        # Visit each node only once:
        if id(self) in visited: return
        visited.add(id(self))
            
        for fname, fval in self._features.items():
            if isinstance(fval, FeatStruct):
                # Replace w/ forwarded value.
                while id(fval) in forward:
                    fval = forward[id(fval)]
                self._features[fname] = fval
                # Recurse to child.
                fval._apply_forwards(forward, visited)

        return self

    ##////////////////////////////////////////////////////////////
    ## Unification: trace helper functions
    ##////////////////////////////////////////////////////////////

    def _trace_unify_start(self, path, other):
        print '  '+'|   '*len(path)+' /'+self._trace_valrepr(self)
        print '  '+'|   '*len(path)+'|\\'+self._trace_valrepr(other)
    def _trace_unify_identity(self, path):
        print '  '+'|   '*len(path)+'|'
        print '  '+'|   '*len(path)+'| (identical objects)'
        print '  '+'|   '*len(path)+'|'
        print '  '+'|   '*len(path)+'+-->'+`self`
    def _trace_unify_feature(self, path, fname):
        fullname = '.'.join(path+(fname,))
        print '  '+'|   '*len(path)+'|'
        print '  '+'|   '*len(path)+'| Unify feature: %s' % fullname
    def _trace_unify_fval(self, path, val1, val2, result, forward):
        # Resolve any forward pointers
        if isinstance(val2, FeatStruct):
            val2 = val2._apply_forwards(forwards, set())
        if isinstance(result, FeatStruct):
            result = result._apply_forwards(forwards, set())
        # Print the unification.
        print '  '+'|   '*len(path)+'|    /%s' % self._trace_valrepr(val1)
        print '  '+'|   '*len(path)+'|   |\\%s' % self._trace_valrepr(val2)
        print '  '+'|   '*len(path)+'|   |'
        print '  '+'|   '*len(path)+'|   +-->%s' % self._trace_valrepr(result)
    def _trace_unify_fail(self, path):
        print '  '+'|   '*len(path)+'X <-- FAIL'
    def _trace_unify_succeed(self, path, bindings, forward):
        # Resolve any forwards pointers.
        self = self._apply_forwards(forward, set())
        # Print the result.
        print '  '+'|   '*len(path)+'|'
        print '  '+'|   '*len(path)+'+-->'+`self`
        # Print the bindings (if any).
        if len(bindings) > 0:
            binditems = sorted(bindings.items(), key=lambda v:v[0].name)
            bindstr = '{%s}' % ', '.join(
                '?%s: %s' % (var.name, self._trace_valrepr(val))
                for (var, val) in binditems)
            print '  '+'|   '*len(path)+'    Bindings: '+bindstr
    def _trace_valrepr(self, val):
        if isinstance(val, Variable):
            return '?%s' % val.name
        else:
            return '%r' % val

    ##////////////////////////////////////////////////////////////
    ## String Representations
    ##////////////////////////////////////////////////////////////

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
            if isinstance(fval, Variable):
                segments.append('%s=?%s' % (fname, fval.name))
            elif not isinstance(fval, FeatStruct):
                segments.append('%s=%r' % (fname, fval))
            elif reentrance_ids.has_key(id(fval)):
                segments.append('%s->(%s)' % (fname,
                                              reentrance_ids[id(fval)]))
            else:
                fval_repr = fval._repr(reentrances, reentrance_ids)
                segments.append('%s=%s' % (fname, fval_repr))

        # If it's reentrant, then add on an identifier tag.
        if reentrances[id(self)]:
            return '(%s)[%s]' % (reentrance_ids[id(self)],
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
        maxfnamelen = max(len(k) for k in self.keys())

        lines = []
        items = self._features.items()
        items.sort() # sorting note: keys are unique strings, so we'll
                     # never fall through to comparing values.
        for (fname, fval) in items:
            if isinstance(fval, Variable):
                lines.append('%s=?%s' % (fname, fval.name))
                
            elif not isinstance(fval, FeatStruct):
                # It's not a nested feature structure -- just print it.
                lines.append('%s = %r' % (fname.ljust(maxfnamelen), fval))

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
                            
                # Separate FeatStructs by a blank line.
                lines.append('')

        # Get rid of any excess blank lines.
        if lines[-1] == '': lines = lines[:-1]
        
        # Add brackets around everything.
        maxlen = max(len(line) for line in lines)
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
                if isinstance(fval, FeatStruct):
                    fval._find_reentrances(reentrances)

        return reentrances

    ##////////////////////////////////////////////////////////////
    ## Parsing
    ##////////////////////////////////////////////////////////////

    @classmethod
    def parse(cls, s):
        """
        Convert a string representation of a feature structure (as
        displayed by repr) into a C{FeatStruct}.  This parse
        imposes the following restrictions on the string
        representation:
          - Feature names cannot contain any of the following:
            whitespace, parenthases, quote marks, equals signs,
            dashes, and square brackets.
          - Only the following basic feature value are supported:
            strings, integers, variables, C{None}, and unquoted
            alphanumeric strings.
          - For reentrant values, the first mention must specify
            a reentrance identifier and a value; and any subsequent
            mentions must use arrows (C{'->'}) to reference the
            reentrance identifier.
        """
        try:
            value, position = cls._parse(s.strip(), 0, {})
        except ValueError, e:
            estr = ('Error parsing field structure\n\n    ' +
                    s + '\n    ' + ' '*e.args[1] + '^ ' +
                    'Expected %s\n' % e.args[0])
            raise ValueError, estr
        if position != len(s):
            raise ValueError('Feature structure ended before string end')
        return value

    # Regular expressions for parsing.
    _PARSE_RE = {'name': re.compile(r'\s*([^\s\(\)"\'\-=\[\]]+)\s*'),
                 'fstruct': re.compile(r'\s*(?:\((\d+)\)\s*)?\['),
                 'reentrance': re.compile(r'\s*->\s*\((\d+)\)\s*'),
                 'assign': re.compile(r'\s*=\s*'),
                 'bracket': re.compile(r'\s*]\s*'),
                 'comma': re.compile(r'\s*,\s*'),
                 'none': re.compile(r'None(?=\s|\]|,)'),
                 'int': re.compile(r'-?\d+(?=\s|\]|,)'),
                 'var': re.compile(r'\?[a-zA-Z_][a-zA-Z0-9_]*'),
                 'symbol': re.compile(r'\w+'),
                 'stringstart': re.compile("[uU]?[rR]?(['\"])"),
                 'stringmarker': re.compile("['\"\\\\]")}

    @classmethod
    def _parse(cls, s, position=0, reentrances=None):
        """
        Helper function that parses a feature structure.
        @param s: The string to parse.
        @param position: The position in the string to start parsing.
        @param reentrances: A dictionary from reentrance ids to values.
        @return: A tuple (val, pos) of the feature structure created
            by parsing and the position where the parsed feature
            structure ends.
        """
        # A set of useful regular expressions (precompiled)
        _PARSE_RE = cls._PARSE_RE

        # Create a feature structure.  We do this before we've
        # collected all the features, in case the feature structure is
        # cyclic.
        new_fstruct = cls()

        # Get the reentrance identifier and the open bracket.
        match = _PARSE_RE['fstruct'].match(s, position)
        if not match:
            raise ValueError('open bracket or identifier', position)
        if match.group(1):
            identifier = match.group(1)
            if identifier in reentrances:
                raise ValueError('new identifier', position.start(1))
            reentrances[identifier] = new_fstruct
        position = match.end()

        # If it's immediately followed by a close bracket, then just
        # return an empty feature structure.
        match = _PARSE_RE['bracket'].match(s, position)
        if match is not None: return new_fstruct, match.end()

        # Build a list of the features defined by the structure.
        # Each feature has one of the three following forms:
        #     name = value
        #     name -> (target)
        features = new_fstruct._features
        while position < len(s):
            # Use these variables to hold info about the feature:
            name = id = target = val = None
            
            # Find the next feature's name.
            match = _PARSE_RE['name'].match(s, position)
            if match is None: raise ValueError('feature name', position)
            name = match.group(1)
            position = match.end()

            # Check for a reentrance link ("-> (target)")
            match = _PARSE_RE['reentrance'].match(s, position)
            if match is not None:
                target = match.group(1)
                position = match.end()
                if target not in reentrances:
                    raise ValueError('bound identifier', position)
                features[name] = reentrances[target]

            # If it's not a reentrance link, it must be an assignment.
            else:
                match = _PARSE_RE['assign'].match(s, position)
                if match is None: raise ValueError('equals sign', position)
                position = match.end()

                val, position = cls._parseval(s, position, reentrances)
                features[name] = val
                if id is not None:
                    reentrances[id] = val

            # Check for a close bracket
            match = _PARSE_RE['bracket'].match(s, position)
            if match is not None:
                return new_fstruct, match.end()

            # Otherwise, there should be a comma
            match = _PARSE_RE['comma'].match(s, position)
            if match is None: raise ValueError('comma', position)
            position = match.end()

        # We never saw a close bracket.
        raise ValueError('close bracket', position)

    @classmethod
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
        match = _PARSE_RE['stringstart'].match(s, position)
        if match is not None:
            start = position
            quotemark = match.group(1)
            position = match.end()
            while 1:
                match = _PARSE_RE['stringmarker'].search(s, position)
                if not match: raise ValueError('close quote', position)
                position = match.end()
                if match.group() == '\\': position += 1
                elif match.group() == quotemark:
                    try:
                        return eval(s[start:position]), position
                    except ValueError, e:
                        raise ValueError('valid string (%s)' % e, start)

        # Nested feature structure
        if _PARSE_RE['fstruct'].match(s, position):
            return cls._parse(s, position, reentrances)

        # Variable
        match = _PARSE_RE['var'].match(s, position)
        if match is not None:
            return Variable(match.group()[1:]), match.end()

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
            return match.group(), match.end()

        # We don't know how to parse this value.
        raise ValueError('value', position)

#//////////////////////////////////////////////////////////////////////
# TESTING...
#//////////////////////////////////////////////////////////////////////

import unittest

# Note: since FeatStruct.__repr__() sorts by keys before
# displaying, there is a single unique string repr for each
# FeatStruct.
class FeatStructTestCase(unittest.TestCase):
    'Unit testing for FeatStruct'

    def testUnification(self):
        'Basic unification tests'

        # Copying from self to other.
        fs1 = FeatStruct(number='singular')
        fs2 = fs1.unify(FeatStruct())
        self.failUnlessEqual(repr(fs2), "[number='singular']")

        # Copying from other to self
        fs1 = FeatStruct()
        fs2 = fs1.unify(FeatStruct(number='singular'))
        self.failUnlessEqual(repr(fs2), "[number='singular']")

        # Cross copying
        fs1 = FeatStruct(number='singular')
        fs2 = fs1.unify(FeatStruct(person=3))
        self.failUnlessEqual(repr(fs2), "[number='singular', person=3]")

        # Merging a nested structure
        fs1 = FeatStruct.parse('[A=[B=b]]')
        fs2 = FeatStruct.parse('[A=[C=c]]')
        fs3 = fs1.unify(fs2)
        self.failUnlessEqual(repr(fs3), "[A=[B='b', C='c']]")

    def testReentrantUnification(self):
        'Reentrant unification tests'
        # A basic case of reentrant unification
        fs1 = FeatStruct.parse('[A=(1)[B=b], E=[F->(1)]]')
        fs2 = FeatStruct.parse("[A=[C='c'], E=[F=[D='d']]]")
        fs3 = fs1.unify(fs2)
        fs3repr = "[A=(1)[B='b', C='c', D='d'], E=[F->(1)]]"
        self.failUnlessEqual(repr(fs3), fs3repr)
        fs3 = fs2.unify(fs1) # Try unifying both ways.
        self.failUnlessEqual(repr(fs3), fs3repr)

        # More than 2 paths to a value
        fs1 = FeatStruct.parse("[a=[],b=[],c=[],d=[]]")
        fs2 = FeatStruct.parse('[a=(1)[], b->(1), c->(1), d->(1)]')
        fs3 = fs1.unify(fs2)
        self.failUnlessEqual(repr(fs3), '[a=(1)[], b->(1), c->(1), d->(1)]')

        # fs1[a] gets unified with itself:
        fs1 = FeatStruct.parse('[x=(1)[], y->(1)]')
        fs2 = FeatStruct.parse('[x=(1)[], y->(1)]')
        fs3 = fs1.unify(fs2)
        
    def testVariableForwarding(self):
        'Bound variables should get forwarded appropriately'
        fs1 = FeatStruct.parse('[A=(1)[X=x], B->(1), C=?cvar, D=?dvar]')

        fs2y = FeatStruct(Y='y')
        fs2z = FeatStruct(Z='z')
        fs2 = FeatStruct.parse('[A=(1)[Y=y], B=(2)[Z=z], C->(1), D->(2)]')

        fs3 = fs1.unify(fs2)
        fs3repr = ("[A=(1)[X='x', Y='y', Z='z'], B->(1), C->(1), D->(1)]")
        self.failUnlessEqual(repr(fs3), fs3repr)

    def testCyclicStructures(self):
        'Cyclic structure tests'
        # Create a cyclic structure via unification.
        fs1 = FeatStruct.parse('[F=(1)[], G->(1)]')
        fs2 = FeatStruct.parse('[F=[H=(2)[]], G->(2)]')
        fs3 = fs1.unify(fs2)

        # Check that we got the value right.
        self.failUnlessEqual(repr(fs3), '[F=(1)[H->(1)], G->(1)]')

        # Check that we got the cyclicity right.
        self.failUnless(fs3['F'] is fs3['G'])
        self.failUnless(fs3['F'] is fs3['G', 'H'])
        self.failUnless(fs3['F'] is fs3['G', 'H', 'H'])
        self.failUnless(fs3['F'] is fs3[('G',)+(('H',)*10)])

        # Create a cyclic structure with variables.
        x = Variable('x')
        fs1 = FeatStruct(F=FeatStruct(H=x))
        fs2 = FeatStruct(F=x)
        fs3 = fs1.unify(fs2)

        # Check that we got the value right.
        self.failUnlessEqual(repr(fs3), '[F=(1)[H->(1)]]')

        # Check that we got the cyclicity right.
        self.failUnless(fs3['F'] is fs3['F','H'])
        self.failUnless(fs3['F'] is fs3['F','H','H'])
        self.failUnless(fs3['F'] is fs3[('F',)+(('H',)*10)])

        # Cyclic structure as LHS
        fs4 = FeatStruct.parse('[F=[H=[H=[H=(1)[]]]], K->(1)]')
        fs5 = fs3.unify(fs4)
        self.failUnlessEqual(repr(fs5), '[F=(1)[H->(1)], K->(1)]')

        # Cyclic structure as RHS
        fs6 = fs4.unify(fs3)
        self.failUnlessEqual(repr(fs6), '[F=(1)[H->(1)], K->(1)]')

        # LHS and RHS both cyclic
        fs7 = fs3.unify(fs3.copy(deep=True))

    def testVariablesPreserveReentrance(self):
        'Variable bindings should preserve reentrance.'
        bindings = {}
        fs1 = FeatStruct.parse("[a=?x]")
        fs2 = fs1.unify(FeatStruct.parse("[a=[]]"), bindings)
        fs3 = fs2.unify(FeatStruct.parse("[b=?x]"), bindings)
        self.failUnlessEqual(repr(fs3), '[a=(1)[], b->(1)]')

    def testVariableMerging(self):
        'Aliased variable tests'
        fs1 = FeatStruct.parse("[a=?x, b=?x]")
        fs2 = fs1.unify(FeatStruct.parse("[b=?y, c=?y]"))
        self.failUnlessEqual(repr(fs2), '[a=?x, b=?<x=y>, c=?y]')
        fs3 = fs2.unify(FeatStruct.parse("[a=1]"))
        self.failUnlessEqual(repr(fs3), '[a=1, b=1, c=1]')

        fs1 = FeatStruct.parse("[a=1]")
        fs2 = FeatStruct.parse("[a=?x, b=?x]")
        fs3 = fs2.unify(fs1)
        self.failUnlessEqual(repr(fs3), '[a=1, b=1]')

def testsuite():
    t1 = unittest.makeSuite(FeatStructTestCase)
    return unittest.TestSuite( (t1,) )

def test(verbosity):
    runner = unittest.TextTestRunner(verbosity=verbosity)
    runner.run(testsuite())

#//////////////////////////////////////////////////////////////////////
# Demo..
#//////////////////////////////////////////////////////////////////////

def display_unification(fs1, fs2, indent='  '):
    # Print the two input feature structures, side by side.
    fs1_lines = str(fs1).split('\n')
    fs2_lines = str(fs2).split('\n')
    if len(fs1_lines) > len(fs2_lines):
        blankline = '['+' '*(len(fs2_lines[0])-2)+']'
        fs2_lines += [blankline]*len(fs1_lines)
    else:
        blankline = '['+' '*(len(fs1_lines[0])-2)+']'
        fs1_lines += [blankline]*len(fs2_lines)
    for (fs1_line, fs2_line) in zip(fs1_lines, fs2_lines):
        print indent + fs1_line + '   ' + fs2_line
    print indent+'-'*len(fs1_lines[0])+'   '+'-'*len(fs2_lines[0])

    linelen = len(fs1_lines[0])*2+3
    print indent+'|               |'.center(linelen)
    print indent+'+-----UNIFY-----+'.center(linelen)
    print indent+'|'.center(linelen)
    print indent+'V'.center(linelen)

    bindings = {}

    result = fs1.unify(fs2, bindings)
    if result is None:
        print indent+'(FAILED)'.center(linelen)
    else:
        print '\n'.join(indent+l.center(linelen)
                         for l in str(result).split('\n'))
        if bindings and len(bindings.bound_variables()) > 0:
            print repr(bindings).center(linelen)
    return result

def demo(trace=False):
    import random, sys

    HELP = '''
    1-%d: Select the corresponding feature structure
    q: Quit
    t: Turn tracing on or off
    l: List all feature structures
    ?: Help
    '''
    
    print '''
    This demo will repeatedly present you with a list of feature
    structures, and ask you to choose two for unification.  Whenever a
    new feature structure is generated, it is added to the list of
    choices that you can pick from.  However, since this can be a
    large number of feature structures, the demo will only print out a
    random subset for you to choose between at a given time.  If you
    want to see the complete lists, type "l".  For a list of valid
    commands, type "?".
    '''
    print 'Press "Enter" to continue...'
    sys.stdin.readline()
    
    fstruct_strings = [
        '[agr=[number=sing, gender=masc]]',
        '[agr=[gender=masc, person=3rd]]',
        '[agr=[gender=fem, person=3rd]]',
        '[subj=[agr=(1)[]], agr->(1)]',
        '[obj=?x]', '[subj=?x]',
        '[/=None]', '[/=NP]',
        '[cat=NP]', '[cat=VP]', '[cat=PP]',
        '[subj=[agr=[gender=?y]], obj=[agr=[gender=?y]]]',
        '[gender=masc, agr=?C]',
        '[gender=?S, agr=[gender=?S,person=3rd]]'
        ]
    
    all_fstructs = [(i, FeatStruct.parse(fstruct_strings[i]))
                    for i in range(len(fstruct_strings))]

    def list_fstructs(fstructs):
        for i, fstruct in fstructs:
            print
            lines = str(fstruct).split('\n')
            print '%3d: %s' % (i+1, lines[0])
            for line in lines[1:]: print '     '+line
        print

    
    while 1:
        # Pick 5 feature structures at random from the master list.
        MAX_CHOICES = 5
        if len(all_fstructs) > MAX_CHOICES:
            fstructs = random.sample(all_fstructs, MAX_CHOICES)
            fstructs.sort()
        else:
            fstructs = all_fstructs
        
        print '_'*75
        
        print 'Choose two feature structures to unify:'
        list_fstructs(fstructs)
        
        selected = [None,None]
        for (nth,i) in (('First',0), ('Second',1)):
            while selected[i] is None:
                print ('%s feature structure (1-%d,q,t,l,?): '
                       % (nth, len(all_fstructs))),
                try:
                    input = sys.stdin.readline().strip()
                    if input in ('q', 'Q', 'x', 'X'): return
                    if input in ('t', 'T'):
                        trace = not trace
                        print '   Trace = %s' % trace
                        continue
                    if input in ('h', 'H', '?'):
                        print HELP % len(fstructs); continue
                    if input in ('l', 'L'):
                        list_fstructs(all_fstructs); continue
                    num = int(input)-1
                    selected[i] = all_fstructs[num][1]
                    print
                except:
                    print 'Bad sentence number'
                    continue

        if trace:
            result = selected[0].unify(selected[1], trace=1)
        else:
            result = display_unification(selected[0], selected[1])
        if result is not None:
            for i, fstruct in all_fstructs:
                if `result` == `fstruct`: break
            else:
                all_fstructs.append((len(all_fstructs), result))

        print '\nType "Enter" to continue unifying; or "q" to quit.'
        input = sys.stdin.readline().strip()
        if input in ('q', 'Q', 'x', 'X'): return


if __name__ == '__main__':
    test(verbosity=0)
    demo()
