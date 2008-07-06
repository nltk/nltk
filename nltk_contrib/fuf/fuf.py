import os
import nltk
import fufconvert
from fufconvert import *
from link import *
from linearizer import *


def unify_with_grammar(input_fs, grammar_fs):
    """
    Unify the input feature structure with the grammar feature structure
    """

    def unpack_alt(grammar):
        """
        Traverses the grammar and expands all the possible 
        paths through the grammar
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
            alt_keys = grammar[alt_name].keys()
            # if this is a named alt structure go one level deeper
            if len(alt_keys) == 1 and alt_keys[0].isalpha():
                alt = grammar['alt'][alt_keys[0]]
            for key in alt.keys():
                fscopy = fs.copy()
                if isinstance(alt[key], nltk.sem.Variable):
                    fscopy[key] = alt[key]
                else:
                    for akey, avalue in alt[key].items():
                        fscopy[akey] = avalue
                packs.append(fscopy)

        # recursively try to unpack any
        # possible nested alts
        unpacked = list()
        while len(packs) > 0:
            pack = packs.pop(0)
            temp = unpack_alt(pack)
            if isinstance(temp, list):
                for i in temp:
                    packs.append(i)
            else:
                unpacked.append(temp)
        return unpacked


    def unify_with_grammar_helper(fstruct, grammar_rules):
        """
        Unify the input with the grammar
        """
        # Try unifying the given feature structure with each of 
        # the grammar rules
        for grammar_rule in grammar_rules:
            unified_fstruct = fstruct.unify(grammar_rule)
            if unified_fstruct is not None:
                # unified, now recursively apply grammar rules to 
                # the child features
                for (feat_name, feat_val) in unified_fstruct.items():
                    if isinstance(feat_val, nltk.FeatStruct):
                        new_val = unify_with_grammar_helper(feat_val,
                                                            grammar_rules)
                        unified_fstruct[feat_name] = new_val
                return unified_fstruct
         
        return unified_fstruct


    # Unpack the alt's in the grammar
    # Generates a list of grammar rules
    grammar_rules = unpack_alt(grammar_fs)

    # resolve the links
    lr = LinkResolver()
    for rule in grammar_rules:
        lr.resolve(rule)


    # make a copy of the original input
    return unify_with_grammar_helper(input_fs.copy(), grammar_rules)

def draw(fstruct, filename=None):
    """
    Draw graph representation of the feature structure using graphviz syntax
    """
    def draw_helper(output, fstruct, pcount, ccount):
        output += 'fs%d [label=" " style="filled" fillcolor="white"];\n' % (pcount)
        for fs, val in fstruct.items():
            if isinstance(val, nltk.FeatStruct):
                output +=  'fs%d -> fs%d [label="%s"];\n' % (pcount, ccount, fs)
                output, ccount = draw_helper(output, val, ccount,
                                                     ccount+1)
            else:
                output +=  'fs%d -> fs%d [label="%s"]; fs%d [label="%s" \
                style=filled fillcolor=grey];\n' % (pcount, ccount, fs,
                                                            ccount, val)
            ccount +=1 
        return output, ccount

    output, ccount = draw_helper("", fstruct, 0, 1)
    return "digraph fs {\n nodesep=1.0;\n" + output + "\n}";

if __name__ == "__main__":
    # tests for unification


    # simple
    #itext, gtext = open('tests/uni.fuf').readlines()
    #ifs = fuf_to_featstruct(itext)
    #gfs = fuf_to_featstruct(gtext)
    #result = unify_with_grammar(ifs, gfs)
    #print ifs
    #print 
    #print gfs
    #print
    #print result


    # inputs and grammars from fuf distribution
    grammar_files = [gfile for gfile in os.listdir('tests/') if gfile.startswith('gr')]
    input_files = [ifile for ifile in os.listdir('tests/') if ifile.startswith('ir')]
    for ifile, gfile in zip(input_files, grammar_files):
        # input files contain more than one definition of input
        result = None
        print ifile, gfile
        print "INPUT FILE: %s, GRAMMAR FILE: %s" % (ifile, gfile)
        gfs = fuf_to_featstruct(open('tests/%s' % gfile).read())
        for iline in open('tests/%s' % ifile).readlines():
            print 'GRAMMAR'
            print gfs
            print
            try:
                ifs = fuf_to_featstruct(iline)
            except Exception, e:
                print e
                print 'failed to convert'
                print iline
                exit()
            print "INPUT"
            print ifs
            print
            result = unify_with_grammar(ifs, gfs)
            print 'RESULT'
            print result
            print 
            print 'LINEARIZATION'
            if result:
                print " ".join(linearize(result))
            else:
                print ''
            print
            print '----------' 
            
            # quit after the first 2 sets of files have been processed
        exit()
