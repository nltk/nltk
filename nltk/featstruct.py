# Natural Language Toolkit: Feature Structures
#
# Copyright (C) 2001-2008 University of Pennsylvania
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

Features can be specified using X{feature paths}, or tuples of feature
names that specify path through the nested feature structures to a
value.  Feature structures may contain reentrant feature values.  A
X{reentrant feature value} is a single feature value that can be
accessed via multiple feature paths.  Unification preserves the
reentrance relations imposed by both of the unified feature
structures.  In the feature structure resulting from unification, any
modifications to a reentrant feature value will be visible using any
of its feature paths.  Feature structures may also contain X{cyclic
feature values}, i.e., values that recursively contain themself.

Feature structure variables are encoded using the L{nltk.sem.Variable}
class.  The variables' values are tracked using a X{bindings}
dictionary, which maps variables to their values.  When two feature
structures are unified, a fresh bindings dictionary is created to
track their values; and before unification completes, all bound
variables are replaced by their values.  Thus, the bindings
dictionaries are usually strictly internal to the unification process.
However, it is possible to track the bindings of variables if you
choose to, by supplying your own initial bindings dictionary to the
L{unify() <FeatStruct.unify>} method.

When unbound variables are unified with one another, they become
X{aliased}.  This is encoded by binding one variable to the other.

@todo: define __div__ for feature structures?
"""

import re, copy
from nltk.sem.logic import Variable, Expression, SubstituteBindingsI
from nltk.sem.logic import LogicParser
import nltk.internals

######################################################################
# Feature Structure
######################################################################

class FeatStruct(SubstituteBindingsI):
    """
    A structured set of features.  These features are represented as a
    mapping from feature names to feature values, where each feature
    value is either a basic value (such as a string or an integer), or
    a nested feature structure.  A feature structure acts much like a
    read-only dictionary.  In particular, feature values may be
    accessed via indexing:

      >>> fstruct1 = FeatStruct(number='singular', person='3rd')
      >>> print fstruct1['number']
      'singular'

      >>> fstruct2 = FeatStruct(subject=fstruct1)
      >>> print fstruct2['subject']['person']
      '3rd'

    A nested feature value can be also accessed via a X{feature
    paths}, or a tuple of feature names that specifies the paths to
    the nested feature:

      >>> print fstruct2['subject', 'number']
      'singular'

    Feature structures may contain reentrant feature values.  A
    X{reentrant feature value} is a single feature value that can be
    accessed via multiple feature paths.  Feature structures may also
    be cyclic.

    Two feature structures are considered equal if they assign the
    same values to all features, and have the same reentrances.

    By default, feature structures are mutable.  They may be made
    immutable with the L{freeze()} function.  Once they have been
    frozen, they may be hashed, and thus used as dictionary keys.

    @ivar _features: A dictionary mapping from feature names to values.
    @ivar _frozen: True if this feature structure is frozen.
    """
    def __init__(self, features=None, **morefeatures):
        """
        Create a new feature structure, with the specified features.

        @param features: The initial value for this feature structure.
        If C{features} is a C{FeatStruct}, then its features are copied
        (shallow copy).  If C{features} is a C{dict}, then a feature is
        created for each item, mapping its key to its value.  If
        C{features} is a string, then it is parsed using L{parse()}.  If
        C{features} is a list of tuples C{name,val}, then a feature is
        created for each tuple.
        """
        self._frozen = False
        self._features = {}
        if isinstance(features, basestring):
            FeatStructParser().parse(features, self)
            self.update(morefeatures)
        else:
            self.update(features, **morefeatures)

    # Note: The Feature class is added to this list, when it is defined
    # below.
    _feature_name_types = (basestring,)
    """A list of the types that feature names may have."""
    
    #////////////////////////////////////////////////////////////
    #{ Read-only mapping methods
    #////////////////////////////////////////////////////////////
    
    def __getitem__(self, name_or_path):
        """If the feature with the given name or path exists, return
        its value; otherwise, raise C{KeyError}."""
        if isinstance(name_or_path, self._feature_name_types):
            return self._features[name_or_path]
        if name_or_path == ():
            return self
        else:
            try:
                parent, name = self._path_parent(name_or_path, '')
                return parent._features[name]
            except KeyError: raise KeyError(name_or_path)
        
    def get(self, name_or_path, default=None):
        """If the feature with the given name or path exists, return its
        value; otherwise, return C{default}."""
        try:
            return self[name_or_path]
        except KeyError:
            return default
    def __contains__(self, name_or_path):
        """Return true if a feature with the given name or path exists."""
        try:
            self[name_or_path]; return True
        except KeyError:
            return False
    def has_key(self, name_or_path):
        """Return true if a feature with the given name or path exists."""
        return name_or_path in self
    def keys(self):
        """Return a list of the feature names in this FeatStruct."""
        return self._features.keys()
    def values(self):
        """Return a list of the feature values in this FeatStruct."""
        return self._features.values()
    def items(self):
        """Return a list of (name, value) pairs for all features in
        this FeatStruct."""
        return self._features.items()
    def iterkeys(self):
        """Return an iterator over the feature names in this FeatStruct."""
        return self._features.iterkeys()
    def itervalues(self):
        """Return an iterator over the feature values in this FeatStruct."""
        return self._features.itervalues()
    def iteritems(self):
        """Return an iterator over (name, value) pairs for all
        features in this FeatStruct."""
        return self._features.iteritems()
    def __iter__(self): # same as iterkeys
        """Return an iterator over the feature names in this FeatStruct."""
        return iter(self._features)
    def __len__(self):
        """Return the number of features defined by this FeatStruct."""
        return len(self._features)

    #////////////////////////////////////////////////////////////
    #{ Mutating mapping methods
    #////////////////////////////////////////////////////////////

    def __delitem__(self, name_or_path):
        """If the feature with the given name or path exists, delete
        its value; otherwise, raise C{KeyError}."""
        if self._frozen: raise ValueError(self._FROZEN_ERROR)
        if isinstance(name_or_path, self._feature_name_types):
            del self._features[name_or_path]
        else:
            try:
                parent, name = self._path_parent(name_or_path, 'deleted')
                del parent._features[name]
            except KeyError: raise KeyError(name_or_path)
            
    def __setitem__(self, name_or_path, value):
        """Set the value for the feature with the given name or path
        to C{value}.  If C{name_or_path} is an invalid path, raise
        C{KeyError}."""
        if self._frozen: raise ValueError(self._FROZEN_ERROR)
        if isinstance(name_or_path, self._feature_name_types):
            self._features[name_or_path] = value
        else:
            try:
                parent, name = self._path_parent(name_or_path, 'set')
                parent[name] = value
            except KeyError: raise KeyError(name_or_path)

    def clear(self):
        """Remove all features from this C{FeatStruct}."""
        if self._frozen: raise ValueError(self._FROZEN_ERROR)
        self._features.clear()

    def pop(self, name_or_path, default=None):
        """If the feature with the given name or path exists, delete
        it and return its value; otherwise, return C{default}."""
        if self._frozen: raise ValueError(self._FROZEN_ERROR)
        if isinstance(name_or_path, self._feature_name_types):
            return self._features.pop(name_or_path, default)
        else:
            try:
                parent, name = self._path_parent(name_or_path, 'popped')
                return parent._features.pop(name, default)
            except KeyError: 
                return default

    def popitem(self):
        """Remove some feature from this C{FeatStruct}, and return
        a tuple C{(name, value)} containing its name and value.  If
        this C{FeatStruct} is empty, raise C{KeyError}."""
        if self._frozen: raise ValueError(self._FROZEN_ERROR)
        return self._features.popitem()

    def setdefault(self, name_or_path, default=None):
        """If the feature with the given name or path exists, return
        its value.  Otherwise, set the feature's value to C{default}
        and return C{default}.  If C{name_or_path} is an invalid path,
        raise C{KeyError}."""
        if self._frozen: raise ValueError(self._FROZEN_ERROR)
        if isinstance(name_or_path, self._feature_name_types):
            return self._features.setdefault(name_or_path, default)
        else:
            try:
                parent, name = self._path_parent(name_or_path, 'set')
                parent.setdefault(name, default)
            except KeyError: raise KeyError(name_or_path)
            
    def update(self, features=None, **morefeatures):
        """
        If C{features} is a mapping, then:
            >>> for name in features:
            ...     self[name] = features[name]

        Otherwise, if C{features} is a list of tuples, then:
            >>> for (name, value) in features:
            ...     self[name] = value

        Then:
            >>> for name in morefeatures:
            ...     self[name] = morefeatures[name]
        """
        if self._frozen: raise ValueError(self._FROZEN_ERROR)
        if features is None:
            items = ()
        elif hasattr(features, 'has_key'):
            items = features.items()
        elif hasattr(features, '__iter__'):
            items = features
        else:
            raise ValueError('Expected mapping or list of tuples')
        
        for key, val in items:
            if not isinstance(key, self._feature_name_types):
                raise TypeError('Feature names must be strings')
            self[key] = val
        for key, val in morefeatures.items():
            if not isinstance(key, self._feature_name_types):
                raise TypeError('Feature names must be strings')
            self[key] = val

    # [xx] doesn't play well w/ featurelists??
    def _path_parent(self, path, operation):
        """
        Helper function -- given a feature path,return a tuple
        (parent, name) containing the parent and name of the specified
        feature.  If path is (), then raise a TypeError.
        """
        if not isinstance(path, tuple):
            raise TypeError('Expected str or tuple of str.  Got %r.' % path)
        if len(path) == 0:
            raise TypeError('The path () can not be %s' % operation)
        val = self
        for name in path[:-1]:
            if not isinstance(name, str):
                raise TypeError('Expected str or tuple of str.  Got %r.'%path)
            if not isinstance(val.get(name), FeatStruct):
                raise KeyError(path)
            val = val[name]
        if not isinstance(path[-1], str):
            raise TypeError('Expected str or tuple of str.  Got %r.' % path)
        return val, path[-1]

    ##////////////////////////////////////////////////////////////
    #{ Equality & Hashing
    ##////////////////////////////////////////////////////////////

    def equal_values(self, other, check_reentrance=False):
        """
        @return: True if C{self} and C{other} assign the same value to
        to every feature.  In particular, return true if
        C{self[M{p}]==other[M{p}]} for every feature path M{p} such
        that C{self[M{p}]} or C{other[M{p}]} is a base value (i.e.,
        not a nested feature structure).

        @param check_reentrance: If true, then also return false if
            there is any difference between the reentrances of C{self}
            and C{other}.
            
        @note: the L{== operator <__eq__>} is equivalent to
            C{equal_values()} with C{check_reentrance=True}.
        """
        return self._equal(other, check_reentrance, set(), set(), set())

    def __eq__(self, other):
        """
        Return true if C{self} and C{other} are both feature
        structures, assign the same values to all features, and
        contain the same reentrances.  I.e., return 
        C{self.equal_values(other, check_reentrance=True)}.
        
        @see: L{equal_values()}
        """
        return self._equal(other, True, set(), set(), set())
    
    def __ne__(self, other):
        """
        Return true unless C{self} and C{other} are both feature
        structures, assign the same values to all features, and
        contain the same reentrances.  I.e., return 
        C{not self.equal_values(other, check_reentrance=True)}.
        """
        return not self.__eq__(other)
    
    def _equal(self, other, check_reentrance, visited_self,
               visited_other, visited_pairs):
        """
        Helper function for L{equal_values} -- return true iff self
        and other have equal values.
        
        @param visited_self: A set containing the ids of all C{self}
            values we've already visited.
        @param visited_other: A set containing the ids of all C{other}
            values we've already visited.
        @param visited_pairs: A set containing C{(selfid, otherid)}
            pairs for all pairs of values we've already visited.
        """
        # If we're the same object, then we're equal.
        if self is other: return True

        # If other's not a feature struct, we're definitely not equal.
        if not isinstance(other, FeatStruct): return False

        # If we define different features, we're definitely not equal.
        # (Perform len test first because it's faster -- we should
        # do profiling to see if this actually helps)
        if len(self) != len(other): return False
        if set(self) != set(other): return False

        # If we're checking reentrance, then any time we revisit a
        # self or other structure, make sure that it was paired with
        # the same feature structure that it is now.  Note: for each
        # value of self, visited_pairs will contain at most one pair
        # containing self.  Similary for other.
        if check_reentrance:
            if id(self) in visited_self or id(other) in visited_other:
                return (id(self), id(other)) in visited_pairs

        # If we're not checking reentrance, then we still need to deal
        # with cycles.  If we encounter the same (self, other) pair a
        # second time, then we won't learn anything more by examining
        # their children a second time, so just return true.
        else:
            if (id(self), id(other)) in visited_pairs:
                return True

        # Keep track of which nodes we've visited.
        visited_self.add(id(self))
        visited_other.add(id(other))
        visited_pairs.add( (id(self), id(other)) )
        
        # Now we have to check all values.  If any of them don't match,
        # then return false.
        for (fname, self_fval) in self.items():
            other_fval = other[fname]
            if isinstance(self_fval, FeatStruct):
                if not self_fval._equal(other_fval, check_reentrance,
                                        visited_self, visited_other,
                                        visited_pairs):
                    return False
            else:
                if self_fval != other_fval: return False
                
        # Everything matched up; return true.
        return True
    
    def __hash__(self):
        """
        If this feature structure is frozen, return its hash value;
        otherwise, raise C{TypeError}.
        """
        if not self._frozen:
            raise TypeError('FeatStructs must be frozen before they '
                            'can be hashed.')
        try: return self.__hash
        except AttributeError:
            self.__hash = self._hash(set())
            return self.__hash

    def _hash(self, visited):
        if id(self) in visited: return 1
        visited.add(id(self))

        hashval = 0
        for (fname, fval) in sorted(self.items()):
            hashval += hash(fname)
            if isinstance(fval, FeatStruct):
                hashval += fval._hash(visited)
            else:
                hashval += hash(fval)

        # Convert to a 32 bit int.
        return int(hashval & 0x7fffffff)

    ##////////////////////////////////////////////////////////////
    #{ Freezing
    ##////////////////////////////////////////////////////////////
    
    #: Error message used by mutating methods when called on a frozen
    #: feature structure.
    _FROZEN_ERROR = "Frozen FeatStructs may not be modified."

    def freeze(self):
        """
        Make this feature structure, and any feature structures it
        contains, immutable.  Note: this method does not attempt to
        'freeze' any feature values that are not C{FeatStruct}s; it
        is recommended that you use only immutable feature values.
        """
        if self._frozen: return
        self._freeze(set())

    def frozen(self):
        """
        @return: True if this feature structure is immutable.  Feature
        structures can be made immutable with the L{freeze()} method.
        Immutable feature structures may not be made mutable again,
        but new mutale copies can be produced with the L{copy()} method.
        """
        return self._frozen

    def _freeze(self, visited):
        if id(self) in visited: return
        visited.add(id(self))
        self._frozen = True
        for (fname, fval) in sorted(self.items()):
            if isinstance(fval, FeatStruct):
                fval._freeze(visited)

    ##////////////////////////////////////////////////////////////
    #{ Copying
    ##////////////////////////////////////////////////////////////

    def copy(self, deep=True):
        """
        Return a new copy of C{self}.  The new copy will not be
        frozen.

        @param deep: If true, create a deep copy; if false, create
            a shallow copy.
        """
        if deep:
            return copy.deepcopy(self)
        else:
            return FeatStruct(self)

    def __deepcopy__(self, memo):
        memo[id(self)] = selfcopy = self.__class__()
        for (key, val) in self.items():
            selfcopy[copy.deepcopy(key,memo)] = copy.deepcopy(val,memo)
        return selfcopy
    
    ##////////////////////////////////////////////////////////////
    #{ Unsorted
    ##////////////////////////////////////////////////////////////

    def cyclic(self):
        """
        @return: True if this feature structure contains itself.
        """
        return self._find_reentrances({})[id(self)]

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

    def walk(self):
        """
        Return an iterator that generates this feature structure, and
        each feature structure it contains.  Each feature structure will
        be generated exactly once.
        """
        return self._walk(set())

    def _walk(self, visited):
        if id(self) in visited: return
        visited.add(id(self))
        yield self
        for fval in self.values():
            if isinstance(fval, FeatStruct):
                for elt in fval._walk(visited):
                    yield elt

    ##////////////////////////////////////////////////////////////
    #{ Variables & Bindings
    ##////////////////////////////////////////////////////////////

    def substitute_bindings(self, bindings):
        """@see: L{nltk.featstruct.substitute_bindings()}"""
        return substitute_bindings(self, bindings)
    
    def retract_bindings(self, bindings):
        """@see: L{nltk.featstruct.retract_bindings()}"""
        return retract_bindings(self, bindings)
    
    def variables(self):
        """@see: L{nltk.featstruct.find_variables()}"""
        return find_variables(self)
    
    def rename_variables(self, vars=None, used_vars=(), new_vars=None):
        """@see: L{nltk.featstruct.rename_variables()}"""
        return rename_variables(self, vars, used_vars, new_vars)

    def remove_variables(self):
        """
        @rtype: L{FeatStruct}
        @return: The feature structure that is obtained by deleting
        all features whose values are L{Variable}s.
        """
        return copy.deepcopy(self)._remove_variables(set())

    def _remove_variables(self, visited):
        if id(self) in visited: return
        visited.add(id(self))
        for (fname, fval) in self.items():
            if isinstance(fval, Variable):
                del self[fname]
            elif isinstance(fval, FeatStruct):
                fval._remove_variables(visited)
        return self

    ##////////////////////////////////////////////////////////////
    #{ Unification
    ##////////////////////////////////////////////////////////////
    
    def unify(self, other, bindings=None, trace=False,
              fail=None, rename_vars=True):
        return unify(self, other, bindings, trace, fail, rename_vars)

    ##////////////////////////////////////////////////////////////
    #{ String Representations
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
        prefix = ''
        suffix = ''

        # If this is the first time we've seen a reentrant structure,
        # then assign it a unique identifier.
        if reentrances[id(self)]:
            assert not reentrance_ids.has_key(id(self))
            reentrance_ids[id(self)] = `len(reentrance_ids)+1`

        items = self.items()
        # sorting note: keys are unique strings, so we'll never fall
        # through to comparing values.
        for (fname, fval) in sorted(items):
            display = getattr(fname, 'display', None)
            if reentrance_ids.has_key(id(fval)):
                segments.append('%s->(%s)' %
                                (fname, reentrance_ids[id(fval)]))
            elif (display == 'prefix' and not prefix and
                  isinstance(fval, (Variable, basestring))):
                    prefix = '%s' % fval
            elif display == 'slash' and not suffix:
                if isinstance(fval, Variable):
                    suffix = '?%s' % fval.name
                else:
                    suffix = '/%r' % fval
            elif isinstance(fval, Variable):
                segments.append('%s=%s' % (fname, fval.name))
            elif fval is True:
                segments.append('+%s' % fname)
            elif fval is False:
                segments.append('-%s' % fname)
            elif isinstance(fval, Expression):
                segments.append('%s=<%s>' % (fname, fval))
            elif not isinstance(fval, FeatStruct):
                segments.append('%s=%r' % (fname, fval))
            else:
                fval_repr = fval._repr(reentrances, reentrance_ids)
                segments.append('%s=%s' % (fname, fval_repr))
        # If it's reentrant, then add on an identifier tag.
        if reentrances[id(self)]:
            prefix = '(%s)%s' % (reentrance_ids[id(self)], prefix)
        return '%s[%s]%s' % (prefix, ', '.join(segments), suffix)

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
        if len(self) == 0:
            if reentrances[id(self)]:
                return ['(%s) []' % reentrance_ids[id(self)]]
            else:
                return ['[]']
        
        # What's the longest feature name?  Use this to align names.
        maxfnamelen = max(len(str(k)) for k in self.keys())

        lines = []
        items = self.items()
        # sorting note: keys are unique strings, so we'll never fall
        # through to comparing values.
        for (fname, fval) in sorted(items):
            fname = str(fname)
            if isinstance(fval, Variable):
                lines.append('%s = %s' % (fname.ljust(maxfnamelen),
                                          fval.name))
                
            elif isinstance(fval, Expression):
                lines.append('%s = <%s>' % (fname.ljust(maxfnamelen), fval))
                
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
            for fval in self.values():
                if isinstance(fval, FeatStruct):
                    fval._find_reentrances(reentrances)

        return reentrances

######################################################################
# Playing around -- feature lists
######################################################################

class FeatureList(list):
    """Under construction"""
    _frozen = False
    def items(self):
        return list(enumerate(self))
    def keys(self):
        return range(len(self))
    def values(self):
        return self
    def has_key(self, key):
        return (isinstance(key, int) and 0<=key<len(self))
    def __contains__(self, key):
        return (isinstance(key, int) and 0<=key<len(self))
    def get(self, key, default=None):
        try: return self[key]
        except (IndexError, KeyError): return default 
    def setdefault(self, key, default=None):
        # [xx] doesn't actually set default!
        try: return self[key]
        except (IndexError, KeyError): return default

    # Mutation: disable if frozen.
    _FROZEN_ERROR = "Frozen FeatStructs may not be modified."
    def check_frozen(func):
        def wrapped(self, *args, **kwargs):
            if self._frozen: raise ValueError(self._FROZEN_ERROR)
            else: return func(self, *args, **kwargs)
        return wrapped
    __delitem__ = check_frozen(list.__delitem__)
    __setitem__ = check_frozen(list.__setitem__)
    __delslice__ = check_frozen(list.__delslice__)
    __setslice__ = check_frozen(list.__setslice__)
    __iadd__ = check_frozen(list.__iadd__)
    __imul__ = check_frozen(list.__imul__)
    append = check_frozen(list.append)
    extend = check_frozen(list.extend)
    insert = check_frozen(list.insert)
    pop = check_frozen(list.pop)
    remove = check_frozen(list.remove)
    reverse = check_frozen(list.reverse)
    sort = check_frozen(list.sort)

    def freeze(self):
        if self._frozen: return
        self._freeze(set()) # all da way down..

    def _freeze(self):
        self._frozen = True # hack4now.

######################################################################
# Variables & Bindings
######################################################################

def substitute_bindings(fstruct, bindings, fs_class='default'):
    """
    @return: The feature structure that is obtained by replacing each
    variable bound by C{bindings} with its binding.  If a variable is
    aliased to a bound variable, then it will be replaced by that
    variable's value.  If a variable is aliased to an unbound
    variable, then it will be replaced by that variable.
    
    @type bindings: C{dict} with L{Variable} keys
    @param bindings: A dictionary mapping from variables to values.
    """
    if fs_class == 'default': fs_class = fstruct.__class__
    fstruct = copy.deepcopy(fstruct)
    _substitute_bindings(fstruct, bindings, fs_class, set())
    return fstruct

def _substitute_bindings(fstruct, bindings, fs_class, visited):
    # Visit each node only once:
    if id(fstruct) in visited: return
    visited.add(id(fstruct))
    
    if _is_mapping(fstruct): items = fstruct.items()
    elif _is_sequence(fstruct): items = enumerate(fstruct)
    else: raise ValueError('Expected mapping or sequence')
    for (fname, fval) in items:
        while (isinstance(fval, Variable) and fval in bindings):
            fval = fstruct[fname] = bindings[fval]
        if isinstance(fval, fs_class):
            _substitute_bindings(fval, bindings, fs_class, visited)
        elif isinstance(fval, SubstituteBindingsI):
            fstruct[fname] = fval.substitute_bindings(bindings)

def retract_bindings(fstruct, bindings, fs_class='default'):
    """
    @return: The feature structure that is obtained by replacing each
    feature structure value that is bound by C{bindings} with the
    variable that binds it.  A feature structure value must be
    identical to a bound value (i.e., have equal id) to be replaced.

    C{bindings} is modified to point to this new feature structure,
    rather than the original feature structure.  Feature structure
    values in C{bindings} may be modified if they are contained in
    C{fstruct}.
    """
    if fs_class == 'default': fs_class = fstruct.__class__
    (fstruct, new_bindings) = copy.deepcopy((fstruct, bindings))
    bindings.update(new_bindings)
    inv_bindings = dict((id(val),var) for (var,val) in bindings.items())
    _retract_bindings(fstruct, inv_bindings, fs_class, set())
    return fstruct

def _retract_bindings(fstruct, inv_bindings, fs_class, visited):
    # Visit each node only once:
    if id(fstruct) in visited: return
    visited.add(id(fstruct))
    
    if _is_mapping(fstruct): items = fstruct.items()
    elif _is_sequence(fstruct): items = enumerate(fstruct)
    else: raise ValueError('Expected mapping or sequence')
    for (fname, fval) in items:
        if isinstance(fval, fs_class):
            if id(fval) in inv_bindings:
                fstruct[fname] = inv_bindings[id(fval)]
            _retract_bindings(fval, inv_bindings, fs_class, visited)
    
                
def find_variables(fstruct, fs_class='default'):
    """
    @return: The set of variables used by this feature structure.
    @rtype: C{set} of L{Variable}
    """
    if fs_class == 'default': fs_class = fstruct.__class__
    return _variables(fstruct, set(), fs_class, set())

def _variables(fstruct, vars, fs_class, visited):
    # Visit each node only once:
    if id(fstruct) in visited: return
    visited.add(id(fstruct))
    if _is_mapping(fstruct): items = fstruct.items()
    elif _is_sequence(fstruct): items = enumerate(fstruct)
    else: raise ValueError('Expected mapping or sequence')
    for (fname, fval) in items:
        if isinstance(fval, Variable):
            vars.add(fval)
        elif isinstance(fval, fs_class):
            _variables(fval, vars, fs_class, visited)
        elif isinstance(fval, SubstituteBindingsI):
            vars.update(fval.variables())
    return vars

def rename_variables(fstruct, vars=None, used_vars=(), new_vars=None,
                     fs_class='default'):
    """
    @return: The feature structure that is obtained by replacing
    any of this feature structure's variables that are in C{vars}
    with new variables.  The names for these new variables will be
    names that are not used by any variable in C{vars}, or in
    C{used_vars}, or in this feature structure.

    @type vars: C{set}
    @param vars: The set of variables that should be renamed.
    If not specified, C{find_variables(fstruct)} is used; i.e., all
    variables will be given new names.
    
    @type used_vars: C{set}
    @param used_vars: A set of variables whose names should not be
    used by the new variables.
    
    @type new_vars: C{dict} from L{Variable} to L{Variable}
    @param new_vars: A dictionary that is used to hold the mapping
    from old variables to new variables.  For each variable M{v}
    in this feature structure:

      - If C{new_vars} maps M{v} to M{v'}, then M{v} will be
        replaced by M{v'}.
      - If C{new_vars} does not contain M{v}, but C{vars}
        does contain M{v}, then a new entry will be added to
        C{new_vars}, mapping M{v} to the new variable that is used
        to replace it.

    To consistantly rename the variables in a set of feature
    structures, simply apply rename_variables to each one, using
    the same dictionary:

        >>> new_vars = {}  # Maps old vars to alpha-renamed vars
        >>> new_fstruct1 = fstruct1.rename_variables(new_vars=new_vars)
        >>> new_fstruct2 = fstruct2.rename_variables(new_vars=new_vars)
        >>> new_fstruct3 = fstruct3.rename_variables(new_vars=new_vars)

    If new_vars is not specified, then an empty dictionary is used.
    """
    if fs_class == 'default': fs_class = fstruct.__class__
    
    # Default values:
    if new_vars is None: new_vars = {}
    if vars is None: vars = find_variables(fstruct, fs_class)
    else: vars = set(vars)

    # Add our own variables to used_vars.
    used_vars = find_variables(fstruct, fs_class).union(used_vars)

    # Copy ourselves, and rename variables in the copy.
    return _rename_variables(copy.deepcopy(fstruct), vars, used_vars,
                             new_vars, fs_class, set())

def _rename_variables(fstruct, vars, used_vars, new_vars, fs_class, visited):
    if id(fstruct) in visited: return
    visited.add(id(fstruct))
    if _is_mapping(fstruct): items = fstruct.items()
    elif _is_sequence(fstruct): items = enumerate(fstruct)
    else: raise ValueError('Expected mapping or sequence')
    for (fname, fval) in items:
        if isinstance(fval, Variable):
            # If it's in new_vars, then rebind it.
            if fval in new_vars:
                fstruct[fname] = new_vars[fval]
            # If it's in vars, pick a new name for it.
            elif fval in vars:
                new_vars[fval] = _rename_variable(fval, used_vars)
                fstruct[fname] = new_vars[fval]
                used_vars.add(new_vars[fval])
        elif isinstance(fval, fs_class):
            _rename_variables(fval, vars, used_vars, new_vars,
                              fs_class, visited)
        elif isinstance(fval, SubstituteBindingsI):
            # Pick new names for any variables in `vars`
            for var in fval.variables():
                if var in vars and var not in new_vars:
                    new_vars[var] = _rename_variable(var, used_vars)
                    used_vars.add(new_vars[var])
            # Replace all variables in `new_vars`.
            fstruct[fname] = fval.substitute_bindings(new_vars)
    return fstruct

def _rename_variable(var, used_vars):
    name, n = re.sub('\d+$', '', var.name), 2
    if not name: name = '?'
    while Variable('%s%s' % (name, n)) in used_vars: n += 1
    return Variable('%s%s' % (name, n))

######################################################################
# Unification
######################################################################

class _UnificationFailure(object):
    def __repr__(self): return 'nltk.featstruct.UnificationFailure'
UnificationFailure = _UnificationFailure()
"""A unique value used to indicate unification failure.  It can be
   returned by L{Feature.unify_base_values()} or by custom C{fail()}
   functions to indicate that unificaiton should fail."""

def _is_mapping(v):
    return hasattr(v, 'has_key') and hasattr(v, 'items')

def _is_sequence(v):
    return (hasattr(v, '__iter__') and hasattr(v, '__len__') and
            not isinstance(v, basestring))

# The basic unification algorithm:
#   1. Make copies of self and other (preserving reentrance)
#   2. Destructively unify self and other
#   3. Apply forward pointers, to preserve reentrance.
#   4. Replace bound variables with their values.
def unify(fstruct1, fstruct2, bindings=None, trace=False,
          fail=None, rename_vars=True, fs_class='default'):
    """
    Unify C{fstruct1} with C{fstruct2}, and return the resulting feature
    structure.  This unified feature structure is the minimal
    feature structure that:
      - contains all feature value assignments from both C{fstruct1}
        and C{fstruct2}.
      - preserves all reentrance properties of C{fstruct1} and
        C{fstruct2}.

    If no such feature structure exists (because C{fstruct1} and
    C{fstruct2} specify incompatible values for some feature), then
    unification fails, and C{unify} returns C{None}.

    @type bindings: C{dict} with L{Variable} keys
    @param bindings: A set of variable bindings to be used and
        updated during unification.

        Bound variables are replaced by their values.  Aliased
        variables are replaced by their representative variable
        (if unbound) or the value of their representative variable
        (if bound).  I.e., if variable C{I{v}} is in C{bindings},
        then C{I{v}} is replaced by C{bindings[I{v}].  This will
        be repeated until the variable is replaced by an unbound
        variable or a non-variable value.

        Unbound variables are bound when they are unified with
        values; and aliased when they are unified with variables.
        I.e., if variable C{I{v}} is not in C{bindings}, and is
        unified with a variable or value C{I{x}}, then
        C{bindings[I{v}]} is set to C{I{x}}.
    
        If C{bindings} is unspecified, then all variables are
        assumed to be unbound.  I.e., C{bindings} defaults to an
        empty C{dict}.

    @type trace: C{bool}
    @param trace: If true, generate trace output.

    @type rename_vars: C{bool}
    @param rename_vars: If true, then rename any variables in
        C{fstruct2} that are also used in C{fstruct1}.  This prevents
        aliasing in cases where C{fstruct1} and C{fstruct2} use the
        same variable name.  E.g.:

            >>> FeatStruct('[a=?x]').unify(FeatStruct('[b=?x]'))
            [a=?x, b=?x2]

        If you intend for a variables in C{fstruct1} and C{fstruct2} with
        the same name to be treated as a single variable, use
        C{rename_vars=False}.
    """
    # Decide which class(es) will be treated as feature structures,
    # for the purposes of unification.
    if fs_class == 'default':
        if (isinstance(fstruct1, FeatStruct) and
            isinstance(fstruct2, FeatStruct)):
            fs_class = FeatStruct
        elif (isinstance(fstruct1, (list, dict)) and
              isinstance(fstruct2, (list, dict))):
            fs_class = (list, dict)
        elif fstruct1.__class__ is fstruct2.__class__:
            fs_class = fstruct1.__class__
        else:
            raise ValueError("fstruct1 and fstruct2 should belong to "
                             "the same class.")
    assert isinstance(fstruct1, fs_class)
    assert isinstance(fstruct2, fs_class)
    
    # If bindings are unspecified, use an empty set of bindings.
    user_bindings = (bindings is not None)
    if bindings is None: bindings = {}

    # Make copies of fstruct1 and fstruct2 (since the unification
    # algorithm is destructive). Do it all at once, to preserve
    # reentrance links between fstruct1 and fstruct2.  Copy bindings
    # as well, in case there are any bound vars that contain parts
    # of fstruct1 or fstruct2.
    (fstruct1copy, fstruct2copy, bindings_copy) = (
        copy.deepcopy((fstruct1, fstruct2, bindings)))

    # Copy the bindings back to the original bindings dict.
    bindings.update(bindings_copy)

    if rename_vars:
        vars1 = find_variables(fstruct1copy, fs_class)
        vars2 = find_variables(fstruct2copy, fs_class)
        _rename_variables(fstruct2copy, vars1, vars2, {}, fs_class, set())

    # Do the actual unification.  If it fails, return None.
    forward = {}
    if trace: _trace_unify_start((), fstruct1copy, fstruct2copy)
    try: result = _destructively_unify(fstruct1copy, fstruct2copy, bindings, 
                                       forward, trace, fail, fs_class, ())
    except _UnificationFailureError: return None

    # _destructively_unify might return UnificationFailure, e.g. if we
    # tried to unify a mapping with a sequence.
    if result is UnificationFailure:
        if fail is None: return None
        else: return fail(fstruct1copy, fstruct2copy, ())

    # Replace any feature structure that has a forward pointer
    # with the target of its forward pointer.
    result = _apply_forwards(result, forward, fs_class, set())
    if user_bindings: _apply_forwards_to_bindings(forward, bindings)

    # Replace bound vars with values.
    _resolve_aliases(bindings)
    _substitute_bindings(result, bindings, fs_class, set())
    
    # Return the result.
    if trace: _trace_unify_succeed((), result)
    if trace: _trace_bindings((), bindings)
    return result

class _UnificationFailureError(Exception):
    """An exception that is used by C{_destructively_unify} to abort
    unification when a failure is encountered."""

def _destructively_unify(fstruct1, fstruct2, bindings, forward,
                         trace, fail, fs_class, path):
    """
    Attempt to unify C{fstruct1} and C{fstruct2} by modifying them
    in-place.  If the unification succeeds, then C{fstruct1} will
    contain the unified value, the value of C{fstruct2} is undefined,
    and forward[id(fstruct2)] is set to fstruct1.  If the unification
    fails, then a _UnificationFailureError is raised, and the
    values of C{fstruct1} and C{fstruct2} are undefined.

    @param bindings: A dictionary mapping variables to values.
    @param forward: A dictionary mapping feature structures ids
        to replacement structures.  When two feature structures
        are merged, a mapping from one to the other will be added
        to the forward dictionary; and changes will be made only
        to the target of the forward dictionary.
        C{_destructively_unify} will always 'follow' any links
        in the forward dictionary for fstruct1 and fstruct2 before
        actually unifying them.
    @param trace: If true, generate trace output
    @param path: The feature path that led us to this unification
        step.  Used for trace output.
    """
    # If fstruct1 is already identical to fstruct2, we're done.
    # Note: this, together with the forward pointers, ensures
    # that unification will terminate even for cyclic structures.
    if fstruct1 is fstruct2:
        if trace: _trace_unify_identity(path, fstruct1)
        return fstruct1

    # Set fstruct2's forward pointer to point to fstruct1; this makes
    # fstruct1 the canonical copy for fstruct2.  Note that we need to
    # do this before we recurse into any child structures, in case
    # they're cyclic.
    forward[id(fstruct2)] = fstruct1

    # Unifying two mappings:
    if _is_mapping(fstruct1) and _is_mapping(fstruct2):
        for fname in fstruct1:
            if getattr(fname, 'default', None) is not None:
                fstruct2.setdefault(fname, fname.default)
        for fname in fstruct2:
            if getattr(fname, 'default', None) is not None:
                fstruct1.setdefault(fname, fname.default)
    
        # Unify any values that are defined in both fstruct1 and
        # fstruct2.  Copy any values that are defined in fstruct2 but
        # not in fstruct1 to fstruct1.  Note: sorting fstruct2's
        # features isn't actually necessary; but we do it to give
        # deterministic behavior, e.g. for tracing.
        for fname, fval2 in sorted(fstruct2.items()):
            if fname in fstruct1:
                fstruct1[fname] = _unify_feature_values(
                    fname, fstruct1[fname], fval2, bindings,
                    forward, trace, fail, fs_class, path+(fname,))
            else:
                fstruct1[fname] = fval2

        return fstruct1 # Contains the unified value.

    # Unifying two sequences:
    elif _is_sequence(fstruct1) and _is_sequence(fstruct2):
        # If the lengths don't match, fail.
        if len(fstruct1) != len(fstruct2):
            return UnificationFailure

        # Unify corresponding values in fstruct1 and fstruct2.
        for findex in range(len(fstruct1)):
            fstruct1[findex] = _unify_feature_values(
                findex, fstruct1[findex], fstruct2[findex], bindings,
                forward, trace, fail, fs_class, path+(findex,))

        return fstruct1 # Contains the unified value.

    # Unifying sequence & mapping: fail.  The failure function
    # doesn't get a chance to recover in this case.
    elif ((_is_sequence(fstruct1) or _is_mapping(fstruct1)) and
          (_is_sequence(fstruct2) or _is_mapping(fstruct2))):
        return UnificationFailure

    # Unifying anything else: not allowed!
    raise TypeError('Expected mappings or sequences')

def _unify_feature_values(fname, fval1, fval2, bindings, forward,
                          trace, fail, fs_class, fpath):
    """
    Attempt to unify C{fval1} and and C{fval2}, and return the
    resulting unified value.  The method of unification will depend on
    the types of C{fval1} and C{fval2}:
    
      1. If they're both feature structures, then destructively
         unify them (see L{_destructively_unify()}.
      2. If they're both unbound variables, then alias one variable
         to the other (by setting bindings[v2]=v1).
      3. If one is an unbound variable, and the other is a value,
         then bind the unbound variable to the value.
      4. If one is a feature structure, and the other is a base value,
         then fail.
      5. If they're both base values, then unify them.  By default,
         this will succeed if they are equal, and fail otherwise.
    """
    if trace: _trace_unify_start(fpath, fval1, fval2)

    # Look up the "canonical" copy of fval1 and fval2
    while id(fval1) in forward: fval1 = forward[id(fval1)]
    while id(fval2) in forward: fval2 = forward[id(fval2)]

    # If fval1 or fval2 is a bound variable, then
    # replace it by the variable's bound value.  This
    # includes aliased variables, which are encoded as
    # variables bound to other variables.
    fvar1 = fvar2 = None
    while isinstance(fval1, Variable) and fval1 in bindings:
        fvar1 = fval1
        fval1 = bindings[fval1]
    while isinstance(fval2, Variable) and fval2 in bindings:
        fvar2 = fval2
        fval2 = bindings[fval2]

    # Case 1: Two feature structures (recursive case)
    if isinstance(fval1, fs_class) and isinstance(fval2, fs_class):
        result = _destructively_unify(fval1, fval2, bindings, forward,
                                      trace, fail, fs_class, fpath)

    # Case 2: Two unbound variables (create alias)
    elif (isinstance(fval1, Variable) and
          isinstance(fval2, Variable)):
        if fval1 != fval2: bindings[fval2] = fval1
        result = fval1
    
    # Case 3: An unbound variable and a value (bind)
    elif isinstance(fval1, Variable):
        result = bindings[fval1] = fval2
    elif isinstance(fval2, Variable):
        result = bindings[fval2] = fval1

    # Case 4: A feature structure & a base value (fail)
    elif isinstance(fval1, fs_class) or isinstance(fval2, fs_class):
        result = UnificationFailure
        
    # Case 5: Two base values
    else:
        if isinstance(fname, Feature):
            result = fname.unify_base_values(fval1, fval2, bindings)
            if fvar1 is not None: bindings[fvar1] = result
            if fvar2 is not None: bindings[fvar2] = result
        elif fval1 == fval2:
            result = fval1
        else:
            result = UnificationFailure

    # If we unification failed, call the failure function; it
    # might decide to continue anyway.
    if result is UnificationFailure:
        if fail is not None: result = fail(fval1, fval2, fpath)
        if trace: _trace_unify_fail(fpath[:-1], result)
        if result is UnificationFailure:
            raise _UnificationFailureError

    # Normalize the result.
    if isinstance(result, fs_class):
        result = _apply_forwards(result, forward, fs_class, set())
    
    if trace: _trace_unify_succeed(fpath, result)
    if trace and isinstance(result, fs_class):
        _trace_bindings(fpath, bindings)

    return result

def _apply_forwards_to_bindings(forward, bindings):
    """
    Replace any feature structure that has a forward pointer with
    the target of its forward pointer (to preserve reentrancy).
    """
    for (var, value) in bindings.items():
        while id(value) in forward:
            value = forward[id(value)]
        bindings[var] = value

def _apply_forwards(fstruct, forward, fs_class, visited):
    """
    Replace any feature structure that has a forward pointer with
    the target of its forward pointer (to preserve reentrancy).
    """
    # Follow our own forwards pointers (if any)
    while id(fstruct) in forward: fstruct = forward[id(fstruct)]
        
    # Visit each node only once:
    if id(fstruct) in visited: return
    visited.add(id(fstruct))
        
    if _is_mapping(fstruct): items = fstruct.items()
    elif _is_sequence(fstruct): items = enumerate(fstruct)
    else: raise ValueError('Expected mapping or sequence')
    for fname, fval in items:
        if isinstance(fval, fs_class):
            # Replace w/ forwarded value.
            while id(fval) in forward:
                fval = forward[id(fval)]
            fstruct[fname] = fval
            # Recurse to child.
            _apply_forwards(fval, forward, fs_class, visited)

    return fstruct

def _resolve_aliases(bindings):
    """
    Replace any bound aliased vars with their binding; and replace
    any unbound aliased vars with their representative var.
    """
    for (var, value) in bindings.items():
        while isinstance(value, Variable) and value in bindings:
            value = bindings[var] = bindings[value]
                
def _trace_unify_start(path, fval1, fval2):
    if path == ():
        print '\nUnification trace:'
    else:
        fullname = '.'.join(str(n) for n in path)
        print '  '+'|   '*(len(path)-1)+'|'
        print '  '+'|   '*(len(path)-1)+'| Unify feature: %s' % fullname
    print '  '+'|   '*len(path)+' / '+_trace_valrepr(fval1)
    print '  '+'|   '*len(path)+'|\\ '+_trace_valrepr(fval2)
def _trace_unify_identity(path, fval1):
    print '  '+'|   '*len(path)+'|'
    print '  '+'|   '*len(path)+'| (identical objects)'
    print '  '+'|   '*len(path)+'|'
    print '  '+'|   '*len(path)+'+-->'+`fval1`
def _trace_unify_fail(path, result):
    if result is UnificationFailure: resume = ''
    else: resume = ' (nonfatal)'
    print '  '+'|   '*len(path)+'|   |'
    print '  '+'X   '*len(path)+'X   X <-- FAIL'+resume
def _trace_unify_succeed(path, fval1):
    # Print the result.
    print '  '+'|   '*len(path)+'|'
    print '  '+'|   '*len(path)+'+-->'+`fval1`
def _trace_bindings(path, bindings):
    # Print the bindings (if any).
    if len(bindings) > 0:
        binditems = sorted(bindings.items(), key=lambda v:v[0].name)
        bindstr = '{%s}' % ', '.join(
            '%s: %s' % (var, _trace_valrepr(val))
            for (var, val) in binditems)
        print '  '+'|   '*len(path)+'    Bindings: '+bindstr
def _trace_valrepr(val):
    if isinstance(val, Variable):
        return '%s' % val
    else:
        return '%r' % val


def conflicts(fs1, fs2, trace=0):
    conflict_list = []
    def add_conflict(fval1, fval2, path):
        conflict_list.append(path)
        return fval1
    unify(fs1, fs2, fail=add_conflict, trace=trace)
    return conflict_list

######################################################################
# FeatureValueSet & FeatureValueTuple
######################################################################

class SubstituteBindingsSequence(SubstituteBindingsI):
    """
    A mixin class for sequence clases that distributes variables() and
    substitute_bindings() over the object's elements.
    """
    def variables(self):
        return ([elt for elt in self if isinstance(elt, Variable)] +
                sum([elt.variables() for elt in self
                     if isinstance(elt, SubstituteBindingsI)], []))
    
    def substitute_bindings(self, bindings):
        return self.__class__([self.subst(v, bindings) for v in self])
    
    def subst(self, v, bindings):
        if isinstance(v, SubstituteBindingsI):
            return v.substitute_bindings(bindings)
        else:
            return bindings.get(v, v)

class FeatureValueTuple(SubstituteBindingsSequence, tuple):
    """
    A base feature value that is a tuple of other base feature values.
    FeatureValueTuple implements L{SubstituteBindingsI}, so it any
    variable substitutions will be propagated to the elements
    contained by the set.  C{FeatureValueTuple}s are immutable.
    """
    def __repr__(self): # [xx] really use %s here?
        if len(self) == 0: return '()'
        return '(%s)' % ', '.join('%s' % (b,) for b in self)

class FeatureValueSet(SubstituteBindingsSequence, frozenset):
    """
    A base feature value that is a set of other base feature values.
    FeatureValueSet implements L{SubstituteBindingsI}, so it any
    variable substitutions will be propagated to the elements
    contained by the set.  C{FeatureValueSet}s are immutable.
    """
    def __repr__(self): # [xx] really use %s here?
        if len(self) == 0: return '{/}' # distinguish from dict.
        # n.b., we sort the string reprs of our elements, to ensure
        # that our own repr is deterministic.
        return '{%s}' % ', '.join(sorted('%s' % (b,) for b in self))
    __str__ = __repr__

class FeatureValueUnion(SubstituteBindingsSequence, frozenset):
    """
    A base feature value that represents the union of two or more
    L{FeatureValueSet}s or L{Variable}s.
    """
    def __new__(cls, values):
        # If values contains FeatureValueUnions, then collapse them.
        values = _flatten(values, FeatureValueUnion)
        
        # If the resulting list contains no variables, then 
        # use a simple FeatureValueSet instead.
        if sum(isinstance(v, Variable) for v in values) == 0:
            values = _flatten(values, FeatureValueSet)
            return FeatureValueSet(values)
        
        # If we contain a single variable, return that variable.
        if len(values) == 1:
            return list(values)[0]
        
        # Otherwise, build the FeatureValueUnion.
        return frozenset.__new__(cls, values)

    def __repr__(self):
        # n.b., we sort the string reprs of our elements, to ensure
        # that our own repr is deterministic.  also, note that len(self)
        # is guaranteed to be 2 or more.
        return '{%s}' % '+'.join(sorted('%s' % (b,) for b in self))

class FeatureValueConcat(SubstituteBindingsSequence, tuple):
    """
    A base feature value that represents the concatenation of two or
    more L{FeatureValueTuple}s or L{Variable}s.
    """
    def __new__(cls, values):
        # If values contains FeatureValueConcats, then collapse them.
        values = _flatten(values, FeatureValueConcat)
        
        # If the resulting list contains no variables, then 
        # use a simple FeatureValueTuple instead.
        if sum(isinstance(v, Variable) for v in values) == 0:
            values = _flatten(values, FeatureValueTuple)
            return FeatureValueTuple(values)
        
        # If we contain a single variable, return that variable.
        if len(values) == 1:
            return list(values)[0]
        
        # Otherwise, build the FeatureValueConcat.
        return tuple.__new__(cls, values)

    def __repr__(self):
        # n.b.: len(self) is guaranteed to be 2 or more.
        return '(%s)' % '+'.join('%s' % (b,) for b in self)

def _flatten(lst, cls):
    """
    Helper function -- return a copy of list, with all elements of
    type C{cls} spliced in rather than appended in.
    """
    result = []
    for elt in lst:
        if isinstance(elt, cls): result.extend(elt)
        else: result.append(elt)
    return result

######################################################################
# Specialized Features
######################################################################

class Feature(object):
    """
    A feature identifier that's specialized to put additional
    constraints, default values, etc.
    """
    def __init__(self, name, default=None, display=None):
        assert display in (None, 'prefix', 'slash')
        
        self._name = name # [xx] rename to .identifier?
        """The name of this feature."""
        
        self._default = default # [xx] not implemented yet.
        """Default value for this feature.  Use None for unbound."""

        self._display = display
        """Custom display location: can be prefix, or slash."""

        if self._display == 'prefix':
            self._sortkey = (-1, self._name)
        elif self._display == 'slash':
            self._sortkey = (1, self._name)
        else:
            self._sortkey = (0, self._name)

    name = property(lambda self: self._name)
    default = property(lambda self: self._default)
    display = property(lambda self: self._display)

    def __repr__(self):
        return '*%s*' % self.name

    def __cmp__(self, other):
        if not isinstance(other, Feature): return -1
        if self._name == other._name: return 0
        return cmp(self._sortkey, other._sortkey)

    def __hash__(self):
        return hash(self._name)

    #////////////////////////////////////////////////////////////
    # These can be overridden by subclasses:
    #////////////////////////////////////////////////////////////
    
    def parse_value(self, s, position, reentrances, parser):
        return parser.parse_value(s, position, reentrances)

    def unify_base_values(self, fval1, fval2, bindings):
        """
        If possible, return a single value..  If not, return
        the value L{UnificationFailure}.
        """
        if fval1 == fval2: return fval1
        else: return UnificationFailure

# Add ourselves to the list of permissible types for feature names.
FeatStruct._feature_name_types += (Feature,)


class SlashFeature(Feature):
    def parse_value(self, s, position, reentrances, parser):
        return parser.partial_parse(s, position, reentrances)

class RangeFeature(Feature):
    RANGE_RE = re.compile('(-?\d+):(-?\d+)')
    def parse_value(self, s, position, reentrances, parser):
        m = self.RANGE_RE.match(s, position)
        if not m: raise ValueError('range', position)
        return (int(m.group(1)), int(m.group(2))), m.end()

    def unify_base_values(self, fval1, fval2, bindings):
        if fval1 is None: return fval2
        if fval2 is None: return fval1
        rng = max(fval1[0], fval2[0]), min(fval1[1], fval2[1])
        if rng[1] < rng[0]: return UnificationFailure
        return rng
    
SLASH = SlashFeature('slash', default=False, display='slash')
TYPE = Feature('type', display='prefix')
    
######################################################################
# Feature Structure Parser
######################################################################

class FeatStructParser(object):
    def __init__(self, features=(SLASH, TYPE), cls=FeatStruct):
        self._features = dict((f.name,f) for f in features)
        self._class = cls
        self._prefix_feature = None
        self._slash_feature = None
        for feature in features:
            if feature.display == 'slash':
                if self._slash_feature:
                    raise ValueError('Multiple features w/ display=slash')
                self._slash_feature = feature
            if feature.display == 'prefix':
                if self._prefix_feature:
                    raise ValueError('Multiple features w/ display=prefix')
                self._prefix_feature = feature
        self._features_with_defaults = [feature for feature in features
                                        if feature.default is not None]

    def parse(self, s, fstruct=None):
        """
        Convert a string representation of a feature structure (as
        displayed by repr) into a C{FeatStruct}.  This parse
        imposes the following restrictions on the string
        representation:
          - Feature names cannot contain any of the following:
            whitespace, parenthases, quote marks, equals signs,
            dashes, commas, and square brackets.  Feature names may
            not begin with plus signs or minus signs.
          - Only the following basic feature value are supported:
            strings, integers, variables, C{None}, and unquoted
            alphanumeric strings.
          - For reentrant values, the first mention must specify
            a reentrance identifier and a value; and any subsequent
            mentions must use arrows (C{'->'}) to reference the
            reentrance identifier.
        """
        s = s.strip()
        value, position = self.partial_parse(s, 0, {}, fstruct)
        if position != len(s):
            self._error(s, 'end of string', position)
        return value

    _START_FSTRUCT_RE = re.compile(r'\s*(?:\((\d+)\)\s*)?(\??[\w-]+)?(\[)')
    _END_FSTRUCT_RE = re.compile(r'\s*]\s*')
    _SLASH_RE = re.compile(r'/')
    _FEATURE_NAME_RE = re.compile(r'\s*([+-]?)([^\s\(\)"\'\-=\[\],]+)\s*')
    _REENTRANCE_RE = re.compile(r'\s*->\s*')
    _TARGET_RE = re.compile(r'\s*\((\d+)\)\s*')
    _ASSIGN_RE = re.compile(r'\s*=\s*')
    _COMMA_RE = re.compile(r'\s*,\s*')
    _BARE_PREFIX_RE = re.compile(r'\s*(?:\((\d+)\)\s*)?(\??[\w-]+\s*)()')

    def partial_parse(self, s, position=0, reentrances=None, fstruct=None):
        """
        Helper function that parses a feature structure.
        @param s: The string to parse.
        @param position: The position in the string to start parsing.
        @param reentrances: A dictionary from reentrance ids to values.
            Defaults to an empty dictionary.
        @return: A tuple (val, pos) of the feature structure created
            by parsing and the position where the parsed feature
            structure ends.
        """
        if reentrances is None: reentrances = {}
        try:
            return self._partial_parse(s, position, reentrances, fstruct)
        except ValueError, e:
            if len(e.args) != 2: raise
            self._error(s, *e.args)

    def _partial_parse(self, s, position, reentrances, fstruct=None):
        # Create the new feature structure
        if fstruct is None:
            fstruct = self._class()
        else:
            fstruct.clear()

        # Read up to the open bracket.  
        match = self._START_FSTRUCT_RE.match(s, position)
        if not match:
            match = self._BARE_PREFIX_RE.match(s, position)
            if not match:
                raise ValueError('open bracket or identifier', position)
        position = match.end()

        # If there as an identifier, record it.
        if match.group(1):
            identifier = match.group(1)
            if identifier in reentrances:
                raise ValueError('new identifier', match.start(1))
            reentrances[identifier] = fstruct

        # If there was a prefix feature, record it.
        if match.group(2):
            if self._prefix_feature is None:
                raise ValueError('open bracket or identifier', match.start(2))
            prefixval = match.group(2).strip()
            if prefixval.startswith('?'):
                prefixval = Variable(prefixval)
            fstruct[self._prefix_feature] = prefixval

        # If group 3 is emtpy, then we just have a bare prefix, so
        # we're done.
        if not match.group(3):
            return self._finalize(s, match.end(), reentrances, fstruct)

        # Build a list of the features defined by the structure.
        # Each feature has one of the three following forms:
        #     name = value
        #     name -> (target)
        #     +name
        #     -name
        while position < len(s):
            # Use these variables to hold info about each feature:
            name = target = value = None

            # Check for the close bracket.
            match = self._END_FSTRUCT_RE.match(s, position)
            if match is not None:
                return self._finalize(s, match.end(), reentrances, fstruct)
            
            # Get the feature name's name
            match = self._FEATURE_NAME_RE.match(s, position)
            if match is None: raise ValueError('feature name', position)
            name = match.group(2)
            position = match.end()

            # Check if it's a special feature.
            if name[0] == '*' and name[-1] == '*':
                name = self._features.get(name[1:-1])
                if name is None:
                    raise ValueError('known special feature', match.start(2))

            # Check if this feature has a value already.
            if name in fstruct:
                raise ValueError('new name', match.start(2))

            # Boolean value ("+name" or "-name")
            if match.group(1) == '+': value = True
            if match.group(1) == '-': value = False

            # Reentrance link ("-> (target)")
            if value is None:
                match = self._REENTRANCE_RE.match(s, position)
                if match is not None:
                    position = match.end()
                    match = self._TARGET_RE.match(s, position)
                    if not match:
                        raise ValueError('identifier', position)
                    target = match.group(1)
                    if target not in reentrances:
                        raise ValueError('bound identifier', position)
                    position = match.end()
                    value = reentrances[target]

            # Assignment ("= value").
            if value is None:
                match = self._ASSIGN_RE.match(s, position)
                if match:
                    position = match.end()
                    value, position = (
                        self._parse_value(name, s, position, reentrances))
                # None of the above: error.
                else:
                    raise ValueError('equals sign', position)

            # Store the value.
            fstruct[name] = value
            
            # If there's a close bracket, handle it at the top of the loop.
            if self._END_FSTRUCT_RE.match(s, position):
                continue

            # Otherwise, there should be a comma
            match = self._COMMA_RE.match(s, position)
            if match is None: raise ValueError('comma', position)
            position = match.end()

        # We never saw a close bracket.
        raise ValueError('close bracket', position)

    def _finalize(self, s, pos, reentrances, fstruct):
        """
        Called when we see the close brace -- checks for a slash feature,
        and adds in default values.
        """
        # Add the slash feature (if any)
        match = self._SLASH_RE.match(s, pos)
        if match:
            name = self._slash_feature
            v, pos = self._parse_value(name, s, match.end(), reentrances)
            fstruct[name] = v
        ## Add any default features.  -- handle in unficiation instead?
        #for feature in self._features_with_defaults:
        #    fstruct.setdefault(feature, feature.default)
        # Return the value.
        return fstruct, pos
    
    def _parse_value(self, name, s, position, reentrances):
        if isinstance(name, Feature):
            return name.parse_value(s, position, reentrances, self)
        else:
            return self.parse_value(s, position, reentrances)

    def parse_value(self, s, position, reentrances):
        for (handler, regexp) in self.VALUE_HANDLERS:
            match = regexp.match(s, position)
            if match:
                handler_func = getattr(self, handler)
                return handler_func(s, position, reentrances, match)
        raise ValueError('value', position)

    def _error(self, s, expected, position):
        estr = ('Error parsing feature structure\n    ' +
                s + '\n    ' + ' '*position + '^ ' +
                'Expected %s' % expected)
        raise ValueError, estr

    #////////////////////////////////////////////////////////////
    #{ Value Parsers
    #////////////////////////////////////////////////////////////

    #: A table indicating how feature values should be parsed.  Each
    #: entry in the table is a pair (handler, regexp).  The first entry
    #: with a matching regexp will have its handler called.  Handlers
    #: should have the following signature:
    #:
    #:    def handler(s, position, reentrances, match): ...
    #:
    #: and should return a tuple (value, position), where position is
    #: the string position where the value ended.  (n.b.: order is
    #: important here!)
    VALUE_HANDLERS = [
        ('parse_fstruct_value', _START_FSTRUCT_RE),
        ('parse_var_value', re.compile(r'\?[a-zA-Z_][a-zA-Z0-9_]*')),
        ('parse_str_value', re.compile("[uU]?[rR]?(['\"])")),
        ('parse_int_value', re.compile(r'-?\d+')),
        ('parse_sym_value', re.compile(r'[a-zA-Z_][a-zA-Z0-9_]*')),
        ('parse_app_value', re.compile(r'<(app)\((\?[a-z][a-z]*)\s*,'
                                       r'\s*(\?[a-z][a-z]*)\)>')),
        ('parse_logic_value', re.compile(r'<([^>]*)>')),
        ('parse_set_value', re.compile(r'{')),
        ('parse_tuple_value', re.compile(r'\(')),
        ]

    def parse_fstruct_value(self, s, position, reentrances, match):
        return self.partial_parse(s, position, reentrances)

    def parse_str_value(self, s, position, reentrances, match):
        return nltk.internals.parse_str(s, position)

    def parse_int_value(self, s, position, reentrances, match):
        return int(match.group()), match.end()

    # Note: the '?' is included in the variable name.
    def parse_var_value(self, s, position, reentrances, match):
        return Variable(match.group()), match.end()

    _SYM_CONSTS = {'None':None, 'True':True, 'False':False}
    def parse_sym_value(self, s, position, reentrances, match):
        val, end = match.group(), match.end()
        return self._SYM_CONSTS.get(val, val), end

    def parse_app_value(self, s, position, reentrances, match):
        """Mainly included for backwards compat."""
        return LogicParser().parse('(%s %s)' % match.group(2,3)), match.end()

    def parse_logic_value(self, s, position, reentrances, match):
        parser = LogicParser()
        try:
            expr = parser.parse(match.group(1))
            if parser.buffer: raise ValueError()
            return expr, match.end()
        except ValueError:
            raise ValueError('logic expression', match.start(1))

    def parse_tuple_value(self, s, position, reentrances, match):
        return self._parse_seq_value(s, position, reentrances, match, ')', 
                                     FeatureValueTuple, FeatureValueConcat)

    def parse_set_value(self, s, position, reentrances, match):
        return self._parse_seq_value(s, position, reentrances, match, '}',
                                     FeatureValueSet, FeatureValueUnion)
    
    def _parse_seq_value(self, s, position, reentrances, match,
                         close_paren, seq_class, plus_class):
        """
        Helper function used by parse_tuple_value and parse_set_value.
        """
        cp = re.escape(close_paren)
        position = match.end()
        # Special syntax fo empty tuples:
        m = re.compile(r'\s*/?\s*%s' % cp).match(s, position)
        if m: return seq_class(), m.end()
        # Read values:
        values = []
        seen_plus = False
        while True:
            # Close paren: return value.
            m = re.compile(r'\s*%s' % cp).match(s, position)
            if m:
                if seen_plus: return plus_class(values), m.end()
                else: return seq_class(values), m.end()
            
            # Read the next value.
            val, position = self.parse_value(s, position, reentrances)
            values.append(val)

            # Comma or looking at close paren
            m = re.compile(r'\s*(,|\+|(?=%s))' % cp).match(s, position)
            if m.group(1) == '+': seen_plus = True
            if not m: raise ValueError("',' or '+' or '%s'" % cp, position)
            position = m.end()

######################################################################
#{ Demo
######################################################################

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

def interactivedemo(trace=False):
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

def demo(trace=False):
    """
    Just for testing
    """
    #import random
    
    # parser breaks with values like '3rd'
    fstruct_strings = [
        '[agr=[number=sing, gender=masc]]',
        '[agr=[gender=masc, person=3]]',
        '[agr=[gender=fem, person=3]]',
        '[subj=[agr=(1)[]], agr->(1)]',
        '[obj=?x]', '[subj=?x]',
        '[/=None]', '[/=NP]',
        '[cat=NP]', '[cat=VP]', '[cat=PP]',
        '[subj=[agr=[gender=?y]], obj=[agr=[gender=?y]]]',
        '[gender=masc, agr=?C]',
        '[gender=?S, agr=[gender=?S,person=3]]'
        ]
    all_fstructs = [FeatStruct(fss) for fss in fstruct_strings]    
    #MAX_CHOICES = 5
    #if len(all_fstructs) > MAX_CHOICES:
        #fstructs = random.sample(all_fstructs, MAX_CHOICES)
        #fstructs.sort()
    #else:
        #fstructs = all_fstructs
                
    for fs1 in all_fstructs:
        for fs2 in all_fstructs:
            print "\n*******************\nfs1 is:\n%s\n\nfs2 is:\n%s\n\nresult is:\n%s" % (fs1, fs2, unify(fs1, fs2))
 

if __name__ == '__main__':
    demo()
