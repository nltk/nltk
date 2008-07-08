"""Module for resolving relative and absolute paths in FUF"""
import nltk

class LinkResolver(object):
    """
    Object for resolving links
    Note: links should not be resolved if 'alt' is present 
    in the feature structure.
    """

    def __init__(self):
        self.unique_var_counter = 0

    
    def _unique_var(self):
        """
        Ensures that unique variable names are used when resolving links
        """

        self.unique_var_counter += 1
        return nltk.Variable("?x%s" % self.unique_var_counter)
    
    def resolve(self, fstruct, alt_check=True):
        """
        Resolve the relative and absolute links in the feature structure
        """

        def get_link_value(fs, path):
            target = None
            
            # in case we find another link keep a copy
            ancestors = [fs]
            resolved_inner_link = False

            # to to the end
            last_step = path[-1]
            path = path[:-1]

            for step in path:
                if step in fs and not isinstance(fs[step], ReentranceLink):
                    fs = fs[step]
                    ancestors.append(fs)
                elif step not in fs:
                    fs[step] = nltk.FeatStruct()
                    fs = fs[step]
                    ancestors.append(fs)
                elif isinstance(fs[step], ReentranceLink):
                    fs[step] = get_link_value(ancestors[-1*fs[step].up],
                                              fs[step].down)
                    fs = fs[step]
                    resolved_inner_link = True
                    
            if last_step in fs:
                if isinstance(fs[last_step], ReentranceLink):
                    print 'doh'
                    exit()
                return fs[last_step]
            fs[last_step] = self._unique_var()
            return fs[last_step]


        def resolve_helper2(fs, ancestors, lnk=None):
            # start looking for links
            for feat, val in fs.items():
                # add to path and recurse
                if isinstance(val, nltk.FeatStruct):
                    ancestors.append(val)
                    resolve_helper2(val, ancestors)
                    ancestors.pop()
                # found the link
                elif isinstance(val, ReentranceLink):
                    if val.up > 0 and len(val.down) > 0:
                        # relative link with a path
                        if (val.up >= len(ancestors)):
                            fs[feat] = get_link_value(ancestors[-1*val.up], val.down)
                        else:
                            # we will try to resolve this link later
                            pass
                    elif val.up == 0 and len(val.down) > 0:
                        # get the value for the absolute link
                        fs[feat] = get_link_value(ancestors[0], val.down)
                    else:
                        raise ValueError("Malformed Link: %s" % val)

        resolve_helper2(fstruct, [fstruct])


class ReentranceLink(object):
    """
    Used to store fuf's reentrance links; these are resolved
    after the parsing and alt structure generation.

    First go up C{self.up} levels then follow the 
    featrue path C{self.down}
    """

    def __init__(self, path):
        self.up = 0
        self.down = []

        for feat in path:
            if feat == "^":
                self.up +=1
                assert self.down == []
            else:
                self.down.append(feat)
        self.down = tuple(self.down)

    def __repr__(self):
        return "{%s%s}" % ("^"* self.up, ' '.join( self.down))

if __name__ == '__main__':
    # testing the link resolution using gr0.fuf grammar and ir0.fuf inputs
    import os
    from fufconvert import *
    from fuf import *

    gfs = fuf_to_featstruct(open('tests/gr0.fuf').read())
    itext = open('tests/ir0.fuf').readlines()[2]
    
    ifs = fuf_to_featstruct(itext)
    result = unify_with_grammar(ifs, gfs)

    print output_html([ifs, gfs, result])
