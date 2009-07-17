# Natural Language Toolkit: Resolve Anaphora for DRT 
#
# Author: Dan Garrette <dhgarrette@gmail.com>
#
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
This module performs the anaphora resolution functionality for DRT.py.  It may be 
modified or swapped out to test different resolution techniques.
"""

import logic


class AnaphoraResolutionException(Exception):
    pass


class DRS(object):
    def resolve_anaphora(self, trail=[]):
        r_conds = []
        for cond in self.conds:
            r_cond = cond.resolve_anaphora(trail + [self])
            
            # if the condition is of the form '(x = [])' then do not include it
            if not isinstance(r_cond, EqualityExpression) or \
               not r_cond.isNullResolution():
                r_conds.append(r_cond)
            else:
                raise AnaphoraResolutionException("Variable '%s' does not "
                        "resolve to anything." % r_cond.get_assigned_variable())
                
        return self.__class__(self.refs, r_conds)
    
class AbstractVariableExpression(object):
    def resolve_anaphora(self, trail=[]):
        return self
    
class NegatedExpression(object):
    def resolve_anaphora(self, trail=[]):
        return self.__class__(self.term.resolve_anaphora(trail + [self]))

class LambdaExpression(object):
    def resolve_anaphora(self, trail=[]):
        return self.__class__(self.variable, self.term.resolve_anaphora(trail + [self]))

class BinaryExpression(object):
    def resolve_anaphora(self, trail=[]):
        return self.__class__(self.first.resolve_anaphora(trail + [self]), 
                              self.second.resolve_anaphora(trail + [self]))

class BooleanExpression(BinaryExpression):
    pass

class OrExpression(BooleanExpression):
    pass

class ImpExpression(BooleanExpression):
    def resolve_anaphora(self, trail=[]):
        trail_addition = [self, self.first]
        return self.__class__(self.first.resolve_anaphora(trail + trail_addition),
                              self.second.resolve_anaphora(trail + trail_addition))

class IffExpression(BooleanExpression):
    pass

class EqualityExpression(BinaryExpression):
    def isNullResolution(self):
        return (isinstance(self.second, PossibleAntecedents) and not self.second) or \
                (isinstance(self.first, PossibleAntecedents) and not self.first)
                
    def get_assigned_variable(self):
        """
        Since an equality expression will assign a variable to something, but
        that variable may be on either side of the equality sign, return the
        variable no matter which side it is on.
        """
        if isinstance(self.first, AbstractVariableExpression):
            return self.first
        else:
            return self.second

class ConcatenationDRS(BooleanExpression):
    pass

class ApplicationExpression(object):
    def resolve_anaphora(self, trail=[]):
        if self.is_pronoun_function():
            possible_antecedents = PossibleAntecedents()
            for ancestor in trail:
                for ref in ancestor.get_refs():
                    refex = self.make_VariableExpression(ref)
                    
                    #==========================================================
                    # Don't allow resolution to itself or other types
                    #==========================================================
                    if refex.__class__ == self.argument.__class__ and \
                       not (refex == self.argument):
                        possible_antecedents.append(refex)
                
            if len(possible_antecedents) == 1:
                resolution = possible_antecedents[0]
            else:
                resolution = possible_antecedents 
            return self.make_EqualityExpression(self.argument, resolution)
        else:
            r_function = self.function.resolve_anaphora(trail + [self])
            r_argument = self.argument.resolve_anaphora(trail + [self])
            return self.__class__(r_function, r_argument)

class PossibleAntecedents(list, logic.Expression):
    def free(self, indvar_only=True):
        """Set of free variables."""
        return set(self)

    def replace(self, variable, expression, replace_bound=False):
        """Replace all instances of variable v with expression E in self,
        where v is free in self."""
        result = PossibleAntecedents()
        for item in self:
            if item == variable:
                self.append(expression)
            else:
                self.append(item)
        return result
    
    def simplify(self):
        return self

    def str(self, syntax=logic.Tokens.NLTK):
        return '[' + ','.join([str(item) for item in self]) + ']'
