# Natural Language Toolkit: Resolve Anaphora for DRT 
#
# Author: Dan Garrette <dhgarrette@gmail.com>
#
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""
This module performs the anaphora resolution functionality for DRT.py.  It may be 
modified or swapped out to test different resolution techniques.
"""

from nltk.sem import logic

class DRS:
    def resolve_anaphora(self, trail=[]):
        r_conds = []
        for cond in self.conds:
            r_cond = cond.resolve_anaphora(trail + [self])
            
            # if the condition is of the form '(x = [])' then do not include it
            if not isinstance(r_cond, EqualityExpression) or not r_cond.isNullResolution():
                r_conds.append(r_cond)
                
        return self.__class__(self.refs, r_conds)
    
class VariableExpression:
    def resolve_anaphora(self, trail=[]):
        return self

class NegatedExpression:
    def resolve_anaphora(self, trail=[]):
        return self.__class__(self.term.resolve_anaphora(trail + [self]))

class LambdaExpression:
    def resolve_anaphora(self, trail=[]):
        return self.__class__(self.variables, self.term.resolve_anaphora(trail + [self]))

class BooleanExpression:
    def resolve_anaphora(self, trail=[]):
        return self.__class__(self.first.resolve_anaphora(trail + [self]), 
                              self.second.resolve_anaphora(trail + [self]))

class OrExpression(BooleanExpression):
    pass

class ImpExpression(BooleanExpression):
    def resolve_anaphora(self, trail=[]):
        trail_addition = [self, self.first]
        return self.__class__(self.first.resolve_anaphora(trail + trail_addition),
                              self.second.resolve_anaphora(trail + trail_addition))

class IffExpression(BooleanExpression):
    pass

class EqualityExpression(BooleanExpression):
    def isNullResolution(self):
        return (isinstance(self.second, PossibleAntecedents) and not self.second) or \
                (isinstance(self.first, PossibleAntecedents) and not self.first)

class ConcatenationDRS(BooleanExpression):
    pass

class ApplicationExpression:
    def resolve_anaphora(self, trail=[]):
        if isinstance(self.function, VariableExpression) and self.function.name == self.get_pronoun_token():
            assert len(self.args) == 1 #only one arg is allowed in PRO(x)
            possible_antecedents = PossibleAntecedents()
            for ancestor in trail:
                try:
                    possible_antecedents.extend(ancestor.get_refs())
                except AttributeError:
                    pass #the ancestor does not have a get_refs method
                
            #===============================================================================
            #   This line ensures that statements of the form ( x = x ) wont appear.
            #   Possibly amend to remove antecedents with the wrong 'gender' 
            #===============================================================================
            arg = self.args[0]
            possible_antecedents.remove(arg)
            equalityExpression = self.get_EqualityExpression()
            if len(possible_antecedents) == 1:
                equalityExp = equalityExpression(arg, possible_antecedents[0])
            else:
                equalityExp = equalityExpression(arg, possible_antecedents) 
            return equalityExp
        else:
            r_function = self.function.resolve_anaphora(trail + [self])
            r_args = [arg.resolve_anaphora(trail + [self]) for arg in self.args]
            return self.__class__(r_function, r_args)

class PossibleAntecedents(list, logic.Expression):
    def free(self):
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

    def str(self, syntax=logic.Tokens.NEW_NLTK):
        return '[' + ','.join([str(item) for item in self]) + ']'
