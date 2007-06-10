# New lambda system (Steven Bird)

class Lambda:
    def __init__(self, *args):
        if isinstance(args[0], str):
            if len(args) == 1:
                self._var = args[0]
                self._type = 'v'
            else:
                self._var = args[0]
                self._term = args[1]
                self._type = 'l'
        else:
            self._f = args[0]
            self._arg = args[1]
            self._type = 'f'
            
    def equals(self, other):
        if self.__class__ is not other.__class__:
            return False
        elif self._type is not other._type:
            return False
        elif self._type == 'v':
            return self._var == other._var
        elif self._type == 'l':
            return self._var == other._var and self._term.equals(other._term)
        elif self._type == 'f':
            return self._f.equals(other._f) and self._arg.equals(other._arg)

    def variables(self):
        if self._type == 'v':
            return set([self._var])
        elif self._type == 'l':
            return set([self._var]).union(self._term.variables())
        elif self._type == 'f':
            return self._f.variables().union(self._arg.variables())

    def free(self):
        if self._type == 'v':
            return set([self._var])
        elif self._type == 'l':
            return self._term.free().difference(set([self._var]))
        elif self._type == 'f':
            return self._f.free().union(self._arg.free())

    def subterms(self):
        if self._type == 'v':
            return set([self])
        elif self._type == 'l':
            return self._term.subterms().union([self])
        elif self._type == 'f':
            return self._f.subterms().union(self._arg.subterms()).union(set([self]))

    def replace(self, variable, expression):
        if self._type == 'v':
            if self._var == variable:
                return expression
            else:
                return self
        elif self._type == 'l':
            return Lambda(self._var,\
                                self._term.replace(variable, expression))
        elif self._type == 'f':
            return Lambda(self._f.replace(variable, expression),\
                                     self._arg.replace(variable, expression))

    def simplify(self):
        if self._type == 'v':
            return self
        elif self._type == 'l':
            return Lambda(self._var, self._term.simplify())
        elif self._type == 'f':
            f = self._f.simplify()
            arg = self._arg.simplify()
            if f._type == 'l':
                return f._term.replace(f._var, arg).simplify()
            else:
                return self

    def __str__(self, continuation=0):
        if self._type == 'v':
            return '%s' % self._var
        elif self._type == 'l':
            if continuation:
                prefix = ' '
            else:
                prefix = '\\'
            if self._term._type == 'l':
                return '%s%s%s' % (prefix, self._var, self._term.__str__(1))
            else:
                return '%s%s.%s' % (prefix, self._var, self._term)
        elif self._type == 'f':
            str_f = str(self._f)
            if self._f._type == 'f':
                str_f = str_f[1:-1]
            return '(%s %s)' % (str_f, self._arg)

    def __repr__(self):
        if self._type == 'v':
            return "Lambda('%s')" % self._var
        elif self._type == 'l':
            return "Lambda('%s', '%s')" % (self._var, self._term)
        elif self._type == 'f':
            return "Lambda('%s', '%s')" % (self._f, self._arg)

def expressions():
    """Return a sequence of test expressions."""
    A = Lambda('a')
    X = Lambda('x')
    Y = Lambda('y')
    Z = Lambda('z')
    XA = Lambda(X, A)
    XY = Lambda(X, Y)
    XZ = Lambda(X, Z)
    YZ = Lambda(Y, Z)
    XYZ = Lambda(XY, Z)
    xX = Lambda('x', X)
    xyX = Lambda('x', Lambda('y', X))
    xXY = Lambda('x', XY)
    S = Lambda(xyX, A)
    B = Lambda('x', Lambda('y', Lambda('z', Lambda(X, YZ))))
    C = Lambda('x', Lambda('y', Lambda('z', Lambda(XZ, Y))))
    O = Lambda('x', Lambda('y', XY))
    N = Lambda(xX, A)
    P = Lambda(Lambda('x', XA), xX)
    return [N, P, S]

for expr in expressions():
    print expr, "->", expr.simplify()
