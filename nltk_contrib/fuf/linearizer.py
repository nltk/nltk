"""
The linearizer for unified fuf feature structures

"""

import nltk

def linearize(fstruct):
    """
    Perfom the linearilization of the input feature structure.
    Returns a list
    """
    def lin_helper(fs, pattern, output):
        for item in pattern:
            if item == 'dots':
                output.append('')
            else:
                if fs[item].has_key('pattern'):
                    lin_helper(fs[item], fs[item]['pattern'], output)
                elif fs[item].has_key('lex'):
                    output.append(fs[item]['lex'])

    output = []
    lin_helper(fstruct, fstruct['pattern'], output)
    return output

if __name__ == '__main__':
    from fufconvert import *
    from fuf import *
   
    gfs = fuf_to_featstruct(open('tests/gr0.fuf').read())
 
    itext = open('tests/ir0.fuf').readlines()[3]
    ifs = fuf_to_featstruct(itext)
    result = unify_with_grammar(ifs, gfs) 
    print result
    print linearize(result)


