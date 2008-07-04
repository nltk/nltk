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

        def resolve_helper(fstruct, ancestors):
            for feat, val in fstruct.items():
                if isinstance(val, nltk.FeatStruct):
                    # bulding the path of how we got here
                    ancestors.append(val)
                    resolve_helper(val, ancestors)
                    ancestors.pop()
                elif isinstance(val, ReentranceLink):
                    target = None
                    parent = None
                    # decide if this is a relative or absolute link
                    if val.up > 0:
                        parent = ancestors[:-1*(val.up-1)]
                    else:
                        parent = [ancestors[0]]
                    # if the parent is empty then introduce a variable
                    if len(parent) == 0:
                        target = self._unique_var()
                    else:
                        target = parent[-1]
                        for path_feat in val.down:
                            # if the features doesn't exist there
                            if path_feat not in target:
                                if path_feat == val.down[-1]:
                                    target[path_feat] = self._unique_var()
                                else:
                                    target[path_feat] = nltk.FeatStruct()
                            target = target[path_feat]
                            #else:
                                #target = target[path_feat]
                    fstruct[feat] = target

        resolve_helper(fstruct, [fstruct])


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

