import os
import nltk
import fufconvert
from fufconvert import *
from link import *
from linearizer import *
from util import output_html


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
            alt_keys = alt.keys()
            alt_keys.sort()
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
        for i, grammar_rule in enumerate(grammar_rules):
            try:
                unified_fstruct = fstruct.unify(grammar_rule)
            except Exception, e:
                print 
                print 'EXCEPTION:', e
                print fstruct
                print 
                print grammar_rule
                exit()
            if unified_fstruct is not None:
                # unified, now recursively apply grammar rules to 
                # the child features
                #lr.resolve(unified_fstruct)

                # debugging_start
                #raw_input('paused')
                temp = [fstruct, '%d' % i, grammar_rule, unified_fstruct ]
                header = ['input', 'grammar_number', 'grammar', 'result']
                print output_html(temp, header)
                # debuggin_end

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
    grammar_rules.reverse()


    # resolve the links
    lr = LinkResolver()
    
    # debugging_start
    for i, rule in enumerate(grammar_rules):
        lr.resolve(rule)
        print output_html(['%s' % i, rule])
    # debugging_end

    # before the unification we have to resolve all the relative and absolute
    # links 

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
    from util import output_html

    #simple
    itext, gtext = open('tests/uni.fuf').readlines()
    ifs = fuf_to_featstruct(itext)
    gfs = fuf_to_featstruct(gtext)
    result = unify_with_grammar(ifs, gfs)

    # inputs and grammars from fuf distribution
    grammar_files = [gfile for gfile in os.listdir('tests/') if gfile.startswith('gr')]
    input_files = [ifile for ifile in os.listdir('tests/') if ifile.startswith('ir')]
    for ifile, gfile in zip(input_files, grammar_files):
        # input files contain more than one definition of input
        output = None
        result = None
        print ifile, gfile
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
