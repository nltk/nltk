import nltk
import fufconvert
#from nltk.featstruct import FeatStruct


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
            if gkey != "alt":
                fs[gkey] = gvalue

        # unpacking the alt
        if not grammar.has_key('alt'):
            return grammar

        if grammar.has_key('alt'):
            alt = grammar['alt']
            alt_keys = alt.keys()
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

    # make a copy of the original input
    return unify_with_grammar_helper(input_fs.copy(), grammar_rules)


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
    result = unify_with_grammar(input_fs, grammar_fs)
    # the number doesn't propagate which means that we will have to set it
    #result['number'] = 3
    print result

