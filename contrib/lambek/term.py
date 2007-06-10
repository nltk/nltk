#!/usr/bin/python
#
# term.py
#
# Edward Loper
# Created [12/10/00 01:58 PM]
# $Id$
#

"""Lambda calculus stuff"""

import types, re
from copy import deepcopy

class Term:
    #FREEVAR_NAME = ['e', 'd', 'c', 'b', 'a']
    FREEVAR_NAME = ['$\\epsilon$', '$\\delta$', '$\\gamma$', \
                    '$\\beta$', '$\\alpha$']
    BOUNDVAR_NAME = ['z', 'y', 'x']
    def __init__(self):
        raise TypeError("Term is an abstract class")
    
class Var(Term):
    _max_id = 0
    def __init__(self):
        Var._max_id += 1
        self.id = Var._max_id
    def __repr__(self):
        return '?' + `self.id`
    def pp(self, pp_varmap=None):
        if pp_varmap == None: pp_varmap = make_pp_varmap(self)
        return pp_varmap[self]
    def to_latex(self, pp_varmap=None):
        if pp_varmap == None: pp_varmap = make_pp_varmap(self)
        return '\\textit{'+pp_varmap[self]+'}'
    def __hash__(self):
        return self.id
    def __cmp__(self, other):
        if isinstance(other, Var) and other.id == self.id: return 0
        else: return -1

class Const(Term):
    def __init__(self, name):
        if type(name) != types.StringType:
            raise TypeError("Expected a string name")
        self.name = name
    def __repr__(self):
        return self.name
    def pp(self, pp_varmap=None):
        return self.name
    def to_latex(self, pp_varmap=None):
        return '\\textbf{'+self.name+'}'
    def __cmp__(self, other):
        if isinstance(other, Const) and other.name == self.name:
            return 0
        else: return -1

class Appl(Term):
    def __init__(self, func, arg):
        self.func = func
        self.arg = arg
        if not isinstance(self.func, Term) or \
           not isinstance(self.arg, Term):
            raise TypeError('Expected Term argument', func, arg)
    def __repr__(self):
        if isinstance(self.func, Appl) or \
           isinstance(self.func, Abstr):
            return '('+`self.func` + ')(' + `self.arg` + ')'
        else:
            return `self.func` + '(' + `self.arg` + ')'
    def pp(self, pp_varmap=None):
        if pp_varmap == None: pp_varmap = make_pp_varmap(self)
        if isinstance(self.func, Appl) or \
           isinstance(self.func, Abstr):
            return '(' + self.func.pp(pp_varmap) + ')(' + \
                   self.arg.pp(pp_varmap) + ')'
        else:
            return self.func.pp(pp_varmap) + '(' + \
                   self.arg.pp(pp_varmap) + ')'
    def to_latex(self, pp_varmap=None):
        if pp_varmap == None: pp_varmap = make_pp_varmap(self)
        if isinstance(self.func, Appl) or \
           isinstance(self.func, Abstr):
            return '\\left(' + self.func.to_latex(pp_varmap) + \
                   '\\right)\\left(' + \
                   self.arg.to_latex(pp_varmap) + '\\right)'
        else:
            return self.func.to_latex(pp_varmap) + '(' + \
                   self.arg.to_latex(pp_varmap) + ')'
    def __cmp__(self, other):
        if isinstance(other, Appl) and other.func == self.func and \
           other.arg == self.arg: return 0
        else: return -1

class Abstr(Term):
    def __init__(self, var, body):
        self.var = var
        self.body = body
        if not isinstance(self.var, Var) or \
           not isinstance(self.body, Term):
            raise TypeError('Expected Var and Term arguments')
    def __repr__(self):
        if isinstance(self.body, Abstr) or \
           isinstance(self.body, Appl):
            return '(\\' + `self.var` + '.' + `self.body`+')'
        else:
            return '\\' + `self.var` + '.' + `self.body`
    def pp(self, pp_varmap=None):
        if pp_varmap == None: pp_varmap = make_pp_varmap(self)
        if isinstance(self.body, Abstr) or \
           isinstance(self.body, Appl):
            return '(' + '\\' + self.var.pp(pp_varmap) + '.' + \
                   self.body.pp(pp_varmap) + ')'
        else:
            return '\\' + self.var.pp(pp_varmap) + '.' + \
                   self.body.pp(pp_varmap)
    def to_latex(self, pp_varmap):
        if pp_varmap == None: pp_varmap = make_pp_varmap(self)
        if isinstance(self.body, Abstr) or \
           isinstance(self.body, Appl):
            return '\\left(' + '\\lambda ' + self.var.to_latex(pp_varmap) + \
                   '.' + self.body.to_latex(pp_varmap) + '\\right)'
        else:
            return '\\lambda' + self.var.to_latex(pp_varmap) + \
                   '.' + self.body.to_latex(pp_varmap)
    def __cmp__(self, other):
        if isinstance(other, Abstr) and \
           self.body == replace(other.var, self.var, other.body):
            return 0
        else: return -1

class Tuple(Term):
    def __init__(self, left, right):
        self.left = left
        self.right = right
        if not isinstance(self.left, Term) or \
           not isinstance(self.right, Term):
            raise TypeError('Expected Term arguments')
    def __repr__(self):
        return '<'+`self.left`+', '+`self.right`+'>'
    def pp(self, pp_varmap=None):
        if pp_varmap == None: pp_varmap = make_pp_varmap(self)
        return '<'+self.left.pp(pp_varmap)+', '+\
               self.right.pp(pp_varmap)+'>'
    def to_latex(self, pp_varmap=None):
        if pp_varmap == None: pp_varmap = make_pp_varmap(self)
        return '\\left\\langle'+self.left.to_latex(pp_varmap)+', '+\
               self.right.to_latex(pp_varmap)+'\\right\\rangle'
    def __cmp__(self, other):
        if isinstance(other, Tuple) and other.left == self.left and \
           other.right == self.right: return 0
        else: return -1

def make_pp_varmap(term):
    return extend_pp_varmap({}, term)
        
def extend_pp_varmap(pp_varmap, term):
    # Get free and bound vars
    free = freevars(term)
    bound = boundvars(term)

    # Get the remaining names.
    freenames = [n for n in Term.FREEVAR_NAME \
                 if n not in pp_varmap.values()]
    boundnames = Term.BOUNDVAR_NAME[:]

    for fv in free:
        if not pp_varmap.has_key(fv):
            if freenames == []:
                pp_varmap[fv] = `fv`
            else:
                pp_varmap[fv] = freenames.pop()

    for bv in bound:
        if not pp_varmap.has_key(bv):
            if boundnames == []:
                pp_varmap[bv] = `bv`
            else:
                pp_varmap[bv] = boundnames.pop()

    return pp_varmap

class VarMap:
    def __init__(self):
        self._map = {}
    def add(self, var, term):
        if self._map.has_key(var):
            if term != None and term != self._map[var]:
                # Unclear what I should do here -- for now, just pray
                # for the best. :)
                None
        else:
            self._map[var] = term
    def __repr__(self):
        return `self._map`
    def _get(self, var, orig, getNone=1):
        val = self._map[var]
        if not getNone and val == None: return var
        if not isinstance(val, Var): return val
        if val == orig:
            #print 'WARNING: CIRCULAR LOOP'
            # Break the loop at an arbitrary point.
            del(self._map[val])
            return val
        elif self._map.has_key(val):
            return(self._get(val, orig, getNone))
        else:
            return val
    def __getitem__(self, var):
        if self._map.has_key(var):
            return self._get(var, var, 1)
        else:
            return var
    def simplify(self, var):
        if self._map.has_key(var):
            return self._get(var, var, 0)
        else:
            return var
    def copy(self):
        result = VarMap()
        result._map = self._map.copy()
        return result
    def __add__(self, other):
        result = self.copy()
        for var in other._map.keys():
            result.add(var, other[var])
        return result
    def copy_from(self, other):
        self._map = other._map.copy()
    def force(self, var, term):
        self._map[var] = term

# Use a varmap to simplify an term.
def simplify(term, varmap):
    if isinstance(term, Var):
        e = varmap.simplify(term)
        if e == term or e == None:
            return term
        else:
            return simplify(e, varmap)
    if isinstance(term, Appl):
        return Appl(simplify(term.func, varmap), \
                    simplify(term.arg, varmap))
    if isinstance(term, Tuple):
        return Tuple(simplify(term.left, varmap), \
                     simplify(term.right, varmap))
    if isinstance(term, Abstr):
        return Abstr(term.var, simplify(term.body, varmap))
    if isinstance(term, Const):
        return term

_VERBOSE = 0
    
def unify(term1, term2, varmap=None, depth=0):
    if _VERBOSE: print '  '*depth+'>> unify', term1, term2, varmap
    term1 = reduce(term1)
    term2 = reduce(term2)
    if varmap == None: varmap = VarMap()

    old_varmap = varmap.copy()
    result = unify_oneway(term1, term2, varmap, depth+1)
    if result:
        if _VERBOSE:
            print '  '*depth+'<<unify', term1, term2, varmap, '=>', result
        return result
    varmap.copy_from(old_varmap)

    result = unify_oneway(term2, term1, varmap, depth+1)
    if result:
        if _VERBOSE:
            print '  '*depth+'<<unify', term1, term2, varmap, '=>', result
        return result
    #raise(ValueError("can't unify", term1, term2, varmap))
    if _VERBOSE:
        print '  '*depth+'unify', term1, term2, varmap, '=>', None
    
    return None
    
#### THIS FUNCTION IS CURRENTLY PARTIALLY BROKEN
# Possible pairings:
#   var <-> abstr
#   var <-> appl
#   var <-> var
#   var <-> const
#   abstr <-> abstr
#   abstr <-> apl
#   apl <-> apl
#   const <-> const
#   tuple <-> tuple
#
def unify_oneway(term1, term2, varmap, depth):
    term1 = reduce(term1)
    term2 = reduce(term2)

    # Identical
    if term1 == term2: return term1

    # If term1 is a var in varmap, get its value...
    if isinstance(term1, Var):
        if varmap[term1] != None:
            term1 = varmap[term1]
        
    # Variable
    if isinstance(term1, Var):
        if varmap[term1] == None:
            # It's a bound var
            if term1 == term2: return term1
            else: return None
        elif term1 in freevars(term2):
            if  term1 == term2: return term1
            else: return None
        else:
            # Eliminate it.
            varmap.add(term1, term2)
            return term2

    # Tuple
    if isinstance(term1, Tuple):
        if isinstance(term2, Tuple):
            left = unify(term1.left, term2.left, varmap, depth)
            right = unify(term1.right, term2.right, varmap, depth)
            if left != None and right != None:
                return Tuple(left, right)
        
    # Abstraction
    if isinstance(term1, Abstr):
        if isinstance(term2, Abstr):
            x = Var()
            body1 = replace(term1.var, x, term1.body)
            body2 = replace(term2.var, x, term2.body)
            
            varmap.force(term1.var, x)
            varmap.force(term2.var, x)
            varmap.add(x, None)
            abstr = Abstr(x, unify(body1, body2, varmap, depth))
            return abstr
        if isinstance(term2, Appl):
            ## ***** There is a way to do this, but I haven't figured
            ## ***** it out yet.
            return None

    if isinstance(term1, Appl):
        if isinstance(term2, Appl):
            # Try unifying func and arg..
            old_varmap = varmap.copy()
            func = unify(term1.func, term2.func, varmap, depth)
            arg = unify(term1.arg, term2.arg, varmap, depth)
            if func != None and arg != None:
                return Appl(func, arg)
            varmap.copy_from(old_varmap)

            # If the functor of term1 is a variable, try instantiating 
            # it as a lambda term of some sort.
            if isinstance(term1.func, Var) and \
               varmap[term1.func] != None and \
               isinstance(term1.arg, Var):
                x = Var()
                body = replace(term1.arg, x, term2)
                # I need some sort of check here!!
                abstr = Abstr(x, body)
                varmap.add(x, None)
                varmap.add(term1.func, abstr)
                return term2
            
    if isinstance(term1, Const):
        if term1 == term2: return term1
        else: return None

    return None
                
def replace(oldval, newval, term):
    "Replace all occurances of oldval with newval in term"
    if term == oldval:
        return newval
    elif isinstance(term, Appl):
        return Appl(replace(oldval, newval, term.func),\
                    replace(oldval, newval, term.arg))
    elif isinstance(term, Abstr):
        if (oldval == term.var):
            return term
        else:
            return Abstr(term.val, replace(oldval, newval, term.body))
    elif isinstance(term, Tuple):
        return Tuple(replace(oldval, newval, term.left),
                     replace(oldval, newval, term.right))
    else:
        return term

def union(lst1, lst2):
    lst = lst1[:]
    for elt in lst2:
        if elt not in lst:
            lst.append(elt)
    return lst
    
def freevars(term):
    if isinstance(term, Var):
        return [term]
    elif isinstance(term, Appl):
        return union(freevars(term.func), freevars(term.arg))
    elif isinstance(term, Abstr):
        return [var for var in freevars(term.body) if var != term.var]
    elif isinstance(term, Tuple):
        return union(freevars(term.left), freevars(term.right))
    else:
        return []

def vars(term):
    if isinstance(term, Var):
        return [term]
    elif isinstance(term, Appl):
        return union(vars(term.func), vars(term.arg))
    elif isinstance(term, Abstr):
        return union(vars(term.body), [term.var])
    elif isinstance(term, Tuple):
        return union(vars(term.left), vars(term.right))
    else:
        return []

def boundvars(term):
    free = freevars(term)
    return [var for var in vars(term) if var not in free]
    
def reduce(term):
    if isinstance(term, Var) or isinstance(term, Const):
        return term

    if isinstance(term, Tuple):
        return Tuple(reduce(term.left), reduce(term.right))

    if isinstance(term, Appl):
        # Reduce the function and argument
        func = reduce(term.func)
        arg = reduce(term.arg)

        if isinstance(func, Abstr):
            return reduce(replace(func.var, arg, func.body))
        else:
            return Appl(func, arg)

    if isinstance(term, Abstr):
        # Reduce the body
        var = term.var
        body = reduce(term.body)

        if isinstance(body, Appl) and \
           body.arg == var and \
           var not in freevars(body.func):
            return body.func
        else:
            return Abstr(var, body)

# Strip outermost parens from a string..  inefficient, but simple :)
def strip_parens(str):
    if len(str) < 2 or str[0] != '(' or str[-1] != ')': return str

    depth = 0
    for c in str[:-1]:
        if c == '(': depth += 1
        if c == ')': depth -= 1
        if depth == 0: return str

    return strip_parens(str[1:-1])

def extract_tuple(str):
    if str[0] != '<' or str[-1] != '>': return None
    comma = None
    depth = 1
    for i in range(1, len(str)-1):
        if str[i] in '(<': depth += 1
        if str[i] in ')>': depth -= 1
        if depth == 1 and str[i] == ',':
            if comma == None: comma = i
            else: raise ValueError('bad tuple')
        if depth == 0: return None
    if comma == None: raise ValueError('bad tuple', str)
    return (str[1:comma], str[comma+1:-1])


# Maps str -> lambda term.
# Vars should start with '?'
def parse_term(str, varmap=None):
    if varmap == None: varmap = {}

    str = strip_parens(str.strip())

    # Abstractions with numbered vars
    abstr = re.match(r'\\\?([^\.]+)\.(.*)', str)
    if abstr:
        (varname, body) = abstr.groups()
        var = Var()
        varmap[varname]=var
        return Abstr(var, parse_term(body, varmap))

    # Tuple
    tuple = extract_tuple(str)
    if tuple:
        return Tuple(parse_term(tuple[0], varmap), \
                     parse_term(tuple[1], varmap))
    
    # Application
    if '(' in str:
        depth = 0
        for i in range(len(str)):
            if str[i] in '(<':
                if depth == 0 and i > 0: break
                else: depth += 1
            if str[i] in ')>':
                depth -= 1
        func = parse_term(str[:i], varmap)
        arg = parse_term(str[i:], varmap)
        return Appl(func, arg)
    
    # Variable
    var = re.match(r'\?(.*)', str)
    if var:
        varname = var.groups()[0]
        if varmap.has_key(varname):
            return varmap[varname]
        else:
            var = Var()
            varmap[varname] = var
            return var

    # Constant
    return Const(str)
        
def test():
    x = Var()
    y = Var()
    z = Var()
    c = Const('c')
    
    f1 = Appl(Abstr(x, Appl(x, c)), z)
    f2 = Appl(Abstr(x, Appl(c, x)), z)
    f3 = Abstr(x, Appl(c, x))
    f4 = Abstr(y, Appl(c, y))
    
    print f1, '=>', reduce(f1)
    print f2, '=>', reduce(f2)
    print f3, '=>', reduce(f3)

    print f1.pp()
    print f2.pp()
    print f3.pp()

    print
    print unify(x, y)
    print unify(x, c)
    print unify(x, f1)
    print unify(f3, f4)
    print unify(Abstr(x,Appl(x,x)), Abstr(y,Appl(y,y)))

    print parse_term('<(\?var.<const,const2>(?var))(?other_var),?x>').pp()

    reduce(parse_term('<a,b>'))
    
if __name__ == '__main__':
    test()

