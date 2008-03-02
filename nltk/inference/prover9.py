# Natural Language Toolkit: Interface to the Prover9 Theorem Prover 
#
# Author: Dan Garrette <dhgarrette@gmail.com>
#              Ewan Klein <ewan@inf.ed.ac.uk>

# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

import os
import tempfile
from string import join
from nltk.sem.logic import *
from api import ProverI
from nltk.internals import deprecated, Deprecated

"""
A theorem prover that makes use of the external 'Prover9' package.
"""
#
# Following is not yet used. Return code for 2 actually realized as 512. 
#
p9_return_codes = {0: True,
                   1:  "(FATAL)",       #A fatal error occurred (user's syntax error or Prover9's bug).
                   2: False,           # (SOS_EMPTY) Prover9 ran out of things to do (sos list exhausted).
                   3: "(MAX_MEGS)",    # The max_megs (memory limit) parameter was exceeded.
                   4: "(MAX_SECONDS)", # The max_seconds parameter was exceeded.
                   5: "(MAX_GIVEN)",   # The max_given parameter was exceeded.
                   6: "(MAX_KEPT)",    # The max_kept parameter was exceeded.
                   7: "(ACTION)",      # A Prover9 action terminated the search.
                   101: "(SIGSEGV)",   # Prover9 crashed, most probably due to a bug.   
 }
 
HELPMSG = """
Unable to find Prover9 executable! Use 
Prover9().config_prover9(path='/path/to/prover9directory'),
or set the PROVER9HOME environment variable to a valid path.
For more information about Prover9, please see 
http://www.cs.unm.edu/~mccune/prover9/
"""


    
    
class Prover9Parent:
    def __init__(self, goal=None, assumptions=[], timeout=60):
        """
        @param goal: Input expression to prove
        @type goal: L{logic.Expression}
        @param assumptions: Input expressions to use as assumptions in the proof
        @type assumptions: C{list} of L{logic.Expression} objects
        @param timeout: number of seconds before timeout; set to 0 for no timeout.
        @type timeout: C{int}
        """
        self.config_prover9(verbose=False)
        self._goal = goal       
        self._assumptions = assumptions
        self._p9_dir = ''
        self._infile = ''
        self._outfile = '' 
        self._p9_assumptions = []
        if goal:
            self._p9_goal = convert_to_prover9(self._goal)
        else:
            self._p9_goal = None
        if self._assumptions:
            self._p9_assumptions = convert_to_prover9(self._assumptions)
        else:
            self._p9_assumptions = []
        self._result = None
        self._timeout = timeout
        
    prover9_search = ['.',
                    '/usr/local/bin/prover9',
                    '/usr/local/bin/prover9/bin',
                    '/usr/local/bin',
                    '/usr/bin',
                    '/usr/local/prover9',
                    '/usr/local/share/prover9']

    def config_prover9(self, path=None, verbose=True):
        """
        Configure the location of Prover9 Executable
        
        @param path: Path to the Prover9 executable
        @type path: C{str}
        """

        self._executable_path = None
        
        if path is not None:
            searchpath = (path,)
    
        if  path is  None:
            searchpath = Prover9Parent.prover9_search
            if 'PROVER9HOME' in os.environ:
                searchpath.insert(0, os.environ['PROVER9HOME'])
    
        for path in searchpath:
            exe = os.path.join(path, self.get_executable())
            if os.path.exists(exe):
                self._executable_path = path
                if verbose:
                    print '[Found %s: %s]' % (self.get_executable(), exe)
                break
      
        if self._executable_path is None:
            if verbose:
                print "Searching in these locations:\n %s" % join(searchpath, sep=', ')
            print HELPMSG
            
           
    def prover9_files(self, prefix='prover9', p9_dir=None):
        """
        Generate names for the input and output files and write to the input file.
        
        @parameter prefix: prefix to use for the input files; 
        appropriate values are 'prover9' and 'mace4'. 
        The full filename is created by the C{tempfile} module.
        @type filename: C{str}
        @parameter p9_dir: location of directory for writing input and output files; 
        if not specified, the C{tempfile} module specifies the directory.
        @type p9_dir: C{str}
        
        """     
        (fd, filename) = tempfile.mkstemp(suffix=".in", prefix=prefix, dir=p9_dir)
        self._infile = filename
        self._outfile = os.path.splitext(filename)[0] + '.out'
        #NB self._p9_dir is used by _transform_output() in the mace module
        if p9_dir is None:
            self._p9_dir = os.path.split(filename)[0]
        fp = os.fdopen(fd, 'w')
        
        if self._timeout > 0:
            fp.write('assign(max_seconds, %d).\n' % self._timeout)
            
        if self._p9_assumptions:
            fp.write('formulas(assumptions).\n')
            for p9_assumption in self._p9_assumptions:
                fp.write('    %s.\n' % p9_assumption)
            fp.write('end_of_list.\n\n')
    
        fp.write('formulas(goals).\n')
        if self._p9_goal:
            fp.write('    %s.\n' % self._p9_goal)
        fp.write('end_of_list.\n\n')

        fp.close()
            
        return None
    
    def add_assumptions(self, new_assumptions):
        """
        Add new assumptions to the assumption list.
        
        @param new_assumptions: new assumptions
        @type new_assumptions: C{list} of L{sem.logic.Expression}s
        """
        self._assumptions += new_assumptions
        self._p9_assumptions += convert_to_prover9(new_assumptions)
        return None
    
    def retract_assumptions(self, retracted, debug=False):
        """
        Retract assumptions from the assumption list.
        
        @param debug: If True, give warning when C{retracted} is not present on 
        assumptions list.
        @type debug: C{bool}
        @param retracted: assumptions to be retracted
        @type retracted: C{list} of L{sem.logic.Expression}s
        """
        
        result = set(self._assumptions) - set(retracted)
        if debug and result == set(self._assumptions):
            print Warning("Assumptions list has not been changed:")
            self.assumptions()
            
        self._assumptions = list(result)
        self._p9_assumptions = convert_to_prover9(self._assumptions)
        return None
    
    def assumptions(self, output_format='nltk'):
        """
        List the current assumptions.       
        """
        if output_format.lower() == 'nltk':
            for a in self._assumptions:
                print a.infixify()
        elif output_format.lower() == 'prover9':
            for a in self._p9_assumptions:
                print a
        else:
            raise NameError("Unrecognized value for 'output_format': %s" % output_format)
        
#{ Deprecated     
    @deprecated("Use nltk.data.load(<file.fol>) instead.")    
    def load(self, filename):
        """
        Load and parse a file of logical statements.
        These must be parsable by LogicParser.
        """
        statements = open(filename).readlines()
        lp = LogicParser()
        result = []
        for s in statements:
            result.append(lp.parse(s))
        return result                 
#}       

def convert_to_prover9(input):
    """
    Convert C{logic.Expression}s to Prover9 format.
    """
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


class Prover9(Prover9Parent, ProverI):
    def get_executable(self):
        return 'prover9'

    def prove(self, debug=False):
        """
        Use Prover9 to prove a theorem.
        @return: C{True} if the proof was successful 
        (i.e. returns value of 0), else C{False}        
        """
        if self._executable_path is None:
            print HELPMSG
            return None
        self.prover9_files()
        exe = os.path.join(self._executable_path, self.get_executable())
        execute_string = '%s -f %s > %s 2>> %s' % \
            (exe, self._infile, self._outfile, self._outfile)
        
        tp_result = os.system(execute_string)
        self._result = (tp_result == 0)
        return self._result
    
    def proof_successful(self):
        return self._result
    
    def _simplify_proof(self):
        """
        Simplify a Prover9 output file.    
        """
        output_file = None
        
        (dir, base) = os.path.split(self._outfile)
        output_file = os.path.join(dir, 'prooftrans.' + base)
        exe = os.path.join(self._executable_path, 'prooftrans')
        execute_string = '%s -f %s striplabels > %s 2>> %s' % \
            (exe, self._outfile, output_file, output_file)
        os.system(execute_string)
            
        return output_file
    
    def show_proof(self, simplify=True):
        """
        Print out a Prover9 proof.    
        
        @parameter simplify: if C{True}, simplify the output file 
        using Prover9's C{prooftrans}.
        @type simplify: C{bool}
        """
        if self._outfile:
            proof_file = self._outfile
            if simplify:
                proof_file = self._simplify_proof()
            for l in open(proof_file):
                print l,
        else:
            raise LookupError("You have to call prove() first to get a proof!")


def test_config():
    
    a = LogicParser().parse('((walk j) and (sing j))')
    g = LogicParser().parse('(walk j)')
    p = Prover9(g, assumptions=[a])
    p._executable_path = None
    p.prover9_search=[]
    p.prove()
    p.config_prover9(path='/usr/local/bin')
    print p.prove()
    p.show_proof()
    
def test_convert_to_prover9(expr):
    """
    Test that parsing works OK.
    """
    for t in expr:
        e = LogicParser().parse(t)
        print convert_to_prover9(e)
        
def test_prove(arguments):
    """
    Try some proofs and exhibit the results.
    """
    for (goal, assumptions) in arguments:
        g = LogicParser().parse(goal)
        alist = [LogicParser().parse(a) for a in assumptions]
        p = Prover9(g, assumptions=alist).prove()
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

def spacer(num=45):
    print '-' * num

if __name__ == '__main__':
    print "Testing configuration"
    spacer()
    test_config()
    print
    print "Testing conversion to Prover9 format"
    spacer()
    test_convert_to_prover9(expressions)
    print
    print "Testing proofs"
    spacer()
    test_prove(arguments)
