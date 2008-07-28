"""
The linearizer for unified fuf feature structures

"""

import nltk
from link import *
from util import output_html

def linearize(fstruct):
    """
    Perfom the linearilization of the input feature structure.

    @param fstruct: feature structure
    @type fstruct: C{nltk.featstruct.FeatStruct}
    @return: string
    """
    def lin_helper(fs, pattern, output):
        for item in pattern:
            if item == 'dots':
                output.append('')
            elif not (item in fs):
                # the key in the pattern is not in the feature
                pass
            else:
                if isinstance(fs[item], ReentranceLink):
                    LinkResolver().resolve(fs)
                if fs[item].has_key('pattern'):
                    lin_helper(fs[item], fs[item]['pattern'], output)
                elif fs[item].has_key('lex'):
                    output.append(fs[item]['lex'])

    assert isinstance(fstruct, nltk.FeatStruct)
    output = []
    assert fstruct
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


