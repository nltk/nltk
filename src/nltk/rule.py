from token import *
from string import join

class Rule:
    def __init__(self, lhs, *rhs):
        self._lhs = lhs
        self._rhs = rhs
    def lhs(self):
        return self._lhs
    def rhs(self, pos=-1):
        if pos == -1:
            return self._rhs
        else:
            if pos < len(self):
                return self._rhs[pos]
            else:
                raise IndexError('The specified position does not exist')
    def __len__(self):
        return len(self._rhs)
    def pp(self):
        return self._lhs + ' -> ' + join(self._rhs)
    def __repr__(self):
        str = repr(self._lhs) + ' ->'
        for c in self._rhs:
            str += ' '+repr(c)
        return str
    def __str__(self):
        return self.pp()
    def __eq__(self, other):
        return (self._lhs == other._lhs and
                self._rhs == other._rhs)
    def __hash__(self):
        return hash((self._lhs, self._rhs))

class DottedRule(Rule):
    def __init__(self, rule, pos):
        self._rule = rule
        self._lhs = rule.lhs()
        self._rhs = rule.rhs()
        self._pos = pos
    def rule(self):
        return self._rule
    def pos(self):
        return self._pos
    def next(self):
        return Rule.rhs(self,self._pos)
    def incr(self):
        if self._pos < len(self):
            self._pos += 1
        else:
            raise IndexError('Attempt to move dot position past end of rule')
    def final(self):
        return self._pos == len(self)
    def pp(self):
        return Rule.pp(self) + ' [' + `self._pos` + ']'
    def __repr__(self):
        return Rule.__repr__(self) + ' [' + `self._pos` + ']'
    def __str__(self):
        return self.pp()
    def __eq__(self, other):
        return (Rule.__eq__(self, other) and
                self._pos == other._pos)
