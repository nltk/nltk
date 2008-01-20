# Natural Language Toolkit: Interface to the Prover9 Theorem Prover 
#
# Author: Dan Garrette <dhgarrette@gmail.com>
#         Ewan Klein <ewan@inf.ed.ac.uk>

# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

import os
import tempfile
from string import join
from nltk.sem.logic import *
from api import ProverI

_prover9_path = None
_prover9_executable = None

_prover9_search = ['.',
                   '/usr/local/bin/prover9',
                   '/usr/local/bin/prover9/bin',
                   '/usr/local/bin',
                   '/usr/bin',
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
            _prover9_executable = exe
            if verbose:
                print '[Found Prover9: %s]' % _prover9_executable
            break
  
    if _prover9_path is None:
        raise LookupError("Unable to find Prover9 executable in '%s'\n" 
            "Use 'config_prover9(path=<path>) '," 
            " or set the PROVER9HOME environment variable to a valid path." % join(searchpath))
    
    
class Prover9(ProverI):
    def __init__(self, goal, assumptions=None, ontology=None, **options):
        """
        @param goal: Input expression to prove
        @type goal: L{logic.Expression}
        @param assumptions: Input expressions to use as assumptions in the proof
        @type assumptions: L{list} of logic.Expression objects
        @param options: options to pass to Prover9
        """
        config_prover9(verbose=False)
        self._goal = goal        
        self._assumptions = assumptions
        self._ontology = ontology
        self._infile = ''
        self._ontologyfile = ''
        self._outfile = '' 
        self._p9_assumptions = None
        self._p9_ontology = None
        self._p9_goal = convert_to_prover9(self._goal)
        if self._assumptions is not None:
            self._p9_assumptions = convert_to_prover9(self._assumptions)
        if self._ontology is not None:    
            self._p9_ontology = convert_to_prover9(self._ontology)
        self._options = options
        
    
    def prover9_files(self, filename='prover9', p9_dir=None):
        """
        
        """     
        # If no directory specified, use system temp directory
        if p9_dir is None:
            p9_dir = tempfile.gettempdir()
        self._infile = os.path.join(p9_dir, filename + '.in')
        self._outfile = os.path.join(p9_dir, filename + '.out')
        f = open(self._infile, 'w')
        
        if self._p9_assumptions is not None:
            f.write('formulas(assumptions).\n')
            for p9_assumption in self._p9_assumptions:
                f.write('    %s.\n' % p9_assumption)
            f.write('end_of_list.\n\n')
    
        f.write('formulas(goals).\n')
        f.write('    %s.\n' % self._p9_goal)
        f.write('end_of_list.\n')
        f.close()
        
        if self._p9_ontology is not None:
            self._ontologyfile = os.path.join(p9_dir, 'p9ontology.in')
            f = open(self._ontologyfile, 'w')
            f.write('formulas(assumptions).\n')
            for fmla in self._p9_ontology:
                f.write('    %s.\n' % fmla)
            f.write('end_of_list.\n\n')
    
            f.write('formulas(goals).\nend_of_list.\n')
            f.close()        
            
        return None
    
    def prove(self):
        """
        Use Prover9 to prove a theorem.
        @return: C{True} if the proof was successful 
        (i.e. returns value of 0), else C{False}
        
        """
        self.prover9_files()
        execute_string = '%s -f %s %s > %s 2>> %s' % \
            (_prover9_executable, self._ontologyfile, self._infile, self._outfile, self._outfile)
                
        tp_result = os.system(execute_string)
        return tp_result == 0


def convert_to_prover9(input):
    if isinstance(input, list):
        result = []
        for s in input:
            try:
                result.append(toProver9String(s.simplify().infixify()))
            except AssertionError:
                print 'input %s cannot be converted to Prover9 input syntax' % input
        return result    
    else:
        try:
            return toProver9String(input.simplify().infixify())
        except AssertionError:
            print 'input %s cannot be converted to Prover9 input syntax' % input

    
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

    
def testToProver9Input(expr):
    for t in expr:
        p = LogicParser().parse(t)
        print toProver9String(p.simplify().infixify());
        
def testAttempt_proof():
    
    f = LogicParser().parse(r'((man x) iff (not (not (man x))))')
    p = Prover9(f).prove()
    print '|- %s: %s' % (f.infixify(), p)
    #f = LogicParser().parse(r'(not ((man x) and (not (man x))))')
    #print '|- %s: %s' % (f.infixify(), attempt_proof(f))
    #f = LogicParser().parse(r'((man x) or (not (man x)))')
    #print '|- %s: %s' % (f.infixify(), attempt_proof(f))
    #f = LogicParser().parse(r'((man x) implies (man x))')
    #print '|- %s: %s' % (f.infixify(), attempt_proof(f))
    #f = LogicParser().parse(r'(not ((man x) and (not (man x))))')
    #print '|- %s: %s' % (f.infixify(), attempt_proof(f))
    #f = LogicParser().parse(r'((man x) or (not (man x)))')
    #print '|- %s: %s' % (f.infixify(), attempt_proof(f))
    #f = LogicParser().parse(r'((man x) implies (man x))')
    #print '|- %s: %s' % (f.infixify(), attempt_proof(f))
    #f = LogicParser().parse(r'((man x) iff (man x))')
    #print '|- %s: %s' % (f.infixify(), attempt_proof(f))
    #f = LogicParser().parse(r'(not ((man x) iff (not (man x))))')
    #print '|- %s: %s' % (f.infixify(), attempt_proof(f))
    p1 = LogicParser().parse(r'all x.((man x) implies (mortal x))')
    p2 = LogicParser().parse(r'(man Socrates)')
    g = LogicParser().parse(r'(mortal Socrates)')
    proof = Prover9(g, assumptions=[p1, p2]).prove()
    print '%s, %s |- %s: %s' % (p1.infixify(), p2.infixify(), g.infixify(), proof)
    #f = LogicParser().parse(r'((all x.((man x) implies (walks x)) and (man Socrates)) implies some y.(walks y))')
    #print '|- %s: %s' % (f.infixify(), attempt_proof(f))
    #f = LogicParser().parse('(all x.(man x) implies all x.(man x))')
    #print '|- %s: %s' % (f.infixify(), attempt_proof(f))
    #f = LogicParser().parse('some x.all y.(sees x y)')
    #print '|- %s: %s' % (f.infixify(), attempt_proof(f))
    #p = LogicParser().parse(r'some e1.((see e1) and (subj e1 john) and some e2.((pred e1 e2) and (walk e2) and (subj e2 mary)))')
    #g = LogicParser().parse(r'some e3.((walk e3) and (subj e3 mary))')
    #print '%s |- %s: %s' % (p.infixify(), g.infixify(), attempt_proof(g, [p]))
    #p = LogicParser().parse(r'some e1.((see e1) and (subj e1 john) and some e2.((pred e1 e2) and (walk e2) and (subj e2 mary)))')
    #g = LogicParser().parse(r'some x e1.((see e1) and (subj e1 x) and some e2.((pred e1 e2) and (walk e2) and (subj e2 mary)))')
    #print '%s |- %s: %s' % (p.infixify(), g.infixify(), attempt_proof(g, [p]))

if __name__ == '__main__':
    expressions = [r'some x y.(sees x y)',
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
    testToProver9Input(expressions)
    print '\n\n'
    testAttempt_proof()
