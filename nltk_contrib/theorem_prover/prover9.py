import os
from string import join
from nltk.sem.logic import *

_prover9_path = None
_prover9_executable = None

_prover9_search = ['.',
                   '/usr/local/bin',
                   '/usr/local/prover9',
                   '/usr/local/share/prover9']

def config_prover9(path=None, verbose=True):
    """
    Configure the location of Prover9 Executable
    
    @param path: Path to the Prover9 executable
    @type path: C{str}
    """
    
    global _prover9_path, _prover9_executable
    _prover_path = None

    if path is not None:
        searchpath = (path,)

    if  path is  None:
        searchpath = _prover9_search
        if 'PROVER9HOME' in os.environ:
            searchpath.insert(0, os.environ['PROVER9HOME'])

    for path in searchpath:
        exe = os.path.join(path, 'prover9')
        if os.path.exists(exe):
            _prover9_path = path
            _prover9_executable = '%s/bin/prover9' % exe
            if verbose:
                print '[Found Prover9: %s]' % _prover9_executable
            break
  
    if _prover9_path is None:
        raise LookupError("Unable to find Prover9 executable in '%s'\n" 
            "Use 'config_prover9(path=<path>) '," 
            " or set the PROVER9HOME environment variable to a valid path." % join(searchpath)) 
        
def attempt_proof(expression):
    """
    Use Prover9 to prove an expression.
    
    @param expression: Input expression to prove
    @type expression: L{logic.Expression}
    @return: C{True} if the proof was successful (i.e. returns value of 0),
    else C{False}
    
    """
    config_prover9(verbose=False)
    try:
        p9_expression = toProver9String(expression.simplify().infixify())
    except:
        raise AttributeError("%s cannot be converted to Prover9 input syntax" % expression)
    
    if _prover9_executable is None:
        config_prover9(verbose=False)
        
    FILENAME = 'prove'
    f = None
    
    try:
        FILEPATH = os.path.join('/tmp', FILENAME)
        
        f = open('%s.in' % FILEPATH, 'w')
        f.write('formulas(goals).\n')
        #s = expression.infixify().toProver9String()
        f.write('    %s.\n' % p9_expression)
        f.write('end_of_list.\n')
        f.close()
        
        execute_string = \
                       '%s -f %s.in > %s.out 2>> %s.out' % \
                       (_prover9_executable, FILEPATH, FILEPATH, FILEPATH)
        
    finally:
        if f: f.close()

    tp_result = os.system(execute_string)
    return tp_result == 0


def toProver9String(current):
    toProver9String_method = None
    if isinstance(current, SomeExpression):
        toProver9String_method = _toProver9String_SomeExpression
    elif isinstance(current, VariableBinderExpression):
        toProver9String_method = _toProver9String_VariableBinderExpression
    elif isinstance(current, ApplicationExpression):
        toProver9String_method = _toProver9String_ApplicationExpression
    elif isinstance(current, Operator):
        toProver9String_method = _toProver9String_Operator
    elif isinstance(current, Expression):
        toProver9String_method = _toProver9String_Expression
    elif isinstance(current, Variable):
        toProver9String_method = _toProver9String_Variable
    elif isinstance(current, Constant):
        toProver9String_method = _toProver9String_Constant
    else:
        raise AssertionError, 'Not a valid expression'

    return toProver9String_method(current)


def _toProver9String_SomeExpression(current):
        return '%s %s %s' % ('exists', toProver9String(current.variable), toProver9String(current.term))
    
def _toProver9String_VariableBinderExpression(current):
    prefix = current.__class__.PREFIX
    variable = toProver9String(current.variable)
    term = toProver9String(current.term)
    return '%s%s %s' % (prefix, variable, term)

def _toProver9String_ApplicationExpression(current):
    # Print '((M op) N)' as '(M op N)'.
    # Print '(M N)' as 'M(N)'.
    if isinstance(current.first, ApplicationExpression) \
        and isinstance(current.first.second, Operator):
            firstStr = toProver9String(current.first.first)
            opStr = toProver9String(current.first.second)
            secondStr = toProver9String(current.second)
            return '(%s %s %s)' % (firstStr, opStr, secondStr)
    else:
        accum = '%s(' % toProver9String(current.fun)
        for arg in args(current):
            accum += '%s, ' % toProver9String(arg)
        return '%s)' % accum[0:-2]

def args(appEx):
    """
    Uncurry the argument list.  
    This is an 'overload' of logic.ApplicationExpression._args() 
    because this version returns a list of Expressions instead 
    of str objects.
    """
    assert isinstance(appEx, ApplicationExpression)
    if isinstance(appEx.first, ApplicationExpression):
        return args(appEx.first) + [appEx.second]
    else:
        return [appEx.second]

def _toProver9String_Operator(current):
    if(current.operator == 'and'):
        return '&';
    if(current.operator == 'or'):
        return '|';
    if(current.operator == 'not'):
        return '-';
    if(current.operator == 'implies'):
        return '->';
    if(current.operator == 'iff'):
        return '<->';
    else:
        return current.operator

def _toProver9String_Expression(current):
    return current.__str__()

def _toProver9String_Variable(current):
    return current.name

def _toProver9String_Constant(current):
    return current.name

def expressions():
    return [r'some x y.(sees x y)',
            r'some x.((man x) and (walks x))',
            r'\x.((man x) and (walks x))',
            r'\x y.(sees x y)',
            r'(walks john)',
            r'\x.(big x \y.(mouse y))',
            r'((walks x) and ((runs x) and ((threes x) and (fours x))))',
            r'((walks x) implies (runs x))',
            r'some x.((PRO x) and (sees John x))',
            r'some x.((man x) and (not (walks x)))',
            r'all x.((man x) implies (walks x))']
    
def testToProver9Input():
    for t in expressions():
        p = LogicParser().parse(t)
        print toProver9String(p.simplify().infixify());
        
def testAttempt_proof():
    f = LogicParser().parse(r'((man x) iff (not (not (man x))))')
    print '|- %s: %s' % (f.infixify(), attempt_proof(f))
    f = LogicParser().parse(r'(not ((man x) and (not (man x))))')
    print '|- %s: %s' % (f.infixify(), attempt_proof(f))
    f = LogicParser().parse(r'((man x) or (not (man x)))')
    print '|- %s: %s' % (f.infixify(), attempt_proof(f))
    f = LogicParser().parse(r'((man x) implies (man x))')
    print '|- %s: %s' % (f.infixify(), attempt_proof(f))
    f = LogicParser().parse(r'(not ((man x) and (not (man x))))')
    print '|- %s: %s' % (f.infixify(), attempt_proof(f))
    f = LogicParser().parse(r'((man x) or (not (man x)))')
    print '|- %s: %s' % (f.infixify(), attempt_proof(f))
    f = LogicParser().parse(r'((man x) implies (man x))')
    print '|- %s: %s' % (f.infixify(), attempt_proof(f))
    f = LogicParser().parse(r'((man x) iff (man x))')
    print '|- %s: %s' % (f.infixify(), attempt_proof(f))
    f = LogicParser().parse(r'(not ((man x) iff (not (man x))))')
    print '|- %s: %s' % (f.infixify(), attempt_proof(f))
    f = LogicParser().parse(r'((all x.((man x) implies (mortal x)) and (man Socrates)) implies (mortal Socrates))')
    print '|- %s: %s' % (f.infixify(), attempt_proof(f))
    f = LogicParser().parse(r'((all x.((man x) implies (walks x)) and (man Socrates)) implies some y.(walks y))')
    print '|- %s: %s' % (f.infixify(), attempt_proof(f))
    f = LogicParser().parse('(all x.(man x) implies all x.(man x))')
    print '|- %s: %s' % (f.infixify(), attempt_proof(f))
    f = LogicParser().parse('some x.all y.(sees x y)')
    print '|- %s: %s' % (f.infixify(), attempt_proof(f))

if __name__ == '__main__': 
    testToProver9Input()
    print '\n\n'
    testAttempt_proof()
