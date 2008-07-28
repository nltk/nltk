"""
C{fstypes.py} module contains the implementation of feature
value types as defined in the FUF manual (v5.2)
"""
from sexp import *
from nltk.featstruct import CustomFeatureValue, UnificationFailure

class FeatureTypeTable(object):
    """
    The C{FeatureTypeTable} maintains relationships between 
    a given feature value and its specializations.
    """

    def __init__(self):
        """
        Instantiate and return the object
        """
        self.table = {}

    def define_type(self, name, children):
        """
        Add a relationship between C{name} and it is specializations
        C{children}.
    
        @param name: The most general value
        @type name: string
        @param children: The specialization of a name
        @type children: single string or list of strings
        """

        if name not in self.table.keys():
            self.table[name] = []
        if isinstance(children, basestring):
            children = [children]
        for child in children:
            self.table[name].append(child)

    def subsume(self, name, specialization):
        """
        Check if C{name} is subsumes the C{specialization}.

        @param name: Feature value
        @type name: string
        @param specialization: Possible specialization of C{name}
        @type specialization: string
        """

        # quick check if the specialization is the immediate one
        spec = specialization
        if name == spec: return True
        if not self.table.has_key(name): return False
        if spec in self.table[name]:
            return True
        return any(self.subsume(item, spec) for item in self.table[name])

    def __repr__(self):
        output = ""
        for key, value in self.table.items():
            output += "%s <--- %s\n" % (key, value)
        return output

class TypedFeatureValue(CustomFeatureValue):
    """
    Feature value that has been defined as a FUF type
    """
    def __init__(self, value, type_table):
        """
        Initialize and return the object.
        
        @param value: The feature value
        @type value: string
        @param type_table: The table of feature value types defined in the
        current grammar.
        @type type_table: FeatureTypeTable
        """
        assert value
        assert type_table
        self.value = value
        self.table = type_table
    
    def __repr__(self):
        """
        Return the string representation of the typed
        feature value.

        @returns: t'featurevalue'
        """
        return "t'%s'" % (self.value)

    def unify(self, other):
        """
        Unify the typed feature value with the other 
        feature value. 
        
        The unification succeeds if both, this and the other
        feature are of C{TypefFeatureValue} type and:
            - this feature is a specialization of the other feature
            - the other feature is a specialization of this feature
            - both features are the same value

        The unification fails if:
            - the feature values are of different types
            - there is no relationship between the two features

        @param other: Feature value
        @type other: C{TypedFeatureValue}
        @return: The most specific type based on the relationship
        defined in the type table of this feature value (C{self.table})

        """
        # feature values must be of the same type
        if not isinstance(other, TypedFeatureValue):
            return UnificationFailure

        # other.value is the specialization of self.value
        if (self.table.subsume(self.value, other.value)):
            return TypedFeatureValue(other.value, self.table)

        # this value is the specialization of other value
        if (self.table.subsume(other.value, self.value)):
            return TypedFeatureValue(self.value, self.table)

        # everything failed
        return UnificationFailure
        
    def __cmp__(self, other):
        if not isinstance(other, TypedFeatureValue):
            return -1
        return cmp(self.value, other.value)

def assign_types(table, fs):
    """
    Convert those feature values that are in the type table to
    C{TypedFeatureValue} objects. This function modifies
    the C{fs} feature structure.

    @param table: The type table
    @type table: C{FeatureTypeTable}
    @param fs: Feature structure
    @type fs: C{nltk.featstruct.FeatStruct}
    """
    def assign_types_helper(fs, type_table, flat_type_table):
        # go through the feature structure and convert the typed values
        for fkey, fval in fs.items():
            if isinstance(fval, nltk.FeatStruct):
                assign_types_helper(fval, type_table, flat_type_table)
            elif isinstance(fval, basestring) and (fval in flat_type_table):
                newval = TypedFeatureValue(fval, table)
                fs[fkey] = newval

    # flattten the table 
    flat_type_table = list()
    for tkey, tvalue in table.table.items():
        flat_type_table.append(tkey)
        for tval in tvalue:
            flat_type_table.append(tval)
   
    assign_types_helper(fs, table, flat_type_table)
    return fs

if __name__ == "__main__":
    typedefs = open('tests/types.fuf').readlines()
    type_table = FeatureTypeTable()
    for typedef in typedefs:
        sexp = SexpListParser().parse(typedef)
        type_table.define_type(sexp[1], sexp[2])

    print type_table
    print type_table.subsume('np', 'common')
    print type_table.subsume('mood', 'imperative')



