"""
A preliminary feature structure module.

Based loosely on C{feature.py} by Rob Speer.
"""

import re, copy

# This class doesn't actually do anything; all the work is done
# by FeatureVariableBinding, and during unification.
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
    def __init__(self):
        self._bindings = {}
        self._merged_vars = {}

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
    @ivar _forward: This variable is used during unification to record
        the 'cannonical' copy of a feature structure.  This is
        necessary to maintain reentrance links.
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

    #################################################################
    ## Unification
    #################################################################

    # Unification is done in two steps:
    #   1. Make copies of self and other, and destructively unify
    #      them.
    #   2. Make a pass through the unified structure to make sure
    #      that we preserved reentrancy.
    def unify(self, other, apply_bindings=1):
        """
        @param apply_bindings: As the two feature structures get
            unified, we construct a set of variable bindings.
            If C{apply_bindings} is true, then any bound variables
            are replaced by their values.  In the future, we
            probably want some way to I{return} the bindings.
        """
        try:
            selfcopy = copy.deepcopy(self)
            othercopy = copy.deepcopy(other)
            bindings = FeatureVariableBinding()
            
            selfcopy._destructively_unify(othercopy, bindings)
            selfcopy._cleanup_forwards()
            if apply_bindings:
                selfcopy._apply_bindings(bindings)
            return selfcopy
        except FeatureStructure._UnificationFailureError: return None

    def _apply_bindings(self, bindings):
        for (fname, fval) in self._features.items():
            if (isinstance(fval, FeatureVariable) and
                bindings.is_bound(fval)):
                self._features[fname] = bindings.lookup(fval)
            if isinstance(fval, FeatureStructure):
                fval._apply_bindings(bindings)

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

    def _cleanup_forwards(self):
        """
        Use the C{_forward} links on a feature structure generated
        by L{_destructively_unify} to ensure that reentrancy is
        preserved.
        """
        for fname, fval in self._features.items():
            if isinstance(fval, FeatureStructure):
                if fval._forward is not None:
                    self._features[fname] = fval._forward
                fval._cleanup_forwards()
    
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
        for (fname, fval) in self._features.items():
            if not isinstance(fval, FeatureStructure):
                segments.append('%s = %s' % (fname, fval))
            elif reentrance_ids.has_key(id(fval)):
                segments.append('%s -> (%s)' % (fname,
                                                reentrance_ids[id(fval)]))
            else:
                fval_repr = fval._repr(reentrances, reentrance_ids)
                is_reentrant = reentrances[id(fval)]
                if is_reentrant:
                    # Pick a new id.
                    reentrance_ids[id(fval)] = len(reentrance_ids)+1
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
        # What's the longest feature name?  Use this to align names.
        maxfnamelen = max([len(fname) for fname in self._features.keys()])

        lines = []
        for (fname, fval) in self._features.items():
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
                
                # Is it reentrant?  If it is, then pick a new
                # identifier number for it; and display that id
                # (along with fname) on the name line.
                is_reentrant = reentrances[id(fval)]
                if is_reentrant:
                    # Pick a new id.
                    reentrance_ids[id(fval)] = len(reentrance_ids)+1
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

    def _find_reentrances(self, reentrances=None):
        """
        Find all of the feature values contained by self that are
        reentrant (i.e., that can be reached by multiple paths through
        feature structure's features).  Return a dictionary
        C{reentrances} that maps from the C{id} of each feature value
        to a boolean value, indicating whether it is reentrant or not.
        """
        if reentrances is None: reentrances={}

        # Walk through the feature tree.  The first time we see a
        # feature value, map it to False (not reentrant).  If we see a
        # feature value more than once, then map it to C{True}
        # (reentrant).
        for fval in self._features.values():
            # False the first time we see it; True if we see it more
            # than once.
            reentrances[id(fval)] = reentrances.has_key(id(fval))
            # Recurse to contained feature structures (only if this
            # is the first time we saw it).
            if not reentrances[id(fval)]:
                if isinstance(fval, FeatureStructure):
                    fval._find_reentrances(reentrances)

        return reentrances

    #################################################################
    ## Parsing
    #################################################################
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

#f1=FeatureStructure.parse('[CAT=np, AGREE=[number=singular, gender=?g]]')
#f2=FeatureStructure.parse('[CAT=np, AGREE=[gender=masculine]]')
#
f6=FeatureStructure.parse('[SUBJECT=[AGREE=[PERSON=third]]]')
#
ftemp=FeatureStructure(NUMBER='singular')
f7=FeatureStructure(AGREE=ftemp, SUBJECT=FeatureStructure(AGREE=ftemp))
f8 = f6.unify(f7)


#x,y,z=[FeatureStructure(x=1), FeatureStructure(y=1), FeatureStructure(z=1)]
#f6=FeatureStructure(A=x,B=x, C=z)
#f7=FeatureStructure(B=y,C=y)
#f6=FeatureStructure(A=x,B=z)
#f7=FeatureStructure(A=y,B=y)

x,y,z = [FeatureVariable(n) for n in 'xyz']
f1 = FeatureStructure(A=FeatureStructure(a=1), B=FeatureStructure(b=1))
f2 = FeatureStructure(A=y, B=y)
f3 = f1.unify(f2)

print f6,'\n'
print f7,'\n'
print f8,'\n'
print `f8`



# Reentrancy?
# [AGREE=1[NUMBER=singular, PERSON=third], SUBJECT=[AGREE->1]]
