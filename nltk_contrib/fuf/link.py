"""Module for resolving relative and absolute paths in FUF"""
import nltk

class LinkResolver(object):
    """
    Object for resolving links
    Note: links should not be resolved if 'alt' is present 
    in the feature structure.
    """

    def __init__(self):
        """
        Initialize and return the object.
        """
        self.unique_var_counter = 0

    
    def _unique_var(self):
        """
        Ensures that unique variable names are used when resolving links
        """

        self.unique_var_counter += 1
        return nltk.Variable("?x%s" % self.unique_var_counter)
    
    def _get_value(self, fs, path):
        """
        Find and return the value within the feature structure
        given a path.

        @param fs: Feature structre
        @type fs: C{nltk.featstruct.FeatStruct}
        @param path: list of keys to follow
        @type path: list
        @return: the feature value at the end of the path
        """
        target = None
        
        # in case we find another link keep a copy
        ancestors = [fs]

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
                parent = ancestors[-1*fs[step].up]
                new_path = fs[step].down
                fs[step] = self._get_value(parent, new_path)
                fs = fs[step]
                
        if isinstance(fs, nltk.sem.Variable):
            return fs

        if last_step in fs:
            assert (not isinstance(fs[last_step], ReentranceLink))
            return fs[last_step]

        # All the way through the path but the value doesn't exist
        # create a variable
        fs[last_step] = self._unique_var()
        return fs[last_step]

    def resolve(self, fstruct):
        """
        Resolve the relative and absolute links in the feature structure
        
        @param fstruct: Feature structure that may contain relative and absolute
        links
        @type fstruct: C{nltk.featstruct.FeatStruct}
        """

        def resolve_helper(fs, ancestors):
            # start looking for links
            for feat, val in fs.items():
                # add to path and recurse
                if isinstance(val, nltk.FeatStruct):
                    ancestors.append(val)
                    resolve_helper(val, ancestors)
                    ancestors.pop()
                # found the link
                elif isinstance(val, ReentranceLink):
                    if val.up > 0 and len(val.down) > 0:
                        # relative link with a path
                        if (val.up >= len(ancestors)):
                            parent = ancestors[-1*val.up]
                            path = val.down
                            fs[feat] = self._get_value(parent, path)
                        else:
                            # we will try to resolve this link later
                            pass
                    elif val.up == 0 and len(val.down) > 0:
                        # get the value for the absolute link
                        parent = ancestors[0]
                        path = val.down
                        fs[feat] = self._get_value(parent, path)
                    else:
                        raise ValueError("Malformed Link: %s" % val)

        resolve_helper(fstruct, [fstruct])


class ReentranceLink(object):
    """
    Used to store fuf's reentrance links; these are resolved
    after the parsing and alt structure generation.

    First go up C{self.up} levels then follow the 
    featrue path C{self.down}
    """

    def __init__(self, path):
        """
        Initialize and return the object

        @param path: the path to the value of the link
        @type path: list
        """
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
        """
        Return a string representation of this link
        """
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
