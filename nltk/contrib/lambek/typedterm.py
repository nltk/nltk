#!/usr/bin/python
#
# type.py
#
# Edward Loper
# Created [12/10/00 01:58 PM]
# $Id$
#

"""CG-style types"""

import types
from term import *

#####################################
# TYPEDTERM
#####################################

class TypedTerm:
    def __init__(self, term, type):
        # Check types, because we're paranoid.
        if not isinstance(term, Term) or \
           not isinstance(type, Type):
            raise TypeError('Expected Term, Type arguments', term, type)
        
        self.term = term
        self.type = type

    def __repr__(self):
        return `self.term`+': '+`self.type`

    def pp(self, pp_varmap=None):
        return self.term.pp(pp_varmap)+': '+`self.type`

    def to_latex(self, pp_varmap=None):
        term = self.term.to_latex(pp_varmap)
        type = `self.type`
        type = re.sub(r'\\', r'$\\backslash$', type)
        type = re.sub(r'\*', r'$\\cdot$', type)
        return term+': \\textrm{'+type+'}'

    def unify(self, other, varmap):
        if not isinstance(other, TypedTerm):
            raise TypeError('Expected TypedTerm')
        if self.type != other.type:
            raise ValueError("Can't unify -- types don't match", \
                             self.type, other.type)
        term = unify(self.term, other.term, varmap)
        if term == None:
            return None
        else:
            return TypedTerm(term, self.type)

    def simplify(self, varmap):
        return TypedTerm(reduce(simplify(self.term, varmap)), self.type) 

#####################################
# TYPES
#####################################
    
class Type:
    def __init__(self):
        raise TypeError("Type is an abstract class")

class LSlash(Type):
    # arg is the type of the expected argument
    # result is the resultant type.
    def __init__(self, arg, result):
        self.arg = arg
        self.result = result
        if not isinstance(arg, Type) or not isinstance(result, Type):
            raise TypeError('Expected Type arguments')
    def __repr__(self):
        if isinstance(self.result, RSlash) or \
           isinstance(self.result, LSlash):
            right = '('+`self.result`+')'
        else: right = `self.result`
        if isinstance(self.arg, RSlash):
            left = '('+`self.arg`+')'
        else: left = `self.arg`
        return left + '\\' + right
    def __cmp__(self, other):
        if isinstance(other, LSlash) and  self.arg == other.arg and \
           self.result == other.result:
            return 0
        else:
            return -1

class RSlash(Type):
    # arg is the type of the expected argument
    # result is the resultant type.
    def __init__(self, result, arg):
        self.arg = arg
        self.result = result
        if not isinstance(arg, Type) or not isinstance(result, Type):
            raise TypeError('Expected Type arguments')
    def __repr__(self):
        if isinstance(self.result, RSlash):
            left = '('+`self.result`+')'
        else: left = `self.result`
        return left + '/' + `self.arg`
    
        #return '('+`self.result`+'/'+`self.arg`+')'
        if isinstance(self.arg, LSlash):
            return `self.result`+'/('+`self.arg`+')'
        else:
            return `self.result`+'/'+`self.arg`
    def __cmp__(self, other):
        if isinstance(other, RSlash) and  self.arg == other.arg and \
           self.result == other.result:
            return 0
        else:
            return -1
            
class BaseType(Type):
    def __init__(self, name):
        if type(name) != types.StringType:
            raise TypeError("Expected a string name")
        self.name = name
    def __repr__(self):
        return self.name
    def __cmp__(self, other):
        if isinstance(other,BaseType) and self.name == other.name:
            return 0
        else:
            return -1
        
class Dot(Type):
    def __init__(self, left, right):
        self.right = right
        self.left = left
        if not isinstance(right, Type) or not isinstance(left, Type):
            raise TypeError('Expected Type arguments')
    def __repr__(self):
        return '('+`self.left`+'*'+`self.right`+')'
    def __cmp__(self, other):
        if isinstance(other, Dot) and  self.left == other.left and \
           self.right == other.right:
            return 0
        else:
            return -1

# Strip outermost parens from a string..  inefficient, but simple :)
def strip_parens(str):
    if len(str) < 2 or str[0] != '(' or str[-1] != ')': return str

    depth = 0
    for c in str[:-1]:
        if c == '(': depth += 1
        if c == ')': depth -= 1
        if depth == 0: return str

    return strip_parens(str[1:-1])
        
def parse_type(str):
    """parse(str)
    Parse a type string.  Use the order-of-operations specified in
    Carpenter.  An example input string is 'A/B\(C\(D*E))'"""  
    str = strip_parens(str.strip())

    # Find all the top-level operators
    ops = [('BEGIN', -1)]
    depth = 0
    for i in range(0, len(str)):
        if str[i] == '(': depth += 1
        if str[i] == ')': depth -= 1
        if depth == 0 and str[i] in '/\\*':
            ops.append((str[i], i))
    ops.append(('END', len(str)+1))

    # Base type?
    if len(ops) == 2:
        return BaseType(str)

    # Get the segments, and parse them
    segments = []
    for i in range(len(ops)-1):
        seg_type = parse_type(str[ops[i][1]+1:ops[i+1][1]])
        segments.append(seg_type)

    # Dot binds most strongly, left-to-right
    i = 1
    while i < len(ops)-1:
        if ops[i][0] == '*':
            segments[i-1] = Dot(segments[i-1], segments[i])
            segments.remove(segments[i])
            ops.remove(ops[i])
        else: i += 1
        
    # Then left slashes, right-to-left.
    i = len(ops)-2
    while i > 0:
        if ops[i][0] == '\\':
            segments[i-1] = LSlash(segments[i-1], segments[i])
            segments.remove(segments[i])
            ops.remove(ops[i])
        else: i -= 1

    # Then right slashes, left-to-right.
    i = 1
    while i < len(ops)-1:
        if ops[i][0] == '/':
            segments[i-1] = RSlash(segments[i-1], segments[i])
            segments.remove(segments[i])
            ops.remove(ops[i])
        else: i += 1

    if len(segments) != 1:
        print 'Ouch!!', segments, ops

    return segments[0]
        
def test():
    A = BaseType('A')
    B = BaseType('B')
    n = BaseType('n')
    np = BaseType('np')
    s = BaseType('s')
    det = RSlash(np, n)
    vp = LSlash(np, s)
    v2 = RSlash(vp, np)
    AB = Dot(A, B)
    print v2
    print AB
    print LSlash(AB, v2)
    print Dot(v2, AB)

    print parse_type('A / B')
    print parse_type('A \\ B')
    print parse_type('A / B / C')
    print parse_type('A * B')
    print parse_type('A \\ B \\ C')
    print parse_type('A \\ (B / C)')
    print parse_type('(A / B) \\ C')
    print parse_type('(A / B) \\ C')
