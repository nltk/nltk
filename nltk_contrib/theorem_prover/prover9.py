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

prover9_search = ['.',
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
    _prover9_path = None

    if path is not None:
        searchpath = (path,)

    if  path is  None:
        searchpath = prover9_search
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
    def __init__(self, goal, assumptions=[], ontology=None, **options):
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
        self._p9_assumptions = []
        self._p9_ontology = None
        self._p9_goal = convert_to_prover9(self._goal)
        if self._assumptions:
            self._p9_assumptions = convert_to_prover9(self._assumptions)
        if self._ontology is not None:    
            self._p9_ontology = convert_to_prover9(self._ontology)
        self._options = options
        
    
    def prover9_files(self, filename='prover9', p9_dir=None):
        """
        Generate names for the input and output files and write to the input file.
        """     
        # If no directory specified, use system temp directory
        if p9_dir is None:
            p9_dir = tempfile.gettempdir()
        self._infile = os.path.join(p9_dir, filename + '.in')
        self._outfile = os.path.join(p9_dir, filename + '.out')
        f = open(self._infile, 'w')
        
        if self._p9_assumptions:
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
    
    def show_proof(self):
        """
        Print out a Prover9 proof.
        """
        if self._outfile:
            for l in open(self._outfile):
                print l,
        else:
            print "You have to call prove() first to get a proof!"
        return None
    
            
    def add_assumptions(self, new_assumptions):
        """
        Add new assumptions to the assumption list.
        
        @param new_assumptions: new assumptions
        @type new_assumptions: C{list} of L{sem.logic.Expression}s
        """
        self._assumptions += new_assumptions
        self._p9_assumptions += convert_to_prover9(self._assumptions)
        return None
    
    def assumptions(self, output_format='nltk'):
        """
        List the current assumptions.
        
        """
        if output_format.lower() == 'nltk':
            print [str(a.infixify()) for a in self._assumptions]
 
        elif output_format.lower() == 'prover9':
            print self._p9_assumptions
        else:
            raise NameError("Unrecognized value for 'output_format': %s" % output_format)

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
        for arg in current.args:
            accum += '%s, ' % toProver9String(arg)
        return '%s)' % accum[0:-2]
    


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
        
def testAttempt_proof(arguments):
    for (goal, assumptions) in arguments:
        g = LogicParser().parse(goal)
        alist = [LogicParser().parse(a) for a in assumptions]
        p = Prover9(g, assumptions=alist).prove()
        #alist = [str(a.infixify()) for a in alist]
        for a in alist:
            print '   %s' % a.infixify()
        print '|- %s: %s\n' % (g.infixify(), p)
    
arguments = [
    ('((man x) iff (not (not (man x))))', []),
    ('(not ((man x) and (not (man x))))', []),
    ('((man x) or (not (man x)))', []),
    ('((man x) and (not (man x)))', []),
    ('((man x) implies (man x))', []),
    ('(not ((man x) and (not (man x))))', []),
    ('((man x) or (not (man x)))', []),
    ('((man x) implies (man x))', []),
    ('((man x) iff (man x))', []),
    ('(not ((man x) iff (not (man x))))', []),
    ('(mortal Socrates)', ['all x.((man x) implies (mortal x))', '(man Socrates)']),
    ('((all x.((man x) implies (walks x)) and (man Socrates)) implies some y.(walks y))', []),
    ('(all x.(man x) implies all x.(man x))', []),
    ('some x.all y.(sees x y)', []),
    ('some e3.((walk e3) and (subj e3 mary))', 
        ['some e1.((see e1) and (subj e1 john) and some e2.((pred e1 e2) and (walk e2) and (subj e2 mary)))']),
    ('some x e1.((see e1) and (subj e1 x) and some e2.((pred e1 e2) and (walk e2) and (subj e2 mary)))', 
       ['some e1.((see e1) and (subj e1 john) and some e2.((pred e1 e2) and (walk e2) and (subj e2 mary)))'])
]

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
    
if __name__ == '__main__':
    
    testToProver9Input(expressions)
    print '\n'
    testAttempt_proof(arguments)
    g = LogicParser().parse('(mortal Socrates)')
    prover = Prover9(g)
    print prover.prove()
    prover.assumptions()
    a1 = LogicParser().parse('all x.((man x) implies (mortal x))')
    a2 = LogicParser().parse('(man Socrates)')
    prover.add_assumptions([a1, a2])
    prover.assumptions()
    prover.assumptions(output_format='Prover9')
    print prover.prove()
    
 
    
    
