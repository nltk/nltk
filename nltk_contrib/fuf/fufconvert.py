import re
import os
import nltk
from sexp import *
from link import *
from specialfs import *

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
    
