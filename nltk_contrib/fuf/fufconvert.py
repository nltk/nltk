import re
import os
import nltk
from sexp import *
from link import *
from specialfs import *
from fstypes import *

def fuf_to_featstruct(fuf):
    """
    Convert a FUF (as a sexpr string) to a FeatureStruct object.
    """
    slp = SexpListParser()
    sexp = slp.parse(fuf)
    return _convert_fuf_featstruct(sexp)

def _convert_fuf_featstruct(sexp):
    assert sexp.lparen == '('
    fs = nltk.FeatStruct()
    for child in sexp:
        if isinstance(child, basestring):
            feat, val = _convert_fuf_feature(sexp)
            fs[feat] = val
            break
        else:
            feat, val = _convert_fuf_feature(child)
            fs[feat] = val
    return fs

def _convert_fuf_feature(sexp):
    assert sexp.lparen == '(', sexp
    feat, name, index, val = ('', '', '', '')

    # Special handling for the alt feature
    if sexp[0] == 'alt':
        feat, name, index, val = parse_alt(sexp)
    elif sexp[0] == 'opt':
        feat, name, index, val = parse_opt(sexp)
    elif len(sexp) == 3 and sexp[1] == '===':
        temp = SexpList('(', ')')
        temp.append('lex')
        temp.append(sexp.pop())
        sexp[1] = temp
        feat, val = sexp
    else:
        assert len(sexp) == 2, sexp[1]
        assert isinstance(sexp[0], basestring), sexp
        feat, val = sexp

    # Special handling for pattern feature
    if feat in ('pattern', 'cset'):
        assert isinstance(val, SexpList) and val.lparen == '('
        return feat, nltk.FeatureValueTuple(val)

    # Special handling of the alt feature
    if feat == 'alt':
        assert isinstance(val, SexpList) and val.lparen == '('
        choices = list()
        for c in val:
            if isinstance(c, basestring):
                choices.append(c)
            else:
                choices.append(_convert_fuf_featstruct(c))
            val = nltk.FeatStruct(dict([('%d' % (i+1), choice)
                                        for i, choice in enumerate(choices)]))
        # Process the alt with a name
        if len(name) > 0:
            return "%s_%s" % (feat, name), val

        # there is an index defined on this alt
        if isinstance(index, SexpList):
            ifs = _convert_fuf_featstruct(index)
            val["_index_"] = ifs[":index"]
        return feat, val

    if isinstance(val, SexpList):
        # If value is a feature structure, then recurse.
        if val.lparen == '(':
            return feat, _convert_fuf_featstruct(val)
        # If value is a pointer, then do something.
        if val.lparen == '{':
            # We'll resolve this later, using _resolve_fs_links():
            return feat, ReentranceLink(val)
        else:
            assert False, 'unexpected sexp type'
            
    # Otherwise, return the value as a string.
    return feat, val

 
def fuf_file_to_featstruct(fuf_filename):
    """
    Convert fuf file to C{nltk.FeatStruct} and processed the type definitions
    Returns the type table and the converted feature structure
    """

    # Convert the fuf code into expression lists
    sfp = SexpFileParser(fuf_filename)
    lsexp = sfp.parse()
    assert lsexp

    type_table = FeatureTypeTable()
    fs = nltk.FeatStruct()

    # process the type defs and the grammar
    for sexp in lsexp:
        if isinstance(sexp[0], basestring) and sexp[0] == 'define-feature-type':
            assert len(sexp) == 3
            name, children = sexp[1], sexp[2]
            type_table.define_type(name, children)
        else:
            # assuming that it is a feature structure
            fs = _convert_fuf_featstruct(sexp)
            # there should be nothing following the feature definition
            break
    return type_table, fs
            
            
            





######################################################################
# Test code:
######################################################################


if __name__ == '__main__':
    # the tests below are for conversion of fuf syntax to nltk.FeatStruct

    #test the alt feature

    # test the relative link feature
    print "START LINK TEST"
    linklines = open('tests/link.fuf').readlines()
    for line in linklines:
        print "INPUT:", line
        print fuf_to_featstruct(line)
        print

    # test the opt feature
    print "START OPT TEST"
    optlines = open('tests/opt.fuf').readlines()
    for line in optlines:
        print "INPUT:", line
        print fuf_to_featstruct(line)
        print


    # test the example grammars
    grammar_files = [gfile for gfile in os.listdir('tests/') if gfile.startswith('gr')]
    print grammar_files
    for gfile in grammar_files:
        print "FILE: %s" % gfile
        text = open('tests/%s' % gfile).read()
        print fuf_to_featstruct(text)
        print
        exit()

    
    type_table, grammar = fuf_file_to_featstruct('tests/typed_gr4.fuf')
    print type_table
    print grammar
