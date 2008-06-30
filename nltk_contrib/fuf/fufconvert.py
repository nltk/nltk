import re
import os
import nltk
from sexp import *
from link import *
from specialfs import *

counter = 0
def fuf_to_featstruct(fuf):
    """
    Convert a FUF (as a sexpr string) to a FeatureStruct object.
    """
    slp = SexpListParser()
    sexp = slp.parse(fuf)
    #sexp = SexpListParser.parse(fuf)
    fstruct = _convert_fuf_featstruct(sexp)

    # resole relative and absolute links
    resolver = LinkResolver()
    # we dont resolve before we break stuff up
    #resolver.resolve(fstruct)
    return fstruct

def _convert_fuf_featstruct(sexp):
    assert sexp.lparen == '('
    fs = nltk.FeatStruct()
    for child in sexp:
        if "%" in child or "control" in child:
            continue
        feat, val = _convert_fuf_feature(child)
        print fs.has_key(feat)
        fs[feat] = val
    return fs

def _convert_fuf_feature(sexp):
    assert sexp.lparen == '(', sexp
    feat, name, index, val = ('', '', '', '')

    if sexp == []:
        return "empty", nltk.FeatStruct()

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
    if feat == 'pattern':
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
            tempfs = nltk.FeatStruct()
            tempfs[name] = val
            return feat, tempfs
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
    TEST_FILES = False
    t = r"""
        ((alt top (((cat s) 
            (prot ((cat np))) 
            (goal ((cat np))) 
            (verb ((cat vp) 
                   (number {prot number}))) 
            (pattern (prot verb goal))) 
           ((cat np) 
            (n ((cat noun) (number {^ ^ number}))) 
            (alt altname (((proper yes) 
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
    # the relative path should refer to the value of 
    #  prot number
    # TODO: absolute paths and resolving relative paths correctly
    te = r"""
    ((cat s)
     (prot (( cat np)
            ( number sing)))
     (verb ((cat vp) 
            (number {^ ^ prot number}))))
    """
    t = open("tests/gr4.fuf").read()
    print fuf_to_featstruct(t)

    if TEST_FILES:
        for gfile in os.listdir('tests/'):
            print "FILE: %s" % gfile
            text = open("tests/%s" % gfile).read()
            try:
                print fuf_to_featstruct(t)
            except Exception,e:
                print "Exception -->> %s" % e
