import os
import nltk

from fufconvert import *
from link import *
from linearizer import *
from util import output_html, flatten


class GrammarPathResolver(object):
    """
    C{GrammarPathResolver} analyses a given grammar and generates 
    the list of possible paths through the grammar by unpacking
    all the possible alternations.
    """
    def __init__(self, grammar, table):
        """
        Instantiate and return the object
        
        @param grammar: The FUF grammar
        @type grammar: C{nltk.featsturct.FeatStruct}
        @param table: Feature type table
        @type table: C{FeatureTypeTable}
        """
        self.grammar = grammar
        self.table = table


    @staticmethod
    def filter_for_alt(grammar):
        """
        Helper function. Separates the I{alt} from other key, value pairs

        @param grammar: The feature structure to filter
        @type grammar: C{nltk.featstruct.FeatStruct}

        @return: Tuple, where the first item is the feature structure
        that does not contain any alternations on the top level and 
        a list of keys of alternations.
        """

        alts = list()
        fs = nltk.FeatStruct()
        for gkey, gvalue in grammar.items():
            if gkey != "alt" and not gkey.startswith("alt_"):
                #if isinstance(gvalue, basestring):
                fs[gkey] = gvalue
                #else:
                    #fs[gkey] = gvalue.copy()
            else:
                alts.append(gkey)
        return fs, alts 

    @staticmethod
    def alt_to_list(fs, altname):
        """
        Helper function. Converts an altenation structure into a list of values

        @param fs: The alternation feature structure
        @type fs: C{nltk.featstruct.FeatStruct}
        @param altname: The key for the alternation structure
        @type altname: string

        @return: list
        """
        altkeys = fs[altname].keys()
        altkeys = sorted([int(key) for key in altkeys if key != "_index_"], cmp)
        altkeys = [str(key) for key in altkeys]

        alternations = list()
        for key in altkeys:
            alternations.append(fs[altname][key])
        return alternations


    @staticmethod
    def _is_subsumed_val(table, fs, fkey, other):
        """
        Check if the value specified by key I{fkey} in 
        feature structure I{fs} subsumes the value
        at key I{fkey} in the feature structure C{other}

        @param table: Feature type table
        @type table: C{fstypes.FeatureTypeTable}
        @param fs: Feature structure
        @type fs: C{nltk.featstruct.FeatStruct}
        @param other: Feature structure
        @type other: C{nltk.featstruct.FeatStruct}
        @return: True, if fs[key] subsumes other[fkey], False otherwise.
        """
        return table and table.subsume(fs[fkey], other[fkey])

    @staticmethod
    def _copy_vals(table, fs, pack):
        """
        Helper method. Copy the keys and values of I{fs}
        into the pack structure. 
        If pack is a list of feature structures then each of them is 
        mofified. Otherwise, pack is a feature structure and it modified.

        @param table: Feature type table
        @type table: C{fstypes.FeatureTypeTable}
        @param fs: Feature structure
        @type fs: C{nltk.featstruct.FeatSturct}
        @param pack: feature structure or list of feature structures
        @type pack: C{nltk.featstruct.FeatStruct} or list of above
        """
        if isinstance(pack, list):
            for subpack in pack:
                for fkey, fvalue in fs.items():
                    if (fkey in subpack) and \
                       GrammarPathResolver._is_subsumed_val(table, fs, fkey, subpack):
                        pass
                    else:
                        if isinstance(subpack, list): 
                            GrammarPathResolver._copy_vals(table, fs, subpack)
                            return
                        assert not isinstance(subpack, list)
                        assert isinstance(subpack, nltk.FeatStruct)
                        subpack[fkey] = fvalue
        else:
            assert isinstance(pack, nltk.FeatStruct)
            for fkey, fvalue in fs.items():
                if (fkey in pack) and \
                   GrammarPathResolver._is_subsumed_val(table, fs, fkey, pack):
                    pass
                else:
                    pack[fkey] = fvalue

    def resolve(self, fstruct):
        """
        Traverse the grammar and find all the possible paths
        throught the alternations.

        @param fstruct: grammar
        @type fstruct: C{nltk.featstruct.FeatStruct}
        @return: A list of feature structure each of which is a possible
        path through the alternations.
        """

        if isinstance(fstruct, basestring):
            return fstruct
        fs, alts = GrammarPathResolver.filter_for_alt(fstruct)

        if len(alts) > 0:
            result = list()
            for altname in alts:
                toplevel_pack =  GrammarPathResolver.alt_to_list(fstruct, altname)
                subpack = list()
                for item in toplevel_pack:
                    if isinstance(item, nltk.FeatStruct) and len(item.keys()) == 0:
                        # empty feature - result of having opts
                        pass
                    elif isinstance(item, nltk.FeatStruct):
                        temp = self.resolve(item)
                        GrammarPathResolver._copy_vals(self.table, fs, temp)
                        subpack.append(temp)
                    else:
                        subpack.append(item)
                for item in subpack:
                    result.append(item)
            return result
        else:
            total_packs = list()
            for fkey, fvalue in fstruct.items():
                if isinstance(fvalue, nltk.FeatStruct):
                    subpack = list()
                    fs, alts = GrammarPathResolver.filter_for_alt(fvalue)
                    if len(alts) > 0:
                        for item in self.resolve(fvalue):
                            newfs = nltk.FeatStruct()
                            newfs[fkey] = item
                            for key, value in fvalue.items():
                                if not ('alt' in value):
                                    newfs[key] = value
                            subpack.append(newfs)
                        for i in subpack: total_packs.append(i)
            if len(total_packs) > 0:
                return total_packs
            else:
                return fstruct

class Unifier(object):
    """
    Class for unification of feature structures defined by FUF. 
    Example usage:

        >>> itext, gtext = open('tests/uni.fuf').readlines()
        # set up the input structure
        >>> fsinput = fuf_to_featstruct(itext)
        >>> print fsinput
        [ cat  = 's'                      ]
        [                                 ]
        [ goal = [ n = [ lex = 'mary' ] ] ]
        [                                 ]
        [ prot = [ n = [ lex = 'john' ] ] ]
        [                                 ]
        [ verb = [ v = [ lex = 'link' ] ] ]
        # set up the grammar structure
        >>> fsgrammar = fuf_to_featstruct(gtext)
        >>> print fsgrammar
        [           [     [ cat     = 's'                        ]            ] ]
        [           [     [                                      ]            ] ]
        [           [     [ goal    = [ cat = 'np' ]             ]            ] ]
        [           [     [                                      ]            ] ]
        [           [ 1 = [ pattern = (prot, verb, goal)         ]            ] ]
        [           [     [                                      ]            ] ]
        [           [     [ prot    = [ cat = 'np' ]             ]            ] ]
        [           [     [                                      ]            ] ]
        [           [     [ verb    = [ cat    = 'vp'          ] ]            ] ]
        [           [     [           [ number = {prot number} ] ]            ] ]
        [           [                                                         ] ]
        [           [     [       [ 1 = [ pattern = (n)   ]               ] ] ] ]
        [           [     [       [     [ proper  = 'yes' ]               ] ] ] ]
        [           [     [       [                                       ] ] ] ]
        [           [     [ alt = [     [ det     = [ cat = 'article' ] ] ] ] ] ]
        [           [     [       [     [           [ lex = 'the'     ] ] ] ] ] ]
        [           [     [       [ 2 = [                               ] ] ] ] ]
        [ alt_top = [ 2 = [       [     [ pattern = (det, n)            ] ] ] ] ]
        [           [     [       [     [ proper  = 'no'                ] ] ] ] ]
        [           [     [                                                 ] ] ]
        [           [     [ cat = 'np'                                      ] ] ]
        [           [     [                                                 ] ] ]
        [           [     [ n   = [ cat    = 'noun'     ]                   ] ] ]
        [           [     [       [ number = {^^number} ]                   ] ] ]
        [           [                                                         ] ]
        [           [     [ cat     = 'vp'             ]                      ] ]
        [           [ 3 = [ pattern = (v)              ]                      ] ]
        [           [     [                            ]                      ] ]
        [           [     [ v       = [ cat = 'verb' ] ]                      ] ]
        [           [                                                         ] ]
        [           [ 4 = [ cat = 'noun' ]                                    ] ]
        [           [                                                         ] ]
        [           [ 5 = [ cat = 'verb' ]                                    ] ]
        [           [                                                         ] ]
        [           [ 6 = [ cat = 'article' ]                                 ] ]
        # unify the input and the grammar
        >>> fuf = Unifier(fsinput, fsgrammar)
        >>> result = fuf.unify()
        # show the result
        >>> print result
        [ cat     = 's'                               ]
        [                                             ]
        [           [ cat     = 'np'                ] ]
        [           [                               ] ]
        [           [           [ cat    = 'noun' ] ] ]
        [           [ n       = [ lex    = 'mary' ] ] ]
        [ goal    = [           [ number = ?x2    ] ] ]
        [           [                               ] ]
        [           [ number  = ?x2                 ] ]
        [           [ pattern = (n)                 ] ]
        [           [ proper  = 'yes'               ] ]
        [                                             ]
        [ pattern = (prot, verb, goal)                ]
        [                                             ]
        [           [ cat     = 'np'                ] ]
        [           [                               ] ]
        [           [           [ cat    = 'noun' ] ] ]
        [           [ n       = [ lex    = 'john' ] ] ]
        [ prot    = [           [ number = ?x1    ] ] ]
        [           [                               ] ]
        [           [ number  = ?x1                 ] ]
        [           [ pattern = (n)                 ] ]
        [           [ proper  = 'yes'               ] ]
        [                                             ]
        [           [ cat     = 'vp'             ]    ]
        [           [ number  = ?x1              ]    ]
        [ verb    = [ pattern = (v)              ]    ]
        [           [                            ]    ]
        [           [ v       = [ cat = 'verb' ] ]    ]
        [           [           [ lex = 'link' ] ]    ]
    
    .
    """

    def __init__(self, fsinput, fsgrammar, table=None):
        """
        Initialize and return the object.

        @param fsinput: The input feature structure
        @type fsinput: C{nltk.featstruct.FeatStruct}
        @param fsgrammar: The generation grammar
        @type fsgrammar: C{nltk.featstruct.FeatStruct}
        @param table: The feature value type table
        @type table: C{fstypes.FeatureTypeTable}
        """
        import copy
        self.fsinput = fsinput
        self.fsgrammar = fsgrammar
        self.table = table
        self.lr = LinkResolver()
        self.gpr = GrammarPathResolver(copy.deepcopy(fsgrammar), table)

        self.grammar_paths = flatten(self.gpr.resolve(copy.deepcopy(fsgrammar)))

        # the type table has been passed in
        # assign types to the feature values
        if table:
            for i, path in enumerate(self.grammar_paths):
                path = assign_types(table, path)
                self.grammar_paths[i] = path


        
    @staticmethod
    def _isconstituent(fstruct, subfs_key, subfs_val):
        """
        Features containing cat attributes are constituents.
        If feature (cset (c1 .. cn)) is foudn i the FS then the cset is just (c1 ..
        cn)
        if no feature cset is found, the set is the unifion o the following fs:
            - if a pair contains feature (cat xx), it is constituent
            - if sub-fd is mentioned in the (pattern ..) it is a constituent
        """
        if not isinstance(subfs_val, nltk.FeatStruct):
            return False

        if 'cat' in subfs_val:
            return True

        if ('pattern' in fstruct):
            for fkey in subfs_val.keys():
                if fkey in fstruct['pattern']:
                    return True
        return False


    @staticmethod
    def _unify(fs, grs, resolver=None, trace=False):
        unifs = None
        for gr in grs:
            unifs = fs.unify(gr)
            if unifs:
                resolver.resolve(unifs)
                for fname, fval in unifs.items():
                    if Unifier._isconstituent(unifs, fname, fval):
                        newval = Unifier._unify(fval, grs, resolver)
                        if newval:
                            unifs[fname] = newval
                return unifs
        return unifs
    

    def unify(self):
        """
        Unify the input feature structure with the grammar feature structure
        
        @return: If unification is succesful the result is the unified
        structure. Otherwise return value is None.
        
        """
        
        self.lr.resolve(self.fsinput)
        # make a copy of the original input
        return Unifier._unify(self.fsinput, self.grammar_paths, self.lr)


if __name__ == "__main__":
    # tests for unification

    # inputs and grammars from fuf distribution
    grammar_files = [gfile for gfile in os.listdir('tests/') if gfile.startswith('gr')]
    input_files = [ifile for ifile in os.listdir('tests/') if ifile.startswith('ir')]

    grammar_files = ['gr2.fuf']
    input_files = ['ir2.fuf']
    for ifile, gfile in zip(input_files, grammar_files):
        if ifile == 'ir3.fuf' and gfile == 'gr3.fuf':
            print 'gr3.fuf doesn\'t work because of the (* focus) s-expression in the feature structure'
            continue
        # input files contain more than one definition of input
        output = None
        result = None
        print "\nINPUT FILE: %s, GRAMMAR FILE: %s" % (ifile, gfile)
        gfs = fuf_to_featstruct(open('tests/%s' % gfile).read())
        for i, iline in enumerate(open('tests/%s' % ifile).readlines()):
            try:
                ifs = fuf_to_featstruct(iline)
            except Exception, e:
                print 'Failed to convert %s to nltk.FeatStruct' % iline
                exit()
            fuf = Unifier(ifs, gfs)
            result = fuf.unify()
            if result:
                output = " ".join(linearize(result))
                print output_html([ifs, gfs, result, output])
                print i, "result:", output
            else:
                print i, 'result: failed'
