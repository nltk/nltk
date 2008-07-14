import os
import nltk

from fufconvert import *
from link import *
from linearizer import *
from util import output_html

def _unpack_alt(grammar):
    """
    Traverses the grammar and expands all the possible 
    paths through the grammar. Returns a list of 
    all possible paths of constituents.
    """
    # used to store the alternatives
    packs = list()

    # make a copy of everything without the alt
    fs = nltk.featstruct.FeatStruct()
    for gkey, gvalue in grammar.items():
        if gkey != "alt" and not gkey.startswith("alt_"):
            fs[gkey] = gvalue

    # unpacking the alt
    alts = [key for key in grammar.keys() \
            if key.startswith('alt_') or key == 'alt']
    
    # If there are no alts our work here is done
    if len(alts) == 0:
        return grammar


    for alt_name in alts:
        alt = grammar[alt_name]
        alt_keys = [int(key) for key in alt.keys() if key != '_index_']

        alt_keys.sort()
        alt_keys = [str(key) for key in alt_keys]
        for key in alt_keys:
            fscopy = fs.copy()
            for akey, avalue in alt[key].items():
                fscopy[akey] = avalue
            packs.append(fscopy)

    # recursively try to unpack any
    # possible nested alts
    unpacked = list()
    while len(packs) > 0:
        pack = packs.pop()
        temp = _unpack_alt(pack)
        if isinstance(temp, list):
            for i in temp:
                packs.insert(0, i)
        else:
            unpacked.insert(0, temp)
    
    return unpacked

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


def _unify(fs, grs, resolver=None, trace=False):
    unifs = None
    for gr in grs:
        unifs = fs.unify(gr)
        if unifs:
            resolver.resolve(unifs)
            print output_html([fs, gr, unifs])
            for fname, fval in unifs.items():
                if _isconstituent(unifs, fname, fval):
                    newval = _unify(fval, grs, resolver)
                    if newval:
                        unifs[fname] = newval
            return unifs
    return unifs
    

def unify_with_grammar(input_fs, grammar_fs, trace=False):
    """
    Unify the input feature structure with the grammar feature structure
    """

    # Generates a list of grammar rules
    grammar_rules = _unpack_alt(grammar_fs)
    #grammar_rules.reverse()

    lr = LinkResolver()
    
    for i, rule in enumerate(grammar_rules):
        print output_html([str(i), rule])
        #lr.resolve(rule)
        pass

    # make a copy of the original input
    return _unify(input_fs.copy(), grammar_rules, resolver=lr)


if __name__ == "__main__":
    # tests for unification
    from util import output_html

    #simple
    itext, gtext = open('tests/uni.fuf').readlines()
    ifs = fuf_to_featstruct(itext)
    gfs = fuf_to_featstruct(gtext)
    result = unify_with_grammar(ifs, gfs)

    # inputs and grammars from fuf distribution
    grammar_files = [gfile for gfile in os.listdir('tests/') if gfile.startswith('gr')]
    input_files = [ifile for ifile in os.listdir('tests/') if ifile.startswith('ir')]

    #grammar_files = ['gr1.fuf']
    #input_files = ['ir1.fuf']
    for ifile, gfile in zip(input_files, grammar_files):
        if ifile == 'ir3.fuf' and gfile == 'gr3.fuf':
            continue
        # input files contain more than one definition of input
        output = None
        result = None
        print "INPUT FILE: %s, GRAMMAR FILE: %s" % (ifile, gfile)
        gfs = fuf_to_featstruct(open('tests/%s' % gfile).read())
        for iline in open('tests/%s' % ifile).readlines():
            try:
                ifs = fuf_to_featstruct(iline)
            except Exception, e:
                print 'Failed to convert %s to nltk.FeatStruct' % iline
                exit()
            result = unify_with_grammar(ifs, gfs)
            if result:
                output = " ".join(linearize(result))
                print output_html([ifs, gfs, result, output])
