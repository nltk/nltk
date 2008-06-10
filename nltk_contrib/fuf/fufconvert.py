import re
import os
import nltk
from sexp import *

def fuf_to_featstruct(fuf):
    """
    Convert a FUF (as a sexpr string) to a FeatureStruct object.
    """
    slp = SexpListParser()
    sexp = slp.parse(fuf)
    #sexp = SexpListParser.parse(fuf)
    fstruct = _convert_fuf_featstruct(sexp)
    _resolve_fs_links(fstruct, [])
    return fstruct

def _convert_fuf_featstruct(sexp):
    assert sexp.lparen == '('
    fs = nltk.FeatStruct()
    for child in sexp:
        feat, val = _convert_fuf_feature(child)
        fs[feat] = val
    return fs

def _convert_fuf_feature(sexp):
    assert sexp.lparen == '(', sexp
    feat, name, val = ('', '','')
    if sexp[0] == 'alt' and isinstance(sexp[1], basestring):
        assert len(sexp) == 3
        feat, name, val = sexp
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
        choices = [_convert_fuf_featstruct(c) for c in val]
        val = nltk.FeatStruct(dict([('%d' % (i+1), choice)
                                    for i, choice in enumerate(choices)]))
        # Process the alt with a name
        if len(name) > 0:
            fs = nltk.FeatStruct()
            fs[name] = val
            return feat, fs
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

class ReentranceLink(object):
    """
    Used to store fuf's reenttrance links; these are resolved *after* the
    entire input has been parsed, to make the resolution algorithm simpler.
    
    First go up C{self.up} levels, then follow the feature path C{self.down}
    """
    def __init__(self, path):
        self.up = 0
        self.down = []

        for feat in path:
            if feat == '^':
                self.up += 1
                assert self.down == []
            else:
                self.down.append(feat)
        self.down = tuple(self.down)

    def __repr__(self):
        return '{%s%s}' % ('^ '*self.up, ' '.join(self.down))

_unique_var_counter = 0
def _unique_var():
    global _unique_var_counter
    _unique_var_counter += 1
    return nltk.Variable('?x%s' % _unique_var_counter)

def _resolve_fs_links(fstruct, ancestors):
    ancestors = ancestors + [fstruct]
    for feat, val in fstruct.items():
        if isinstance(val, nltk.FeatStruct):
            _resolve_fs_links(val, ancestors)
        elif isinstance(val, ReentranceLink):
            target = ancestors[len(ancestors)-1-val.up]
            for i, path_feat in enumerate(val.down):
                # Create the target, if necessary.
                if path_feat not in target:
                    if i == len(val.down)-1:
                        target[path_feat] = _unique_var()
                    else:
                        target[path_feat] = nltk.FeatStruct()
                # Walk down the feature path.
                target = target[path_feat]
            # The final value of 'target' is the value we
            # should use to replace the reentrance link.
            fstruct[feat] = target

######################################################################
# Test code:
######################################################################


if __name__ == '__main__':
    t = r"""
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
    print fuf_to_featstruct(t)
    print

    for gfile in os.listdir('tests/'):
        print "FILE: %s" % gfile
        text = open("tests/%s" % gfile).read()
        try:
            print fuf_to_featstruct(t)
        except Exception,e:
            print "Exception -->> %s" % e



