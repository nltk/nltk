import nltk
import fufconvert
from link import *


def unify_with_grammar(input_fs, grammar_fs):
    """
    Unify the input feature structure with the grammar feature structure
    """

    def unpack_alt(grammar):
        """
        Traveres the grammar and expands all the possible 
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
                    if isinstance(feat_val, nltk.featstruct.FeatStruct):
                        new_val = unify_with_grammar_helper(feat_val,
                                                            grammar_rules)
                        unified_fstruct[feat_name] = new_val
                return unified_fstruct
         
        return unified_fstruct


    # Unpack the alt's in the grammar
    # Generates a list of grammar rules
    grammar_rules = unpack_alt(grammar_fs)

    # resolve the links
    for rule in grammar_rules:
        print rule
        LinkResolver().resolve(rule)
        print
        print rule
        print '---------'

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
    input_fs = nltk.featstruct.FeatStruct("""
        [cat=s, 
            prot=[n=[lex=John]],
            verb=[v=[lex=like]],
            goal=[n=[lex=Mary]]]""")
    # convert the grammar to featstruct
    grammar = r"""
    ((alt top (((cat s) 
                (prot ((cat np))) 
                (goal ((cat np))) 
                (verb ((cat vp) 
                       (number {prot number}))) 
                (pattern (prot verb goal))) 
               ((cat np) 
                (n ((cat noun) 
                    (number {^ ^ number}))) 
                (alt (((proper yes) 
                       (pattern (n))) 
                      ((proper no) 
                       (pattern (det n)) 
                       (det ((cat article) 
                             (lex the))))))) 
               ((cat vp) 
                (pattern (v)) 
                (v ((cat verb)))) 
              ((cat noun)) 
               ((cat verb)) 
               ((cat article)))))
       """

    grammar_fs = fufconvert.fuf_to_featstruct(grammar)
    print 'grammar'
    print grammar_fs
    result = unify_with_grammar(input_fs, grammar_fs)

    print 'input'
    print input_fs
    print "RESULT"
    print result

